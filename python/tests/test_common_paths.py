from pathlib import Path

from location_platform.common.paths import display_path, resolve_path


def test_display_path_uses_posix_style():
    assert display_path(Path("data") / "scenarios" / "x.json") == "data/scenarios/x.json"


def test_resolve_path_relative_resolves_against_project_root(tmp_path):
    project_root = tmp_path
    resolved = resolve_path("data/candidate_points.csv", project_root)
    assert resolved == (project_root / "data" / "candidate_points.csv").resolve()


def test_resolve_path_absolute_is_returned_as_is(tmp_path):
    absolute = (tmp_path / "somewhere" / "file.json").resolve()
    absolute.parent.mkdir(parents=True, exist_ok=True)
    resolved = resolve_path(str(absolute), project_root=tmp_path / "unrelated")
    assert resolved == absolute
