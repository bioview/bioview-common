"""Per-device translation of the global ``calibration.inject_channels`` list."""

from bioview_common.signal_schemes import scheme_from_config


def _cfg(**cal):
    return {
        "signal_scheme": "cw",
        "if_freq": [100e3],
        "tx_amplitude": [1.0],
        "tx_phase": [0.0],
        "calibration": {"enabled": True, **cal},
    }


def test_default_inject_channel_is_not_duplicated_onto_every_device():
    # Global Tx0 lives on the first device. A second device starting at global
    # Tx2 must not inject on its own local Tx0 as well.
    first = scheme_from_config(1e6, 1, _cfg(), global_tx_offset=0)
    second = scheme_from_config(1e6, 1, _cfg(), global_tx_offset=2)

    assert first._inject_channels == {0}
    assert second._inject_channels == set()


def test_explicit_inject_channels_are_translated_to_local_indices():
    cfg = _cfg(inject_channels=[2])
    owning = scheme_from_config(1e6, 1, cfg, global_tx_offset=2)
    other = scheme_from_config(1e6, 2, cfg, global_tx_offset=0)

    assert owning._inject_channels == {0}
    assert other._inject_channels == set()


def test_out_of_window_channels_are_dropped_not_wrapped():
    # global Tx5 belongs to no device in a 2-channel group starting at 0
    scheme = scheme_from_config(1e6, 2, _cfg(inject_channels=[5]), global_tx_offset=0)
    assert scheme._inject_channels == set()
