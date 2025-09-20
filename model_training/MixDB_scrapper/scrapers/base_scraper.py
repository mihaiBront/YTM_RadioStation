import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup

from models.mix_data import Mix, Genre, ScrapingSession
from utils.scraper_utils import ScraperUtils


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self, config_path: str = "config/genres_config.json"):
        """
        Initialize the base scraper
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.utils = ScraperUtils(self.config.get('scraping_config', {}))
        self.session = self.utils.get_session()
        self.current_session: Optional[ScrapingSession] = None
        
        # Create output directories
        self._create_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.utils.logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            self.utils.logger.error(f"Invalid JSON in configuration file: {e}")
            raise
    
    def _create_directories(self):
        """Create necessary output directories"""
        directories = [
            "output/data",
            "output/logs",
            "output/sessions"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def start_session(self, genres: List[str] = None) -> ScrapingSession:
        """
        Start a new scraping session
        
        Args:
            genres: List of genres to scrape. If None, all genres will be scraped
            
        Returns:
            ScrapingSession object
        """
        session_id = str(uuid.uuid4())
        self.current_session = ScrapingSession(
            session_id=session_id,
            start_time=datetime.now(),
            genres_scraped=genres or []
        )
        
        self.utils.logger.info(f"Started scraping session: {session_id}")
        return self.current_session
    
    def end_session(self, status: str = "completed"):
        """
        End the current scraping session
        
        Args:
            status: Final status of the session
        """
        if self.current_session:
            self.current_session.end_time = datetime.now()
            self.current_session.status = status
            
            # Save session data
            session_file = f"output/sessions/session_{self.current_session.session_id}.json"
            self.utils.save_json(self.current_session.to_dict(), session_file)
            
            duration = self.current_session.end_time - self.current_session.start_time
            self.utils.logger.info(
                f"Session {self.current_session.session_id} ended. "
                f"Status: {status}, Duration: {duration}, "
                f"Mixes scraped: {self.current_session.total_mixes_scraped}"
            )
    
    def get_genres(self) -> List[Genre]:
        """
        Get all available genres from configuration
        
        Returns:
            List of Genre objects
        """
        genres = []
        base_url = self.config['category_base_url']
        
        # Process main genre groups
        for group_name, group_data in self.config['genre_groups'].items():
            for genre_data in group_data['genres']:
                genre = Genre(
                    name=genre_data['name'],
                    slug=genre_data['slug'],
                    description=group_data.get('description', ''),
                    mix_count=genre_data.get('count', 0),
                    url=f"{base_url}{genre_data['slug']}"
                )
                genres.append(genre)
        
        # Process additional genres
        additional_genres = self.config.get('additional_genres', {})
        if additional_genres:
            for genre_data in additional_genres.get('genres', []):
                genre = Genre(
                    name=genre_data['name'],
                    slug=genre_data['slug'],
                    description=additional_genres.get('description', ''),
                    mix_count=genre_data.get('count', 0),
                    url=f"{base_url}{genre_data['slug']}"
                )
                genres.append(genre)
        
        return genres
    
    def get_genre_by_name(self, name: str) -> Optional[Genre]:
        """
        Get a specific genre by name
        
        Args:
            name: Name of the genre
            
        Returns:
            Genre object or None if not found
        """
        genres = self.get_genres()
        for genre in genres:
            if genre.name.lower() == name.lower():
                return genre
        return None
    
    def save_mixes(self, mixes: List[Mix], filename: str = None) -> str:
        """
        Save scraped mixes to JSON file
        
        Args:
            mixes: List of Mix objects
            filename: Custom filename. If None, auto-generated
            
        Returns:
            Path to saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mixes_{timestamp}.json"
        
        filepath = f"output/data/{filename}"
        
        # Convert mixes to dictionaries
        mixes_data = [mix.to_dict() for mix in mixes]
        
        # Add metadata
        data = {
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "total_mixes": len(mixes),
                "session_id": self.current_session.session_id if self.current_session else None
            },
            "mixes": mixes_data
        }
        
        if self.utils.save_json(data, filepath):
            self.utils.logger.info(f"Saved {len(mixes)} mixes to {filepath}")
            return filepath
        else:
            raise Exception(f"Failed to save mixes to {filepath}")
    
    def load_mixes(self, filepath: str) -> List[Mix]:
        """
        Load mixes from JSON file
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            List of Mix objects
        """
        data = self.utils.load_json(filepath)
        if not data:
            return []
        
        mixes = []
        for mix_data in data.get('mixes', []):
            # Convert back to Mix object
            mix = Mix(
                title=mix_data['title'],
                url=mix_data['url'],
                dj_name=mix_data.get('dj_name'),
                genre=mix_data.get('genre'),
                date=datetime.fromisoformat(mix_data['date']) if mix_data.get('date') else None,
                duration=mix_data.get('duration'),
                description=mix_data.get('description'),
                download_links=mix_data.get('download_links', []),
                stream_links=mix_data.get('stream_links', []),
                tags=mix_data.get('tags', []),
                bpm_range=mix_data.get('bpm_range'),
                rating=mix_data.get('rating'),
                views=mix_data.get('views'),
                comments_count=mix_data.get('comments_count'),
                scraped_at=datetime.fromisoformat(mix_data['scraped_at'])
            )
            mixes.append(mix)
        
        return mixes
    
    @abstractmethod
    def scrape_genre(self, genre: Genre, limit: int = None) -> List[Mix]:
        """
        Scrape mixes for a specific genre
        
        Args:
            genre: Genre object to scrape
            limit: Maximum number of mixes to scrape
            
        Returns:
            List of Mix objects
        """
        pass
    
    @abstractmethod
    def scrape_mix_details(self, mix_url: str) -> Optional[Mix]:
        """
        Scrape detailed information for a specific mix
        
        Args:
            mix_url: URL of the mix page
            
        Returns:
            Mix object with detailed information
        """
        pass
    
    def scrape_all_genres(self, limit_per_genre: int = None) -> List[Mix]:
        """
        Scrape mixes from all available genres
        
        Args:
            limit_per_genre: Maximum number of mixes per genre
            
        Returns:
            List of all scraped Mix objects
        """
        if not self.current_session:
            self.start_session()
        
        all_mixes = []
        genres = self.get_genres()
        
        self.utils.logger.info(f"Starting to scrape {len(genres)} genres")
        
        for genre in genres:
            try:
                self.utils.logger.info(f"Scraping genre: {genre.name}")
                mixes = self.scrape_genre(genre, limit_per_genre)
                all_mixes.extend(mixes)
                
                if self.current_session:
                    self.current_session.total_mixes_scraped += len(mixes)
                    if genre.name not in self.current_session.genres_scraped:
                        self.current_session.genres_scraped.append(genre.name)
                
                self.utils.logger.info(f"Scraped {len(mixes)} mixes from {genre.name}")
                
            except Exception as e:
                error_msg = f"Error scraping genre {genre.name}: {str(e)}"
                self.utils.logger.error(error_msg)
                if self.current_session:
                    self.current_session.errors.append(error_msg)
        
        return all_mixes 