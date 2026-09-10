"""Tests for USRP channel map resolution."""

import pytest

from bioview_common.datatypes.configuration.usrp_channel_map import (
    build_global_registry,
    components_from_config,
    normalize_components,
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


def test_components_default_to_amplitude_only():
    """The bare labels and channel numbering predate components; keep them."""
    hardware = {"A": {"tx_channels": [0, 1], "rx_channels": [0, 1]}}
    sources, _registry, _dpic = resolve_channel_map("grp", None, hardware)

    assert {s.label for s in sources} == {"Tx1Rx1", "Tx1Rx2", "Tx2Rx1", "Tx2Rx2"}
    assert {s.component for s in sources} == {"amplitude"}
    assert sorted(s.channel for s in sources) == [0, 1, 2, 3]


def test_two_components_double_the_rows_per_pair():
    hardware = {"A": {"tx_channels": [0, 1], "rx_channels": [0, 1]}}
    sources, _registry, _dpic = resolve_channel_map(
        "grp", None, hardware, components=["amplitude", "phase"]
    )

    by_channel = sorted(sources, key=lambda s: s.channel)
    assert [s.label for s in by_channel] == [
        "Tx1Rx1",
        "Tx1Rx1_Phase",
        "Tx2Rx1",
        "Tx2Rx1_Phase",
        "Tx1Rx2",
        "Tx1Rx2_Phase",
        "Tx2Rx2",
        "Tx2Rx2_Phase",
    ]
    # Both rows of a pair demodulate the same physical channel.
    for amp, phase in zip(by_channel[::2], by_channel[1::2], strict=True):
        assert (amp.tx_idx, amp.rx_idx) == (phase.tx_idx, phase.rx_idx)
        assert (amp.component, phase.component) == ("amplitude", "phase")


def test_custom_layout_labels_carry_the_component_suffix():
    hardware = {"A": {"tx_channels": [0, 1], "rx_channels": [0, 1]}}
    channel_map = {
        "layout": "custom",
        "pairs": [{"tx": 0, "rx": 0, "label": "Chest"}],
        "dpic": [],
    }
    sources, _registry, _dpic = resolve_channel_map(
        "grp", channel_map, hardware, components=["amplitude", "phase"]
    )
    assert {s.label for s in sources} == {"Chest", "Chest_Phase"}


def test_components_from_config_reads_the_legacy_switch():
    assert components_from_config({}) == ["amplitude"]
    assert components_from_config({"display_imaginary": True}) == ["phase"]
    # An explicit list wins over the older boolean.
    assert components_from_config(
        {"display_imaginary": True, "components": ["amplitude", "phase"]}
    ) == ["amplitude", "phase"]


def test_normalize_components_rejects_unknown_names():
    assert normalize_components(["Amp", "ANGLE", "amplitude"]) == [
        "amplitude",
        "phase",
    ]
    with pytest.raises(ValueError):
        normalize_components(["quadrature"])
