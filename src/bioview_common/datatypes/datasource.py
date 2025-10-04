# This represents a custom data source for the plot
class DataSource:
    def __init__(self, group_id: str, channel: int, label: str):
        ''' 
        Keeps track of where the data is from (group_id, group_channel)
        '''
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
        return f"{self.group_id}[{self.channel}]: {self.label}"