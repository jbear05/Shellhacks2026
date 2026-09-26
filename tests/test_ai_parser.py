"""Tests for the AI parser (parsers/ai_parser). None of them call the API: the model's
replies are written by hand, over page text copied from pypdf's output of the real PDFs,
and the API round trip goes through a mock HTTP transport."""

import csv
import json
from pathlib import Path

import pytest

from parsers.ai_parser import __main__ as cli
from parsers.ai_parser import evaluate
from parsers.ai_parser.checks import PageText, check_date, dates_in, locate, normalize_id
from parsers.ai_parser.llm import (
    FALLBACK_BETA, AnswerTooLong, Model, ModelError, ResponseCache, extraction_task, inventory_task,
)
from parsers.ai_parser.pages import Page, make_chunks, parse_page_ranges, render, shifted_chunks
from parsers.ai_parser.pipeline import ParseError, Settings, run, write_outputs
from parsers.ai_parser.records import COLUMNS, REVIEW_COLUMNS
from parsers.ai_parser.schema import DateQuote, Extraction, Fragment, Inventory, PageLabel, Quote

REPO_ROOT = Path(__file__).resolve().parents[1]
DESC_PDF = REPO_ROOT / "Sperry-Tech-Challenge" / "Project Listings" / "Dominion Energy" / (
    "2024-2028-2million-and-above-project-descriptions.pdf")

