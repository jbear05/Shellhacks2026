"""The prompts, the Claude and Gemini API calls and the response cache.

A model whose name starts with "gemini-" goes to Google's Gemini API; any other goes to
Claude. Every reply is cached under a hash of what shaped it (model, prompt, schema,
effort and the pages' text), so running again costs nothing unless one of those changed,
and teammates without an API key can rebuild the CSV from the cache with --offline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from parsers.ai_parser.pages import Page, render, split_chunk
from parsers.ai_parser.schema import Extraction, Inventory

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"
MAX_TOKENS = 64_000  # replies are streamed, so a long one doesn't time out
# If the model declines a request on policy grounds, the API retries it on its default
# fallback model instead of failing. Transmission plans shouldn't trigger it. Claude only.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Dollars per million input and output tokens, only for the cost line in the log. Claude's
# are from 2026-06, Gemini's from Google's page updated 2026-09-24 (both Flash prices
# double on 2027-01-01). Gemini bills its thinking tokens as output.
PRICES = {
    "claude-opus-5": (5.0, 25.0), "claude-sonnet-5": (2.0, 10.0),
    "gemini-3.8-flash": (0.75, 3.75), "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.1-pro-preview": (2.0, 12.0),
}
# Gemini 3 models take a thinking level instead of Claude's effort. They stop at "high".
THINKING_LEVELS = {"low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}
# Tries per Gemini request. Busy models answer 503 for minutes at a time, so the waits
# (1, 2, 4 ... seconds, then 60 each) add up to about 4 minutes before a request fails.
GEMINI_ATTEMPTS = 10

EXTRACT_PROMPT = """\
You copy the planned projects out of pages of a utility's transmission planning document, as JSON. The pages are pypdf's text extraction of a PDF. Each page starts with a line "=== PAGE n ===", and n is the page number to cite. Text extraction can scramble a layout: a form may list all of its labels before all of its values, table rows can wrap over several lines, and banners, headers and footers repeat on every page.

A program checks your answer against this same text, so:
- Copy, don't rewrite. Every "text" must appear on the page you cite exactly as it's written there, with the same spelling, capitals, punctuation and typos. A line break may become a single space. Never correct, expand, combine or summarize.
- Leave out what isn't printed. If a project doesn't state a field, use null or an empty list. Don't work out, estimate or guess a value.
- Only cite the pages you were given.

Projects
- A project is a planned transmission line, substation or similar piece of work with its own identifier: a project ID, TEAMS number, work order number or similar.
- Skip projects in lists of cancelled, completed or removed projects.
- A project can appear in several places, such as a row of a project list and, pages later, its own detail page. Return one entry for each place, each with the project ID and the fields printed there.
- If a project runs onto the next page, keep it in one entry. If it's cut off at the last page you were given, return what you can see; another request reads the next pages.

Fields
- project_id: the identifier alone, without its label ("Teams #", "Project ID").
- project_name: the project's title.
- sponsor: the company, or company code, named as this project's sponsor or owner. Only when it's printed for this project.
- in_service_date: the planned in-service date or need date. "text" is the date as printed, and "iso" is the same date as YYYY-MM-DD. If several dates are given, as for a project built in phases, copy all of them into "text" and give the last one as "iso". If the date has no day (only a month or a year), set "iso" to null.
- start_date: the construction or project start date, only when one is printed. Same format.
- description: the scope of work. If it continues onto the next page, give one piece per page, leaving out the banners, headers and footers between them. Leave out other sections, such as the need, justification or status.
- locations: the named places the project is at or connects, taken from its title and description: substations, switching stations, plants, towns, customers' sites. Copy each name once, without its voltage and without words like "Substation", "Sub" or "Tap".

pages: label every page you were given as "project_list" (a table or list of several projects), "project_detail" (a page about one or a few projects), "excluded_list" (cancelled, completed or removed projects) or "other".
"""

INVENTORY_PROMPT = """\
You read pages of a utility's transmission planning document: pypdf's text extraction of a PDF, where each page starts with a line "=== PAGE n ===".

List the identifier of every planned project on these pages: its project ID, TEAMS number, work order number or similar. Copy each identifier exactly as printed, without its label, and cite a page it's printed on; a program checks both. List each project once. Skip lists of cancelled, completed or removed projects.
"""


@dataclass(frozen=True)
class Task:
    name: str
    system: str
    output: type[BaseModel]
    effort: str  # "low" to "max"; how much the model thinks before answering


def extraction_task(effort: str = "high") -> Task:
    return Task("extract", EXTRACT_PROMPT, Extraction, effort)


def inventory_task() -> Task:
    return Task("inventory", INVENTORY_PROMPT, Inventory, "low")  # listing IDs needs little thought


class ModelError(Exception):
    """No usable reply: the request failed, the model declined, or the reply isn't in the schema."""


class AnswerTooLong(ModelError):
    """The reply hit MAX_TOKENS. Ask again with fewer pages."""


