"""Factory for signal scheme instances."""

from __future__ import annotations

from .base import SignalScheme
from .cdma import CdmaScheme
from .cw import CwScheme
from .fmcw import FmcwScheme
from .pulsed_doppler import PulsedDopplerScheme


def scheme_from_config(
    samp_rate: float,
    num_tx: int,
    config: dict,
    global_tx_offset: int = 0,
) -> SignalScheme:
    """Build a SignalScheme from a hardware or group config dict."""
    scheme_type = config.get("signal_scheme", "cw")
    tx_amplitude = config.get("tx_amplitude", [1.0] * num_tx)
    if len(tx_amplitude) < num_tx:
        tx_amplitude = list(tx_amplitude) + [1.0] * (num_tx - len(tx_amplitude))

    tx_phase = config.get("tx_phase", [0.0] * num_tx)
    if len(tx_phase) < num_tx:
        tx_phase = list(tx_phase) + [0.0] * (num_tx - len(tx_phase))

    calibration = dict(config.get("calibration", {}))
    inject = calibration.get("inject_channels", [0])
    calibration["inject_channels"] = [
        c - global_tx_offset
        for c in inject
        if global_tx_offset <= c < global_tx_offset + num_tx
    ]

    if scheme_type == "fmcw":
        return FmcwScheme(
            samp_rate=samp_rate,
            num_tx=num_tx,
            fmcw_config=config.get("fmcw", {}),
            tx_amplitude=tx_amplitude,
            calibration=calibration,
        )
    if scheme_type == "pulsed_doppler":
        if_freq = config.get("if_freq", [100e3] * num_tx)
        return PulsedDopplerScheme(
            samp_rate=samp_rate,
            num_tx=num_tx,
            pd_config=config.get("pulsed_doppler", {}),
            tx_amplitude=tx_amplitude,
            if_freq=if_freq,
            calibration=calibration,
        )
    if scheme_type == "cdma":
        if_freq = config.get("if_freq", [100e3] * num_tx)
        return CdmaScheme(
            samp_rate=samp_rate,
            num_tx=num_tx,
            cdma_config=config.get("cdma", {}),
            tx_amplitude=tx_amplitude,
            if_freq=if_freq,
            calibration=calibration,
        )

    if_freq: list[float] = config.get("if_freq", [100e3] * num_tx)

    if len(if_freq) < num_tx:
        if_freq = list(if_freq) + [if_freq[-1]] * (num_tx - len(if_freq))
    return CwScheme(
        samp_rate=samp_rate,
        if_freq=if_freq,
        tx_amplitude=tx_amplitude,
        tx_phase_deg=tx_phase,
        calibration=calibration,
    )
