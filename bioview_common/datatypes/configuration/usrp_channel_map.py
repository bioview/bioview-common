"""USRP virtual-group channel map resolution for MIMO and DPIC layouts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from bioview_common.datatypes.datasource import DataSource


@dataclass
class GlobalChannelRegistry:
    """Flat global Tx/Rx indices across all hardware in a virtual USRP group."""

    tx_entries: List[Tuple[str, int]] = field(default_factory=list)
    rx_entries: List[Tuple[str, int]] = field(default_factory=list)
    tx_if_freq: List[float] = field(default_factory=list)
    tx_filter_bw: List[float] = field(default_factory=list)

    @property
    def num_tx(self) -> int:
        return len(self.tx_entries)

    @property
    def num_rx(self) -> int:
        return len(self.rx_entries)


@dataclass
class DpicPair:
    inject_tx: int
    measure_tx: int

    @property
    def target_rx(self) -> int:
        return self.measure_tx


def build_global_registry(hardware: Dict[str, dict]) -> GlobalChannelRegistry:
    """Flatten hardware dict (keyed by device_name) into global channel indices."""
    registry = GlobalChannelRegistry()
    for _device_name, hw in hardware.items():
        tx_channels = hw.get("tx_channels", [0])
        rx_channels = hw.get("rx_channels", [0])
        if_freqs = hw.get("if_freq", [100e3] * len(tx_channels))
        filter_bw = hw.get("if_filter_bw", 5e3)
        if not isinstance(filter_bw, (list, tuple)):
            filter_bw = [filter_bw] * len(tx_channels)

        for local_idx, ch in enumerate(tx_channels):
            registry.tx_entries.append((_device_name, ch))
            registry.tx_if_freq.append(
                if_freqs[local_idx] if local_idx < len(if_freqs) else if_freqs[-1]
            )
            registry.tx_filter_bw.append(
                filter_bw[local_idx] if local_idx < len(filter_bw) else filter_bw[-1]
            )
        for ch in rx_channels:
            registry.rx_entries.append((_device_name, ch))
    return registry


def _measurement_tx_rx_sets(
    channel_map: dict, registry: GlobalChannelRegistry
) -> Tuple[List[int], List[int]]:
    layout = channel_map.get("layout", "full_nxn")
    inject_txs = {p["inject_tx"] for p in channel_map.get("dpic", [])}

    if layout == "hybrid_mimo":
        tx_global = list(channel_map.get("mimo", {}).get("tx_global", []))
        rx_global = list(channel_map.get("mimo", {}).get("rx_global", []))
    elif layout == "custom":
        pairs = channel_map.get("pairs", [])
        tx_global = sorted({p["tx"] for p in pairs})
        rx_global = sorted({p["rx"] for p in pairs})
    else:
        tx_global = [i for i in range(registry.num_tx) if i not in inject_txs]
        rx_global = list(range(registry.num_rx))

    return tx_global, rx_global


def resolve_channel_map(
    group_id: str,
    channel_map: Optional[dict],
    hardware: Dict[str, dict],
) -> Tuple[Set[DataSource], GlobalChannelRegistry, List[DpicPair]]:
    """Build DataSource set and DPIC pairs from hardware + channel_map config."""
    registry = build_global_registry(hardware)

    if not channel_map:
        channel_map = {"layout": "full_nxn", "dpic": []}

    tx_global, rx_global = _measurement_tx_rx_sets(channel_map, registry)
    layout = channel_map.get("layout", "full_nxn")

    tx_label_map = {g: i + 1 for i, g in enumerate(tx_global)}
    rx_label_map = {g: i + 1 for i, g in enumerate(rx_global)}

    data_sources: Set[DataSource] = set()
    ch_ctr = 0

    if layout == "custom":
        for pair in channel_map.get("pairs", []):
            t_idx = pair["tx"]
            r_idx = pair["rx"]
            label = pair.get("label") or f"Tx{tx_label_map[t_idx]}Rx{rx_label_map[r_idx]}"
            source = DataSource(group_id=group_id, channel=ch_ctr, label=label)
            source.tx_idx = t_idx
            source.rx_idx = r_idx
            source.tx_label = tx_label_map.get(t_idx, t_idx + 1)
            source.rx_label = rx_label_map.get(r_idx, r_idx + 1)
            data_sources.add(source)
            ch_ctr += 1
    else:
        for r_idx in rx_global:
            for t_idx in tx_global:
                label = f"Tx{tx_label_map[t_idx]}Rx{rx_label_map[r_idx]}"
                source = DataSource(group_id=group_id, channel=ch_ctr, label=label)
                source.tx_idx = t_idx
                source.rx_idx = r_idx
                source.tx_label = tx_label_map[t_idx]
                source.rx_label = rx_label_map[r_idx]
                data_sources.add(source)
                ch_ctr += 1

    dpic_pairs = [
        DpicPair(inject_tx=p["inject_tx"], measure_tx=p["measure_tx"])
        for p in channel_map.get("dpic", [])
    ]
    return data_sources, registry, dpic_pairs


def build_hardware_dict(device_cfg, group_id: str) -> Dict[str, dict]:
    """Return hardware dict keyed by device_name; wrap single-device configs."""
    hardware = device_cfg.get_param("hardware")
    if hardware:
        return dict(hardware)

    device_name = device_cfg.get_param("device_name") or group_id
    skip = {
        "hardware",
        "channel_map",
        "type",
        "device_type",
        "cfg_type",
        "device_name",
        "absolute_channel_nums",
        "signal_scheme",
        "calibration",
        "dpic_balance",
        "tx_phase",
        "fmcw",
        "pulsed_doppler",
    }
    hw_entry = {
        k: v
        for k, v in device_cfg.to_dict().items()
        if k not in skip and not k.startswith("_")
    }
    hw_entry["device_name"] = device_name
    return {device_name: hw_entry}


def resolve_device_serial(
    device_name: str,
    hw_entry: dict,
    discovered: dict,
    cache_lookup,
) -> Optional[str]:
    """Resolve serial: config -> cache -> discovery by name."""
    serial = hw_entry.get("serial")
    if serial:
        return serial
    serial = cache_lookup(device_name)
    if serial:
        return serial
    if device_name in discovered:
        return discovered[device_name].get("serial")
    for info in discovered.values():
        if info.get("name") == device_name:
            return info.get("serial")
    return None
