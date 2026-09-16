"""Code Division Multiple Access (CDMA / PMCW) transmit scheme."""

from __future__ import annotations

import math

import numpy as np
import scipy.linalg

from bioview_common.utils import apply_filter, get_filter

from .base import RxProcessor, SignalScheme
from .calibration import BurstEnvelopeMixin


class CdmaRxProcessor(RxProcessor):
    def __init__(
        self, scheme: CdmaScheme, tx_idx: int, if_freq: float, if_filter_bw: float
    ):
        self.scheme = scheme
        self.tx_idx = tx_idx
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

        tx_code = self.scheme.get_code_at(
            self.tx_idx, len(rx_samples), self.accumulated_sample_idx
        )
        despread_samples = rx_samples * tx_code

        filt_data, new_filter_state = apply_filter(
            despread_samples, self.filt, zi=self.filter_state
        )
        self.filter_state = new_filter_state

        phase_increment = 2 * np.pi * self.if_freq / self.samp_rate
        phases = self.accumulated_phase + np.arange(len(filt_data)) * phase_increment
        self.accumulated_phase = phases[-1] + phase_increment

        downconversion = np.exp(-1j * phases)
        baseband_data = filt_data * downconversion

        self.accumulated_sample_idx += len(filt_data)
        return baseband_data


class CdmaScheme(BurstEnvelopeMixin, SignalScheme):
    scheme_type = "cdma"

    def __init__(
        self,
        samp_rate: float,
        num_tx: int,
        cdma_config: dict,
        tx_amplitude: list[float],
        if_freq: list[float] | None = None,
        calibration: dict | None = None,
    ):
        self.samp_rate = float(samp_rate)
        self.num_tx = num_tx
        cfg = cdma_config or {}
        self.chip_rate_hz = float(cfg.get("chip_rate_hz", 100e3))
        self.code_length = int(cfg.get("code_length", 1024))
        self.code_type = cfg.get("code_type", "Walsh-Hadamard")

        self.tx_amplitude = tx_amplitude if tx_amplitude else [1.0] * num_tx
        self.if_freq = if_freq if if_freq else [100e3] * num_tx

        self._init_calibration(samp_rate, calibration or {})
        self._generate_codes()

    def _generate_codes(self):
        """Generates orthogonal codes for each Tx channel."""
        power = max(1, int(math.ceil(math.log2(self.code_length))))
        actual_len = 2**power

        if self.code_type == "Walsh-Hadamard":
            hadamard_matrix = scipy.linalg.hadamard(actual_len)
            self.codes = []
            for i in range(self.num_tx):
                row_idx = i % actual_len
                self.codes.append(hadamard_matrix[row_idx].astype(np.float32))
        else:
            rng = np.random.RandomState(42)
            self.codes = []
            for _ in range(self.num_tx):
                seq = rng.choice([-1.0, 1.0], size=actual_len).astype(np.float32)
                self.codes.append(seq)

        self.code_length = actual_len
        self.samples_per_chip = max(1, int(self.samp_rate / self.chip_rate_hz))
        self._period_samples = self.code_length * self.samples_per_chip

    def _recompute_rate_derived(self) -> None:
        self._generate_codes()

    def get_num_tx_channels(self) -> int:
        return self.num_tx

    def get_tx_amplitude(self, tx_idx: int) -> float:
        return self.tx_amplitude[tx_idx] if tx_idx < len(self.tx_amplitude) else 1.0

    def cycle_length(self) -> int | None:
        if self._cal_enabled:
            return None
        return self._period_samples

    def get_code_at(self, tx_idx: int, n_samples: int, start_sample: int) -> np.ndarray:
        """Returns the upsampled BPSK code sequence for the given sample range."""
        idx = start_sample + np.arange(n_samples, dtype=np.int64)
        pos_in_period = idx % self._period_samples
        chip_indices = pos_in_period // self.samples_per_chip
        return self.codes[tx_idx][chip_indices]

    def tx_phase_at(self, tx_idx: int, sample_idx: int) -> float:
        if_freq = self.if_freq[tx_idx] if tx_idx < len(self.if_freq) else 100e3
        return 2.0 * math.pi * if_freq * sample_idx / self.samp_rate

    def generate(self, n_samples: int, start_sample: int) -> np.ndarray:
        out = np.zeros((self.num_tx, n_samples), dtype=np.complex64)
        t = (start_sample + np.arange(n_samples, dtype=np.float64)) / self.samp_rate

        for tx_idx in range(self.num_tx):
            if_freq = self.if_freq[tx_idx] if tx_idx < len(self.if_freq) else 100e3
            amp = self.get_tx_amplitude(tx_idx)

            code_seq = self.get_code_at(tx_idx, n_samples, start_sample)

            phases = 2.0 * np.pi * if_freq * t
            carrier = (amp * code_seq * np.exp(1j * phases)).astype(np.complex64)

            out[tx_idx] = self._apply_calibration(carrier, tx_idx, start_sample)

        return out

    def create_rx_processor(
        self, tx_idx: int, if_freq: float, if_filter_bw: float, samp_rate: float
    ) -> RxProcessor | None:
        return CdmaRxProcessor(
            self,
            tx_idx,
            self.if_freq[tx_idx] if tx_idx < len(self.if_freq) else 100e3,
            if_filter_bw,
        )

    def update_param(self, param: str, value) -> None:
        if param == "tx_amplitude":
            self.tx_amplitude = [float(v) for v in value]
        elif param == "cdma":
            self.__init__(
                self.samp_rate,
                self.num_tx,
                value,
                self.tx_amplitude,
                self.if_freq,
                self._cal_config,
            )
