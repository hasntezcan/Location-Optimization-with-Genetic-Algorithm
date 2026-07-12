import math

import pytest

from location_platform.common.parsing import (
    finite_float,
    is_integer,
    is_numeric,
    nonnegative_integer,
    parse_float,
    parse_int,
    require_fields,
    require_mapping,
)


def test_parse_int_valid():
    assert parse_int("42", "field") == 42


def test_parse_int_invalid_raises():
    with pytest.raises(ValueError):
        parse_int("not-a-number", "field")


def test_parse_float_valid():
    assert parse_float("3.5", "field") == 3.5


def test_parse_float_invalid_raises():
    with pytest.raises(ValueError):
        parse_float("nope", "field")


def test_finite_float_rejects_non_finite():
    with pytest.raises(ValueError):
        finite_float(float("inf"), "field")
    with pytest.raises(ValueError):
        finite_float(float("nan"), "field")


def test_finite_float_accepts_finite():
    assert finite_float("2.0", "field") == 2.0


def test_nonnegative_integer_rejects_negative():
    with pytest.raises(ValueError):
        nonnegative_integer(-1, "field")


def test_nonnegative_integer_rejects_non_integer():
    with pytest.raises(ValueError):
        nonnegative_integer(1.5, "field")


def test_nonnegative_integer_accepts_valid():
    assert nonnegative_integer(3, "field") == 3


def test_is_integer_excludes_bool():
    assert is_integer(3) is True
    assert is_integer(True) is False
    assert is_integer(3.0) is False


def test_is_numeric_excludes_bool():
    assert is_numeric(3) is True
    assert is_numeric(3.5) is True
    assert is_numeric(True) is False
    assert is_numeric("3") is False


def test_require_mapping_accepts_dict():
    value = {"a": 1}
    assert require_mapping(value, "label") is value


def test_require_mapping_rejects_non_mapping():
    with pytest.raises(ValueError):
        require_mapping([1, 2, 3], "label")
    with pytest.raises(ValueError):
        require_mapping(None, "label")


def test_require_fields_passes_when_all_present():
    require_fields({"a": 1, "b": 2}, ["a", "b"], "label")


def test_require_fields_raises_listing_missing():
    with pytest.raises(ValueError, match="c, d"):
        require_fields({"a": 1, "b": 2}, ["a", "c", "d"], "label")


def test_require_fields_works_on_plain_iterable_container():
    fieldnames = ["id", "lat", "lon"]
    require_fields(fieldnames, ["id", "lat"], "label")
    with pytest.raises(ValueError):
        require_fields(fieldnames, ["id", "missing_column"], "label")
