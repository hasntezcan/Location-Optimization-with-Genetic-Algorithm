"""Shared numeric parsing and structural type-checking helpers.

Every function here raises on invalid input rather than collecting errors
into a list. Callers that want error-collecting behavior (e.g. a scenario
validator that reports every problem at once instead of failing on the
first one) catch these exceptions at their own call site and append to
their own error list — this module intentionally provides one behavior
per operation, not a raising and a collecting variant of everything.

No scenario-specific validation rules live here — only structural/type
checks that make sense for any dict, mapping, or numeric value.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping


def parse_int(value: Any, label: str) -> int:
    """Parse ``value`` as an integer, raising ``ValueError`` with context on failure."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer, got {value!r}.") from exc


def parse_float(value: Any, label: str) -> float:
    """Parse ``value`` as a float, raising ``ValueError`` with context on failure."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a float, got {value!r}.") from exc


def finite_float(value: Any, label: str) -> float:
    """Parse ``value`` as a finite float, raising ``ValueError`` if not finite."""
    parsed = parse_float(value, label)
    if not math.isfinite(parsed):
        raise ValueError(f"{label} must be finite, got {value!r}.")
    return parsed


def nonnegative_integer(value: Any, label: str) -> int:
    """Parse ``value`` as a non-negative integer-valued number."""
    parsed = finite_float(value, label)
    if parsed < 0 or not parsed.is_integer():
        raise ValueError(f"{label} must be a non-negative integer, got {value!r}.")
    return int(parsed)


def is_integer(value: Any) -> bool:
    """Return True if ``value`` is a Python ``int`` and not a ``bool``."""
    return isinstance(value, int) and not isinstance(value, bool)


def is_numeric(value: Any) -> bool:
    """Return True if ``value`` is a Python ``int``/``float`` and not a ``bool``."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    """Return ``value`` if it is a mapping, else raise ``ValueError``."""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    return value


def require_fields(container: Mapping[str, Any] | Iterable[str], required: Iterable[str], label: str) -> None:
    """Raise ``ValueError`` listing every field in ``required`` missing from ``container``.

    ``container`` may be a mapping (checked by key) or any iterable of field
    names (e.g. a CSV header list) — both support the ``in`` operator, which
    is all this check needs.
    """
    missing = [field for field in required if field not in container]
    if missing:
        raise ValueError(f"{label} is missing required field(s): {', '.join(missing)}.")
