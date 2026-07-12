import json

import pytest

from location_platform.scenario.loading import load_scenario_json


def test_valid_top_level_object_accepted(tmp_path):
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps({"scenarioId": "test"}), encoding="utf-8")
    scenario = load_scenario_json(path)
    assert scenario == {"scenarioId": "test"}


def test_json_array_rejected(tmp_path):
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        load_scenario_json(path)


def test_malformed_json_rejected(tmp_path):
    path = tmp_path / "scenario.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_scenario_json(path)


def test_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_scenario_json(tmp_path / "missing.json")
