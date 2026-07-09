"""Abstract base for platform-agnostic transmit signal schemes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class SignalScheme(ABC):
    """Generates per-Tx-channel IQ samples for SDR transmission."""

    scheme_type: str = "base"

    @abstractmethod
    def generate(self, n_samples: int, start_sample: int) -> np.ndarray:
        """Return (n_tx_channels, n_samples) complex64 array."""

    def cycle_length(self) -> Optional[int]:
        """Period in samples for cyclic buffering; None if aperiodic."""
        return None

    def tx_phase_at(self, tx_idx: int, sample_idx: int) -> float:
        """Analytic Tx phase (rad) at sample index."""
        return 0.0

    def get_tx_amplitude(self, tx_idx: int) -> float:
        return 1.0

    def get_num_tx_channels(self) -> int:
        return 0

    def update_param(self, param: str, value) -> None:
        pass

    def set_calibration_enabled(self, enabled: bool) -> None:
        pass

    def get_calibration_reference(
        self, tx_idx: int, start_sample: int, n_samples: int
    ) -> np.ndarray:
        """Gated calibration envelope for save stream (zeros outside bursts)."""
        return np.zeros(n_samples, dtype=np.float32)