# pypdf's text of DESC pages 14 and 34, and of Georgia Power pages 177 (the start of
# Table 2) and 231 (TEAMS 19523's detail page, whose need date differs from Table 2's)
DESC_14 = (
    "Project 14 of 44 \n \nDominion Energy South Carolina \nPlanned Transmission Projects $2M and above Total \n"
    "5 Year Budget \n \n   \nStevens Creek - Hooks 115kV/LR Plumb Branch 46kV Rebuilds \n \nProject ID \n6809 E \n"
    " \nProject Description \n9.5 miles. Scope includes rebuilding the 115 and 46 kV lines in this corridor SPDC. \n"
    " \nProject Need \nThis project is required to address end of life and reliability issues on these lines. \n"
    " \nProject Status \nIn Progress \n \nPlanned In-Service Date \n12/31/24 \n \nEstimated Project Cost \n"
    "Previous 2024 2025 2026 2027 2028 Total \n$8,195,543 \n \n$3,550,000 \n \n$0 \n \n$0 $0 $0 $11,745,543 \n"
    " \n   \n*Total Estimated Amount applied to the 2024 Rate Base Calculation \n  "
)
DESC_34 = (
    "Project 34 of 44 \n \nDominion Energy South Carolina \nPlanned Transmission Projects $2M and above Total \n"
    "5 Year Budget \n \n   \nDawson 230kV Sub and Fold-in: Construct and Rebuild \n \nProject ID \n6859  \n \n"
    "Project Description \nConstruct Dawson 230kV substation. Fold in the existing Canadys – Church Creek and "
    "Canadys – Faber \nPlace 230kV lines at the Dawson 230kV substation (phase 1). Rebuild Canadys – Dawson "
    "230kV #1 and \n#2 with B1272 ACSR (phase 2). \n \nProject Need \nLoad growth. \n \nProject Status \n"
    "In Progress \n \nPlanned In-Service Date \n10/1/2025 (phase 1) and 10/1/2026 (phase 2) \n \n"
    "Estimated Project Cost \nPrevious 2024 2025 2026 2027 2028 Total* \n$284,366 $8,014,000 \n \n$45,475,000 \n"
    " \n$39,764,841 \n \n$0 $0 $93,538,207 \n \n \n*Total Estimated Amount applied to 2026 Rate Base Calculation \n  "
)
GA_177 = (
    "CRITICAL ENERGY INFRASTRUCTURE INFORMATION - CONFIDENTIAL. This data is confidential CEII and is subject to "
    "Regulation by CFR Sec. 388.113.  Recipient should be aware that disclosure of this material and its \n"
    "contents shall be handled in accordance with CEII procedures. Any and all duplications of this data must "
    "contain this notification. This document contains non-public transmission information and in accordance "
    "with FERC \npolicy, should not be disclosed to Marketing Function employees. \n \n"
    "2024 GA ITS Ten-Year Plan (2025-2034) Page 7 of 304 \n \nA.  Georgia ITS 10 Year Expansion Plan Projects List \n"
    "Table 2 Georgia ITS 10 Year Plan Project List below briefly lists projects in the 10 Year Expansion Plan "
    "(details for each project are in later sections). \nTable 2 Georgia ITS 10 Year Plan Project List \n"
    "Zone Year TEAMS \nNumber Project Name Need Date \n2024 \nProject \nSponsor Estimated Cost - GPC Estimated "
    "Cost - GTC Estimated Cost - \nMEAG \nEstimated Cost - \nDU Totals \n"
    "219 2025 19523 SAV: CC - HYUNDAI MOTORS \nSAVANNAH AKA. PROJECT EA \n"
    "1/1/2025 SAV REDACTED  REDACTED  REDACTED  REDACTED  REDACTED  \n"
    "212 2025 18670 GTC: BANKS CROSSING - \nPOND FORK 115 KV \n"
    "5/1/2025 GTC REDACTED  REDACTED  REDACTED  REDACTED  REDACTED  \n"
    "216 2025 18492 MITCHELL - NORTH TIFTON \n230KV RECONDUCTOR \n"
    "5/1/2025 GPC REDACTED  REDACTED  REDACTED  REDACTED  REDACTED  \n"
    "214 2025 18153 GTC: BONAIRE PRI-\nECHECONNEE 115 KV \nPARTIAL REBUILD \n"
)
GA_231 = (
    "CRITICAL ENERGY INFRASTRUCTURE INFORMATION - CONFIDENTIAL. This data is confidential CEII and is subject to "
    "Regulation by CFR Sec. 388.113.  Recipient should \nbe aware that disclosure of this material and its contents "
    "shall be handled in accordance with CEII procedures. Any and all duplications of this data must contain this "
    "\nnotification. This document contains non-public transmission information and in accordance with FERC policy, "
    "should not be disclosed to Marketing Function \nemployees. \n \n"
    "2024 GA ITS Ten-Year Plan (2025-2034)       Page 61 of 304 \n \n"
    "SAV: CC - HYUNDAI MOTORS SAVANNAH AKA. PROJECT EA \nTeams # 19523 \n"
    "Need Date 04/25/2025 Start Date 06/01/2022 \nDescription \n \nSupporting Statement \n \n"
    "Change From Previous Ten Year Plan \n \nChange From Previous IRP \n \n"
    "Estimated Cost – GPC   REDACTED \nEstimated Cost – GTC   REDACTED \n"
    "Estimated Cost – MEAG   REDACTED \nEstimated Cost – DU   REDACTED \nEstimated Cost – ITS \n"
    "Assigned*   \nREDACTED \n* The ITS Assigned designation is for parity forecast purposes only \n  \n"
    "Construct a new Hyundai 230kV substation with an eight element 230kV ring bus and four 230/25kV \n"
    "banks. Construct a new Newton Rd 230kV substation with a five element 230kV ring bus and loop \n"
    "through the Little Ogeechee - Meldrim Black and White 230kV lines. Build two new 230kV lines \n"
    "connecting from Hyundai - Newton Rd (12 miles) and Hyundai - Meldrim (10 miles). At Meldrim, add \n"
    "a breaker to accommodate for the new Hyundai line. Install a 115/25kV bank at Interstate Centre \n"
    "and build a new 115kV line from Interstate Centre - Hyundai (2.3 miles) for bridge power. \n \n"
    "REDACTED \nNew Project \nNew Project \nPUBLIC DISCLOSURE "
)
GA_19523_DESCRIPTION = (
    "Construct a new Hyundai 230kV substation with an eight element 230kV ring bus and four 230/25kV banks. "
    "Construct a new Newton Rd 230kV substation with a five element 230kV ring bus and loop through the Little "
    "Ogeechee - Meldrim Black and White 230kV lines. Build two new 230kV lines connecting from Hyundai - Newton Rd "
    "(12 miles) and Hyundai - Meldrim (10 miles). At Meldrim, add a breaker to accommodate for the new Hyundai line. "
    "Install a 115/25kV bank at Interstate Centre and build a new 115kV line from Interstate Centre - Hyundai "
    "(2.3 miles) for bridge power."
)