class ResponseCache:
    """One JSON file per reply or split decision, hashed by everything that shaped it."""

    def __init__(self, directory: Path):
        self.directory = directory

    @staticmethod
    def key(model: str, task: Task, text: str) -> str:
        shaping = {
            "model": model,
            "system": task.system,
            "schema": task.output.model_json_schema(),  # pydantic is pinned, so this is stable
            "effort": task.effort,
            "text": text,
        }
        return hashlib.sha256(json.dumps(shaping, sort_keys=True).encode("utf-8")).hexdigest()[:32]

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # don't quietly pay for it again; someone should look
            raise ModelError(f"cached reply {path} is broken ({exc}); delete it to ask again") from exc

    def put(self, key: str, entry: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(entry, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temporary, path)  # a run stopped mid-write leaves no half-written reply


class Model:
    """Answers a task for a chunk of pages: from the cache when it can, otherwise from the API.

    Oversized multi-page requests keep a split marker so reruns reuse their children.
    Other failures aren't cached, so they're retried on the next run.
    """

    def __init__(self, cache: ResponseCache, model: str = DEFAULT_MODEL, *,
                 offline: bool = False, fallback: bool = True, client: Any = None):
        self.cache = cache
        self.model = model
        self.offline = offline
        self.fallback = fallback
        self._client = client
        self._lock = threading.Lock()
        self.requests = 0  # sent this run; cache hits don't count
        self.usage: dict[str, Counter[str]] = {}  # tokens those requests used, by the model that answered
        self.answered_by: Counter[str] = Counter()  # every reply used this run, cached or not

    def is_cached(self, task: Task, chunk: Sequence[Page]) -> bool:
        entry = self.cache.get(self.cache.key(self.model, task, render(chunk)))
        if entry is not None and entry.get("split") is True:
            return all(self.is_cached(task, child) for child in split_chunk(chunk))
        return entry is not None

    def request_chunks(self, task: Task, chunks: Sequence[Sequence[Page]]) -> list[list[Page]]:
        """Expand known splits into distinct leaf requests, including missing replies."""
        leaves: list[list[Page]] = []
        seen: set[str] = set()

        def visit(chunk: Sequence[Page]) -> None:
            key = self.cache.key(self.model, task, render(chunk))
            if key in seen:
                return
            seen.add(key)
            entry = self.cache.get(key)
            if entry is not None and entry.get("split") is True:
                for child in split_chunk(chunk):
                    visit(child)
            else:
                leaves.append(list(chunk))

        for chunk in chunks:
            visit(chunk)
        return leaves

    def ask(self, task: Task, chunk: Sequence[Page]) -> BaseModel:
        text = render(chunk)
        key = self.cache.key(self.model, task, text)
        entry = self.cache.get(key)
        if entry is not None and entry.get("split") is True:
            raise AnswerTooLong(f"cached split for {task.name} pages {_span(chunk)}")
        if entry is None:
            if self.offline:
                raise ModelError(f"no cached {task.name} reply for pages {_span(chunk)}, and --offline was given")
            log.info("Asking %s to %s pages %s", self.model, task.name, _span(chunk))
            metadata = {"task": task.name, "pages": [page.number for page in chunk]}
            try:
                reply = self._call(task, text)
            except AnswerTooLong:
                if len(chunk) > 1:
                    self.cache.put(key, {**metadata, "split": True})
                raise
            entry = {**metadata, **reply}
            self.cache.put(key, entry)
            with self._lock:
                self.usage.setdefault(entry["model"], Counter()).update(entry["usage"])
                self.requests += 1
        with self._lock:
            self.answered_by[entry["model"]] += 1
        try:
            return task.output.model_validate(entry["output"])
        except ValidationError as exc:
            raise ModelError(f"cached reply {key} doesn't match the schema: {exc}") from exc

    def tokens(self, kind: str) -> int:
        return sum(usage[kind] for usage in self.usage.values())

    def cost(self) -> float | None:
        """Dollars for this run's requests, at each answering model's prices; None if one isn't in PRICES."""
        total = 0.0
        for model, usage in self.usage.items():
            if model not in PRICES:
                return None
            total += (usage["input_tokens"] * PRICES[model][0] + usage["output_tokens"] * PRICES[model][1]) / 1e6
        return total

    @property
    def is_gemini(self) -> bool:
        return self.model.startswith("gemini-")

    def _get_client(self) -> Any:
        with self._lock:
            if self._client is None:  # the SDKs are only needed when a reply isn't cached
                if self.is_gemini:
                    from google import genai
                    from google.genai import types

                    try:  # retries rate limits, server errors and dropped connections
                        self._client = genai.Client(http_options=types.HttpOptions(
                            retry_options=types.HttpRetryOptions(attempts=GEMINI_ATTEMPTS, max_delay=60)))
                    except ValueError as exc:  # the SDK found no key
                        raise ModelError("no API key: set GEMINI_API_KEY") from exc
                else:
                    import anthropic

                    self._client = anthropic.Anthropic(max_retries=6)  # retries rate limits and server errors
            return self._client

    def _call(self, task: Task, text: str) -> dict[str, Any]:
        if self.is_gemini:
            return self._call_gemini(task, text)
        import anthropic

        client = self._get_client()
        options: dict[str, Any] = {"betas": [FALLBACK_BETA], "fallbacks": "default"} if self.fallback else {}
        try:
            with client.beta.messages.stream(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=task.system,
                messages=[{"role": "user", "content": text}],
                thinking={"type": "adaptive"},
                output_config={
                    "effort": task.effort,
                    "format": {"type": "json_schema", "schema": anthropic.transform_schema(task.output)},
                },
                **options,
            ) as stream:
                message = stream.get_final_message()
        except anthropic.APIError as exc:
            raise ModelError(f"API request failed: {exc}") from exc
        except TypeError as exc:
            if "authentication" not in str(exc):
                raise
            # The SDK raises TypeError when it finds no credentials at all
            raise ModelError("no API key: set ANTHROPIC_API_KEY or run `ant auth login`") from exc
        return read_reply(message, task)

    def _call_gemini(self, task: Task, text: str) -> dict[str, Any]:
        import httpx
        from google.genai import errors, types

        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=task.system,
            max_output_tokens=MAX_TOKENS,  # the model's thinking counts toward it too
            response_mime_type="application/json",
            response_json_schema=task.output.model_json_schema(),
            thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVELS[task.effort]),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # no tools
        )
        try:
            chunks = list(client.models.generate_content_stream(model=self.model, contents=text, config=config))
        except (errors.APIError, httpx.HTTPError) as exc:
            raise ModelError(f"API request failed: {exc}") from exc
        return read_gemini_reply(chunks, task, self.model)


