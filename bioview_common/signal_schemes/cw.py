"""Continuous-wave (CW) FDM superheterodyne transmit scheme."""

from __future__ import annotations

import math

import numpy as np

from bioview_common.utils import apply_filter, get_filter

from .base import RxProcessor, SignalScheme
from .calibration import BurstEnvelopeMixin


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
        if_freq: list[float],
        tx_amplitude: list[float],
        tx_phase_deg: list[float],
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
        """Samples in one whole cycle of ``freq`` at this sample rate."""
        fs, f = int(round(self.samp_rate)), int(round(abs(freq)))
        divisor = math.gcd(fs, f)
        if divisor == 0:
            return 0
        return fs // divisor

    def _get_lcm(self, a: int, b: int) -> int:
        return int(a * b / math.gcd(int(a), int(b)))

    def cycle_length(self) -> int | None:
        """Samples after which every Tx tone repeats together."""
        if self._cal_enabled:
            return None
        periods = [self._get_buf_size(freq) for freq in self.if_freq]
        if not periods or any(period <= 0 for period in periods):
            return None
        common = periods[0]
        for period in periods[1:]:
            common = self._get_lcm(common, period)
        return common

    def tx_phase_at(self, tx_idx: int, sample_idx: int) -> float:
        phase_deg = self.tx_phase_deg[tx_idx]
        phase_rad = math.radians(phase_deg)
        inc = 2.0 * math.pi * self.if_freq[tx_idx] / self.samp_rate
        return phase_rad + inc * sample_idx

    def tx_phase_offset(self, tx_idx: int) -> float:
        if tx_idx >= len(self.tx_phase_deg):
            return 0.0
        return math.radians(self.tx_phase_deg[tx_idx])

    def generate(self, n_samples: int, start_sample: int) -> np.ndarray:
        n_tx = len(self.if_freq)
        out = np.zeros((n_tx, n_samples), dtype=np.complex64)

        for idx in range(n_tx):
            phase = self.tx_phase_at(idx, start_sample)
            phase_inc = 2.0 * np.pi * self.if_freq[idx] / self.samp_rate
            phases = phase + np.arange(n_samples) * phase_inc
            carrier = self.tx_amplitude[idx] * np.exp(1j * phases).astype(np.complex64)
            out[idx] = self._apply_calibration(carrier, idx, start_sample)

        return out

    def create_rx_processor(
        self, tx_idx: int, if_freq: float, if_filter_bw: float, samp_rate: float
    ) -> RxProcessor | None:
        return CwRxProcessor(samp_rate, self.if_freq[tx_idx], if_filter_bw)

    def update_param(self, param: str, value) -> None:
        if param == "tx_amplitude":
            self.tx_amplitude = [float(v) for v in value]
        elif param == "if_freq":
            self.if_freq = [float(v) for v in value]
        else:
            self.handle_common_param(param, value)
