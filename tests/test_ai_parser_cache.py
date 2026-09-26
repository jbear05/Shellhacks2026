"""Split-cache regressions, with model calls replaced by in-process replies."""

from __future__ import annotations

import re

import pytest

from parsers.ai_parser.__main__ import INPUT_TOKENS, dry_run
from parsers.ai_parser.llm import AnswerTooLong, Model, ModelError, ResponseCache, extraction_task, inventory_task
from parsers.ai_parser.pages import Page, render
from parsers.ai_parser.pipeline import Settings, _ask_chunk, run


def reply(task, numbers):
    output = ({"pages": [{"page": number, "kind": "other"} for number in numbers], "projects": []}
              if task.name == "extract" else {"project_ids": []})
    return {"model": "claude-opus-5", "usage": {"input_tokens": 10, "output_tokens": 5}, "output": output}


def split_model(tmp_path, monkeypatch):
    model = Model(ResponseCache(tmp_path))
    calls = []

    def call(task, text):
        numbers = tuple(int(number) for number in re.findall(r"=== PAGE (\d+) ===", text))
        calls.append((task.name, numbers))
        if len(numbers) > 1:
            raise AnswerTooLong("mock reply exceeded its limit")
        return reply(task, numbers)

    monkeypatch.setattr(model, "_call", call)
    return model, calls


def forbid_call(*args):
    pytest.fail("the replay must not call the model")


@pytest.mark.parametrize("task_factory", [extraction_task, inventory_task])
@pytest.mark.parametrize("page_count", [2, 5])
def test_split_replies_replay_online_and_offline(tmp_path, monkeypatch, task_factory, page_count):
    pages = [Page(number, f"page {number}") for number in range(1, page_count + 1)]
    task = task_factory()
    model, calls = split_model(tmp_path, monkeypatch)

    first = _ask_chunk(model.ask, task, pages)
    assert {chunk[0].number for chunk, _ in first} == set(range(1, page_count + 1))
    assert all(len(chunk) == 1 for chunk, _ in first)
    assert len(calls) == len(set(calls))  # overlapping halves reuse the shared pages
    assert model.is_cached(task, pages)
    assert model.cache.get(model.cache.key(model.model, task, render(pages)))["split"] is True

    for offline in (False, True):
        replay = Model(ResponseCache(tmp_path), offline=offline)
        monkeypatch.setattr(replay, "_call", forbid_call)
        assert _ask_chunk(replay.ask, task, pages) == first
        assert replay.requests == 0


def test_both_pipeline_passes_replay_split_replies(tmp_path, monkeypatch):
    pages = [Page(1, "first"), Page(2, "second")]
    settings = Settings(utility="U", state="S")
    model, calls = split_model(tmp_path, monkeypatch)
    first = run(pages, model.ask, settings)

    replay = Model(ResponseCache(tmp_path), offline=True)
    monkeypatch.setattr(replay, "_call", forbid_call)
    assert run(pages, replay.ask, settings) == first
    assert {name for name, _ in calls} == {"extract", "inventory"}


def test_dry_run_counts_distinct_nested_leaves_and_missing_replies(tmp_path, monkeypatch, capsys):
    pages = [Page(number, f"page {number}") for number in range(1, 6)]
    task = extraction_task()
    settings = Settings(utility="U", state="S", inventory=False)
    model, _ = split_model(tmp_path, monkeypatch)
    _ask_chunk(model.ask, task, pages)
    monkeypatch.setattr(model, "_call", forbid_call)

    dry_run(pages, settings, model)
    assert "extract: 5 requests (5 cached); the rest send about 0 input tokens" in capsys.readouterr().out

    missing = [pages[2]]
    key = model.cache.key(model.model, task, render(missing))
    (tmp_path / f"{key}.json").unlink()
    assert not model.is_cached(task, pages)
    dry_run(pages, settings, model)
    per_request, chars_per_token = INPUT_TOKENS["extract"]
    tokens = per_request + len(render(missing)) / chars_per_token
    assert (f"extract: 5 requests (4 cached); the rest send about {tokens:,.0f} input tokens"
            in capsys.readouterr().out)

    offline = Model(ResponseCache(tmp_path), offline=True)
    monkeypatch.setattr(offline, "_call", forbid_call)
    with pytest.raises(ModelError, match="no cached extract reply for pages 3"):
        _ask_chunk(offline.ask, task, pages)


def test_failed_child_is_retried_without_repaying_the_parent(tmp_path, monkeypatch, capsys):
    pages = [Page(1, "first"), Page(2, "second")]
    task = extraction_task()
    model = Model(ResponseCache(tmp_path))

    def interrupted_call(task, text):
        if text == render(pages):
            raise AnswerTooLong("split this request")
        if text == render(pages[1:]):
            raise ModelError("temporary failure")
        return reply(task, [1])

    monkeypatch.setattr(model, "_call", interrupted_call)
    with pytest.raises(ModelError, match="temporary failure"):
        _ask_chunk(model.ask, task, pages)
    assert not model.is_cached(task, pages)
    assert model.cache.get(model.cache.key(model.model, task, render(pages[1:]))) is None
    dry_run(pages, Settings(utility="U", state="S", inventory=False), model)
    assert "extract: 2 requests (1 cached)" in capsys.readouterr().out

    resumed = Model(ResponseCache(tmp_path))
    calls = []

    def resumed_call(task, text):
        calls.append(text)
        return reply(task, [2])

    monkeypatch.setattr(resumed, "_call", resumed_call)
    _ask_chunk(resumed.ask, task, pages)
    assert calls == [render(pages[1:])]
    assert resumed.is_cached(task, pages)


@pytest.mark.parametrize("error,page_count", [(ModelError("declined"), 2), (AnswerTooLong("too long"), 1)])
def test_unsplittable_and_ordinary_failures_are_not_cached(tmp_path, monkeypatch, error, page_count):
    model = Model(ResponseCache(tmp_path))

    def fail(*args):
        raise error

    monkeypatch.setattr(model, "_call", fail)
    with pytest.raises(type(error), match=str(error)):
        model.ask(extraction_task(), [Page(number, "text") for number in range(1, page_count + 1)])
    assert list(tmp_path.iterdir()) == []