DESC_PAGES = [Page(14, DESC_14), Page(34, DESC_34)]
GA_PAGES = [Page(177, GA_177), Page(231, GA_231)]
DESC_SETTINGS = Settings(utility="Dominion Energy South Carolina", state="South Carolina", sponsor="DESC")
GA_SETTINGS = Settings(utility="Georgia Power", state="Georgia")


def q(text, page):
    return Quote(text=text, page=page)


def d(text, page, iso):
    return DateQuote(text=text, page=page, iso=iso)


def fragment(project_id, page, **fields):
    empty = {"project_name": None, "sponsor": None, "in_service_date": None, "start_date": None,
             "description": [], "locations": []}
    return Fragment(project_id=q(project_id, page), **{**empty, **fields})


# What a correct reply looks like for each fixture page
DESC_REPLY = [
    fragment(
        "6809 E", 14,
        project_name=q("Stevens Creek - Hooks 115kV/LR Plumb Branch 46kV Rebuilds", 14),
        in_service_date=d("12/31/24", 14, "2024-12-31"),
        description=[q("9.5 miles. Scope includes rebuilding the 115 and 46 kV lines in this corridor SPDC.", 14)],
        locations=[q("Stevens Creek", 14), q("Hooks", 14), q("Plumb Branch", 14)],
    ),
    fragment(
        "6859", 34,
        project_name=q("Dawson 230kV Sub and Fold-in: Construct and Rebuild", 34),
        in_service_date=d("10/1/2025 (phase 1) and 10/1/2026 (phase 2)", 34, "2026-10-01"),
        description=[q(
            "Construct Dawson 230kV substation. Fold in the existing Canadys – Church Creek and Canadys – "
            "Faber Place 230kV lines at the Dawson 230kV substation (phase 1). Rebuild Canadys – Dawson 230kV "
            "#1 and #2 with B1272 ACSR (phase 2).", 34)],
        locations=[q("Dawson", 34), q("Canadys", 34), q("Church Creek", 34), q("Faber Place", 34)],
    ),
]
GA_REPLY = [
    fragment(
        "19523", 177,
        project_name=q("SAV: CC - HYUNDAI MOTORS SAVANNAH AKA. PROJECT EA", 177),
        sponsor=q("SAV", 177),
        in_service_date=d("1/1/2025", 177, "2025-01-01"),
    ),
    fragment(
        "19523", 231,
        project_name=q("SAV: CC - HYUNDAI MOTORS SAVANNAH AKA. PROJECT EA", 231),
        in_service_date=d("04/25/2025", 231, "2025-04-25"),
        start_date=d("06/01/2022", 231, "2022-06-01"),
        description=[q(GA_19523_DESCRIPTION, 231)],
        locations=[q("Hyundai", 231), q("Newton Rd", 231), q("Meldrim", 231), q("Interstate Centre", 231)],
    ),
]


