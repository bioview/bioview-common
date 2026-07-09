"""Pulsed-Doppler transmit scheme."""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from .base import SignalScheme
from .calibration import BurstEnvelopeMixin


class PulsedDopplerScheme(BurstEnvelopeMixin, SignalScheme):
    scheme_type = "pulsed_doppler"

    def __init__(
        self,
        samp_rate: float,
        num_tx: int,
        pd_config: dict,
        tx_amplitude: List[float],
        if_freq: List[float] | None = None,
        calibration: dict | None = None,
    ):
        self.samp_rate = float(samp_rate)
        self.num_tx = num_tx
        cfg = pd_config or {}
        self.pulse_width_s = float(cfg.get("pulse_width_s", 1e-5))
        self.pri_s = float(cfg.get("pri_s", 1e-3))
        self.doppler_if_hz = float(cfg.get("doppler_if_hz", 100e3))
        self.tx_amplitude = tx_amplitude if tx_amplitude else [1.0] * num_tx
        self.if_freq = if_freq or [self.doppler_if_hz] * num_tx
        self._pulse_samples = max(1, int(round(self.pulse_width_s * self.samp_rate)))
        self._pri_samples = max(self._pulse_samples, int(round(self.pri_s * self.samp_rate)))
        self._init_calibration(samp_rate, calibration or {})

    def get_num_tx_channels(self) -> int:
        return self.num_tx

    def get_tx_amplitude(self, tx_idx: int) -> float:
        return self.tx_amplitude[tx_idx] if tx_idx < len(self.tx_amplitude) else 1.0

    def cycle_length(self) -> Optional[int]:
        if self._cal_enabled:
            return None
        return self._pri_samples

    def tx_phase_at(self, tx_idx: int, sample_idx: int) -> float:
        import math
        if_freq = self.if_freq[tx_idx] if tx_idx < len(self.if_freq) else self.doppler_if_hz
        return 2.0 * math.pi * if_freq * sample_idx / self.samp_rate

    def generate(self, n_samples: int, start_sample: int) -> np.ndarray:
        out = np.zeros((self.num_tx, n_samples), dtype=np.complex64)
        idx = start_sample + np.arange(n_samples, dtype=np.int64)
        pos_in_pri = idx % self._pri_samples
        in_pulse = pos_in_pri < self._pulse_samples
        t = idx.astype(np.float64) / self.samp_rate

        for tx_idx in range(self.num_tx):
            if_freq = self.if_freq[tx_idx] if tx_idx < len(self.if_freq) else self.doppler_if_hz
            amp = self.get_tx_amplitude(tx_idx)
            phases = 2.0 * np.pi * if_freq * t
            carrier = np.zeros(n_samples, dtype=np.complex64)
            carrier[in_pulse] = (
                amp * np.exp(1j * phases[in_pulse]).astype(np.complex64)
            )
            out[tx_idx] = self._apply_calibration(carrier, tx_idx, start_sample)
        return out

    def update_param(self, param: str, value) -> None:
        if param == "tx_amplitude":
            self.tx_amplitude = [float(v) for v in value]
        elif param == "pulsed_doppler":
            self.__init__(
                self.samp_rate,
                self.num_tx,
                value,
                self.tx_amplitude,
                self.if_freq,
                self._cal_config,
            )
