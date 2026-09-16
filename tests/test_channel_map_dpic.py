"""Adding a DPIC pair must retire both halves of the inject channel."""

from bioview_common.datatypes.configuration.usrp_channel_map import (
    build_global_registry,
    inject_rx_indices,
    resolve_channel_map,
)


ONE_RADIO = {
    "B210": {
        "tx_channels": [0, 1],
        "rx_channels": [0, 1],
        "if_freq": [100e3, 100e3],
    }
}

TWO_RADIOS = {
    "A": {"tx_channels": [0, 1], "rx_channels": [0, 1], "if_freq": [100e3, 110e3]},
    "B": {"tx_channels": [0], "rx_channels": [0, 1], "if_freq": [100e3]},
}


def _labels(channel_map, hardware):
    sources, _registry, _pairs = resolve_channel_map("g", channel_map, hardware)
    return sorted(s.label for s in sources)


def test_no_dpic_keeps_the_full_grid():
    assert _labels({"layout": "full_nxn", "dpic": []}, ONE_RADIO) == [
        "Tx1Rx1",
        "Tx1Rx2",
        "Tx2Rx1",
        "Tx2Rx2",
    ]


def test_inject_tx_retires_its_own_rx():
    """Tx2 injecting into Tx1 leaves Rx2 with nothing to receive."""
    channel_map = {
        "layout": "full_nxn",
        "dpic": [{"inject_tx": 1, "measure_tx": 0, "measure_rx": 0}],
    }
    assert _labels(channel_map, ONE_RADIO) == ["Tx1Rx1"]


def test_inject_rx_is_matched_by_physical_channel_not_index():
    """The retired Rx is the inject Tx's own port, on its own radio."""
    registry = build_global_registry(TWO_RADIOS)
    assert registry.tx_entries[2] == ("B", 0)
    assert inject_rx_indices({"dpic": [{"inject_tx": 2}]}, registry) == {2}


def test_hybrid_mimo_drops_a_listed_inject_rx():
    """An explicit rx_global that still lists the inject port is corrected."""
    channel_map = {
        "layout": "hybrid_mimo",
        "mimo": {"tx_global": [0, 1], "rx_global": [0, 1, 2, 3]},
        "dpic": [{"inject_tx": 2, "measure_tx": 0, "measure_rx": 0}],
    }
    labels = _labels(channel_map, TWO_RADIOS)
    assert labels == [
        "Tx1Rx1",
        "Tx1Rx2",
        "Tx1Rx3",
        "Tx2Rx1",
        "Tx2Rx2",
        "Tx2Rx3",
    ]


def test_custom_layout_is_left_alone():
    """Explicit pairs mean the author said exactly what they wanted."""
    channel_map = {
        "layout": "custom",
        "pairs": [{"tx": 0, "rx": 0}, {"tx": 0, "rx": 1}],
        "dpic": [{"inject_tx": 1, "measure_tx": 0, "measure_rx": 0}],
    }
    assert len(_labels(channel_map, ONE_RADIO)) == 2


def test_removing_the_pair_restores_the_grid():
    """The grid follows the pair list in both directions."""
    with_pair = {
        "layout": "full_nxn",
        "dpic": [{"inject_tx": 1, "measure_tx": 0, "measure_rx": 0}],
    }
    without = {"layout": "full_nxn", "dpic": []}
    assert len(_labels(with_pair, ONE_RADIO)) == 1
    assert len(_labels(without, ONE_RADIO)) == 4
