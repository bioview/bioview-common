DEFAULT_DISPLAY_FREQUENCY = 200.0


class DataSource:
    def __init__(
        self,
        group_id: str,
        channel: int,
        label: str,
        disp_freq: float = DEFAULT_DISPLAY_FREQUENCY,
    ):
        self.group_id = group_id
        self.channel = channel
        self.label = label
        self.disp_freq = disp_freq

    def __eq__(self, other):
        if not isinstance(other, DataSource):
            return False
        return self.group_id == other.group_id and self.channel == other.channel

    def __hash__(self):
        return hash((self.group_id, self.channel))

    def __repr__(self):
        return self.get_display_label()

    def get_display_label(self) -> str:
        """Name shown in the UI: the device group followed by the stream label."""
        if not self.group_id:
            return str(self.label)
        return f"{self.group_id}: {self.label}"

    def get_disp_freq(self) -> float:
        """Display refresh frequency (Hz) used to size plot buffers."""
        return getattr(self, "disp_freq", DEFAULT_DISPLAY_FREQUENCY)

    OPTIONAL_FIELDS = ("tx_idx", "rx_idx", "tx_label", "rx_label", "component")

    def to_dict(self):
        payload = {
            "group_id": self.group_id,
            "channel": self.channel,
            "label": self.label,
            "disp_freq": self.get_disp_freq(),
        }
        for field in self.OPTIONAL_FIELDS:
            value = getattr(self, field, None)
            if value is not None:
                payload[field] = value
        if getattr(self, "is_cal_ref", False):
            payload["is_cal_ref"] = True
        return payload

    @classmethod
    def from_dict(cls, data_dict):
        source = cls(
            group_id=data_dict.get("group_id"),
            channel=data_dict.get("channel"),
            label=data_dict.get("label"),
            disp_freq=data_dict.get("disp_freq", DEFAULT_DISPLAY_FREQUENCY),
        )
        for field in cls.OPTIONAL_FIELDS:
            if data_dict.get(field) is not None:
                setattr(source, field, data_dict[field])
        source.is_cal_ref = bool(data_dict.get("is_cal_ref", False))
        return source
