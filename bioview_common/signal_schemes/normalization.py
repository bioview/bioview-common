"""CW demod normalization helpers."""

from __future__ import annotations

import numpy as np


def normalized_amplitude(complex_samples: np.ndarray, tx_amplitude: float) -> float:
    amp = float(np.mean(np.abs(complex_samples)))
    if tx_amplitude > 0:
        return amp / tx_amplitude
    return amp


def differential_phase(
    complex_samples: np.ndarray,
    tx_phase_rad: float,
    prev_phase: float | None,
) -> tuple[float, float]:
    """Return (mean differential phase, last unwrapped phase for continuity)."""
    angles = np.angle(complex_samples)
    if prev_phase is None:
        unwrapped = np.unwrap(angles)
    else:
        unwrapped = np.unwrap(np.concatenate([[prev_phase], angles]))[1:]
    mean_phase = float(np.mean(unwrapped) - tx_phase_rad)
    return mean_phase, float(unwrapped[-1])
