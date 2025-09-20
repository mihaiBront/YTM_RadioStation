from src.utils.Serializable import Serializable
from dataclasses import dataclass, field

@dataclass
class HostConfig(Serializable):
    name: str = field(default="Mike")
    gender: str = field(default="male")
    personality: str = field(default="friendly")
    tone: str = field(default="happy")

@dataclass
class StationConfig(Serializable):
    name: str = field(default="89.9 Synthetic FM")
    genre: str = field(default="hip hop")
    mood: str = field(default="happy")
    tone: str = field(default="warm")
    location: str = field(default="New York")

@dataclass
class UserConfig(Serializable):
    host_config: HostConfig = field(default_factory=HostConfig)
    station_config: StationConfig = field(default_factory=StationConfig)
    
if __name__ == "__main__":
    user_config = UserConfig()
    user_config.to_json("user_config.json")