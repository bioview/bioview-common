"""Flatten and update per-device hardware TX parameters across a virtual group."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

GLOBAL_TX_PARAMS = frozenset({"tx_amplitude", "tx_phase", "if_freq", "tx_gain"})
GLOBAL_RX_PARAMS = frozenset({"rx_gain"})


def build_global_tx_mapping(hardware: Dict[str, dict]) -> Dict[int, Tuple[str, int]]:
    """Map global Tx index -> (device_name, local_tx_index)."""
    mapping: Dict[int, Tuple[str, int]] = {}
    offset = 0
    for device_name, hw in hardware.items():
        n_tx = len(hw.get("tx_channels", [0]))
        for local in range(n_tx):
            mapping[offset + local] = (device_name, local)
        offset += n_tx
    return mapping


def build_global_rx_mapping(hardware: Dict[str, dict]) -> Dict[int, Tuple[str, int]]:
    """Map global Rx index -> (device_name, local_rx_index)."""
    mapping: Dict[int, Tuple[str, int]] = {}
    offset = 0
    for device_name, hw in hardware.items():
        n_rx = len(hw.get("rx_channels", [0]))
        for local in range(n_rx):
            mapping[offset + local] = (device_name, local)
        offset += n_rx
    return mapping


def _coerce_list(value: Any, length: int, fill: float = 0.0) -> List:
    if isinstance(value, (list, tuple)):
        out = list(value)
    elif value is None:
        out = []
    else:
        out = [value]
    while len(out) < length:
        out.append(out[-1] if out else fill)
    return out


def get_global_tx_values(
    hardware: Optional[Dict[str, dict]],
    param: str,
    group_defaults: Optional[dict] = None,
) -> List:
    """Read a Tx parameter as a flat global list (matches backend channel order)."""
    group_defaults = group_defaults or {}
    if not hardware:
        raw = group_defaults.get(param)
        if isinstance(raw, (list, tuple)):
            return list(raw)
        if raw is None:
            return []
        return [raw]

    values: List = []
    for _device_name, hw in hardware.items():
        raw = hw.get(param, group_defaults.get(param))
        if isinstance(raw, (list, tuple)):
            values.extend(raw)
        elif raw is not None:
            values.append(raw)
    return values


def get_global_rx_values(
    hardware: Optional[Dict[str, dict]],
    param: str,
    group_defaults: Optional[dict] = None,
) -> List:
    group_defaults = group_defaults or {}
    if not hardware:
        raw = group_defaults.get(param)
        if isinstance(raw, (list, tuple)):
            return list(raw)
        if raw is None:
            return []
        return [raw]

    values: List = []
    for _device_name, hw in hardware.items():
        raw = hw.get(param, group_defaults.get(param))
        if isinstance(raw, (list, tuple)):
            values.extend(raw)
        elif raw is not None:
            values.append(raw)
    return values


def apply_global_tx_values_to_hardware(
    hardware: Dict[str, dict],
    param: str,
    values: List,
    group_defaults: Optional[dict] = None,
) -> List:
    """Write a flat global Tx list into nested hardware entries; return the list applied."""
    group_defaults = group_defaults or {}
    default_raw = group_defaults.get(param)
    default_fill = default_raw[-1] if isinstance(default_raw, (list, tuple)) and default_raw else 0.0

    offset = 0
    for _device_name, hw in hardware.items():
        n_tx = len(hw.get("tx_channels", [0]))
        slice_vals = _coerce_list(values[offset : offset + n_tx], n_tx, default_fill)
        hw[param] = slice_vals
        offset += n_tx
    return list(values)


def apply_global_rx_values_to_hardware(
    hardware: Dict[str, dict],
    param: str,
    values: List,
    group_defaults: Optional[dict] = None,
) -> List:
    group_defaults = group_defaults or {}
    default_raw = group_defaults.get(param)
    default_fill = default_raw[-1] if isinstance(default_raw, (list, tuple)) and default_raw else 0.0

    offset = 0
    for _device_name, hw in hardware.items():
        n_rx = len(hw.get("rx_channels", [0]))
        slice_vals = _coerce_list(values[offset : offset + n_rx], n_rx, default_fill)
        hw[param] = slice_vals
        offset += n_rx
    return list(values)


def update_device_tx_param(
    device_cfg,
    param: str,
    value: Any,
    idx: Optional[int] = None,
) -> List:
    """Update device config for a Tx param; returns the flat global value list."""
    hardware = device_cfg.get_param("hardware")
    defaults = device_cfg.to_dict()

    if not hardware:
        if idx is not None:
            current = list(get_global_tx_values(None, param, defaults))
            while len(current) <= idx:
                current.append(0.0)
            current[idx] = value
            device_cfg.set_param(param, current)
            return current
        device_cfg.set_param(param, value)
        return list(value) if isinstance(value, (list, tuple)) else [value]

    hw = deepcopy(hardware)
    current = get_global_tx_values(hw, param, defaults)
    if idx is not None:
        while len(current) <= idx:
            current.append(current[-1] if current else 0.0)
        current[idx] = value
    else:
        current = list(value) if isinstance(value, (list, tuple)) else [value]

    apply_global_tx_values_to_hardware(hw, param, current, defaults)
    device_cfg.set_param("hardware", hw)
    return get_global_tx_values(hw, param, defaults)


def update_device_rx_param(
    device_cfg,
    param: str,
    value: Any,
    idx: Optional[int] = None,
) -> List:
    hardware = device_cfg.get_param("hardware")
    defaults = device_cfg.to_dict()

    if not hardware:
        if idx is not None:
            current = list(get_global_rx_values(None, param, defaults))
            while len(current) <= idx:
                current.append(0.0)
            current[idx] = value
            device_cfg.set_param(param, current)
            return current
        device_cfg.set_param(param, value)
        return list(value) if isinstance(value, (list, tuple)) else [value]

    hw = deepcopy(hardware)
    current = get_global_rx_values(hw, param, defaults)
    if idx is not None:
        while len(current) <= idx:
            current.append(current[-1] if current else 0.0)
        current[idx] = value
    else:
        current = list(value) if isinstance(value, (list, tuple)) else [value]

    apply_global_rx_values_to_hardware(hw, param, current, defaults)
    device_cfg.set_param("hardware", hw)
    return get_global_rx_values(hw, param, defaults)


def resolve_param_values(device_cfg, param: str) -> List:
    """Return flat values for UI display (hardware-aware)."""
    defaults = device_cfg.to_dict()
    hardware = device_cfg.get_param("hardware")
    if param in GLOBAL_TX_PARAMS:
        return get_global_tx_values(hardware, param, defaults)
    if param in GLOBAL_RX_PARAMS:
        return get_global_rx_values(hardware, param, defaults)
    raw = device_cfg.get_param(param)
    if isinstance(raw, (list, tuple)):
        return list(raw)
    if raw is None:
        return []
    return [raw]


def _update_scheme_local_list(scheme, attr: str, local_idx: int, value: float, param: str):
    current = list(getattr(scheme, attr, []))
    while len(current) <= local_idx:
        current.append(current[-1] if current else 0.0)
    current[local_idx] = float(value)
    scheme.update_param(param, current)


def apply_global_tx_param_to_schemes(
    schemes_by_device: dict,
    global_tx_to_device: Dict[int, Tuple[str, int]],
    hardware: Optional[Dict[str, dict]],
    group_config: dict,
    param: str,
    values,
) -> None:
    """Push a flat global Tx parameter list into hardware dict and live schemes."""
    flat = list(values) if isinstance(values, (list, tuple)) else [values]
    if hardware:
        apply_global_tx_values_to_hardware(hardware, param, flat, group_config)
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