class FakeModel:
    """Replies to each chunk with the fragments whose project ID is on one of its pages."""

    def __init__(self, fragments, labels=None, listed=None):
        self.fragments = fragments
        self.labels = labels or {}
        self.listed = [f.project_id for f in fragments] if listed is None else listed
        self.chunks = []

    def __call__(self, task, chunk):
        numbers = {page.number for page in chunk}
        self.chunks.append((task.name, sorted(numbers)))
        if task.name == "inventory":
            return Inventory(project_ids=[quote for quote in self.listed if quote.page in numbers])
        return Extraction(
            pages=[PageLabel(page=n, kind=self.labels.get(n, "project_detail")) for n in sorted(numbers)],
            projects=[f for f in self.fragments if f.project_id.page in numbers],
        )


def reference_rows(name):
    with (REPO_ROOT / "data" / "processed" / name).open(newline="", encoding="utf-8") as handle:
        return {row["project_id"]: row for row in csv.DictReader(handle)}


def run_rows(pages, fragments, settings, **fake):
    result = run(pages, FakeModel(fragments, **fake), settings)
    return result, {row["project_id"]: row for row in result.rows()}


# ------------------------------------------------------------------------- pages


def test_page_ranges():
    assert parse_page_ranges("3-5, 1,4") == [1, 3, 4, 5]
    with pytest.raises(ValueError):
        parse_page_ranges("5-3")


def test_chunks_share_a_page_and_keep_to_the_budget():
    pages = [Page(n, "x" * 1000) for n in range(1, 13)]
    assert [[p.number for p in chunk] for chunk in make_chunks(pages, 4000)] == [
        [1, 2, 3, 4], [4, 5, 6, 7], [7, 8, 9, 10], [10, 11, 12]]


def test_a_page_over_the_budget_still_gets_a_chunk_with_its_neighbour():
    pages = [Page(1, "x" * 50), Page(2, "x" * 500), Page(3, "x" * 50)]
    assert [[p.number for p in chunk] for chunk in make_chunks(pages, 100)] == [[1], [1, 2], [2, 3]]


def test_shifted_chunks_break_mid_chunk():
    pages = [Page(n, "x" * 1000) for n in range(1, 13)]
    assert [[p.number for p in chunk] for chunk in shifted_chunks(pages, 4000)] == [
        [1, 2, 3], [3, 4, 5, 6], [6, 7, 8, 9], [9, 10, 11, 12]]


def test_render_labels_each_page():
    assert render([Page(3, "a"), Page(4, "b")]) == "=== PAGE 3 ===\na\n\n=== PAGE 4 ===\nb"


# ------------------------------------------------------------------------ checks


def test_quote_matches_despite_line_breaks_case_and_dashes():
    text = PageText(DESC_PAGES)
    # The PDF has en-dashes and a line break here; the value is the page's own spelling, with hyphens
    assert text.find("canadys - church creek and canadys - faber place", 34) == "Canadys - Church Creek and Canadys - Faber Place"


def test_quote_matches_words_pypdf_split_at_a_line_break():
    assert PageText(GA_PAGES).find("GTC: BONAIRE PRI-ECHECONNEE 115 KV", 177) == "GTC: BONAIRE PRI-ECHECONNEE 115 KV"


def test_quote_on_another_page_is_rejected_and_says_where():
    assert locate(PageText(DESC_PAGES), q("Dawson", 14)) == (None, "not on page 14, but on page 34")


def test_made_up_quote_is_rejected():
    assert locate(PageText(DESC_PAGES), q("Thurmond Dam", 14)) == (None, "not on page 14 or any other page")
    assert locate(PageText(DESC_PAGES), q("Dawson", 99))[1] == "cites page 99, which wasn't in this run"


def test_dates_in_every_supported_format():
    assert [str(value) for value in dates_in("12/31/24, 2026-10-01 and December 31, 2027; Dec. 1 2028")] == [
        "2024-12-31", "2026-10-01", "2027-12-31", "2028-12-01"]


def test_date_must_be_one_of_the_dates_in_its_quote():
    assert str(check_date(d("10/1/2025 (phase 1) and 10/1/2026 (phase 2)", 34, "2026-10-01"))[0]) == "2026-10-01"
    assert check_date(d("12/31/24", 14, "2025-12-31")) == (None, "2025-12-31 isn't a date in '12/31/24'")
    assert check_date(d("Summer 2027", 1, None))[0] is None
    assert check_date(d("Q4", 1, "2027-12-31"))[0] is None


