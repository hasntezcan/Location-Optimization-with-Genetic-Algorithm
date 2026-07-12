"""Scenario JSON loading.

This module owns only "is this file parseable JSON shaped like an object,"
nothing more. It does not own:

- full scenario schema/field validation (``scenario.validation``, Phase 1B)
- current-network seed validation (``scenario.validation``, Phase 1B)
- optimizer-input derivation (``scenario.optimizer_inputs``, Phase 1B+)
- benchmark logic (``benchmark.current_network``, later batch)
- CLI printing or exit codes (the thin wrapper scripts, when migrated)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_scenario_json(path: Path) -> dict[str, Any]:
    """Load and parse a scenario JSON file.

    Raises ``FileNotFoundError`` if the file does not exist, ``json.JSONDecodeError``
    if it is not valid JSON, and ``ValueError`` if the parsed root is not an object.
    """
    if not path.exists():
        raise FileNotFoundError(f"Scenario file does not exist: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Scenario JSON root must be an object.")
    return data
