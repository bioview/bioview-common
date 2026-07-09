"""Tests for hardware-aware parameter flattening."""

from bioview_common.datatypes.configuration.dummy import DummyConfiguration
from bioview_common.datatypes.configuration.hardware_params import (
    get_global_tx_values,
    resolve_param_values,
    update_device_tx_param,
)


def _dpic_dummy_cfg():
    return DummyConfiguration.from_dict(
        {
            "type": "DUMMY",
            "samp_rate": 1e6,
            "hardware": {
                "MyB210_4": {
                    "tx_channels": [0, 1],
                    "rx_channels": [0, 1],
                    "if_freq": [100e3, 110e3],
                    "tx_amplitude": [0.8, 0.9],
                    "tx_phase": [10.0, 20.0],
                },
                "MyB210_7": {
                    "tx_channels": [0],
                    "rx_channels": [0, 1],
                    "if_freq": [120e3],
                    "tx_amplitude": [0.5],
                    "tx_phase": [30.0],
                },
            },
        }
    )


def test_get_global_tx_values_from_hardware():
    cfg = _dpic_dummy_cfg()
    assert get_global_tx_values(cfg.get_param("hardware"), "if_freq", cfg.to_dict()) == [
        100e3,
        110e3,
        120e3,
    ]
    assert resolve_param_values(cfg, "tx_amplitude") == [0.8, 0.9, 0.5]


def test_update_device_tx_param_writes_nested_hardware():
    cfg = _dpic_dummy_cfg()
    updated = update_device_tx_param(cfg, "tx_amplitude", 0.25, idx=2)
    assert updated == [0.8, 0.9, 0.25]
    hw = cfg.get_param("hardware")
    assert hw["MyB210_7"]["tx_amplitude"] == [0.25]
