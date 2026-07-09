"""Tests for configuration parsing and filesystem helpers in bioview-common."""
import json
from pathlib import Path

from bioview_common import (
    Configuration,
    DummyConfiguration,
    SUPPORTED_CONFIGURATION_TYPES,
    USRPConfiguration,
    get_unique_path,
    parse_configuration_file,
)
from bioview_common.datatypes.configuration.usrp_channel_map import (
    build_hardware_dict,
    resolve_channel_map,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DPIC_2X2_CFG = REPO_ROOT / "usrp_dpic_2x2_mimo_cfg.json"
DUMMY_DPIC_2X2_CFG = REPO_ROOT / "dummy_dpic_2x2_mimo_cfg.json"
SAMPLE_USRP_CFG = REPO_ROOT / "sample_usrp_cfg.json"


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


def test_parse_configuration_file_usrp_dpic_2x2_mimo():
    parsed = parse_configuration_file(str(DPIC_2X2_CFG))
    assert "USRP_DPIC_2x2" in parsed
    usrp = parsed["USRP_DPIC_2x2"]
    assert isinstance(usrp, USRPConfiguration)
    assert usrp.get_type() == SUPPORTED_CONFIGURATION_TYPES.USRP
    assert usrp.get_param("signal_scheme") == "cw"

    hardware = build_hardware_dict(usrp, "USRP_DPIC_2x2")
    assert set(hardware) == {"MyB210_4", "MyB210_7"}
    sources, registry, dpic = resolve_channel_map(
        "USRP_DPIC_2x2",
        usrp.get_param("channel_map"),
        hardware,
    )
    assert len(sources) == 4
    assert registry.num_tx == 3
    assert len(dpic) == 1
    assert dpic[0].inject_tx == 2
    assert dpic[0].measure_tx == 0


def test_parse_configuration_file_dummy_dpic_2x2_mimo():
    parsed = parse_configuration_file(str(DUMMY_DPIC_2X2_CFG))
    assert "Dummy_DPIC_2x2" in parsed
    dummy = parsed["Dummy_DPIC_2x2"]
    assert isinstance(dummy, DummyConfiguration)
    assert dummy.get_type() == SUPPORTED_CONFIGURATION_TYPES.DUMMY
    assert dummy.get_param("hardware") is not None
    assert dummy.get_param("channel_map") is not None


def test_parse_configuration_file_sample_usrp_single_radio():
    parsed = parse_configuration_file(str(SAMPLE_USRP_CFG))
    assert "USRP" in parsed
    usrp = parsed["USRP"]
    assert isinstance(usrp, USRPConfiguration)
    assert usrp.get_type() == SUPPORTED_CONFIGURATION_TYPES.USRP

    hardware = build_hardware_dict(usrp, "USRP")
    assert set(hardware) == {"MyB210_7"}
    sources, registry, dpic = resolve_channel_map(
        "USRP",
        usrp.get_param("channel_map"),
        hardware,
    )
    assert len(sources) == 4
    assert registry.num_tx == 2
    assert registry.num_rx == 2
    assert dpic == []


def test_configuration_resolves_device_type_from_type_field():
    config = Configuration.from_dict(
        {
            "DummyDevice": {
                "type": "DUMMY",
                "samp_rate": 500,
                "num_channels": 2,
            }
        }
    )
    assert "DummyDevice" in config.devices
    assert isinstance(config.devices["DummyDevice"], DummyConfiguration)
    assert config.devices["DummyDevice"].get_param("device_type") == "dummy"


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
