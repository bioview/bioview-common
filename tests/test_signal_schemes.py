"""Tests for signal scheme generation."""

import numpy as np

from bioview_common.signal_schemes import (
    BurstEnvelope,
    CwScheme,
    DpicBalancer,
    FmcwScheme,
    PulsedDopplerScheme,
    scheme_from_config,
)


def test_cw_scheme_generate_shape():
    scheme = CwScheme(
        samp_rate=1e6,
        if_freq=[100e3, 110e3],
        tx_amplitude=[1.0, 0.5],
        tx_phase_deg=[0.0, 90.0],
    )
    buf = scheme.generate(1000, 0)
    assert buf.shape == (2, 1000)
    assert np.iscomplexobj(buf)


def test_cw_cycle_length_without_calibration():
    scheme = CwScheme(
        samp_rate=1e6,
        if_freq=[100e3],
        tx_amplitude=[1.0],
        tx_phase_deg=[0.0],
        calibration={"enabled": False},
    )
    assert scheme.cycle_length() is not None
    scheme.set_calibration_enabled(True)
    assert scheme.cycle_length() is None


def test_burst_envelope_gated():
    env = BurstEnvelope(fs=1e6, num_pulses=2, packet_spacing_s=1.0, envelope_freq_hz=10.0)
    wave, gate = env.generate(10000, 0)
    assert wave.shape == (10000,)
    assert np.all(wave[~gate.astype(bool)] == 0)


def test_fmcw_scheme():
    scheme = FmcwScheme(
        samp_rate=1e6,
        num_tx=1,
        fmcw_config={"chirp_start_hz": 50e3, "chirp_end_hz": 150e3, "chirp_duration_s": 0.001},
        tx_amplitude=[1.0],
    )
    buf = scheme.generate(2000, 0)
    assert buf.shape == (1, 2000)
    assert np.count_nonzero(buf) > 0


def test_pulsed_doppler_scheme():
    scheme = PulsedDopplerScheme(
        samp_rate=1e6,
        num_tx=1,
        pd_config={"pulse_width_s": 10e-6, "pri_s": 1e-3, "doppler_if_hz": 100e3},
        tx_amplitude=[1.0],
    )
    buf = scheme.generate(5000, 0)
    assert buf.shape == (1, 5000)


def test_dpic_balancer_picks_minimum():
    calls = []

    def set_phase(_tx, phase):
        calls.append(("phase", phase))

    def set_amplitude(_tx, amp):
        calls.append(("amp", amp))

    metrics = {0.0: 1.0, 45.0: 0.2, 90.0: 0.8}

    def read_metric():
        last = [c for c in calls if c[0] == "phase"]
        if not last:
            return 1.0
        return metrics.get(last[-1][1], 1.0)

    balancer = DpicBalancer(phase_step_deg=45.0, amp_step=1.0, settle_time_s=0)
    result = balancer.run_pair(1, 0, set_phase, set_amplitude, read_metric, lambda: None)
    assert result.best_phase_deg == 45.0


def test_scheme_from_config_factory():
    scheme = scheme_from_config(
        1e6,
        2,
        {"signal_scheme": "cw", "if_freq": [100e3, 110e3], "tx_amplitude": [1, 1]},
    )
    assert scheme.scheme_type == "cw"
