"""Calibration SNR and harmonic detection."""

import numpy as np
import pytest

from bioview_common import calibration_snr_db, top_harmonics


@pytest.fixture
def pilot():
    """Ten seconds of a 10 Hz pilot at 200 Hz, as the cal-ref row carries it."""
    t = np.arange(0, 10.0, 1 / 200.0)
    return np.sin(2 * np.pi * 10.0 * t)


def test_a_clean_copy_of_the_pilot_is_almost_all_signal(pilot):
    result = calibration_snr_db(0.4 * pilot, pilot)
    assert result["snr_db"] > 60
    assert result["correlation"] == pytest.approx(1.0, abs=1e-6)
    assert result["gain"] == pytest.approx(0.4, rel=1e-6)


def test_added_noise_lowers_the_snr_in_the_expected_direction(pilot):
    rng = np.random.default_rng(0)
    quiet = calibration_snr_db(pilot + 0.01 * rng.standard_normal(pilot.size), pilot)
    noisy = calibration_snr_db(pilot + 0.5 * rng.standard_normal(pilot.size), pilot)
    assert quiet["snr_db"] > noisy["snr_db"] + 20


def test_a_row_unrelated_to_the_pilot_reports_a_dead_channel(pilot):
    """The point of correlating: a large, perfectly clean, *wrong* signal."""
    t = np.arange(0, 10.0, 1 / 200.0)
    unrelated = 5.0 * np.sin(2 * np.pi * 33.0 * t)
    assert calibration_snr_db(unrelated, pilot)["snr_db"] < -20


def test_a_constant_offset_counts_as_neither_signal_nor_noise(pilot):
    """A DC level carries no information about the channel, either way."""
    rng = np.random.default_rng(1)
    noise = 0.05 * rng.standard_normal(pilot.size)
    with_offset = calibration_snr_db(pilot + noise + 12.0, pilot)
    without = calibration_snr_db(pilot + noise, pilot)
    assert with_offset["snr_db"] == pytest.approx(without["snr_db"])


def test_a_reference_with_no_pilot_in_it_is_reported_as_unmeasurable(pilot):
    """What an off calibration overlay looks like: a reference row of zeros."""
    assert calibration_snr_db(pilot, np.zeros_like(pilot)) is None


def test_too_short_a_window_is_not_analysed(pilot):
    assert calibration_snr_db(pilot[:8], pilot[:8]) is None


def test_rows_of_different_length_are_aligned_on_their_newest_samples(pilot):
    """Both rows come from one chunk stream, so the tails are what line up."""
    result = calibration_snr_db(0.4 * pilot, pilot[100:])
    assert result["snr_db"] > 60
    assert result["n_samples"] == pilot.size - 100


def test_harmonics_finds_a_fundamental_and_its_overtones():
    fs = 200.0
    t = np.arange(0, 20.0, 1 / fs)
    signal = (
        1.0 * np.sin(2 * np.pi * 1.2 * t)
        + 0.5 * np.sin(2 * np.pi * 2.4 * t)
        + 0.25 * np.sin(2 * np.pi * 3.6 * t)
    )
    peaks = top_harmonics(signal, samp_rate=fs, count=3)

    assert [round(p["freq_hz"], 1) for p in peaks] == [1.2, 2.4, 3.6]
    assert peaks[0]["relative_db"] == pytest.approx(0.0)
    assert peaks[1]["relative_db"] == pytest.approx(-6.0, abs=1.0)


def test_dc_and_drift_are_never_returned_as_harmonics():
    """A large offset plus a slow ramp is not a rate, however strong it is."""
    fs = 100.0
    t = np.arange(0, 20.0, 1 / fs)
    signal = 50.0 + 3.0 * t + np.sin(2 * np.pi * 5.0 * t)
    peaks = top_harmonics(signal, samp_rate=fs, count=3)

    assert peaks
    assert peaks[0]["freq_hz"] == pytest.approx(5.0, abs=0.2)
    assert all(p["freq_hz"] > 0 for p in peaks)


def test_a_flat_row_has_no_harmonics():
    assert top_harmonics(np.full(1024, 7.0), samp_rate=100.0) == []


def test_min_freq_excludes_bands_that_are_not_being_looked_for():
    fs = 100.0
    t = np.arange(0, 20.0, 1 / fs)
    signal = 4.0 * np.sin(2 * np.pi * 0.2 * t) + np.sin(2 * np.pi * 9.0 * t)

    unfiltered = top_harmonics(signal, samp_rate=fs, count=1)
    assert unfiltered[0]["freq_hz"] == pytest.approx(0.2, abs=0.1)

    above_1hz = top_harmonics(signal, samp_rate=fs, count=1, min_freq_hz=1.0)
    assert above_1hz[0]["freq_hz"] == pytest.approx(9.0, abs=0.2)