def test_ids_lose_the_spaces_around_dashes_only():
    assert normalize_id("06367 A - C, H") == "06367 A-C, H"
    assert normalize_id("1060A, I, L") == "1060A, I, L"


# ---------------------------------------------------------------------- pipeline


def test_desc_rows_match_the_hand_written_parser():
    result, rows = run_rows(DESC_PAGES, DESC_REPLY, DESC_SETTINGS)
    reference = reference_rows("dominion_projects.csv")
    for project_id in ("6809 E", "6859"):
        for column in ("utility", "sponsor", "state", "project_name", "in_service_date", "start_date",
                       "line_miles", "miles_mentioned", "description"):
            assert rows[project_id][column] == reference[project_id][column], (project_id, column)
        assert rows[project_id]["status"] == "VERIFIED"
    assert (rows["6809 E"]["voltage_1"], rows["6809 E"]["voltage_2"]) == ("115000", "46000")
    assert [rows["6859"][f"location_{n}"] for n in (1, 2, 3)] + [rows["6859"]["other_locations"]] == [
        "Dawson", "Canadys", "Church Creek", "Faber Place"]
    assert result.review_rows() == []


def test_georgia_table_row_and_detail_page_merge_and_the_table_wins():
    result, rows = run_rows(GA_PAGES, GA_REPLY, GA_SETTINGS)
    row, reference = rows["19523"], reference_rows("georgia_power_projects.csv")["19523"]
    for column in ("sponsor", "project_name", "in_service_date", "start_date", "voltage_1", "voltage_2",
                   "line_miles", "miles_mentioned", "description"):
        assert row[column] == reference[column], column
    assert row["pages"] == "177; 231"
    # Table 2 says 1/1/2025 and the detail page 04/25/2025: kept as the parser does, but flagged
    assert row["status"] == "NEEDS_REVIEW"
    [problem] = result.review_rows()
    assert problem["field"] == "in_service_date" and "2025-04-25" in problem["reason"]


def test_a_made_up_value_is_left_blank_and_reviewed():
    bad = [fragment("6809 E", 14, project_name=DESC_REPLY[0].project_name,
                    in_service_date=d("12/31/25", 14, "2025-12-31"))]
    result, rows = run_rows(DESC_PAGES[:1], bad, DESC_SETTINGS)
    assert rows["6809 E"]["in_service_date"] == ""
    assert rows["6809 E"]["status"] == "NEEDS_REVIEW"
    assert [(r["field"], r["reason"]) for r in result.review_rows()] == [
        ("in_service_date", "not on page 14 or any other page")]


def test_a_page_read_by_two_chunks_gives_each_problem_once():
    # With a 100-character budget the chunks are [177] and [177, 231], so page 177 is read twice
    table_row = GA_REPLY[0].model_copy(update={"sponsor": q("SAVANNAH ELECTRIC", 177)})
    result = run(GA_PAGES, FakeModel([table_row, GA_REPLY[1]]), Settings(utility="U", state="S", chunk_chars=100))
    assert sorted(r["field"] for r in result.review_rows()) == ["in_service_date", "sponsor"]


def test_a_fragment_whose_id_is_not_on_its_page_is_dropped():
    result, rows = run_rows(DESC_PAGES, [fragment("6809 F", 14)], DESC_SETTINGS, listed=[])
    assert rows == {}
    assert result.review_rows()[0]["reason"].startswith("project ID not on page 14")


def test_the_id_pass_catches_a_skipped_project():
    result, rows = run_rows(DESC_PAGES, DESC_REPLY[:1], DESC_SETTINGS,
                            listed=[q("6809 E", 14), q("6859", 34)])
    assert list(rows) == ["6809 E"]
    reasons = {(r["project_id"], r["reason"]) for r in result.review_rows()}
    assert ("6859", "listed by the ID pass, but no project was read for it") in reasons
    assert ("", "labelled project_detail, but no project was read from it") in reasons


