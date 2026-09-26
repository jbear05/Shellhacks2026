"""What the model sends back, as Pydantic models. The JSON schema the API enforces is
built from these, so a reply always has this shape."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Quote(BaseModel):
    """Text copied exactly from one page."""

    text: str = Field(description="Copied character for character from the page")
    page: int = Field(description="The n of the '=== PAGE n ===' line the text is under")


class DateQuote(Quote):
    iso: str | None = Field(description="The date as YYYY-MM-DD, or null if the printed date has no day")


class Fragment(BaseModel):
    """One project as it appears in one place, such as a table row or a detail page."""

    project_id: Quote
    project_name: Quote | None
    sponsor: Quote | None
    in_service_date: DateQuote | None
    start_date: DateQuote | None
    description: list[Quote] = Field(description="The scope of work, one piece per page it's on")
    locations: list[Quote]


PageKind = Literal["project_list", "project_detail", "excluded_list", "other"]


class PageLabel(BaseModel):
    page: int
    kind: PageKind


class Extraction(BaseModel):
    """The extraction pass's reply for one chunk of pages."""

    pages: list[PageLabel]
    projects: list[Fragment]


class Inventory(BaseModel):
    """The ID pass's reply for one chunk of pages: only the project IDs, as a cross-check."""

    project_ids: list[Quote]
