import json


# This represents a custom data source for the plotting mechanism
class DataSource:
    def __init__(self, group_id: str, channel: int, label: str):
        """
        Keeps track of where the data is from (group_id, group_channel)
        """
        self.group_id = group_id
        self.channel = channel
        self.label = label  # Human-readable label for the source

    def __eq__(self, other):
        return self.group_id == other.group_id and self.channel == other.channel

    def __hash__(self):
        # Hash based on the same attributes used in __eq__
        # Use id() for device since device objects might not be hashable
        # Use the channel string directly since it should be hashable
        return hash((id(self.group_id), self.channel))

    def __repr__(self):
        # String display
        return f"{self.label} [{self.group_id}]"

    # The following methods allow transmission over sockets
    def to_dict(self):
        result = {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }

        return result

    @classmethod
    def from_dict(self, data_dict):
        """
        While we can construct a configuration for any dictionary, we check if a
        special class-based configuration can be restored to enable extra features.
        """
        return self(data_dict)

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(self, json_str):
        return self.from_dict(json.loads(json_str))
