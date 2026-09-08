"""Continuous-wave (CW) FDM superheterodyne transmit scheme."""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from .base import SignalScheme, RxProcessor
from .calibration import BurstEnvelopeMixin
from bioview_common.utils import apply_filter, get_filter


class CwRxProcessor(RxProcessor):
    def __init__(self, samp_rate: float, if_freq: float, if_filter_bw: float):
        self.samp_rate = samp_rate
        self.if_freq = if_freq
        self.accumulated_phase = 0.0
        
        low_cutoff = if_freq - if_filter_bw / 2
        high_cutoff = if_freq + if_filter_bw / 2
        self.filt = get_filter(
            bounds=[low_cutoff, high_cutoff],
            samp_rate=self.samp_rate,
            btype="band",
            order=2,
        )
        self.filter_state = None

    def process_chunk(self, rx_samples: np.ndarray) -> np.ndarray:
        if len(rx_samples) == 0:
            return np.array([])
            
        filt_data, new_filter_state = apply_filter(
            rx_samples, self.filt, zi=self.filter_state
        )
        self.filter_state = new_filter_state

        phase_increment = 2 * np.pi * self.if_freq / self.samp_rate
        phases = self.accumulated_phase + np.arange(len(filt_data)) * phase_increment
        self.accumulated_phase = phases[-1] + phase_increment

        downconversion = np.exp(-1j * phases)
        baseband_data = filt_data * downconversion
        return baseband_data



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

    def create_rx_processor(
        self, tx_idx: int, if_freq: float, if_filter_bw: float, samp_rate: float
    ) -> Optional[RxProcessor]:
        return CwRxProcessor(samp_rate, self.if_freq[tx_idx], if_filter_bw)


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