def read_reply(message: Any, task: Task) -> dict[str, Any]:
    """The cache entry for a finished reply, or ModelError if it can't be used."""
    if message.stop_reason == "max_tokens":
        raise AnswerTooLong(f"reply longer than {MAX_TOKENS} tokens")
    if message.stop_reason == "refusal":
        category = getattr(getattr(message, "stop_details", None), "category", None)
        raise ModelError(f"the model declined the request (category: {category})")
    if message.stop_reason != "end_turn":
        raise ModelError(f"unexpected stop reason {message.stop_reason!r}")
    text = ""
    for block in message.content:
        if block.type == "fallback":  # text before a fallback block is the declining model's
            text = ""
        elif block.type == "text":
            text += block.text
    try:
        output = task.output.model_validate_json(text)
    except ValidationError as exc:
        raise ModelError(f"reply doesn't match the schema: {exc}") from exc
    return {
        "model": message.model,  # can differ from the one asked for if the fallback answered
        "usage": {"input_tokens": message.usage.input_tokens, "output_tokens": message.usage.output_tokens},
        "output": output.model_dump(mode="json"),
    }


def read_gemini_reply(chunks: Sequence[Any], task: Task, model: str) -> dict[str, Any]:
    """The cache entry for a finished Gemini reply, streamed as chunks, or ModelError if it can't be used.

    The last chunk carries the stop reason and the token counts.
    """
    if not chunks:
        raise ModelError("the API sent an empty reply")
    last = chunks[-1]
    if not last.candidates:
        feedback = last.prompt_feedback
        reason = feedback.block_reason.value if feedback and feedback.block_reason else "no reason given"
        raise ModelError(f"the API blocked the request ({reason})")
    stop = last.candidates[0].finish_reason
    stop = stop.value if stop is not None else None
    if stop == "MAX_TOKENS":
        raise AnswerTooLong(f"reply longer than {MAX_TOKENS} tokens")
    if stop != "STOP":  # SAFETY, RECITATION, PROHIBITED_CONTENT and the like
        raise ModelError(f"unexpected stop reason {stop!r}")
    text = "".join(chunk.text or "" for chunk in chunks)  # .text leaves out the model's thinking
    try:
        output = task.output.model_validate_json(text)
    except ValidationError as exc:
        raise ModelError(f"reply doesn't match the schema: {exc}") from exc
    usage = last.usage_metadata

    def count(field: str) -> int:
        return getattr(usage, field, None) or 0

    return {
        "model": model,  # Gemini has no fallback, so the model asked is the one that answered
        "model_version": last.model_version,
        "usage": {
            "input_tokens": count("prompt_token_count"),
            # thinking is billed as output, as Claude's is
            "output_tokens": count("candidates_token_count") + count("thoughts_token_count"),
        },
        "output": output.model_dump(mode="json"),
    }


def _span(chunk: Sequence[Page]) -> str:
    return f"{chunk[0].number}-{chunk[-1].number}" if len(chunk) > 1 else str(chunk[0].number)
