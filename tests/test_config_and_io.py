"""Tests for configuration parsing and filesystem helpers in bioview-common."""
import json

from bioview_common import (
    Configuration,
    SUPPORTED_CONFIGURATION_TYPES,
    get_unique_path,
    parse_configuration_file,
)


def _write_json(tmp_path, data):
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_parse_configuration_file_dummy(tmp_path):
    cfg_path = _write_json(
        tmp_path,
        {
            "Experiment": {
                "type": "EXPERIMENT",
                "enable_save": False,
                "save_dir": "./recordings",
                "file_name": "dummy_session.bvr",
            },
            "DummyDevice": {
                "type": "DUMMY",
                "samp_rate": 500,
                "num_channels": 4,
            },
        },
    )

    parsed = parse_configuration_file(cfg_path)
    assert set(parsed.keys()) == {"Experiment", "DummyDevice"}
    assert parsed["Experiment"].get_type() == SUPPORTED_CONFIGURATION_TYPES.EXPERIMENT
    assert parsed["DummyDevice"].get_type() == SUPPORTED_CONFIGURATION_TYPES.DUMMY


def test_parse_configuration_file_drops_unknown_types(tmp_path):
    cfg_path = _write_json(
        tmp_path,
        {
            "Good": {"type": "DUMMY", "samp_rate": 100, "num_channels": 1},
            "Bad": {"type": "NOT_A_REAL_TYPE"},
        },
    )
    parsed = parse_configuration_file(cfg_path)
    assert "Good" in parsed
    assert "Bad" not in parsed


def test_parse_configuration_file_missing_returns_empty():
    assert parse_configuration_file("/no/such/file.json") == {}


def test_configuration_roundtrip(tmp_path):
    cfg_path = _write_json(
        tmp_path,
        {
            "Experiment": {"type": "EXPERIMENT", "file_name": "x.bvr"},
            "DummyDevice": {"type": "DUMMY", "samp_rate": 250, "num_channels": 2},
        },
    )
    parsed = parse_configuration_file(cfg_path)
    config = Configuration.from_dict({k: v.to_dict() for k, v in parsed.items()})
    assert "DummyDevice" in config.devices
    # A round-trip through dict form should preserve the device.
    assert "DummyDevice" in config.to_dict()


def test_get_unique_path_deduplicates(tmp_path):
    first = get_unique_path(str(tmp_path), "rec.bvr")
    assert first.name == "rec.bvr"
    first.write_bytes(b"x")

    second = get_unique_path(str(tmp_path), "rec.bvr")
    assert second.name == "rec_2.bvr"
    second.write_bytes(b"x")

    third = get_unique_path(str(tmp_path), "rec.bvr")
    assert third.name == "rec_3.bvr"
