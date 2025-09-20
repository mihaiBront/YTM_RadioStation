from src.utils.Serializable import Serializable
from dataclasses import dataclass, field

@dataclass
class SongInfo(Serializable):
    name: str = field(default_factory=str)
    artist: str = field(default_factory=str)

@dataclass
class LLM_prompt_input(Serializable):
    previous_song: SongInfo = field(default_factory=SongInfo)
    next_song: SongInfo = field(default_factory=SongInfo)