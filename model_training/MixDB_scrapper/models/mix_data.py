from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Track:
    """Represents a track in a mix"""
    title: str
    artist: Optional[str] = None
    start_time: Optional[str] = None  # Timestamp when track starts (e.g., "1:23:45")
    track_number: Optional[int] = None
    original_text: Optional[str] = None  # Original track text from source
    
    # Keep time_position for backward compatibility, but map to start_time
    @property
    def time_position(self) -> Optional[str]:
        return self.start_time
    
    @time_position.setter
    def time_position(self, value: Optional[str]) -> None:
        self.start_time = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'artist': self.artist,
            'start_time': self.start_time,
            'time_position': self.start_time,  # For backward compatibility
            'track_number': self.track_number,
            'original_text': self.original_text
        }


@dataclass
class Mix:
    """Represents a DJ mix from MixesDB"""
    title: str
    url: str
    id: Optional[str] = None  # Unique identifier extracted from URL
    dj_name: Optional[str] = None
    date: Optional[str] = None  # Changed to string for flexible date formats
    duration: Optional[str] = None
    description: Optional[str] = None
    genres: List[str] = field(default_factory=list)  # Changed from single genre to list
    tracks: List[Track] = field(default_factory=list)
    download_links: List[str] = field(default_factory=list)
    stream_links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None  # Added for additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'dj_name': self.dj_name,
            'date': self.date,
            'duration': self.duration,
            'description': self.description,
            'genres': self.genres,
            'tracks': [track.to_dict() for track in self.tracks],
            'download_links': self.download_links,
            'stream_links': self.stream_links,
            'tags': self.tags,
            'metadata': self.metadata
        }
    
    def add_genre(self, genre: str) -> None:
        """Add a genre to the mix if not already present"""
        if genre and genre not in self.genres:
            self.genres.append(genre)
    
    def add_track(self, track: Track) -> None:
        """Add a track to the mix"""
        self.tracks.append(track)
    
    def add_download_link(self, link: str) -> None:
        """Add a download link if not already present"""
        if link and link not in self.download_links:
            self.download_links.append(link)
    
    def add_stream_link(self, link: str) -> None:
        """Add a stream link if not already present"""
        if link and link not in self.stream_links:
            self.stream_links.append(link)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        if self.metadata is None:
            return default
        return self.metadata.get(key, default)


@dataclass
class Genre:
    """Represents a music genre from MixesDB"""
    name: str
    slug: str
    description: str
    mix_count: int
    url: Optional[str] = None
    category: Optional[str] = None  # Added category field
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'mix_count': self.mix_count,
            'url': self.url,
            'category': self.category
        }


@dataclass
class ScrapingSession:
    """Represents a scraping session with metadata"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    genres_scraped: List[str] = field(default_factory=list)
    total_mixes_found: int = 0
    status: str = "running"  # running, completed, failed, interrupted
    error_message: Optional[str] = None
    config_used: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'genres_scraped': self.genres_scraped,
            'total_mixes_found': self.total_mixes_found,
            'status': self.status,
            'error_message': self.error_message,
            'config_used': self.config_used
        } 