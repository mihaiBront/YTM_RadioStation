from lib.Serializable import Serializable
from dataclasses import dataclass

@dataclass
class Segment(Serializable):
    tone: str
    tone_intensity: float
    text: str

@dataclass
class MultiSegmentListDeser(Serializable):
    segments: list[Segment]
    
    