import numpy as np
import pytest

from bioview_common.signal_schemes import (
    CdmaScheme,
    CwScheme,
    FmcwScheme,
    PulsedDopplerScheme,
    scheme_from_config,
)


@pytest.fixture
def base_config():
    return {
        "samp_rate": 1e6,
        "if_freq": [100e3, 110e3],
        "tx_amplitude": [1.0, 1.0],
        "tx_phase": [0.0, 0.0],
    }


def test_cw_pipeline(base_config):
    base_config["signal_scheme"] = "cw"
    scheme = scheme_from_config(base_config["samp_rate"], 2, base_config)
    assert isinstance(scheme, CwScheme)

    n_samples = 1000
    tx_signals = scheme.generate(n_samples, 0)
    assert tx_signals.shape == (2, n_samples)

    proc = scheme.create_rx_processor(0, 100e3, 10e3, base_config["samp_rate"])
    baseband = proc.process_chunk(tx_signals[0])
    assert baseband.shape == (n_samples,)
    assert np.mean(np.abs(baseband)[100:]) > 0.1


def test_fmcw_pipeline(base_config):
    base_config["signal_scheme"] = "fmcw"
    base_config["fmcw"] = {
        "chirp_start_hz": 50e3,
        "chirp_end_hz": 150e3,
        "chirp_duration_s": 0.001,
        "idle_time_s": 0.0001,
    }
    scheme = scheme_from_config(base_config["samp_rate"], 2, base_config)
    assert isinstance(scheme, FmcwScheme)

    n_samples = 1500
    tx_signals = scheme.generate(n_samples, 0)

    proc = scheme.create_rx_processor(0, 100e3, 100e3, base_config["samp_rate"])
    baseband = proc.process_chunk(tx_signals[0])
    assert baseband.shape == (n_samples,)


def test_pulsed_doppler_pipeline(base_config):
    base_config["signal_scheme"] = "pulsed_doppler"
    base_config["pulsed_doppler"] = {
        "pulse_width_s": 1e-4,
        "pri_s": 1e-3,
        "doppler_if_hz": 100e3,
    }
    scheme = scheme_from_config(base_config["samp_rate"], 2, base_config)
    assert isinstance(scheme, PulsedDopplerScheme)

    n_samples = 2000
    tx_signals = scheme.generate(n_samples, 0)

    proc = scheme.create_rx_processor(0, 100e3, 10e3, base_config["samp_rate"])
    baseband = proc.process_chunk(tx_signals[0])
    assert baseband.shape == (n_samples,)


def test_cdma_pipeline(base_config):
    base_config["signal_scheme"] = "cdma"
    base_config["cdma"] = {
        "chip_rate_hz": 100e3,
        "code_length": 16,
        "code_type": "Walsh-Hadamard",
    }
    scheme = scheme_from_config(base_config["samp_rate"], 2, base_config)
    assert isinstance(scheme, CdmaScheme)

    n_samples = 1000
    tx_signals = scheme.generate(n_samples, 0)

    proc0 = scheme.create_rx_processor(0, 100e3, 10e3, base_config["samp_rate"])
    baseband0 = proc0.process_chunk(tx_signals[0])

    assert np.mean(np.abs(baseband0)[100:]) > 0.1

    proc_cross = scheme.create_rx_processor(0, 100e3, 10e3, base_config["samp_rate"])
    baseband_cross = proc_cross.process_chunk(tx_signals[1])

    cross_power = np.mean(np.abs(baseband_cross)[100:])
    own_power = np.mean(np.abs(baseband0)[100:])
    assert cross_power < own_power * 0.2
