"""Direct-path interference cancellation."""

from __future__ import annotations

import contextlib
import math
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


def _no_wait(_seconds: float = 0.0) -> None:
    """Default ``wait_settle``: nothing to wait for."""


@dataclass
class DpicChannel:
    """Everything the balancer needs to drive and observe one cancellation loop."""

    inject_tx: int
    measure_tx: int
    measure_rx: int

    device: str | None = None

    set_phase: Callable[[float], None] = None
    set_amplitude: Callable[[float], None] = None
    read_metric: Callable[[], float | None] = None
    wait_settle: Callable[[float], None] = _no_wait

    get_gain: Callable[[], float] | None = None

    get_rx_gain: Callable[[], float] | None = None
    set_rx_gain: Callable[[float], None] | None = None
    get_tx_gain: Callable[[], float] | None = None
    set_tx_gain: Callable[[float], None] | None = None
    rx_gain_range: tuple[float, float] = (0.0, 76.0)
    tx_gain_range: tuple[float, float] = (0.0, 90.0)

    start_phase_deg: float = 0.0
    start_amplitude: float = 0.0

    def tunes_gain(self) -> bool:
        return None not in (
            self.get_rx_gain,
            self.set_rx_gain,
            self.get_tx_gain,
            self.set_tx_gain,
        )


@dataclass
class DpicStage:
    """What one sweep actually did, so a short balance is never ambiguous."""

    name: str
    planned: int
    visited: int = 0
    measured: int = 0
    best_value: float = float("nan")
    best_metric: float = float("nan")
    elapsed_s: float = 0.0

    @property
    def truncated(self) -> bool:
        return self.visited < self.planned

    def describe(self) -> str:
        return (
            f"{self.name}: {self.measured}/{self.planned} measured"
            + (f" (TRUNCATED at {self.visited})" if self.truncated else "")
            + (
                f", best={self.best_value:.4g} metric={self.best_metric:.4g}"
                if self.measured
                else ", no usable metric"
            )
            + f", {self.elapsed_s:.1f}s"
        )


@dataclass
class DpicBalanceResult:
    inject_tx: int
    measure_tx: int
    best_phase_deg: float
    best_amplitude: float
    min_metric: float
    measure_rx: int = -1
    inject_gain_db: float = float("nan")
    measure_tx_gain_db: float = float("nan")
    measure_rx_gain_db: float = float("nan")
    method: str = "none"
    converged: bool = True
    num_measurements: int = 0
    elapsed_s: float = 0.0
    start_metric: float = float("nan")
    stages: list[DpicStage] = field(default_factory=list)
    message: str = ""

    @property
    def truncated(self) -> bool:
        """True when the time budget cut any sweep short."""
        return any(stage.truncated for stage in self.stages)

    @property
    def null_depth_db(self) -> float:
        if not (self.start_metric > 0 and self.min_metric > 0):
            return float("nan")
        return 20.0 * math.log10(self.start_metric / self.min_metric)


