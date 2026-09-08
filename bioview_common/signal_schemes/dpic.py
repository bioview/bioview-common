"""Direct-path interference cancellation.

A coarse-to-fine grid search over the inject Tx's digital phase and amplitude,
ported from the ``Pig_2Ch_NCS_BIOPAC_BalanceSignal`` LabVIEW VI. The four
sweeps and their step sizes are the VI's; see bioview-docs/reference/dpic.md.
"""

from __future__ import annotations

import contextlib
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field


def _no_wait(_seconds: float = 0.0) -> None:
    """Default ``wait_settle``: nothing to wait for."""


@dataclass
class DpicChannel:
    """Everything the balancer needs to drive and observe one cancellation loop."""

    inject_tx: int
    measure_tx: int
    measure_rx: int

    #: Set the inject Tx's digital phase, in degrees.
    set_phase: Callable[[float], None] = None
    #: Set the inject Tx's digital amplitude, 0..1.
    set_amplitude: Callable[[float], None] = None
    #: Mean residual magnitude on ``measure_rx``. None if not yet measurable.
    read_metric: Callable[[], float | None] = None
    #: Dwell for the given number of seconds after a change. The VI's per-point
    #: wait, which is also what makes a sweep legible on a live plot.
    wait_settle: Callable[[float], None] = _no_wait

    #: Analog Tx gain (dB) on the inject Tx, reported with the result.
    get_gain: Callable[[], float] | None = None

    # --- the VI's "Tune Rx1 Gain to DC value of ~0.5" stage ---
    #
    # The VI steps the *measure* Tx's analog gain and the Rx gain together, by
    # 1 dB per iteration, until the measured level sits between its two
    # thresholds. Both accessors must be present for the stage to run; a
    # backend with no analog gain control (the simulator) leaves them None and
    # the stage is skipped.
    get_rx_gain: Callable[[], float] | None = None
    set_rx_gain: Callable[[float], None] | None = None
    get_tx_gain: Callable[[], float] | None = None
    set_tx_gain: Callable[[float], None] | None = None
    #: (min, max) dB, so the ladder cannot walk off the end of the range.
    rx_gain_range: tuple[float, float] = (0.0, 76.0)
    tx_gain_range: tuple[float, float] = (0.0, 90.0)

    #: Starting point, so a failed search can restore it.
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
    #: Points the sweep intended to visit.
    planned: int
    #: Points it actually applied before the budget ran out.
    visited: int = 0
    #: Points that returned a usable metric.
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
    #: Analog gain (dB) on the inject Tx.
    inject_gain_db: float = float("nan")
    #: Where the VI's gain stage left the measure Tx / Rx, in dB.
    measure_tx_gain_db: float = float("nan")
    measure_rx_gain_db: float = float("nan")
    #: "grid" or "none".
    method: str = "none"
    # False when no usable metric was read; settings are then restored.
    converged: bool = True
    num_measurements: int = 0
    elapsed_s: float = 0.0
    #: Metric before the search started, for a null-depth figure of merit.
    start_metric: float = float("nan")
    #: One entry per sweep, in order.
    stages: list[DpicStage] = field(default_factory=list)
    #: Why the balance did not run, when it did not.
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
    """Coarse-to-fine grid search for the digital weight that nulls the direct path.

    Four sweeps, in the VI's order: coarse phase at a small fixed injection
    amplitude, coarse amplitude at that phase, then a fine pass over each,
    windowed to +/- one coarse step around the coarse winner. Each sweep takes
    the argmin of everything it measured, exactly as the VI's "array minimum"
    does; it does not require an improvement over the seed.
    """

    # --- coarse pass: the VI's 60 phase points and 20 amplitude points ---
    coarse_phase_step_deg: float = 6.0
    coarse_amp_step: float = 0.05
    #: "Start with small Tx Amp" -- the amplitude the coarse phase sweep runs at.
    coarse_probe_amplitude: float = 0.1

    # --- fine pass: swept over +/- the matching coarse step ---
    phase_step_deg: float = 0.2
    amp_step: float = 0.001

    #: Above this the injection clips the DAC.
    max_amplitude: float = 1.0

    # --- dwell times, straight from the VI's Wait (ms) nodes ---
    #
    # ``read_metric`` additionally blocks for chunks captured *after* the
    # change, which the VI has no equivalent of; these are on top of that, not
    # instead of it. They are also what makes a sweep legible: at a few tens of
    # milliseconds per point the whole search flashes past and the plot shows
    # no pattern at all.
    coarse_settle_time_s: float = 0.2
    fine_settle_time_s: float = 0.1
    #: After a sweep's winner is applied, before the next sweep starts.
    stage_settle_time_s: float = 0.5

    # --- the VI's "Tune Rx1 Gain to DC value of ~0.5" stage ---
    #: Target level, and the half-width of the window around it that counts as
    #: in range (the VI's Upper Th / Lower Th).
    amp_target: float = 0.5
    amp_tolerance: float = 0.05
    #: The VI's +/-1 dB ladder, applied to the measure Tx and the Rx together.
    gain_step_db: float = 1.0
    gain_settle_time_s: float = 0.25
    #: The VI's loop is unbounded; this keeps a level that can never be reached
    #: (a dead path, a disconnected antenna) from running forever.
    max_gain_steps: int = 60

    #: Wall-clock ceiling for one pair, split across pairs by ``balance_all``.
    #: A sweep that runs out stops where it is and keeps the best point found
    #: so far.
    #:
    #: The VI's own dwells put a floor under this: 60*0.2 + 20*0.2 + 60*0.1 +
    #: 100*0.1 = 32 s of sleeping per pair, plus four 0.5 s stage settles and
    #: 240 waits for fresh Rx chunks -- call it 45 s. The default clears that
    #: for three pairs; a rig with more should raise it rather than run every
    #: sweep truncated.
    time_budget_s: float = 300.0

    #: Asked before every sweep point. True ends the search where it stands, so
    #: a Stop or a shutdown does not have to wait out the whole time budget.
    should_abort: Callable[[], bool] | None = None

    #: Called after every measurement with the live state of the loop, so the
    #: UI can show phase, amplitude and gain moving instead of a frozen panel
    #: and a progress-free wait. Never allowed to break the search.
    on_progress: Callable[[dict], None] | None = None

    # ------------------------------------------------------------- internals

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
        """Measure at every value; return the argmin and a record of the sweep.

        The argmin is ``None`` when nothing on the sweep was measurable. The
        stage is always returned, so a sweep that measured nothing -- or that
        the time budget cut short -- is visible rather than silently absent.
        """
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
        """The VI's "Tune Rx1 Gain to DC value of ~0.5" stage.

        A +/-1 dB ladder applied to the **measure Tx's analog gain and the Rx
        gain together**, one step per iteration with a settle in between, until
        the measured level sits inside [target - tolerance, target + tolerance].

        Both halves move because the VI moves both: raising Rx gain alone lifts
        the noise floor with the signal, while raising the measurement Tx as
        well lifts the direct path that is about to be nulled. This ran as a
        proportional single jump before -- fewer measurements, but it converged
        in one invisible step, so nothing on the plot ever showed the level
        being walked into range.
        """
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

            # Both already against the stop the level needs to move past: no
            # further step can change anything, so stop rather than spin.
            if rx_gain == ch.get_rx_gain() and tx_gain == ch.get_tx_gain():
                return

            ch.set_rx_gain(rx_gain)
            ch.set_tx_gain(tx_gain)
            state["settle"](self.gain_settle_time_s)

    def _search(self, ch: DpicChannel, state: dict) -> dict | None:
        """The VI's four sweeps. Returns the best point, or None if none measured.

        Each sweep applies its winner and then waits ``stage_settle_time_s``,
        matching the VI's 500 ms between stages -- long enough that the
        settled point is visible on the plot before the next sweep starts
        moving things again.
        """

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

        # 1. Coarse phase over the full circle, at a small fixed amplitude.
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

        # 2. Coarse amplitude over the whole digital range, at that phase.
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

        # 3. Fine phase, +/- one coarse step around the coarse winner.
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

        # 4. Fine amplitude, +/- one coarse step around the coarse winner.
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

    # ------------------------------------------------------------------- api

    def _measurement_state(self, ch: DpicChannel, deadline: float, counter: dict):
        """The callbacks a search runs on, sharing one counter and stage list.

        ``phase`` and ``amplitude`` read back the values last applied, so a
        progress report always describes the point that was just measured
        rather than the one about to be set.
        """
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
        # Never leave the hardware at an arbitrary point (or amplitude 0).
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

    def balance(self, ch: DpicChannel) -> DpicBalanceResult:
        t_start = time.monotonic()
        counter = {"n": 0}

        # A null search is meaningless if the direct path is in the noise. This
        # runs on its own deadline, *outside* the search budget: it is a
        # prerequisite of the search, not part of it, and on a slow measurement
        # path it could otherwise eat the whole budget and leave every sweep to
        # break on its first point.
        gain_state = self._measurement_state(
            ch, time.monotonic() + self.time_budget_s, counter
        )
        self._tune_gain(ch, gain_state, "before")

        deadline = time.monotonic() + self.time_budget_s
        state = self._measurement_state(ch, deadline, counter)
        stages = state["stages"]

        # Seeded from current settings, so a failed search can restore them.
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
                (
                    f"the {self.time_budget_s:.0f}s budget expired before any "
                    "sweep point was measured"
                )
                if visited == 0
                else "no sweep point returned a usable metric",
            )

        # The direct path is nulled now, so the Rx sits far below its operating
        # point; the VI re-runs the same gain stage here. Done after min_metric
        # is fixed, so the null depth is measured at a single gain setting, and
        # on a fresh deadline for the same reason as the first call.
        after_state = self._measurement_state(
            ch, time.monotonic() + self.time_budget_s, counter
        )
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

    def balance_all(self, channels: Sequence[DpicChannel]) -> list[DpicBalanceResult]:
        """Balance each loop in turn, splitting the time budget between them."""
        channels = list(channels)
        if not channels:
            return []
        per_pair = self.time_budget_s / len(channels)
        saved = self.time_budget_s
        try:
            self.time_budget_s = per_pair
            results = []
            for ch in channels:
                # Checked between pairs as well as inside each sweep: an abort
                # during pair 1 must not start pair 2.
                if self.should_abort is not None and self.should_abort():
                    break
                results.append(self.balance(ch))
            return results
        finally:
            self.time_budget_s = saved
