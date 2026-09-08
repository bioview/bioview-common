"""Pulsed-Doppler transmit scheme."""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from .base import SignalScheme, RxProcessor
from .calibration import BurstEnvelopeMixin
from bioview_common.utils import apply_filter, get_filter

class PulsedDopplerRxProcessor(RxProcessor):
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

    def create_rx_processor(
        self, tx_idx: int, if_freq: float, if_filter_bw: float, samp_rate: float
    ) -> Optional[RxProcessor]:
        return PulsedDopplerRxProcessor(samp_rate, self.if_freq[tx_idx] if tx_idx < len(self.if_freq) else self.doppler_if_hz, if_filter_bw)


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