@dataclass
class DpicBalancer:
    """Coarse-to-fine grid search for the digital weight that nulls the direct path."""

    coarse_phase_step_deg: float = 6.0
    coarse_amp_step: float = 0.05
    coarse_probe_amplitude: float = 0.1

    phase_step_deg: float = 0.2
    amp_step: float = 0.001

    max_amplitude: float = 1.0

    coarse_settle_time_s: float = 0.2
    fine_settle_time_s: float = 0.1
    stage_settle_time_s: float = 0.5

    amp_target: float = 0.5
    amp_tolerance: float = 0.05
    gain_step_db: float = 1.0
    gain_settle_time_s: float = 0.25
    max_gain_steps: int = 60

    time_budget_s: float = 300.0

    should_abort: Callable[[], bool] | None = None

    on_progress: Callable[[dict], None] | None = None

    parallel_devices: bool = True

    @staticmethod
    def _points(start: float, step: float, count: int) -> list[float]:
        return [start + i * step for i in range(max(int(count), 0))]

    def _report(self, ch: DpicChannel, stage_name: str, **fields):
        """Publish the loop's live state. A reporting failure never stops a search."""
        if self.on_progress is None:
            return
        payload = {
            "stage": stage_name,
            "inject_tx": ch.inject_tx,
            "measure_tx": ch.measure_tx,
            "measure_rx": ch.measure_rx,
            **fields,
        }
        if ch.get_rx_gain is not None:
            payload.setdefault("rx_gain_db", ch.get_rx_gain())
        if ch.get_tx_gain is not None:
            payload.setdefault("tx_gain_db", ch.get_tx_gain())
        with contextlib.suppress(Exception):
            self.on_progress(payload)

    def _sweep(
        self, name, values, apply, state, settle_s, ch
    ) -> tuple[float | None, DpicStage]:
        """Measure at every value; return the argmin and a record of the sweep."""
        stage = DpicStage(name=name, planned=len(values))
        started = time.monotonic()
        best_value = None
        best_metric = math.inf
        for index, value in enumerate(values):
            if state["expired"]():
                break
            stage.visited += 1
            applied = apply(value)
            state["settle"](settle_s)
            metric = state["measure"]()
            self._report(
                ch,
                name,
                point=index + 1,
                planned=len(values),
                value=applied,
                metric=metric,
                phase_deg=state["phase"](),
                amplitude=state["amplitude"](),
            )
            if metric is None or not math.isfinite(metric):
                continue
            stage.measured += 1
            if metric < best_metric:
                best_metric = metric
                best_value = value
        stage.elapsed_s = time.monotonic() - started
        if best_value is not None:
            stage.best_value = best_value
            stage.best_metric = best_metric
        state["stages"].append(stage)
        return best_value, stage

    def _tune_gain(self, ch: DpicChannel, state: dict, when: str) -> None:
        """The VI's "Tune Rx1 Gain to DC value of ~0.5" stage."""
        if not ch.tunes_gain():
            return

        lower = self.amp_target - self.amp_tolerance
        upper = self.amp_target + self.amp_tolerance
        rx_min, rx_max = ch.rx_gain_range
        tx_min, tx_max = ch.tx_gain_range

        for step in range(max(int(self.max_gain_steps), 0)):
            if state["expired"]():
                return
            level = state["measure"]()
            self._report(
                ch,
                f"gain ({when})",
                point=step + 1,
                planned=self.max_gain_steps,
                metric=level,
                phase_deg=state["phase"](),
                amplitude=state["amplitude"](),
            )
            if level is None or not math.isfinite(level):
                return
            if lower <= level <= upper:
                return

            delta = self.gain_step_db if level < lower else -self.gain_step_db
            rx_gain = min(max(ch.get_rx_gain() + delta, rx_min), rx_max)
            tx_gain = min(max(ch.get_tx_gain() + delta, tx_min), tx_max)

            if rx_gain == ch.get_rx_gain() and tx_gain == ch.get_tx_gain():
                return

            ch.set_rx_gain(rx_gain)
            ch.set_tx_gain(tx_gain)
            state["settle"](self.gain_settle_time_s)

    def _search(self, ch: DpicChannel, state: dict) -> dict | None:
        """The VI's four sweeps. Returns the best point, or None if none measured."""

        def apply_phase(v):
            value = v % 360.0
            ch.set_phase(value)
            state["last"]["phase"] = value
            return value

        def apply_amp(v):
            value = min(max(v, 0.0), self.max_amplitude)
            ch.set_amplitude(value)
            state["last"]["amp"] = value
            return value

        phase = float(ch.start_phase_deg) % 360.0
        amp = min(max(self.coarse_probe_amplitude, 0.0), self.max_amplitude)
        metric = math.inf

        apply_amp(amp)
        found, stage = self._sweep(
            "coarse phase",
            self._points(
                0.0,
                self.coarse_phase_step_deg,
                round(360.0 / self.coarse_phase_step_deg),
            ),
            apply_phase,
            state,
            self.coarse_settle_time_s,
            ch,
        )
        if found is not None:
            phase, metric = found % 360.0, stage.best_metric
        apply_phase(phase)
        state["settle"](self.stage_settle_time_s)

        found, stage = self._sweep(
            "coarse amplitude",
            self._points(
                0.0,
                self.coarse_amp_step,
                round(self.max_amplitude / self.coarse_amp_step),
            ),
            apply_amp,
            state,
            self.coarse_settle_time_s,
            ch,
        )
        if found is not None:
            amp, metric = found, stage.best_metric
        apply_amp(amp)
        state["settle"](self.stage_settle_time_s)

        found, stage = self._sweep(
            "fine phase",
            self._points(
                phase - self.coarse_phase_step_deg,
                self.phase_step_deg,
                round(2.0 * self.coarse_phase_step_deg / self.phase_step_deg),
            ),
            apply_phase,
            state,
            self.fine_settle_time_s,
            ch,
        )
        if found is not None:
            phase, metric = found % 360.0, stage.best_metric
        apply_phase(phase)
        state["settle"](self.stage_settle_time_s)

        found, stage = self._sweep(
            "fine amplitude",
            self._points(
                amp - self.coarse_amp_step,
                self.amp_step,
                round(2.0 * self.coarse_amp_step / self.amp_step),
            ),
            apply_amp,
            state,
            self.fine_settle_time_s,
            ch,
        )
        if found is not None:
            amp, metric = found, stage.best_metric
        amp = min(max(amp, 0.0), self.max_amplitude)
        apply_amp(amp)
        state["settle"](self.stage_settle_time_s)

        if not math.isfinite(metric):
            return None
        return {"phase": phase, "amp": amp, "metric": metric}

    def _measurement_state(self, ch: DpicChannel, deadline: float, counter: dict):
        """The callbacks a search runs on, sharing one counter and stage list."""
        last = {"phase": float(ch.start_phase_deg), "amp": float(ch.start_amplitude)}

        def expired():
            if self.should_abort is not None and self.should_abort():
                return True
            return time.monotonic() >= deadline

        def settle(seconds: float):
            if seconds > 0:
                ch.wait_settle(seconds)

        def measure():
            value = ch.read_metric()
            if value is not None:
                counter["n"] += 1
            return value

        return {
            "expired": expired,
            "settle": settle,
            "measure": measure,
            "phase": lambda: last["phase"],
            "amplitude": lambda: last["amp"],
            "last": last,
            "stages": [],
        }

    def _failed(self, ch, counter, elapsed, start_metric, stages, message):
        """Restore the pre-search settings and report why."""
        ch.set_phase(float(ch.start_phase_deg))
        ch.set_amplitude(float(ch.start_amplitude))
        return DpicBalanceResult(
            inject_tx=ch.inject_tx,
            measure_tx=ch.measure_tx,
            measure_rx=ch.measure_rx,
            best_phase_deg=float(ch.start_phase_deg),
            best_amplitude=float(ch.start_amplitude),
            min_metric=0.0,
            inject_gain_db=ch.get_gain() if ch.get_gain else float("nan"),
            method="none",
            converged=False,
            num_measurements=counter["n"],
            elapsed_s=elapsed,
            start_metric=start_metric,
            stages=stages,
            message=message,
        )

    def balance(
        self, ch: DpicChannel, time_budget_s: float | None = None
    ) -> DpicBalanceResult:
        """Balance one loop. ``time_budget_s`` overrides the balancer's own."""
        budget = self.time_budget_s if time_budget_s is None else float(time_budget_s)
        t_start = time.monotonic()
        counter = {"n": 0}

        gain_state = self._measurement_state(ch, time.monotonic() + budget, counter)
        self._tune_gain(ch, gain_state, "before")

        deadline = time.monotonic() + budget
        state = self._measurement_state(ch, deadline, counter)
        stages = state["stages"]

        ch.set_phase(float(ch.start_phase_deg))
        ch.set_amplitude(float(ch.start_amplitude))
        state["settle"](self.stage_settle_time_s)
        seed = state["measure"]()
        start_metric = (
            float(seed) if seed is not None and math.isfinite(seed) else float("nan")
        )

        if seed is None:
            return self._failed(
                ch,
                counter,
                time.monotonic() - t_start,
                start_metric,
                stages,
                "no metric could be read before the search started -- check that "
                "the measure Tx/Rx pair is in the channel map and streaming",
            )

        best = self._search(ch, state)
        elapsed = time.monotonic() - t_start
        gain_db = ch.get_gain() if ch.get_gain else float("nan")

        if best is None:
            visited = sum(stage.visited for stage in stages)
            return self._failed(
                ch,
                counter,
                elapsed,
                start_metric,
                stages,
                (f"the {budget:.0f}s budget expired before any sweep point was measured")
                if visited == 0
                else "no sweep point returned a usable metric",
            )

        after_state = self._measurement_state(ch, time.monotonic() + budget, counter)
        after_state["last"].update({"phase": best["phase"], "amp": best["amp"]})
        self._tune_gain(ch, after_state, "after")

        return DpicBalanceResult(
            inject_tx=ch.inject_tx,
            measure_tx=ch.measure_tx,
            measure_rx=ch.measure_rx,
            best_phase_deg=best["phase"],
            best_amplitude=best["amp"],
            min_metric=best["metric"],
            inject_gain_db=gain_db,
            measure_tx_gain_db=ch.get_tx_gain() if ch.get_tx_gain else float("nan"),
            measure_rx_gain_db=ch.get_rx_gain() if ch.get_rx_gain else float("nan"),
            method="grid",
            converged=True,
            num_measurements=counter["n"],
            elapsed_s=elapsed,
            start_metric=start_metric,
            stages=stages,
        )

    @staticmethod
    def _lanes(channels: Sequence[DpicChannel]) -> list[list[DpicChannel]]:
        """Group loops into per-radio lanes, keeping each lane's input order."""
        lanes: dict[object, list[DpicChannel]] = {}
        for ch in channels:
            lanes.setdefault(ch.device, []).append(ch)
        return list(lanes.values())

    def _balance_lane(self, lane: Sequence[DpicChannel], budget: float) -> list:
        """Balance one radio's loops in series, returning (channel, result) pairs."""
        results = []
        for ch in lane:
            if self.should_abort is not None and self.should_abort():
                break
            results.append((ch, self.balance(ch, budget)))
        return results

    def balance_all(self, channels: Sequence[DpicChannel]) -> list[DpicBalanceResult]:
        """Balance every loop, one lane per radio, lanes running together."""
        channels = list(channels)
        if not channels:
            return []

        lanes = self._lanes(channels) if self.parallel_devices else [channels]

        if len(lanes) == 1:
            pairs = self._balance_lane(lanes[0], self.time_budget_s / len(lanes[0]))
        else:
            pairs = []
            with ThreadPoolExecutor(
                max_workers=len(lanes), thread_name_prefix="dpic-balance"
            ) as pool:
                futures = [
                    pool.submit(self._balance_lane, lane, self.time_budget_s / len(lane))
                    for lane in lanes
                ]
                for future in futures:
                    pairs.extend(future.result())

        order = {id(ch): i for i, ch in enumerate(channels)}
        pairs.sort(key=lambda pair: order.get(id(pair[0]), 0))
        return [result for _ch, result in pairs]
