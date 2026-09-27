from __future__ import annotations

import hashlib
import sys
import threading
import uuid
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_loader import _normalize_projects
from parsers.ai_parser.__main__ import DEFAULT_CACHE_DIR
from parsers.ai_parser.llm import DEFAULT_MODEL, Model, ResponseCache
from parsers.ai_parser.pages import read_pages
from parsers.ai_parser.pipeline import Settings, run, write_outputs

OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "ai" / "frontend"
UPLOAD_DIR = Path("/tmp") / "shellhacks2026" / "uploads"

_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class ParseInput:
    utility: str
    state: str
    filename: str
    content: bytes


def start_job(inputs: Sequence[ParseInput]) -> str:
    job_id = uuid.uuid4().hex
    with _LOCK:
        _JOBS[job_id] = {
            "status": "running",
            "message": "Queued parse job.",
            "progress": 0.0,
            "error": "",
            "projects_csv": b"",
            "row_count": 0,
            "project_count": 0,
            "outputs": [],
        }
    _EXECUTOR.submit(_run_job, job_id, list(inputs))
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        return dict(job)


def clear_job(job_id: str) -> None:
    with _LOCK:
        _JOBS.pop(job_id, None)


def _run_job(job_id: str, inputs: list[ParseInput]) -> None:
    try:
        _update(job_id, message="Preparing parser run.", progress=5.0)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        normalized_frames: list[pd.DataFrame] = []
        output_paths: list[str] = []
        total = max(1, len(inputs))
        for index, parse_input in enumerate(inputs, start=1):
            start = 5.0 + ((index - 1) / total) * 85.0
            end = 5.0 + (index / total) * 85.0
            _update(
                job_id,
                message=f"Parsing {parse_input.utility} ({index}/{total}).",
                progress=start,
            )
            projects_path = _parse_one(parse_input, job_id)
            output_paths.append(str(projects_path))
            frame = pd.read_csv(projects_path, keep_default_na=False, dtype=str)
            normalized = _normalize_projects(frame, parse_input.utility, projects_path.name)
            if normalized is None or normalized.empty:
                raise ValueError(
                    f"{parse_input.utility}: parser output did not include any usable projects."
                )
            normalized_frames.append(normalized)
            _update(
                job_id,
                message=f"Finished {parse_input.utility} ({index}/{total}).",
                progress=end,
            )

        projects = pd.concat(normalized_frames, ignore_index=True, sort=False)
        if "Project ID" in projects.columns:
            projects = projects.drop_duplicates(subset=["Project ID"], keep="first")

        combined_path = OUTPUT_DIR / f"{job_id}_projects.csv"
        projects.to_csv(combined_path, index=False)

        _update(
            job_id,
            status="completed",
            message="AI parser completed.",
            progress=100.0,
            projects_csv=projects.to_csv(index=False).encode("utf-8"),
            row_count=len(projects),
            project_count=len(projects),
            outputs=output_paths + [str(combined_path)],
        )
    except Exception as exc:
        _update(
            job_id,
            status="failed",
            message="AI parser failed.",
            progress=100.0,
            error=str(exc),
        )


def _parse_one(parse_input: ParseInput, job_id: str) -> Path:
    upload_dir = UPLOAD_DIR / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{_slug(parse_input.utility)}.pdf"
    pdf_path.write_bytes(parse_input.content)

    pages = read_pages(pdf_path)
    model = Model(ResponseCache(DEFAULT_CACHE_DIR), DEFAULT_MODEL, offline=False, fallback=True)
    settings = Settings(
        utility=parse_input.utility,
        state=parse_input.state,
        sponsor="",
        workers=1,
    )
    result = run(pages, model.ask, settings)
    source_hash = hashlib.sha256(parse_input.content).hexdigest()
    prefix = f"{_slug(parse_input.utility)}_{job_id[:8]}"
    written = write_outputs(
        result,
        OUTPUT_DIR,
        prefix,
        run_info={
            "source_pdf": parse_input.filename,
            "pdf_sha256": source_hash,
            "pages": "all",
            "model": DEFAULT_MODEL,
            "answered_by": dict(model.answered_by),
        },
    )
    return written[0]


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    compact = "_".join(part for part in cleaned.split("_") if part)
    return compact or "utility"


def projects_from_job(job: dict[str, Any]) -> pd.DataFrame:
    payload = job.get("projects_csv", b"")
    if not payload:
        return pd.DataFrame()
    return pd.read_csv(BytesIO(payload))


def _update(job_id: str, **changes: Any) -> None:
    with _LOCK:
        if job_id not in _JOBS:
            return
        _JOBS[job_id].update(changes)
