"""FMCW linear chirp transmit scheme."""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from .base import SignalScheme
from .calibration import BurstEnvelopeMixin


class FmcwScheme(BurstEnvelopeMixin, SignalScheme):
    scheme_type = "fmcw"

    def __init__(
        self,
        samp_rate: float,
        num_tx: int,
        fmcw_config: dict,
        tx_amplitude: List[float],
        calibration: dict | None = None,
    ):
        self.samp_rate = float(samp_rate)
        self.num_tx = num_tx
        cfg = fmcw_config or {}
        self.chirp_start_hz = float(cfg.get("chirp_start_hz", 50e3))
        self.chirp_end_hz = float(cfg.get("chirp_end_hz", 150e3))
        self.chirp_duration_s = float(cfg.get("chirp_duration_s", 0.001))
        self.idle_time_s = float(cfg.get("idle_time_s", 0.001))
        self.tx_amplitude = tx_amplitude if tx_amplitude else [1.0] * num_tx
        self._chirp_samples = max(1, int(round(self.chirp_duration_s * self.samp_rate)))
        self._idle_samples = max(0, int(round(self.idle_time_s * self.samp_rate)))
        self._period_samples = self._chirp_samples + self._idle_samples
        self._k = (self.chirp_end_hz - self.chirp_start_hz) / self.chirp_duration_s
        self._init_calibration(samp_rate, calibration or {})

    def get_num_tx_channels(self) -> int:
        return self.num_tx

    def get_tx_amplitude(self, tx_idx: int) -> float:
        return self.tx_amplitude[tx_idx] if tx_idx < len(self.tx_amplitude) else 1.0

    def cycle_length(self) -> Optional[int]:
        if self._cal_enabled:
            return None
        return self._period_samples

    def _chirp_phase(self, t: np.ndarray) -> np.ndarray:
        """Phase of linear FM chirp: 2*pi*(f0*t + 0.5*k*t^2)."""
        t_clipped = np.clip(t, 0, self.chirp_duration_s)
        return 2.0 * np.pi * (
            self.chirp_start_hz * t_clipped + 0.5 * self._k * t_clipped ** 2
        )

    def generate(self, n_samples: int, start_sample: int) -> np.ndarray:
        out = np.zeros((self.num_tx, n_samples), dtype=np.complex64)
        idx = start_sample + np.arange(n_samples, dtype=np.int64)
        pos_in_period = idx % self._period_samples
        in_chirp = pos_in_period < self._chirp_samples
        t = pos_in_period.astype(np.float64) / self.samp_rate

        for tx_idx in range(self.num_tx):
            amp = self.get_tx_amplitude(tx_idx)
            phases = self._chirp_phase(t)
            carrier = np.zeros(n_samples, dtype=np.complex64)
            carrier[in_chirp] = (
                amp * np.exp(1j * phases[in_chirp]).astype(np.complex64)
            )
            out[tx_idx] = self._apply_calibration(carrier, tx_idx, start_sample)
        return out

    def get_dechirp_reference(self, n_samples: int, start_sample: int) -> np.ndarray:
        """Conjugate chirp reference for Rx dechirp."""
        idx = start_sample + np.arange(n_samples, dtype=np.int64)
        pos_in_period = idx % self._period_samples
        in_chirp = pos_in_period < self._chirp_samples
        t = pos_in_period.astype(np.float64) / self.samp_rate
        phases = self._chirp_phase(t)
        ref = np.zeros(n_samples, dtype=np.complex64)
        ref[in_chirp] = np.exp(-1j * phases[in_chirp]).astype(np.complex64)
        return ref

    def update_param(self, param: str, value) -> None:
        if param == "tx_amplitude":
            self.tx_amplitude = [float(v) for v in value]
        elif param == "fmcw":
            self.__init__(
                self.samp_rate,
                self.num_tx,
                value,
                self.tx_amplitude,
                self._cal_config,
            )
