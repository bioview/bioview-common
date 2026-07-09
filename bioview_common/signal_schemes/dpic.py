"""Direct-path interference cancellation via grid search."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class DpicBalanceResult:
    inject_tx: int
    measure_tx: int
    best_phase_deg: float
    best_amplitude: float
    min_metric: float


@dataclass
class DpicBalancer:
    """Grid search over inject-Tx phase and amplitude to minimize received metric."""

    phase_step_deg: float = 0.1
    amp_step: float = 0.05
    amp_target: float = 0.5
    settle_time_s: float = 0.5

    def run_pair(
        self,
        inject_tx: int,
        measure_tx: int,
        set_phase: Callable[[int, float], None],
        set_amplitude: Callable[[int, float], None],
        read_metric: Callable[[], Optional[float]],
        wait_settle: Callable[[], None],
        auto_gain_rx: Optional[Callable[[], None]] = None,
    ) -> DpicBalanceResult:
        if auto_gain_rx:
            auto_gain_rx()

        best_phase = 0.0
        best_amp = 0.0
        best_metric = float("inf")

        phase = 0.0
        while phase < 360.0:
            set_phase(inject_tx, phase)
            wait_settle()
            metric = read_metric()
            if metric is not None and metric < best_metric:
                best_metric = metric
                best_phase = phase
            phase += self.phase_step_deg

        set_phase(inject_tx, best_phase)

        amp = 0.0
        while amp <= 1.0 + 1e-9:
            set_amplitude(inject_tx, amp)
            wait_settle()
            metric = read_metric()
            if metric is not None and metric < best_metric:
                best_metric = metric
                best_amp = amp
            amp += self.amp_step

        set_phase(inject_tx, best_phase)
        set_amplitude(inject_tx, best_amp)

        return DpicBalanceResult(
            inject_tx=inject_tx,
            measure_tx=measure_tx,
            best_phase_deg=best_phase,
            best_amplitude=best_amp,
            min_metric=best_metric if math.isfinite(best_metric) else 0.0,
        )

    def run_all(
        self,
        pairs: List[tuple],
        set_phase: Callable[[int, float], None],
        set_amplitude: Callable[[int, float], None],
        read_metric: Callable[[int, int], Optional[float]],
        wait_settle: Callable[[], None],
        auto_gain_rx: Optional[Callable[[int], None]] = None,
    ) -> List[DpicBalanceResult]:
        results = []
        for inject_tx, measure_tx in pairs:
            metric_fn = lambda m=measure_tx, i=inject_tx: read_metric(i, m)  # noqa: E731
            gain_fn = (
                (lambda r=measure_tx: auto_gain_rx(r)) if auto_gain_rx else None
            )
            results.append(
                self.run_pair(
                    inject_tx,
                    measure_tx,
                    set_phase,
                    set_amplitude,
                    metric_fn,
                    wait_settle,
                    gain_fn,
                )
            )
        return results
