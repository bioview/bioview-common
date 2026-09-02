"""Direct-path interference cancellation.

Physical model
--------------
One Tx transmits the measurement signal. Its direct path leaks into the Rx as a
complex term ``d``. A second ("inject") Tx radiates a copy of the *same* IF tone
through a coupling ``h``, scaled by a digital weight ``w = a * exp(j*phi)`` and
by the inject Tx's analog gain ``g``. The residual at the receiver is

    r(w) = d + h(g) * w

which is **affine in w**. That single fact drives everything here:

* |r| is sinusoidal in ``phi`` with one minimum, at ``angle(-d/h)``, independent
  of ``a``; and V-shaped in ``a`` once ``phi`` is fixed. Both axes are unimodal,
  so a coarse-to-fine bracket is safe.
* Better still, being affine means ``h`` and ``d`` are *identifiable from two
  probes*, after which the cancelling weight follows in closed form:

      r0 = r(0)      = d
      r1 = r(a0)     = d + h*a0        =>  h = (r1 - r0) / a0
      w* = -d / h    = -r0 * a0 / (r1 - r0)

  Two measurements and a division replace thousands of grid points. Because the
  model is affine, a residual measured at any ``w`` also gives an exact Newton
  correction ``w <- w - r/h``, which mops up whatever the real hardware does
  that the model does not (DAC nonlinearity, slow drift in ``d``).

The digital weight only spans |w| <= 1. When the required |w*| falls outside a
comfortable band, the *analog* gain of the inject Tx is stepped so that |w*|
lands near mid-scale -- that is what makes the full range of direct-path
strengths reachable, rather than clipping at |w| = 1 or squeezing the injection
down into a handful of DAC codes.

IMPORTANT: the inject Tx must be driven at the *same* IF as the measure Tx.
The receive chain band-pass filters around the measure Tx's IF, so an inject Tx
placed on a different IF is rejected by that filter and can never cancel the
direct path, whatever weight the solver picks.
"""

from __future__ import annotations

import cmath
import math
import time
from dataclasses import dataclass
from typing import Callable, Sequence


def _no_wait() -> None:
    """Default ``wait_settle``: nothing to wait for."""


@dataclass
class DpicChannel:
    """Everything the balancer needs to drive and observe one cancellation loop.

    Bundled into an object because the alternative is a ``run_pair`` with
    fifteen positional callbacks.
    """

    inject_tx: int
    measure_tx: int
    measure_rx: int

    #: Set the inject Tx's digital phase, in degrees.
    set_phase: Callable[[float], None] = None
    #: Set the inject Tx's digital amplitude, 0..1.
    set_amplitude: Callable[[float], None] = None
    #: Mean residual magnitude on ``measure_rx``. None if not yet measurable.
    read_metric: Callable[[], float | None] = None
    #: Block until the hardware has settled after a digital change.
    wait_settle: Callable[[], None] = _no_wait

    #: Complex residual phasor. Enables the closed-form solve; without it the
    #: balancer falls back to the coarse-to-fine grid search.
    read_complex: Callable[[], complex | None] | None = None

    #: Analog Tx gain (dB) on the inject Tx, and its valid range.
    set_gain: Callable[[float], None] | None = None
    get_gain: Callable[[], float] | None = None
    gain_range: tuple[float, float] = (0.0, 89.75)
    #: Extra settling after an analog gain change (LO/AGC, not just the DAC).
    wait_gain_settle: Callable[[], None] | None = None

    #: Raise Rx gain to a usable operating point before the search starts.
    auto_gain_rx: Callable[[], None] | None = None

    #: Starting point, so a failed search can restore it.
    start_phase_deg: float = 0.0
    start_amplitude: float = 0.0


