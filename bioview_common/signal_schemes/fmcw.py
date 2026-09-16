"""FMCW linear chirp transmit scheme."""

from __future__ import annotations

import numpy as np

from bioview_common.utils import apply_filter, get_filter

from .base import RxProcessor, SignalScheme
from .calibration import BurstEnvelopeMixin


class FmcwRxProcessor(RxProcessor):
    def __init__(
        self, scheme: FmcwScheme, tx_idx: int, if_freq: float, if_filter_bw: float
    ):
        self.scheme = scheme
        self.samp_rate = scheme.samp_rate
        self.if_freq = if_freq
        self.accumulated_phase = 0.0
        self.accumulated_sample_idx = 0

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

        ref = self.scheme.get_dechirp_reference(
            len(filt_data), self.accumulated_sample_idx
        )
        baseband_data = baseband_data * ref
        self.accumulated_sample_idx += len(filt_data)

        return baseband_data


class FmcwScheme(BurstEnvelopeMixin, SignalScheme):
    scheme_type = "fmcw"

    def __init__(
        self,
        samp_rate: float,
        num_tx: int,
        fmcw_config: dict,
        tx_amplitude: list[float],
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

    def _recompute_rate_derived(self) -> None:
        self._chirp_samples = max(1, int(round(self.chirp_duration_s * self.samp_rate)))
        self._idle_samples = max(0, int(round(self.idle_time_s * self.samp_rate)))
        self._period_samples = self._chirp_samples + self._idle_samples

    def get_num_tx_channels(self) -> int:
        return self.num_tx

    def get_tx_amplitude(self, tx_idx: int) -> float:
        return self.tx_amplitude[tx_idx] if tx_idx < len(self.tx_amplitude) else 1.0

    def cycle_length(self) -> int | None:
        if self._cal_enabled:
            return None
        return self._period_samples

    def _chirp_phase(self, t: np.ndarray) -> np.ndarray:
        """Phase of linear FM chirp: 2*pi*(f0*t + 0.5*k*t^2)."""
        t_clipped = np.clip(t, 0, self.chirp_duration_s)
        return (
            2.0
            * np.pi
            * (self.chirp_start_hz * t_clipped + 0.5 * self._k * t_clipped**2)
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
            carrier[in_chirp] = amp * np.exp(1j * phases[in_chirp]).astype(np.complex64)
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

    def create_rx_processor(
        self, tx_idx: int, if_freq: float, if_filter_bw: float, samp_rate: float
    ) -> RxProcessor | None:
        return FmcwRxProcessor(self, tx_idx, if_freq, if_filter_bw)

    def update_param(self, param: str, value) -> None:
        if param == "tx_amplitude":
            self.tx_amplitude = [float(v) for v in value]
        elif param == "fmcw":
            enabled = self._cal_enabled
            self.__init__(
                self.samp_rate,
                self.num_tx,
                value,
                self.tx_amplitude,
                self._cal_config,
            )
            self.set_calibration_enabled(enabled)
        else:
            self.handle_common_param(param, value)
