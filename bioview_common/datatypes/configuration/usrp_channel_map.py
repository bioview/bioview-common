"""USRP virtual-group channel map resolution for MIMO and DPIC layouts."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioview_common.datatypes.datasource import DataSource


@dataclass
class GlobalChannelRegistry:
    """Flat global Tx/Rx indices across all hardware in a virtual USRP group."""

    tx_entries: list[tuple[str, int]] = field(default_factory=list)
    rx_entries: list[tuple[str, int]] = field(default_factory=list)
    tx_if_freq: list[float] = field(default_factory=list)
    tx_filter_bw: list[float] = field(default_factory=list)

    @property
    def num_tx(self) -> int:
        return len(self.tx_entries)

    @property
    def num_rx(self) -> int:
        return len(self.rx_entries)


@dataclass
class DpicPair:
    """One direct-path cancellation loop.

    ``measure_rx`` is a *receive* index and must be given explicitly unless it
    happens to equal ``measure_tx`` (only true for a 1x1 layout).
    """

    inject_tx: int
    measure_tx: int
    measure_rx: int | None = None

    @property
    def target_rx(self) -> int:
        return self.measure_tx if self.measure_rx is None else self.measure_rx


def build_global_registry(hardware: dict[str, dict]) -> GlobalChannelRegistry:
    """Flatten hardware dict (keyed by device_name) into global channel indices."""
    registry = GlobalChannelRegistry()
    for _device_name, hw in hardware.items():
        tx_channels = hw.get("tx_channels", [0])
        rx_channels = hw.get("rx_channels", [0])
        if_freqs = hw.get("if_freq", [100e3] * len(tx_channels))
        filter_bw = hw.get("if_filter_bw", 5e3)
        if not isinstance(filter_bw, list | tuple):
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


def inject_rx_indices(channel_map: dict, registry: GlobalChannelRegistry) -> set[int]:
    """Rx indices sharing a physical channel with a DPIC inject Tx.

    A radio channel used to radiate the cancellation tone is not receiving a
    measurement, so its Rx half produces rows that are dead by construction --
    every TxNRxM pair against it is noise. Matching is on ``(device, channel)``
    from the registry, so it holds however the hardware is laid out.
    """
    inject_txs = {p["inject_tx"] for p in channel_map.get("dpic", [])}
    inject_ports = {
        registry.tx_entries[t] for t in inject_txs if t < len(registry.tx_entries)
    }
    return {r for r, entry in enumerate(registry.rx_entries) if entry in inject_ports}


def _measurement_tx_rx_sets(
    channel_map: dict, registry: GlobalChannelRegistry
) -> tuple[list[int], list[int]]:
    layout = channel_map.get("layout", "full_nxn")
    inject_txs = {p["inject_tx"] for p in channel_map.get("dpic", [])}

    if layout == "custom":
        # Pairs are written out one by one; the author said exactly what they
        # want and nothing is inferred.
        pairs = channel_map.get("pairs", [])
        return sorted({p["tx"] for p in pairs}), sorted({p["rx"] for p in pairs})

    if layout == "hybrid_mimo":
        tx_global = list(channel_map.get("mimo", {}).get("tx_global", []))
        rx_global = list(channel_map.get("mimo", {}).get("rx_global", []))
    else:
        tx_global = list(range(registry.num_tx))
        rx_global = list(range(registry.num_rx))

    # Adding a DPIC pair retires both halves of the inject channel: the Tx is
    # radiating the cancellation tone rather than a measurement signal, and its
    # Rx has nothing to receive. Applied here rather than left to the config so
    # the grid follows the pair list automatically.
    inject_rxs = inject_rx_indices(channel_map, registry)
    tx_global = [t for t in tx_global if t not in inject_txs]
    rx_global = [r for r in rx_global if r not in inject_rxs]

    return tx_global, rx_global


def resolve_channel_map(
    group_id: str,
    channel_map: dict | None,
    hardware: dict[str, dict],
    disp_freq: float | None = None,
) -> tuple[set[DataSource], GlobalChannelRegistry, list[DpicPair]]:
    """Build DataSource set and DPIC pairs from hardware + channel_map config.

    ``disp_freq`` is the rate (Hz) at which the processing pipeline actually
    emits display samples for these sources. The client sizes its plot buffers
    from it, so it must be the post-decimation rate, not the Rx sample rate.
    """
    src_kwargs = {} if disp_freq is None else {"disp_freq": float(disp_freq)}
    registry = build_global_registry(hardware)

    if not channel_map:
        channel_map = {"layout": "full_nxn", "dpic": []}

    tx_global, rx_global = _measurement_tx_rx_sets(channel_map, registry)
    layout = channel_map.get("layout", "full_nxn")

    tx_label_map = {g: i + 1 for i, g in enumerate(tx_global)}
    rx_label_map = {g: i + 1 for i, g in enumerate(rx_global)}

    data_sources: set[DataSource] = set()
    ch_ctr = 0

    if layout == "custom":
        for pair in channel_map.get("pairs", []):
            t_idx = pair["tx"]
            r_idx = pair["rx"]
            label = (
                pair.get("label") or f"Tx{tx_label_map[t_idx]}Rx{rx_label_map[r_idx]}"
            )
            source = DataSource(
                group_id=group_id, channel=ch_ctr, label=label, **src_kwargs
            )
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
                source = DataSource(
                    group_id=group_id, channel=ch_ctr, label=label, **src_kwargs
                )
                source.tx_idx = t_idx
                source.rx_idx = r_idx
                source.tx_label = tx_label_map[t_idx]
                source.rx_label = rx_label_map[r_idx]
                data_sources.add(source)
                ch_ctr += 1

    dpic_pairs = [
        DpicPair(
            inject_tx=p["inject_tx"],
            measure_tx=p["measure_tx"],
            measure_rx=p.get("measure_rx"),
        )
        for p in channel_map.get("dpic", [])
    ]
    return data_sources, registry, dpic_pairs


def build_hardware_dict(device_cfg, group_id: str) -> dict[str, dict]:
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
) -> str | None:
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
