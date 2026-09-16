"""``balance_all`` runs one lane per radio, and runs the lanes together."""

import threading
import time

from bioview_common.signal_schemes.dpic import DpicBalancer, DpicChannel


def _channel(device, inject_tx, log=None, hold=0.0):
    """A loop whose metric is minimal at phase 0 / amplitude 0."""
    state = {"phase": 0.0, "amp": 0.0}

    def read_metric():
        if log is not None:
            log.append((device, threading.current_thread().name))
        if hold:
            time.sleep(hold)
        return abs(state["amp"]) + abs(state["phase"]) / 360.0

    return DpicChannel(
        inject_tx=inject_tx,
        measure_tx=0,
        measure_rx=0,
        device=device,
        set_phase=lambda p: state.update(phase=p),
        set_amplitude=lambda a: state.update(amp=a),
        read_metric=read_metric,
    )


def _fast_balancer(**kwargs):
    """A balancer with the VI's dwells stripped out, so a test is not 30 s."""
    settings = {
        "coarse_phase_step_deg": 120.0,
        "coarse_amp_step": 0.5,
        "phase_step_deg": 60.0,
        "amp_step": 0.25,
        "coarse_settle_time_s": 0.0,
        "fine_settle_time_s": 0.0,
        "stage_settle_time_s": 0.0,
        "time_budget_s": 60.0,
    }
    settings.update(kwargs)
    return DpicBalancer(**settings)


def test_lanes_are_grouped_by_radio():
    channels = [
        _channel("usrp-a", 1),
        _channel("usrp-b", 3),
        _channel("usrp-a", 5),
    ]
    lanes = DpicBalancer._lanes(channels)

    assert len(lanes) == 2
    assert [ch.inject_tx for ch in lanes[0]] == [1, 5]
    assert [ch.inject_tx for ch in lanes[1]] == [3]


def test_channels_without_a_radio_share_one_lane():
    """Nothing says two unlabelled loops are independent, so they stay serial."""
    lanes = DpicBalancer._lanes([_channel(None, 1), _channel(None, 3)])
    assert len(lanes) == 1


def test_results_come_back_in_the_order_given():
    channels = [_channel("a", 1), _channel("b", 3), _channel("c", 5)]
    results = _fast_balancer().balance_all(channels)

    assert [r.inject_tx for r in results] == [1, 3, 5]
    assert all(r.converged for r in results)


def test_a_radio_is_only_ever_driven_from_one_thread():
    """A radio's loops must never be measured from two threads at once."""
    log = []
    channels = [_channel("a", 1, log), _channel("b", 3, log), _channel("c", 5, log)]
    _fast_balancer().balance_all(channels)

    threads_per_device = {}
    for device, thread in log:
        threads_per_device.setdefault(device, set()).add(thread)

    assert set(threads_per_device) == {"a", "b", "c"}
    assert all(len(threads) == 1 for threads in threads_per_device.values())


def test_parallel_lanes_finish_faster_than_serial_ones():
    hold = 0.004
    made = lambda: [  # noqa: E731
        _channel("a", 1, hold=hold),
        _channel("b", 3, hold=hold),
        _channel("c", 5, hold=hold),
    ]

    start = time.monotonic()
    _fast_balancer(parallel_devices=False).balance_all(made())
    serial = time.monotonic() - start

    start = time.monotonic()
    _fast_balancer(parallel_devices=True).balance_all(made())
    parallel = time.monotonic() - start

    assert parallel < serial


def test_each_lane_gets_the_whole_budget_not_a_share_of_it():
    """A one-loop lane must not be cut to a third because two others exist."""
    budgets = []
    balancer = _fast_balancer(time_budget_s=90.0)
    original = balancer.balance

    def record(ch, time_budget_s=None):
        budgets.append(time_budget_s)
        return original(ch, time_budget_s)

    balancer.balance = record
    balancer.balance_all([_channel("a", 1), _channel("b", 3), _channel("c", 5)])

    assert budgets == [90.0, 90.0, 90.0]


def test_loops_on_one_radio_still_split_that_radio_s_budget():
    budgets = []
    balancer = _fast_balancer(time_budget_s=90.0)
    original = balancer.balance

    def record(ch, time_budget_s=None):
        budgets.append(time_budget_s)
        return original(ch, time_budget_s)

    balancer.balance = record
    balancer.balance_all([_channel("a", 1), _channel("a", 3), _channel("b", 5)])

    assert sorted(budgets) == [45.0, 45.0, 90.0]


def test_abort_stops_the_lanes_where_they_stand():
    aborted = threading.Event()
    balancer = _fast_balancer(should_abort=aborted.is_set)
    aborted.set()

    assert balancer.balance_all([_channel("a", 1), _channel("b", 3)]) == []
