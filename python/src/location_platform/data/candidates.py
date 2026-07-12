"""Reusable candidate CSV loading and structural validation.

This module owns only generic candidate-table loading mechanics. It does
not decide which candidates "count" for any business purpose (e.g. which
rows represent existing facilities) — that is scenario-domain logic that
stays in the scenario package, not here. It never mutates the source CSV,
never infers existing facilities from any column, and never treats
``nearby_locker_count`` as facility presence (it does not read that column
at all).

Candidate IDs are always returned as the stable ``id`` column values, in
file order, never as row offsets.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from location_platform.common.parsing import parse_int, require_fields


def load_candidate_rows(
    csv_path: Path,
    *,
    required_columns: Sequence[str] = ("id",),
) -> list[dict[str, str]]:
    """Load candidate CSV rows in file order as raw string dicts.

    Validates that every column in ``required_columns`` is present in the
    header. Does not coerce or interpret any column value — callers parse
    what they need from the returned rows.
    """
    if not csv_path.is_file():
        raise FileNotFoundError(f"Candidate CSV does not exist: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        require_fields(fieldnames, required_columns, f"Candidate CSV ({csv_path})")
        return [dict(row) for row in reader]


def parse_candidate_ids(rows: list[dict[str, str]]) -> list[int]:
    """Parse the ``id`` column from already-loaded rows, preserving row order."""
    return [
        parse_int(row["id"], f"Candidate row {index + 2} `id`")
        for index, row in enumerate(rows)
    ]


def validate_candidate_id_uniqueness(candidate_ids: Sequence[int]) -> None:
    """Raise ``ValueError`` if any candidate ID appears more than once."""
    seen: set[int] = set()
    duplicates: list[int] = []
    for candidate_id in candidate_ids:
        if candidate_id in seen and candidate_id not in duplicates:
            duplicates.append(candidate_id)
        seen.add(candidate_id)
    if duplicates:
        raise ValueError(f"Duplicate candidate IDs found: {sorted(duplicates)}.")


def load_candidate_ids(csv_path: Path) -> list[int]:
    """Load, parse, and uniqueness-validate candidate IDs from a candidate CSV.

    Returns candidate IDs in file order (never row offsets). Callers that
    only need membership testing can wrap the result in ``set(...)``.
    """
    rows = load_candidate_rows(csv_path, required_columns=("id",))
    candidate_ids = parse_candidate_ids(rows)
    validate_candidate_id_uniqueness(candidate_ids)
    return candidate_ids
