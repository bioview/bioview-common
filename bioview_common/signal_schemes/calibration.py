"""Gated burst calibration envelope for AM overlay on any signal scheme."""

from __future__ import annotations

from typing import Literal, Tuple

import numpy as np

ShapeType = Literal["triangle", "sawtooth", "rectangle"]


class BurstEnvelope:
    """Generates gated repeating calibration bursts."""

    def __init__(
        self,
        fs: float,
        shape: ShapeType = "triangle",
        num_pulses: int = 5,
        pulse_duration_s: float = 0.1,
        packet_spacing_s: float = 1.0,
        envelope_freq_hz: float = 10.0,
        envelope_offset: float = 0.0,
    ):
        self.fs = float(fs)
        self.shape = shape
        self.num_pulses = max(int(num_pulses), 1)
        self.pulse_duration_s = max(float(pulse_duration_s), 1e-6)
        self.packet_spacing_s = max(float(packet_spacing_s), 1e-6)
        self.envelope_freq_hz = max(float(envelope_freq_hz), 1e-9)
        self.envelope_offset = float(envelope_offset)
        self._recalc()

    def _recalc(self):
        self.period_len = max(1, int(round(self.packet_spacing_s * self.fs)))
        burst_samples = int(round(self.num_pulses * self.fs / self.envelope_freq_hz))
        self.burst_len = max(1, min(burst_samples, self.period_len))

    def update_config(self, **kwargs):
        for key, val in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, val)
        self._recalc()

    def _shape_wave(self, t_local: np.ndarray) -> np.ndarray:
        if self.shape == "rectangle":
            return np.ones_like(t_local, dtype=np.float64)
        phase = t_local * self.envelope_freq_hz
        if self.shape == "sawtooth":
            return 2.0 * (phase - np.floor(phase)) - 1.0
        return 2.0 * np.abs(2.0 * (phase - np.floor(phase + 0.5))) - 1.0

    def generate(self, n: int, start_sample: int) -> Tuple[np.ndarray, np.ndarray]:
        """Return (envelope, gate) arrays of length n."""
        idx = start_sample + np.arange(n, dtype=np.int64)
        pos = idx % self.period_len
        gate = (pos < self.burst_len).astype(np.float32)

        t_local = (pos % self.burst_len).astype(np.float64) / self.fs
        wave = self._shape_wave(t_local) + self.envelope_offset

        out = np.zeros(n, dtype=np.float32)
        out[gate.astype(bool)] = wave[gate.astype(bool)].astype(np.float32)
        return out, gate


class BurstEnvelopeMixin:
    """Mixin adding calibration burst overlay to signal schemes."""

    def _init_calibration(self, samp_rate: float, cal_config: dict):
        self._cal_config = dict(cal_config or {})
        self._cal_enabled = bool(self._cal_config.get("enabled", False))
        self._modulation_depth = min(
            float(self._cal_config.get("modulation_depth", 0.2)), 0.5
        )
        inject = self._cal_config.get("inject_channels", [0])
        self._inject_channels = set(
            inject if isinstance(inject, (list, tuple)) else [inject]
        )
        self._envelope = BurstEnvelope(
            fs=samp_rate,
            shape=self._cal_config.get("shape", "triangle"),
            num_pulses=self._cal_config.get("num_pulses", 5),
            pulse_duration_s=self._cal_config.get("pulse_duration_s", 0.1),
            packet_spacing_s=self._cal_config.get("packet_spacing_s", 1.0),
            envelope_freq_hz=self._cal_config.get("envelope_freq_hz", 10.0),
            envelope_offset=self._cal_config.get("envelope_offset", 0.0),
        )

    def set_calibration_enabled(self, enabled: bool) -> None:
        self._cal_enabled = bool(enabled)

    def calibration_enabled(self) -> bool:
        return self._cal_enabled

    def _apply_calibration(
        self, carrier: np.ndarray, tx_idx: int, start_sample: int
    ) -> np.ndarray:
        if not self._cal_enabled or tx_idx not in self._inject_channels:
            return carrier
        env, _ = self._envelope.generate(len(carrier), start_sample)
        return carrier * (1.0 + self._modulation_depth * env)

    def get_calibration_reference(
        self, tx_idx: int, start_sample: int, n_samples: int
    ) -> np.ndarray:
        if tx_idx not in self._inject_channels:
            return np.zeros(n_samples, dtype=np.float32)
        env, gate = self._envelope.generate(n_samples, start_sample)
        return (env * gate).astype(np.float32)
