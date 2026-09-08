"""The search must be the VI, point for point and wait for wait.

Checked against the ``Pig_2Ch_NCS_BIOPAC_BalanceSignal`` block diagram:

| VI stage | Points | Value | Wait |
|---|---|---|---|
| Tune Rx1 gain (before) | until in range | Rx1 *and* Tx1 gain +/-1 dB | 250 ms |
| Coarse phase, Tx2 amp 0.1 | 60 | ``i * (360/60)`` | 200 ms |
| Coarse amplitude | 20 | ``i / 20`` | 200 ms |
| Fine phase | ``(6*2)/0.2`` = 60 | ``start + i*0.2``, start = best - 6 | 100 ms |
| Fine amplitude | ``(0.05*2)/0.001`` = 100 | ``start + i*0.001``, best - 0.05 | 100 ms |
| Tune Rx1 gain (after) | until in range | as above | 250 ms |

Each sweep's winner is applied and followed by a 500 ms settle before the next
sweep starts.
"""

import pytest

from bioview_common.signal_schemes.dpic import DpicBalancer, DpicChannel


def _residual(phase, amp):
    """A residual with a single minimum at 174 deg / 0.37, unimodal on both axes.

    Stands in for ``|d + h*a*e^(j*phi)|``: what matters here is that each sweep
    has a winner that is not its first point, so the fine sweeps really do have
    a coarse result to bracket.
    """
    phase_error = abs(((phase - 174.0 + 180.0) % 360.0) - 180.0)
    return abs(amp - 0.37) + phase_error / 1000.0


class _Recorder:
    """Records every value applied and every dwell the balancer asks for."""

    def __init__(self, metric=None):
        self.phases = []
        self.amps = []
        self.waits = []
        self.stages = []
        self._metric = metric or _residual
        self.phase = 0.0
        self.amp = 0.0
        self.gains = {"rx": 30.0, "tx": 30.0}

    def channel(self, **kwargs):
        return DpicChannel(
            inject_tx=1,
            measure_tx=0,
            measure_rx=0,
            set_phase=self._set_phase,
            set_amplitude=self._set_amp,
            read_metric=lambda: self._metric(self.phase, self.amp),
            wait_settle=self.waits.append,
            **kwargs,
        )

    def _set_phase(self, value):
        self.phase = value
        self.phases.append(value)

    def _set_amp(self, value):
        self.amp = value
        self.amps.append(value)


def _run(recorder=None, **balancer_kwargs):
    recorder = recorder or _Recorder()
    balancer = DpicBalancer(
        on_progress=lambda p: recorder.stages.append(p), **balancer_kwargs
    )
    result = balancer.balance(recorder.channel())
    return recorder, result


def test_sweep_geometry_is_the_vis():
    recorder, result = _run()
    assert result.converged

    planned = [(s.name, s.planned) for s in result.stages]
    assert planned == [
        ("coarse phase", 60),
        ("coarse amplitude", 20),
        ("fine phase", 60),
        ("fine amplitude", 100),
    ]


def test_coarse_phase_is_sixty_points_of_six_degrees_at_amplitude_point_one():
    recorder, _ = _run()
    # The seed applies the start point first; the sweep proper follows.
    coarse = recorder.phases[1:61]
    assert coarse[0] == 0.0
    assert coarse[-1] == 354.0
    assert all(
        abs((b - a) - 6.0) < 1e-9 for a, b in zip(coarse, coarse[1:], strict=False)
    )
    # "1. Start with small Tx Amp"
    assert recorder.amps[1] == pytest.approx(0.1)


def test_coarse_amplitude_is_i_over_twenty():
    recorder, _ = _run()
    coarse_amp = recorder.amps[2:22]
    assert coarse_amp[0] == pytest.approx(0.0)
    assert coarse_amp[-1] == pytest.approx(0.95)
    assert all(
        (b - a) == pytest.approx(0.05)
        for a, b in zip(coarse_amp, coarse_amp[1:], strict=False)
    )


def test_fine_sweeps_bracket_the_coarse_winner():
    recorder, result = _run()
    coarse_phase_best = result.stages[0].best_value
    coarse_amp_best = result.stages[1].best_value

    fine_phase = recorder.phases[62:122]
    assert len(fine_phase) == 60
    assert fine_phase[0] == pytest.approx((coarse_phase_best - 6.0) % 360.0)
    assert (fine_phase[1] - fine_phase[0]) == pytest.approx(0.2)

    fine_amp = recorder.amps[23:123]
    assert len(fine_amp) == 100
    assert fine_amp[0] == pytest.approx(max(coarse_amp_best - 0.05, 0.0))
    assert (fine_amp[1] - fine_amp[0]) == pytest.approx(0.001)


def test_dwell_per_point_matches_the_vis_wait_nodes():
    """200 ms per coarse point, 100 ms per fine point, 500 ms between stages."""
    recorder, _ = _run()
    waits = recorder.waits

    # Seed settle, then the four sweeps each followed by a stage settle.
    assert waits[0] == pytest.approx(0.5)
    assert waits[1:61] == [pytest.approx(0.2)] * 60  # coarse phase
    assert waits[61] == pytest.approx(0.5)
    assert waits[62:82] == [pytest.approx(0.2)] * 20  # coarse amplitude
    assert waits[82] == pytest.approx(0.5)
    assert waits[83:143] == [pytest.approx(0.1)] * 60  # fine phase
    assert waits[143] == pytest.approx(0.5)
    assert waits[144:244] == [pytest.approx(0.1)] * 100  # fine amplitude
    assert waits[244] == pytest.approx(0.5)


def test_the_search_is_241_measurements():
    """60 + 20 + 60 + 100 sweep points, plus the seed."""
    _recorder, result = _run()
    assert result.num_measurements == 241


def test_gain_stage_dwells_250ms_and_moves_both_gains():
    recorder = _Recorder()
    # Level rises with Rx gain; starts below the window and needs three steps.
    channel = recorder.channel(
        get_rx_gain=lambda: recorder.gains["rx"],
        set_rx_gain=lambda v: recorder.gains.__setitem__("rx", v),
        get_tx_gain=lambda: recorder.gains["tx"],
        set_tx_gain=lambda v: recorder.gains.__setitem__("tx", v),
    )
    balancer = DpicBalancer()
    channel.read_metric = lambda: 0.2 + 0.1 * (recorder.gains["rx"] - 30.0)

    balancer._tune_gain(
        channel, balancer._measurement_state(channel, 1e18, {"n": 0}), "before"
    )

    assert recorder.gains == {"rx": 33.0, "tx": 33.0}
    assert recorder.waits == [pytest.approx(0.25)] * 3


def test_progress_names_the_stage_and_the_point():
    """The UI needs to be able to say "coarse phase 12/60" while this runs."""
    recorder, _ = _run()
    names = [p["stage"] for p in recorder.stages]
    assert names[0] == "coarse phase"
    assert names.count("coarse phase") == 60
    assert names.count("fine amplitude") == 100

    first = recorder.stages[0]
    assert first["point"] == 1
    assert first["planned"] == 60
    assert first["inject_tx"] == 1
    assert first["measure_tx"] == 0
    assert first["measure_rx"] == 0
    assert "phase_deg" in first and "amplitude" in first and "metric" in first
