"""Tests for signal scheme generation."""

import numpy as np

from bioview_common.signal_schemes import (
    BurstEnvelope,
    CwScheme,
    DpicBalancer,
    DpicChannel,
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
    env = BurstEnvelope(
        fs=1e6, num_pulses=2, packet_spacing_s=1.0, envelope_freq_hz=10.0
    )
    wave, gate = env.generate(10000, 0)
    assert wave.shape == (10000,)
    assert np.all(wave[~gate.astype(bool)] == 0)


def test_fmcw_scheme():
    scheme = FmcwScheme(
        samp_rate=1e6,
        num_tx=1,
        fmcw_config={
            "chirp_start_hz": 50e3,
            "chirp_end_hz": 150e3,
            "chirp_duration_s": 0.001,
        },
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
    state = {"phase": 0.0, "amp": 0.5}
    metrics = {0.0: 1.0, 45.0: 0.2, 90.0: 0.8}

    ch = DpicChannel(
        inject_tx=1,
        measure_tx=0,
        measure_rx=0,
        set_phase=lambda p: state.update(phase=p),
        set_amplitude=lambda a: state.update(amp=a),
        read_metric=lambda: metrics.get(state["phase"], 1.0),
        start_amplitude=0.5,
    )
    balancer = DpicBalancer(
        coarse_phase_step_deg=45.0,
        phase_step_deg=45.0,
        coarse_amp_step=1.0,
        amp_step=1.0,
    )
    result = balancer.balance(ch)
    assert result.best_phase_deg == 45.0
    assert result.method == "grid"


def test_dpic_sweeps_match_the_labview_vi():
    """Grid geometry is the VI's: 60/20 coarse points, +/- one coarse step fine."""
    phases, amps = [], []
    state = {"phase": 0.0, "amp": 0.0}

    def set_phase(p):
        state["phase"] = p
        phases.append(p)

    def set_amplitude(a):
        state["amp"] = a
        amps.append(a)

    # Minimum at phase 174 deg / amplitude 0.372, on neither coarse grid.
    def read_metric():
        return abs(
            0.372 * np.exp(1j * np.deg2rad(174.0))
            - state["amp"] * np.exp(1j * np.deg2rad(state["phase"]))
        )

    balancer = DpicBalancer(time_budget_s=1e6)
    result = balancer.balance(
        DpicChannel(
            inject_tx=1,
            measure_tx=0,
            measure_rx=0,
            set_phase=set_phase,
            set_amplitude=set_amplitude,
            read_metric=read_metric,
        )
    )

    # 1 seed + 60 coarse phase + 20 coarse amp + 60 fine phase + 100 fine amp.
    assert result.num_measurements == 241
    # Coarse phase sweep: 0, 6, ... 354, all at the 0.1 probe amplitude.
    assert phases[1:61] == [6.0 * i for i in range(60)]
    assert amps[1] == 0.1
    # Coarse amplitude sweep: 0, 0.05, ... 0.95.
    assert len(amps[2:22]) == 20
    assert abs(amps[21] - 0.95) < 1e-9
    # Fine sweeps: 60 phase points of 0.2 deg, 100 amplitude points of 0.001.
    fine_phase = phases[62:122]
    assert len(fine_phase) == 60
    assert abs((fine_phase[1] - fine_phase[0]) - 0.2) < 1e-9
    fine_amp = amps[23:123]
    assert len(fine_amp) == 100
    assert abs((fine_amp[1] - fine_amp[0]) - 0.001) < 1e-9

    assert abs(result.best_phase_deg - 174.0) <= 0.2
    assert abs(result.best_amplitude - 0.372) <= 0.001


def _gain_channel(level, gains, **kwargs):
    """A channel whose measured level is a function of the gains the ladder sets."""
    return DpicChannel(
        inject_tx=1,
        measure_tx=0,
        measure_rx=0,
        set_phase=lambda p: None,
        set_amplitude=lambda a: None,
        read_metric=lambda: level(gains),
        get_rx_gain=lambda: gains["rx"],
        set_rx_gain=lambda v: gains.__setitem__("rx", v),
        get_tx_gain=lambda: gains["tx"],
        set_tx_gain=lambda v: gains.__setitem__("tx", v),
        **kwargs,
    )


def test_dpic_gain_stage_runs_on_both_sides_of_the_search():
    """The VI tunes gain before the sweep and again once the path is nulled."""
    stages = []
    gains = {"rx": 20.0, "tx": 20.0}
    balancer = DpicBalancer(
        coarse_phase_step_deg=90.0,
        phase_step_deg=90.0,
        coarse_amp_step=0.5,
        amp_step=0.5,
        on_progress=lambda p: stages.append(p["stage"]),
    )
    # Already in range, so each stage measures once and returns.
    result = balancer.balance(_gain_channel(lambda g: 0.5, gains))

    assert result.converged
    assert stages[0] == "gain (before)"
    assert stages[-1] == "gain (after)"


def test_dpic_gain_ladder_steps_tx_and_rx_together():
    """The VI's +/-1 dB ladder moves the measure Tx and the Rx in lockstep."""
    gains = {"rx": 20.0, "tx": 20.0}

    # Level starts far below target and rises 0.05 per dB of Rx gain, so the
    # ladder has to climb six steps to reach the 0.45..0.55 window.
    def level(g):
        return 0.2 + 0.05 * (g["rx"] - 20.0)

    balancer = DpicBalancer(gain_step_db=1.0, amp_target=0.5, amp_tolerance=0.05)
    balancer._tune_gain(
        _gain_channel(level, gains),
        balancer._measurement_state(_gain_channel(level, gains), 1e18, {"n": 0}),
        "before",
    )

    assert gains["rx"] == 25.0
    assert gains["tx"] == 25.0, "the measure Tx must track the Rx, as in the VI"


def test_dpic_gain_ladder_stops_at_the_end_of_the_range():
    """A level that can never be reached must not spin forever."""
    gains = {"rx": 70.0, "tx": 70.0}
    balancer = DpicBalancer(max_gain_steps=200)
    ch = _gain_channel(
        lambda g: 0.0,  # never reaches the target, whatever the gain
        gains,
        rx_gain_range=(0.0, 76.0),
        tx_gain_range=(0.0, 76.0),
    )
    balancer._tune_gain(ch, balancer._measurement_state(ch, 1e18, {"n": 0}), "before")

    assert gains["rx"] == 76.0
    assert gains["tx"] == 76.0


def test_scheme_from_config_factory():
    scheme = scheme_from_config(
        1e6,
        2,
        {"signal_scheme": "cw", "if_freq": [100e3, 110e3], "tx_amplitude": [1, 1]},
    )
    assert scheme.scheme_type == "cw"


# ---------------------------------------------------------------------------
# Calibration pilot: parity with the reference B210_2CHANNEL implementation.
# ---------------------------------------------------------------------------


def _reference_triangle(fs, freq, n_tri, period_s, offset, amplitude, n, start):
    """Verbatim port of TriangleGenerator.next() from B210_2CHANNEL.py."""
    period_len = max(1, int(round(period_s * fs)))
    burst_samples = int(round(n_tri * fs / freq))
    burst_len = max(1, min(burst_samples, period_len))

    idx = start + np.arange(n, dtype=np.int64)
    pos = idx % period_len
    gate = pos < burst_len

    t_local = pos.astype(np.float64) / fs
    phase = t_local * freq
    wave = 2.0 * np.abs(2.0 * (phase - np.floor(phase + 0.5))) - 1.0
    wave = wave * amplitude + offset

    out = np.zeros(n, dtype=np.float32)
    out[gate] = wave[gate].astype(np.float32)
    return out, gate.astype(np.float32)


def test_burst_envelope_matches_reference_triangle():
    fs, freq, n_tri, period_s = 1e6, 10.0, 5, 1.0
    env = BurstEnvelope(
        fs=fs,
        shape="triangle",
        num_pulses=n_tri,
        packet_spacing_s=period_s,
        envelope_freq_hz=freq,
        envelope_offset=0.0,
    )
    for start in (0, 12345, 999_997):
        got, gate = env.generate(4096, start)
        want, want_gate = _reference_triangle(
            fs, freq, n_tri, period_s, 0.0, 1.0, 4096, start
        )
        # BioView carries the amplitude as the scheme's modulation_depth, so the
        # envelope itself is the reference triangle at amplitude 1.
        np.testing.assert_allclose(got, want, atol=1e-6)
        np.testing.assert_array_equal(gate, want_gate)


def test_cw_calibration_overlay_matches_reference_modulation():
    """Reference transmits carrier * (1 + tri); depth lives in the tri amplitude."""
    fs, depth = 1e6, 0.5
    scheme = CwScheme(
        samp_rate=fs,
        if_freq=[100e3],
        tx_amplitude=[1.0],
        tx_phase_deg=[0.0],
        calibration={
            "enabled": True,
            "inject_channels": [0],
            "modulation_depth": depth,
            "num_pulses": 5,
            "envelope_freq_hz": 10.0,
            "packet_spacing_s": 1.0,
        },
    )
    n = 8192
    out = scheme.generate(n, 0)[0]
    tri, _ = _reference_triangle(fs, 10.0, 5, 1.0, 0.0, depth, n, 0)
    t = np.arange(n) / fs
    want = (np.exp(1j * 2 * np.pi * 100e3 * t) * (1.0 + tri)).astype(np.complex64)
    np.testing.assert_allclose(np.abs(out), np.abs(want), rtol=1e-5, atol=1e-6)


def test_calibration_reference_is_gated_envelope():
    scheme = CwScheme(
        samp_rate=1e6,
        if_freq=[100e3],
        tx_amplitude=[1.0],
        tx_phase_deg=[0.0],
        calibration={
            "enabled": True,
            "inject_channels": [0],
            "num_pulses": 5,
            "envelope_freq_hz": 1000.0,
            "packet_spacing_s": 0.01,
        },
    )
    ref = scheme.get_calibration_reference(0, 0, 20000)
    assert ref.shape == (20000,)
    assert np.any(ref != 0.0)  # bursts present
    assert np.any(ref == 0.0)  # gated off between bursts
    # A channel outside inject_channels carries no reference.
    assert not np.any(scheme.get_calibration_reference(1, 0, 1000))


def test_pulse_duration_override_changes_burst_length():
    """pulse_duration_s used to be accepted and silently ignored."""
    base = BurstEnvelope(fs=1e6, num_pulses=5, envelope_freq_hz=10.0)
    override = BurstEnvelope(
        fs=1e6, num_pulses=5, envelope_freq_hz=10.0, pulse_duration_s=0.05
    )
    assert base.burst_len == 500_000
    assert override.burst_len == 250_000


def test_calibration_toggles_on_every_scheme():
    """Calibration params used to be wired up on CW only."""
    cal = {"enabled": False, "inject_channels": [0]}
    schemes = [
        CwScheme(1e6, [100e3], [1.0], [0.0], calibration=dict(cal)),
        FmcwScheme(1e6, 1, {}, [1.0], calibration=dict(cal)),
        PulsedDopplerScheme(1e6, 1, {}, [1.0], [100e3], calibration=dict(cal)),
    ]
    for scheme in schemes:
        assert scheme.cycle_length() is not None
        scheme.update_param("calibration.enabled", True)
        assert scheme.calibration_enabled(), scheme.scheme_type
        # Enabling calibration makes the waveform aperiodic, which is what tells
        # TransmitWorker to stop replaying its cyclic buffer.
        assert scheme.cycle_length() is None, scheme.scheme_type
        scheme.update_param("calibration.enabled", False)
        assert not scheme.calibration_enabled()


def test_dpic_balancer_seeds_from_current_settings():
    """The search must never silently settle on amplitude 0."""
    state = {"phase": 30.0, "amp": 0.7}
    balancer = DpicBalancer(phase_step_deg=5.0, amp_step=0.1)
    result = balancer.balance(
        DpicChannel(
            inject_tx=1,
            measure_tx=0,
            measure_rx=0,
            set_phase=lambda p: state.update(phase=p),
            set_amplitude=lambda a: state.update(amp=a),
            read_metric=lambda: None,  # measurement path is silent
            start_phase_deg=30.0,
            start_amplitude=0.7,
        )
    )
    assert not result.converged
    assert state == {"phase": 30.0, "amp": 0.7}
