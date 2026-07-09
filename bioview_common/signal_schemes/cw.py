"""Continuous-wave (CW) FDM superheterodyne transmit scheme."""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from .base import SignalScheme
from .calibration import BurstEnvelopeMixin


class CwScheme(BurstEnvelopeMixin, SignalScheme):
    scheme_type = "cw"

    def __init__(
        self,
        samp_rate: float,
        if_freq: List[float],
        tx_amplitude: List[float],
        tx_phase_deg: List[float],
        calibration: dict | None = None,
    ):
        self.samp_rate = float(samp_rate)
        self.if_freq = [float(f) for f in if_freq]
        self.tx_amplitude = [float(a) for a in tx_amplitude]
        self.tx_phase_deg = [float(p) for p in tx_phase_deg]
        self._sample_idx = 0
        self._init_calibration(samp_rate, calibration or {})

    def get_num_tx_channels(self) -> int:
        return len(self.if_freq)

    def get_tx_amplitude(self, tx_idx: int) -> float:
        return self.tx_amplitude[tx_idx]

    def _get_buf_size(self, freq: float) -> int:
        return int(
            self.samp_rate * freq / (math.gcd(int(self.samp_rate), int(freq)) ** 2)
        )

    def _get_lcm(self, a: int, b: int) -> int:
        return int(a * b / math.gcd(int(a), int(b)))

    def cycle_length(self) -> Optional[int]:
        if self._cal_enabled:
            return None
        if len(self.if_freq) == 1:
            return self._get_buf_size(self.if_freq[0])
        return self._get_lcm(
            self._get_buf_size(self.if_freq[0]),
            self._get_buf_size(self.if_freq[1]),
        )

    def tx_phase_at(self, tx_idx: int, sample_idx: int) -> float:
        phase_deg = self.tx_phase_deg[tx_idx]
        phase_rad = math.radians(phase_deg)
        inc = 2.0 * math.pi * self.if_freq[tx_idx] / self.samp_rate
        return phase_rad + inc * sample_idx

    def generate(self, n_samples: int, start_sample: int) -> np.ndarray:
        n_tx = len(self.if_freq)
        out = np.zeros((n_tx, n_samples), dtype=np.complex64)
        t = (start_sample + np.arange(n_samples, dtype=np.float64)) / self.samp_rate

        for idx in range(n_tx):
            phase = self.tx_phase_at(idx, start_sample)
            phase_inc = 2.0 * np.pi * self.if_freq[idx] / self.samp_rate
            phases = phase + np.arange(n_samples) * phase_inc
            carrier = (
                self.tx_amplitude[idx] * np.exp(1j * phases).astype(np.complex64)
            )
            out[idx] = self._apply_calibration(carrier, idx, start_sample)

        return out

    def update_param(self, param: str, value) -> None:
        if param == "tx_amplitude":
            self.tx_amplitude = [float(v) for v in value]
        elif param == "tx_phase":
            self.tx_phase_deg = [float(v) for v in value]
        elif param == "if_freq":
            self.if_freq = [float(v) for v in value]
        elif param == "calibration":
            self._init_calibration(self.samp_rate, value)
        elif param == "calibration.enabled":
            self.set_calibration_enabled(bool(value))
        elif param.startswith("calibration."):
            key = param.split(".", 1)[1]
            self._cal_config[key] = value
            self._init_calibration(self.samp_rate, self._cal_config)
