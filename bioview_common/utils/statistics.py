"""Per-channel signal statistics: calibration SNR and harmonic content."""

from __future__ import annotations

import numpy as np


MIN_SAMPLES = 32

REFERENCE_VARIANCE_FLOOR = 1e-18


def calibration_snr_db(received, reference) -> dict | None:
    """SNR (dB) of ``received`` against the known calibration ``reference``."""
    rx = np.asarray(received, dtype=np.float64).ravel()
    ref = np.asarray(reference, dtype=np.float64).ravel()

    n = min(rx.size, ref.size)
    if n < MIN_SAMPLES:
        return None
    rx, ref = rx[-n:], ref[-n:]

    if not (np.all(np.isfinite(rx)) and np.all(np.isfinite(ref))):
        return None

    ref_centred = ref - ref.mean()
    ref_var = float(ref_centred @ ref_centred) / n
    if ref_var < REFERENCE_VARIANCE_FLOOR:
        return None

    rx_centred = rx - rx.mean()
    gain = float(ref_centred @ rx_centred) / float(ref_centred @ ref_centred)

    signal = gain * ref_centred
    noise = rx_centred - signal
    signal_power = float(signal @ signal) / n
    noise_power = float(noise @ noise) / n

    rx_var = float(rx_centred @ rx_centred) / n
    correlation = 0.0
    if rx_var > 0:
        correlation = float(signal_power / rx_var) ** 0.5
        correlation = correlation if gain >= 0 else -correlation

    if noise_power <= 0:
        snr_db = float("inf")
    elif signal_power <= 0:
        snr_db = float("-inf")
    else:
        snr_db = 10.0 * np.log10(signal_power / noise_power)

    return {
        "snr_db": snr_db,
        "correlation": correlation,
        "gain": gain,
        "signal_power": signal_power,
        "noise_power": noise_power,
        "n_samples": n,
    }


def top_harmonics(
    samples,
    samp_rate: float,
    count: int = 3,
    min_freq_hz: float = 0.0,
) -> list[dict]:
    """The ``count`` strongest spectral peaks above DC, strongest first."""
    x = np.asarray(samples, dtype=np.float64).ravel()
    if x.size < MIN_SAMPLES or samp_rate <= 0 or count <= 0:
        return []
    if not np.all(np.isfinite(x)):
        return []

    x = x - x.mean()
    if not np.any(x):
        return []

    windowed = x * np.hanning(x.size)
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(samp_rate))

    floor_hz = max(float(min_freq_hz), 2.0 * float(samp_rate) / x.size)
    usable = freqs >= floor_hz
    if spectrum.size < 3 or not np.any(usable):
        return []

    interior = np.zeros_like(usable)
    interior[1:-1] = (spectrum[1:-1] > spectrum[:-2]) & (spectrum[1:-1] >= spectrum[2:])
    candidates = np.flatnonzero(usable & interior)
    if candidates.size == 0:
        return []

    order = candidates[np.argsort(spectrum[candidates])[::-1]][:count]
    peak = float(spectrum[order[0]])

    harmonics = []
    for idx in order:
        magnitude = float(spectrum[idx])
        harmonics.append(
            {
                "freq_hz": float(freqs[idx]),
                "magnitude": magnitude,
                "relative_db": (
                    20.0 * np.log10(magnitude / peak)
                    if magnitude > 0 and peak > 0
                    else float("-inf")
                ),
            }
        )
    return harmonics
