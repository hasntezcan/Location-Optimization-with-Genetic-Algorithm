import pytest

from location_platform.data.candidates import (
    load_candidate_ids,
    load_candidate_rows,
    parse_candidate_ids,
    validate_candidate_id_uniqueness,
)


def write_csv(tmp_path, rows, header="id,lat,lon"):
    path = tmp_path / "candidate_points.csv"
    lines = [header] + rows
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_load_candidate_ids_valid_and_ordered(tmp_path):
    # Deliberately non-sequential IDs, out of numeric order, to prove IDs
    # (not row offsets) are returned, in file order.
    csv_path = write_csv(
        tmp_path,
        ["100,1.0,2.0", "5,1.1,2.1", "42,1.2,2.2"],
    )
    ids = load_candidate_ids(csv_path)
    assert ids == [100, 5, 42]


def test_duplicate_candidate_ids_rejected(tmp_path):
    csv_path = write_csv(tmp_path, ["1,1.0,2.0", "2,1.1,2.1", "1,1.2,2.2"])
    with pytest.raises(ValueError, match="Duplicate candidate IDs"):
        load_candidate_ids(csv_path)


def test_invalid_non_integer_candidate_id_rejected(tmp_path):
    csv_path = write_csv(tmp_path, ["1,1.0,2.0", "not-an-id,1.1,2.1"])
    with pytest.raises(ValueError):
        load_candidate_ids(csv_path)


def test_missing_required_column_rejected(tmp_path):
    csv_path = write_csv(tmp_path, ["1.0,2.0"], header="lat,lon")
    with pytest.raises(ValueError, match="missing required field"):
        load_candidate_rows(csv_path, required_columns=("id",))


def test_missing_csv_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_candidate_ids(tmp_path / "does_not_exist.csv")


def test_parse_candidate_ids_preserves_row_order():
    rows = [{"id": "9"}, {"id": "1"}, {"id": "5"}]
    assert parse_candidate_ids(rows) == [9, 1, 5]


def test_validate_candidate_id_uniqueness_passes_on_unique():
    validate_candidate_id_uniqueness([1, 2, 3])


def test_validate_candidate_id_uniqueness_raises_on_duplicate():
    with pytest.raises(ValueError):
        validate_candidate_id_uniqueness([1, 2, 2, 3])
