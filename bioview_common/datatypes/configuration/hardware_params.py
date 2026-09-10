"""Flatten and update per-device hardware TX parameters across a virtual group."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


GLOBAL_TX_PARAMS = frozenset({"tx_amplitude", "tx_phase", "if_freq", "tx_gain"})
GLOBAL_RX_PARAMS = frozenset({"rx_gain"})


def build_global_mapping(
    hardware: dict[str, dict], kind: str = "tx"
) -> tuple[dict[int, tuple[str, int]], dict[str, int], list[float]]:
    """Flatten per-device channels into global indices.

    Returns ``(index -> (device_name, local_index), device_name -> offset,
    per-global-channel gains)``.
    """
    key = f"{kind}_channels"
    gain_key = f"{kind}_gain"

    mapping: dict[int, tuple[str, int]] = {}
    offsets: dict[str, int] = {}
    gains: list[float] = []

    offset = 0
    for device_name, hw in hardware.items():
        count = len(hw.get(key, [0]))
        offsets[device_name] = offset
        for local in range(count):
            mapping[offset + local] = (device_name, local)

        device_gains = hw.get(gain_key, [])
        if not isinstance(device_gains, list | tuple):
            device_gains = [device_gains] * count
        gains.extend(
            float(device_gains[i]) if i < len(device_gains) else 0.0
            for i in range(count)
        )
        offset += count

    return mapping, offsets, gains


def _coerce_list(value: Any, length: int, fill: float = 0.0) -> list:
    if isinstance(value, list | tuple):
        out = list(value)
    elif value is None:
        out = []
    else:
        out = [value]
    while len(out) < length:
        out.append(out[-1] if out else fill)
    return out


def get_global_values(
    hardware: dict[str, dict] | None,
    param: str,
    group_defaults: dict | None = None,
) -> list:
    """Read a parameter as a flat global list (matches backend channel order).

    Tx and Rx read identically -- the direction only matters when values are
    written back, where the channel count comes from ``tx_channels`` or
    ``rx_channels``.
    """
    group_defaults = group_defaults or {}
    if not hardware:
        raw = group_defaults.get(param)
        if isinstance(raw, list | tuple):
            return list(raw)
        if raw is None:
            return []
        return [raw]

    values: list = []
    for _device_name, hw in hardware.items():
        raw = hw.get(param, group_defaults.get(param))
        if isinstance(raw, list | tuple):
            values.extend(raw)
        elif raw is not None:
            values.append(raw)
    return values


def apply_global_values_to_hardware(
    hardware: dict[str, dict],
    param: str,
    values: list,
    group_defaults: dict | None = None,
    kind: str = "tx",
) -> list:
    """Write a flat global list back into nested hardware entries.

    ``kind`` picks the channel list the slices are cut against: a group's Tx
    and Rx channel counts differ per radio, so a Tx write must not be sliced
    with Rx widths.

    Returns the list actually applied.
    """
    group_defaults = group_defaults or {}
    default_raw = group_defaults.get(param)
    default_fill = (
        default_raw[-1] if isinstance(default_raw, list | tuple) and default_raw else 0.0
    )
    channel_key = f"{kind}_channels"

    offset = 0
    for _device_name, hw in hardware.items():
        count = len(hw.get(channel_key, [0]))
        slice_vals = _coerce_list(values[offset : offset + count], count, default_fill)
        hw[param] = slice_vals
        offset += count
    return list(values)


def update_device_param(
    device_cfg,
    param: str,
    value: Any,
    idx: int | None = None,
    kind: str = "tx",
) -> list:
    """Update a device config's Tx or Rx param; returns the flat global list.

    A group with no ``hardware`` block keeps the value at group level; one with
    hardware has it split back across the radios by channel count.
    """
    hardware = device_cfg.get_param("hardware")
    defaults = device_cfg.to_dict()

    if not hardware:
        if idx is not None:
            current = list(get_global_values(None, param, defaults))
            while len(current) <= idx:
                current.append(0.0)
            current[idx] = value
            device_cfg.set_param(param, current)
            return current
        device_cfg.set_param(param, value)
        return list(value) if isinstance(value, list | tuple) else [value]

    hw = deepcopy(hardware)
    current = get_global_values(hw, param, defaults)
    if idx is not None:
        while len(current) <= idx:
            current.append(current[-1] if current else 0.0)
        current[idx] = value
    else:
        current = list(value) if isinstance(value, list | tuple) else [value]

    apply_global_values_to_hardware(hw, param, current, defaults, kind=kind)
    device_cfg.set_param("hardware", hw)
    return get_global_values(hw, param, defaults)


def resolve_param_values(device_cfg, param: str) -> list:
    """Return flat values for UI display (hardware-aware)."""
    defaults = device_cfg.to_dict()
    hardware = device_cfg.get_param("hardware")
    if param in GLOBAL_TX_PARAMS or param in GLOBAL_RX_PARAMS:
        return get_global_values(hardware, param, defaults)
    raw = device_cfg.get_param(param)
    if isinstance(raw, list | tuple):
        return list(raw)
    if raw is None:
        return []
    return [raw]


def _update_scheme_local_list(
    scheme, attr: str, local_idx: int, value: float, param: str
):
    current = list(getattr(scheme, attr, []))
    while len(current) <= local_idx:
        current.append(current[-1] if current else 0.0)
    current[local_idx] = float(value)
    scheme.update_param(param, current)


def apply_global_tx_param_to_schemes(
    schemes_by_device: dict,
    global_tx_to_device: dict[int, tuple[str, int]],
    hardware: dict[str, dict] | None,
    group_config: dict,
    param: str,
    values,
) -> None:
    """Push a flat global Tx parameter list into hardware dict and live schemes."""
    flat = list(values) if isinstance(values, list | tuple) else [values]
    if hardware:
        apply_global_values_to_hardware(hardware, param, flat, group_config, kind="tx")
        group_config["hardware"] = hardware

    scheme_attr = {
        "tx_amplitude": ("tx_amplitude", "tx_amplitude"),
        "tx_phase": ("tx_phase_deg", "tx_phase"),
        "if_freq": ("if_freq", "if_freq"),
    }.get(param)
    if scheme_attr is None:
        return

    attr_name, update_name = scheme_attr
    for g_idx, val in enumerate(flat):
        loc = global_tx_to_device.get(g_idx)
        if not loc:
            continue
        dev_name, local = loc
        scheme = schemes_by_device.get(dev_name)
        if scheme is None:
            continue
        _update_scheme_local_list(scheme, attr_name, local, val, update_name)