@dataclass
class DpicBalanceResult:
    inject_tx: int
    measure_tx: int
    best_phase_deg: float
    best_amplitude: float
    min_metric: float
    measure_rx: int = -1
    #: Analog gain (dB) left on the inject Tx.
    inject_gain_db: float = float("nan")
    #: "closed_form", "grid", or "none".
    method: str = "none"
    #: False when no usable metric was read; the pair's settings are restored
    #: to their pre-search values instead of being left at an arbitrary point.
    converged: bool = True
    num_measurements: int = 0
    elapsed_s: float = 0.0
    #: Metric before the search started, for a null-depth figure of merit.
    start_metric: float = float("nan")

    @property
    def null_depth_db(self) -> float:
        if not (self.start_metric > 0 and self.min_metric > 0):
            return float("nan")
        return 20.0 * math.log10(self.start_metric / self.min_metric)


@dataclass
class DpicBalancer:
    """Closed-form solve with a coarse-to-fine grid search as fallback."""

    # --- resolution of the grid fallback ---
    phase_step_deg: float = 0.1
    amp_step: float = 0.05
    coarse_phase_step_deg: float = 10.0
    coarse_amp_step: float = 0.1
    refine_factor: float = 8.0

    # --- limits ---
    max_amplitude: float = 1.0
    #: Target mean received magnitude for the Rx auto-gain step.
    amp_target: float = 0.5

    # --- timing ---
    #: Settling after a digital phase/amplitude change. Digital changes take
    #: effect on the next Tx buffer (a couple of ms), so this is deliberately
    #: short; the real wait is for fresh Rx chunks, handled by read_metric.
    settle_time_s: float = 0.02
    #: Settling after an analog gain change.
    gain_settle_time_s: float = 0.05
    #: Wall-clock ceiling for one pair. The grid fallback coarsens itself to fit.
    time_budget_s: float = 25.0

    # --- closed-form solve ---
    #: Digital weight used for the identification probe.
    probe_amplitude: float = 0.5
    #: Where |w*| should ideally land, as a fraction of max_amplitude. Mid-scale
    #: leaves headroom for drift in both directions.
    target_weight: float = 0.5
    #: Below this the injection wastes DAC range; above max_amplitude it clips.
    min_weight: float = 0.15
    #: Analog gain re-centering attempts.
    max_gain_steps: int = 3
    #: Newton corrections after the initial solve.
    refine_iterations: int = 3
    #: Stop refining once a step moves the weight by less than this.
    refine_tol: float = 1e-3

    # ------------------------------------------------------------- internals

    def _apply_weight(self, ch: DpicChannel, w: complex) -> complex:
        """Clamp ``w`` into the digital range and program it. Returns what was set."""
        amp = min(abs(w), self.max_amplitude)
        phase = math.degrees(cmath.phase(w)) % 360.0
        ch.set_phase(phase)
        ch.set_amplitude(amp)
        return cmath.rect(amp, math.radians(phase))

    def _set_gain(self, ch: DpicChannel, gain_db: float) -> float:
        lo, hi = ch.gain_range
        gain_db = min(max(gain_db, lo), hi)
        ch.set_gain(gain_db)
        if ch.wait_gain_settle:
            ch.wait_gain_settle()
        else:
            time.sleep(self.gain_settle_time_s)
        return gain_db

    # -------------------------------------------------------- closed form

    def _solve(self, ch: DpicChannel, state: dict) -> dict | None:
        """Two-probe identification plus Newton refinement.

        Returns the best ``{"w", "gain", "metric"}`` found, or None when the
        measurement path never produced a usable phasor.
        """
        identified = self._identify(ch, state)
        if identified is None:
            return None
        h, w_star, gain = identified
        return self._refine(ch, state, h, w_star, gain)

    def _identify(self, ch: DpicChannel, state: dict):
        """Two-probe identification of the affine model r(w) = h*w + d.

        Re-centers the inject Tx's analog gain when the implied optimum lands
        outside the usable digital range, so strong and weak direct paths are
        equally reachable instead of clipping at |w| = 1.

        Returns ``(h, w_star, gain)``, or None when the measurement path never
        produced a usable phasor.
        """
        gain = ch.get_gain() if ch.get_gain else float("nan")
        h = None
        w_star = None

        for attempt in range(self.max_gain_steps + 1):
            r0 = state["probe_complex"](0.0 + 0.0j)
            r1 = state["probe_complex"](complex(self.probe_amplitude, 0.0))
            if r0 is None or r1 is None:
                return None
            denom = r1 - r0
            if abs(denom) <= 0:
                return None

            h = denom / self.probe_amplitude
            w_star = -r0 / h

            need_more = abs(w_star) > self.max_amplitude
            need_less = abs(w_star) < self.min_weight
            if not (need_more or need_less) or ch.set_gain is None:
                break
            if attempt == self.max_gain_steps or state["expired"]():
                break

            # h scales with the analog gain, so re-center |w*| on mid-scale and
            # re-identify.
            target = self.target_weight * self.max_amplitude
            delta_db = 20.0 * math.log10(max(abs(w_star), 1e-9) / target)
            new_gain = self._set_gain(ch, gain + delta_db)
            if abs(new_gain - gain) < 1e-6:
                break
            gain = new_gain

        if h is None:
            return None
        return h, w_star, gain

    def _refine(self, ch: DpicChannel, state: dict, h, w_star, gain) -> dict | None:
        """Newton refinement from the identified optimum.

        The model is affine, so one Newton step is exact; it is repeated only to
        absorb hardware nonlinearity and drift in d.
        """
        best = None
        w = self._apply_weight(ch, w_star)
        for _ in range(max(int(self.refine_iterations), 0) + 1):
            ch.wait_settle()
            r = state["measure_complex"]()
            if r is None:
                break
            metric = abs(r)
            if best is None or metric < best["metric"]:
                best = {"w": w, "gain": gain, "metric": metric}
            if state["expired"]():
                break
            w_next = w - r / h
            if abs(w_next - w) < self.refine_tol:
                break
            w = self._apply_weight(ch, w_next)

        return best

    # ---------------------------------------------------------- grid search

    @staticmethod
    def _frange(start: float, stop: float, step: float) -> list[float]:
        if step <= 0:
            return []
        n = int(math.floor((stop - start) / step + 1e-9)) + 1
        return [start + i * step for i in range(max(n, 0))]

    def _grids(self, full_lo, full_hi, coarse, fine) -> list:
        """Full pass at ``coarse``, then shrinking windows down to ``fine``."""
        step = max(float(coarse), float(fine))
        grids: list = [self._frange(full_lo, full_hi, step)]
        while step > fine:
            span = step
            step = max(step / self.refine_factor, fine)
            grids.append(("window", span, step))
        return grids

    def _sweep(self, grids, apply, state, best_value, best_metric):
        for grid in grids:
            if isinstance(grid, tuple):
                _, span, step = grid
                values = [best_value + off for off in self._frange(-span, span, step)]
            else:
                values = grid
            for value in values:
                if state["expired"]():
                    return best_value, best_metric
                apply(value)
                metric = state["measure"]()
                if metric is None or not math.isfinite(metric):
                    continue
                if metric < best_metric:
                    best_metric = metric
                    best_value = value
        return best_value, best_metric

    def _search_grid(self, ch: DpicChannel, state: dict) -> dict | None:
        best_phase = float(ch.start_phase_deg)
        best_amp = float(ch.start_amplitude)
        ch.set_phase(best_phase)
        ch.set_amplitude(best_amp)
        seed = state["measure"]()
        best_metric = (
            float(seed) if seed is not None and math.isfinite(seed) else float("inf")
        )

        def apply_phase(v):
            ch.set_phase(v % 360.0)

        def apply_amp(v):
            ch.set_amplitude(min(max(v, 0.0), self.max_amplitude))

        sweep_amp = best_amp if best_amp > 0 else min(0.5, self.max_amplitude)
        apply_amp(sweep_amp)
        best_phase, best_metric = self._sweep(
            self._grids(
                0.0,
                360.0 - self.coarse_phase_step_deg,
                self.coarse_phase_step_deg,
                self.phase_step_deg,
            ),
            apply_phase,
            state,
            best_phase,
            best_metric,
        )
        best_phase %= 360.0
        apply_phase(best_phase)

        best_amp, best_metric = self._sweep(
            self._grids(0.0, self.max_amplitude, self.coarse_amp_step, self.amp_step),
            apply_amp,
            state,
            sweep_amp if best_amp <= 0.0 else best_amp,
            best_metric,
        )
        best_amp = min(max(best_amp, 0.0), self.max_amplitude)
        apply_amp(best_amp)

        # Narrow phase re-pass at the final amplitude.
        fine_span = max(
            self.coarse_phase_step_deg / self.refine_factor, self.phase_step_deg
        )
        best_phase, best_metric = self._sweep(
            [("window", fine_span, self.phase_step_deg)],
            apply_phase,
            state,
            best_phase,
            best_metric,
        )
        best_phase %= 360.0
        apply_phase(best_phase)

        if not math.isfinite(best_metric):
            return None
        return {
            "w": cmath.rect(best_amp, math.radians(best_phase)),
            "gain": ch.get_gain() if ch.get_gain else float("nan"),
            "metric": best_metric,
        }

    # ------------------------------------------------------------------- api

    def _measurement_state(self, ch: DpicChannel, deadline: float, counter: dict):
        """The callbacks a search runs on, sharing one measurement counter.

        Bundled here rather than inline so ``balance`` reads as the sequence of
        steps it is.
        """

        def expired():
            return time.monotonic() >= deadline

        def measure():
            value = ch.read_metric()
            if value is not None:
                counter["n"] += 1
            return value

        def measure_complex():
            if ch.read_complex is None:
                return None
            value = ch.read_complex()
            if value is not None:
                counter["n"] += 1
            return value

        def probe_complex(w):
            self._apply_weight(ch, w)
            ch.wait_settle()
            return measure_complex()

        return {
            "expired": expired,
            "measure": measure,
            "measure_complex": measure_complex,
            "probe_complex": probe_complex,
        }

    def balance(self, ch: DpicChannel) -> DpicBalanceResult:
        t_start = time.monotonic()
        deadline = t_start + self.time_budget_s
        counter = {"n": 0}
        state = self._measurement_state(ch, deadline, counter)
        measure = state["measure"]

        # 1. Bring the receiver to a usable operating point: a null search is
        #    meaningless if the direct path sits in the noise floor.
        if ch.auto_gain_rx:
            ch.auto_gain_rx()

        # 2. Seed from the current settings so a failed search has something to
        #    restore, and so null depth can be reported.
        ch.set_phase(float(ch.start_phase_deg))
        ch.set_amplitude(float(ch.start_amplitude))
        ch.wait_settle()
        seed = measure()
        start_metric = (
            float(seed) if seed is not None and math.isfinite(seed) else float("nan")
        )

        best = None
        method = "none"
        if ch.read_complex is not None:
            best = self._solve(ch, state)
            if best is not None:
                method = "closed_form"

        # 3. Grid fallback: no complex measurement available, or the solve did
        #    not actually beat the starting point.
        needs_grid = best is None or (
            math.isfinite(start_metric) and best["metric"] >= start_metric
        )
        if needs_grid and not state["expired"]():
            grid_best = self._search_grid(ch, state)
            if grid_best is not None and (
                best is None or grid_best["metric"] < best["metric"]
            ):
                best = grid_best
                method = "grid"

        elapsed = time.monotonic() - t_start

        if best is None:
            # Never leave the hardware at an arbitrary point (in particular not
            # at amplitude 0) because the measurement path was silent.
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
            )

        if ch.set_gain and not math.isnan(best["gain"]):
            self._set_gain(ch, best["gain"])
        w = self._apply_weight(ch, best["w"])

        return DpicBalanceResult(
            inject_tx=ch.inject_tx,
            measure_tx=ch.measure_tx,
            measure_rx=ch.measure_rx,
            best_phase_deg=math.degrees(cmath.phase(w)) % 360.0,
            best_amplitude=abs(w),
            min_metric=best["metric"],
            inject_gain_db=best["gain"],
            method=method,
            converged=True,
            num_measurements=counter["n"],
            elapsed_s=elapsed,
            start_metric=start_metric,
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
            return [self.balance(ch) for ch in channels]
        finally:
            self.time_budget_s = saved
