# Default rate (Hz) at which a data source is rendered on screen. The streaming
# pipeline decimates incoming data down to roughly this rate for display.
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

    # Identity is (group_id, channel); `label` is a mutable display name and is
    # deliberately excluded, since sources are dict keys for routing.
    def __eq__(self, other):
        if not isinstance(other, DataSource):
            return False
        return self.group_id == other.group_id and self.channel == other.channel

    def __hash__(self):
        return hash((self.group_id, self.channel))

    def __repr__(self):
        return self.get_display_label()

    def get_display_label(self) -> str:
        """Name shown in the UI: the device group followed by the stream label.

        Channel labels are only unique within a device, so a bare label is
        ambiguous as soon as two devices stream at once.
        """
        if not self.group_id:
            return str(self.label)
        return f"{self.group_id}: {self.label}"

    def get_disp_freq(self) -> float:
        """Display refresh frequency (Hz) used to size plot buffers."""
        return getattr(self, "disp_freq", DEFAULT_DISPLAY_FREQUENCY)

    def to_dict(self):
        return {
            "group_id": self.group_id,
            "channel": self.channel,
            "label": self.label,
            "disp_freq": self.get_disp_freq(),
        }

    @classmethod
    def from_dict(cls, data_dict):
        return cls(
            group_id=data_dict.get("group_id"),
            channel=data_dict.get("channel"),
            label=data_dict.get("label"),
            disp_freq=data_dict.get("disp_freq", DEFAULT_DISPLAY_FREQUENCY),
        )