def test_a_project_the_id_pass_missed_needs_review():
    _, rows = run_rows(DESC_PAGES, DESC_REPLY, DESC_SETTINGS, listed=[q("6809 E", 14)])
    assert rows["6859"]["status"] == "NEEDS_REVIEW"
    assert rows["6809 E"]["status"] == "VERIFIED"


def test_swapped_dates_pass_the_quote_check_but_not_the_order_check():
    # Both dates are on the page, so only "start after in-service" can catch the swap
    swapped = [fragment("19523", 231, project_name=GA_REPLY[1].project_name,
                        in_service_date=d("06/01/2022", 231, "2022-06-01"),
                        start_date=d("04/25/2025", 231, "2025-04-25"))]
    result, rows = run_rows(GA_PAGES[1:], swapped, GA_SETTINGS)
    assert rows["19523"]["status"] == "NEEDS_REVIEW"
    assert [(r["field"], r["reason"]) for r in result.review_rows()] == [
        ("start_date", "starts after its in-service date 2022-06-01")]


def test_a_reply_that_is_too_long_is_asked_again_in_halves():
    pages = [Page(n, f"page {n}") for n in range(1, 6)]
    fake = FakeModel([])

    def ask(task, chunk):
        if len(chunk) > 2:
            raise AnswerTooLong("too long")
        return fake(task, chunk)

    run(pages, ask, Settings(utility="U", state="S", chunk_chars=100, inventory=False))
    assert [numbers for _, numbers in fake.chunks] == [[1, 2], [2, 3], [3, 4], [4, 5]]


def test_a_pdf_without_text_is_refused():
    with pytest.raises(ParseError, match="OCR"):
        run([Page(1, "  \n ")], FakeModel([]), DESC_SETTINGS)


def test_outputs_have_the_documented_columns(tmp_path):
    result = run(DESC_PAGES, FakeModel(DESC_REPLY[:1], listed=[q("6809 E", 14), q("6859", 34)]), DESC_SETTINGS)
    projects_csv, review_csv, evidence_json = write_outputs(result, tmp_path, "desc_ai", {"model": "test"})
    with projects_csv.open(newline="", encoding="utf-8") as handle:
        assert csv.DictReader(handle).fieldnames == COLUMNS
    with review_csv.open(newline="", encoding="utf-8") as handle:
        assert csv.DictReader(handle).fieldnames == REVIEW_COLUMNS
    report = json.loads(evidence_json.read_text(encoding="utf-8"))
    assert report["projects"][0]["fields"]["in_service_date"] == {"value": "2024-12-31", "quote": "12/31/24", "page": 14}


# ------------------------------------------------------------------ cache and API


def sse(events):
    return "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events).encode()


def reply_events(text, stop_reason="end_turn"):
    return [
        {"type": "message_start", "message": {
            "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5", "content": [],
            "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 1200, "output_tokens": 1}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None},
         "usage": {"output_tokens": 300}},
        {"type": "message_stop"},
    ]


def mock_api(cache_dir, events):
    """A Model whose client talks to a fake server; returns it and the requests it received."""
    import anthropic  # takes over a second, so only the slow tests import it
    import httpx2

    received = []

    def handle(request):
        received.append(request)
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=sse(events))

    client = anthropic.Anthropic(api_key="test-key", max_retries=0,
                                 http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handle)))
    return Model(ResponseCache(cache_dir), client=client), received


