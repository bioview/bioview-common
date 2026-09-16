"""Abstract base for platform-agnostic transmit signal schemes."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class RxProcessor(ABC):
    """Abstract base for stateful per-Tx-channel receive DSP."""

    @abstractmethod
    def process_chunk(self, rx_samples: np.ndarray) -> np.ndarray:
        """Process a chunk of received samples and return baseband data."""
        pass


class SignalScheme(ABC):
    """Generates per-Tx-channel IQ samples for SDR transmission."""

    scheme_type: str = "base"

    @abstractmethod
    def generate(self, n_samples: int, start_sample: int) -> np.ndarray:
        """Return (n_tx_channels, n_samples) complex64 array."""

    def cycle_length(self) -> int | None:
        """Period in samples for cyclic buffering; None if aperiodic."""
        return None

    def tx_phase_at(self, tx_idx: int, sample_idx: int) -> float:
        """Analytic Tx phase (rad) at sample index."""
        return 0.0

    def tx_phase_offset(self, tx_idx: int) -> float:
        """Static programmed Tx phase (rad), without the carrier ramp."""
        return 0.0

    def get_tx_amplitude(self, tx_idx: int) -> float:
        return 1.0

    def get_num_tx_channels(self) -> int:
        return 0

    def set_samp_rate(self, samp_rate: float) -> None:
        """Adopt a new sample rate, keeping every programmed setting."""
        self.samp_rate = float(samp_rate)

    def update_param(self, param: str, value) -> None:  # noqa: B027
        pass

    def set_calibration_enabled(self, enabled: bool) -> None:  # noqa: B027
        pass

    def get_calibration_reference(
        self, tx_idx: int, start_sample: int, n_samples: int
    ) -> np.ndarray:
        """Gated calibration envelope for save stream (zeros outside bursts)."""
        return np.zeros(n_samples, dtype=np.float32)

    def create_rx_processor(
        self, tx_idx: int, if_freq: float, if_filter_bw: float, samp_rate: float
    ) -> RxProcessor | None:
        """Create a stateful receive processor for this scheme."""
        return None
