"""Tests for USRP channel map resolution."""

from bioview_common.datatypes.configuration.usrp_channel_map import (
    build_global_registry,
    resolve_channel_map,
)


def test_single_device_full_nxn():
    hardware = {
        "MyB210": {
            "tx_channels": [0, 1],
            "rx_channels": [0, 1],
            "if_freq": [100e3, 110e3],
        }
    }
    sources, registry, dpic = resolve_channel_map("grp", None, hardware)
    assert registry.num_tx == 2
    assert registry.num_rx == 2
    assert len(sources) == 4
    labels = sorted(s.label for s in sources)
    assert labels == ["Tx1Rx1", "Tx1Rx2", "Tx2Rx1", "Tx2Rx2"]
    assert dpic == []


def test_hybrid_dpic_2x2():
    """MyB210_4 runs 2x2 MIMO; MyB210_7 Tx0 injects for DPIC on measure Tx0/Rx0."""
    hardware = {
        "MyB210_4": {
            "tx_channels": [0, 1],
            "rx_channels": [0, 1],
            "if_freq": [100e3, 110e3],
        },
        "MyB210_7": {
            "tx_channels": [0],
            "rx_channels": [0, 1],
            "if_freq": [120e3],
        },
    }
    channel_map = {
        "layout": "hybrid_mimo",
        "mimo": {"tx_global": [0, 1], "rx_global": [0, 1]},
        "dpic": [{"inject_tx": 2, "measure_tx": 0}],
    }
    sources, registry, dpic = resolve_channel_map("grp", channel_map, hardware)
    assert registry.num_tx == 3
    assert registry.num_rx == 4
    assert len(sources) == 4
    labels = sorted(s.label for s in sources)
    assert labels == ["Tx1Rx1", "Tx1Rx2", "Tx2Rx1", "Tx2Rx2"]
    assert len(dpic) == 1
    assert dpic[0].inject_tx == 2
    assert dpic[0].measure_tx == 0
    assert dpic[0].target_rx == 0


def test_hybrid_dpic_3x3():
    hardware = {
        "MyB210_4": {
            "tx_channels": [0, 1],
            "rx_channels": [0, 1],
            "if_freq": [100e3, 110e3],
        },
        "MyB210_7": {
            "tx_channels": [0, 1],
            "rx_channels": [0, 1],
            "if_freq": [120e3, 130e3],
        },
    }
    channel_map = {
        "layout": "hybrid_mimo",
        "mimo": {"tx_global": [0, 1, 2], "rx_global": [0, 1, 2]},
        "dpic": [{"inject_tx": 3, "measure_tx": 2}],
    }
    sources, registry, dpic = resolve_channel_map("grp", channel_map, hardware)
    assert registry.num_tx == 4
    assert len(sources) == 9
    assert len(dpic) == 1
    assert dpic[0].target_rx == 2


def test_build_global_registry_if_freq():
    hardware = {
        "A": {"tx_channels": [0], "rx_channels": [0], "if_freq": [100e3]},
        "B": {"tx_channels": [0, 1], "rx_channels": [0], "if_freq": [200e3, 300e3]},
    }
    reg = build_global_registry(hardware)
    assert reg.tx_if_freq == [100e3, 200e3, 300e3]