@pytest.mark.slow
def test_api_request_and_reply_round_trip(tmp_path):
    reply = Extraction(pages=[PageLabel(page=14, kind="project_detail")], projects=DESC_REPLY[:1])
    model, received = mock_api(tmp_path, reply_events(reply.model_dump_json()))
    chunk = [Page(14, DESC_14)]

    assert model.ask(extraction_task("medium"), chunk) == reply
    assert model.ask(extraction_task("medium"), chunk) == reply  # the second comes from the cache
    assert len(received) == 1 and len(list(tmp_path.glob("*.json"))) == 1
    assert (model.requests, model.usage["output_tokens"]) == (1, 300)

    request = received[0]
    body = json.loads(request.content)
    assert FALLBACK_BETA in request.headers["anthropic-beta"]
    assert body["model"] == "claude-opus-5" and body["stream"] is True and body["fallbacks"] == "default"
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"]["effort"] == "medium"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["messages"] == [{"role": "user", "content": "=== PAGE 14 ===\n" + DESC_14}]


@pytest.mark.slow
def test_a_cut_off_reply_raises_and_is_not_cached(tmp_path):
    model, _ = mock_api(tmp_path, reply_events('{"pages": [', stop_reason="max_tokens"))
    with pytest.raises(AnswerTooLong):
        model.ask(inventory_task(), [Page(14, DESC_14)])
    assert list(tmp_path.glob("*.json")) == []


def test_cache_key_changes_with_the_pages_the_model_or_the_effort():
    key = ResponseCache.key
    base = key("claude-opus-5", extraction_task("high"), "text")
    assert base == key("claude-opus-5", extraction_task("high"), "text")
    assert len({base, key("claude-opus-5", extraction_task("high"), "other"),
                key("claude-sonnet-5", extraction_task("high"), "text"),
                key("claude-opus-5", extraction_task("low"), "text")}) == 4


def test_offline_without_a_cached_reply_fails(tmp_path):
    model = Model(ResponseCache(tmp_path), offline=True, client=object())
    with pytest.raises(ModelError, match="--offline"):
        model.ask(inventory_task(), [Page(14, DESC_14)])


# ------------------------------------------------------------------- command line


@pytest.mark.skipif(not DESC_PDF.is_file(), reason="Dominion project descriptions PDF not present")
def test_dry_run_counts_requests_without_calling_the_api(tmp_path, capsys):
    args = [str(DESC_PDF), "--utility", "U", "--state", "S", "--prefix", "t", "--pages", "1-3",
            "--cache-dir", str(tmp_path), "--out-dir", str(tmp_path)]
    assert cli.main([*args, "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "extract: 1 requests (0 cached)" in output and "inventory:" in output
    assert cli.main([*args, "--offline"]) == 1  # nothing cached, and --offline never asks
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------- evaluation


def test_evaluation_counts_each_outcome_and_verified_rows_that_are_wrong():
    reference = {"A": {"project_id": "A", "project_name": "Okatie - Bluffton", "in_service_date": "2025-01-01",
                       "line_miles": "18.0", "location_1": "Okatie", "location_2": "Bluffton"},
                 "B": {"project_id": "B", "project_name": "X", "in_service_date": "2026-01-01",
                       "line_miles": "", "location_1": "", "location_2": ""}}
    ai = {"A": {"project_id": "A", "project_name": "OKATIE – BLUFFTON", "in_service_date": "2025-01-01",
                "line_miles": "18", "location_1": "Bluffton", "location_2": "Okatie", "status": "VERIFIED"},
          "B": {"project_id": "B", "project_name": "X", "in_service_date": "2027-01-01",
                "line_miles": "2", "location_1": "", "location_2": "", "status": "VERIFIED"},
          "C": {"project_id": "C", "status": "VERIFIED"}}
    report = evaluate.compare(ai, reference, list(reference["A"]))
    assert report.extra == ["C"] and report.missing == [] and report.matched == 2
    assert report.scores["project_name"]["same"] == 2
    assert report.scores["in_service_date"]["differ"] == 1
    assert report.scores["line_miles"] == {"same": 1, "only in AI": 1}
    assert report.scores["locations"]["same"] == 2
    assert (report.verified, report.verified_but_wrong) == (2, ["B"])
