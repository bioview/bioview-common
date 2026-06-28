import json

# Default rate (Hz) at which a data source is rendered on screen. The streaming
# pipeline decimates incoming data down to roughly this rate for display, so the
# plot buffers are sized using it rather than the (much higher) acquisition rate.
DEFAULT_DISPLAY_FREQUENCY = 200.0

class DataSource:
    def __init__(self, group_id: str, channel: int, label: str, disp_freq: float = DEFAULT_DISPLAY_FREQUENCY):
        self.group_id = group_id
        self.channel = channel
        self.label = label
        self.disp_freq = disp_freq

    # Identity is the (group_id, channel) pair that uniquely addresses a physical
    # stream. `label` is a human-facing display name that can be changed freely
    # without making this a different source, so it is deliberately excluded from
    # equality/hashing (sources are used as dict keys / set members for routing).
    def __eq__(self, other):
        if not isinstance(other, DataSource):
            return False
        return self.group_id == other.group_id and self.channel == other.channel

    def __hash__(self):
        return hash((self.group_id, self.channel))

    def __repr__(self):
        return f"{self.label} [{self.group_id}:{self.channel}]"

    def get_disp_freq(self) -> float:
        """Display refresh frequency (Hz) used to size plot buffers."""
        return getattr(self, "disp_freq", DEFAULT_DISPLAY_FREQUENCY)

    def to_dict(self):
        return {
            "group_id": self.group_id,
            "channel": self.channel,
            "label": self.label,
            "disp_freq": self.get_disp_freq()
        }

    @classmethod
    def from_dict(cls, data_dict):
        return cls(
            group_id=data_dict.get("group_id"),
            channel=data_dict.get("channel"),
            label=data_dict.get("label"),
            disp_freq=data_dict.get("disp_freq", DEFAULT_DISPLAY_FREQUENCY)
        )

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str):
        return cls.from_dict(json.loads(json_str))
