"""
Base test class for MixesDB scraper tests.

This module provides common functionality and setup for all genre-specific tests.
"""

import unittest
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

# Add the parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scrapers.mixesdb_scraper import MixesDBScraper
from models.mix_data import Mix, Track, Genre
from utils.scraper_utils import ScraperUtils


class BaseMixesDBTest(unittest.TestCase):
    """Base test class for MixesDB scraper tests."""
    
    # Test configuration
    TARGET_TRACKLISTS = 3000
    BATCH_SIZE = 100
    MAX_RETRIES = 3
    DELAY_BETWEEN_BATCHES = 2.0
    
    # Test data directory
    TEST_DATA_DIR = Path("Tests/test_data")
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once per test class."""
        print(f"\n{'='*60}")
        print(f"🧪 Setting up {cls.__name__}")
        print(f"{'='*60}")
        
        # Create test data directory
        cls.TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize scraper
        cls.scraper = MixesDBScraper(config_path="config/genres_config.json")
        
        # Initialize utils for logging
        cls.utils = ScraperUtils()
        
        # Test results storage
        cls.test_results = {
            'start_time': datetime.now(),
            'total_scraped': 0,
            'successful_batches': 0,
            'failed_batches': 0,
            'errors': []
        }
        
        print(f"✅ Test environment initialized for {cls.__name__}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests in the class."""
        end_time = datetime.now()
        duration = end_time - cls.test_results['start_time']
        
        print(f"\n{'='*60}")
        print(f"📊 Test Results for {cls.__name__}")
        print(f"{'='*60}")
        print(f"⏱️  Duration: {duration}")
        print(f"📈 Total Scraped: {cls.test_results['total_scraped']}")
        print(f"✅ Successful Batches: {cls.test_results['successful_batches']}")
        print(f"❌ Failed Batches: {cls.test_results['failed_batches']}")
        
        if cls.test_results['errors']:
            print(f"🚨 Errors ({len(cls.test_results['errors'])}):")
            for error in cls.test_results['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
        
        print(f"{'='*60}")
    
    def setUp(self):
        """Set up each individual test."""
        self.test_start_time = datetime.now()
        
    def tearDown(self):
        """Clean up after each test."""
        pass
        
    def get_genre_by_name(self, genre_name: str) -> Optional[Genre]:
        """Get genre object by name."""
        return self.scraper.get_genre_by_name(genre_name)
        
    def scrape_genre_batch(self, genre: Genre, batch_size: int = None, 
                          offset: int = 0) -> List[Mix]:
        """Scrape a batch of mixes for a genre."""
        if batch_size is None:
            batch_size = self.BATCH_SIZE
            
        try:
            mixes = self.scraper.scrape_genre(
                genre=genre, 
                limit=batch_size, 
                time_filter="Fresh"
            )
            
            self.test_results['total_scraped'] += len(mixes) if mixes else 0
            
            if mixes:
                self.test_results['successful_batches'] += 1
                return mixes
            else:
                self.test_results['failed_batches'] += 1
                return []
                
        except Exception as e:
            error_msg = f"Failed to scrape batch for {genre.name}: {str(e)}"
            self.test_results['errors'].append(error_msg)
            self.test_results['failed_batches'] += 1
            raise
    
    def save_test_results(self, genre_name: str, mixes: List[Mix], 
                         test_type: str = "genre_test") -> str:
        """Save test results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{genre_name}_{test_type}_{timestamp}.json"
        filepath = self.TEST_DATA_DIR / filename
        
        # Convert mixes to dictionaries
        data = {
            'timestamp': datetime.now().isoformat(),
            'genre': genre_name,
            'test_type': test_type,
            'total_mixes': len(mixes),
            'target_count': self.TARGET_TRACKLISTS,
            'success_rate': len(mixes) / self.TARGET_TRACKLISTS if self.TARGET_TRACKLISTS > 0 else 0,
            'test_duration': str(datetime.now() - self.test_start_time),
            'mixes': [mix.to_dict() for mix in mixes]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Test results saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            error_msg = f"Failed to save test results: {str(e)}"
            self.test_results['errors'].append(error_msg)
            raise
    
    def validate_mix_quality(self, mix: Mix) -> Dict[str, Any]:
        """Validate the quality of a scraped mix."""
        quality_report = {
            'valid': True,
            'issues': [],
            'score': 0.0,
            'details': {}
        }
        
        # Check required fields
        if not mix.id:
            quality_report['issues'].append("Missing mix ID")
            quality_report['valid'] = False
        else:
            quality_report['score'] += 0.2
            
        if not mix.title:
            quality_report['issues'].append("Missing title")
            quality_report['valid'] = False
        else:
            quality_report['score'] += 0.2
            
        if not mix.url:
            quality_report['issues'].append("Missing URL")
            quality_report['valid'] = False
        else:
            quality_report['score'] += 0.1
            
        if not mix.dj_name:
            quality_report['issues'].append("Missing DJ name")
        else:
            quality_report['score'] += 0.1
            
        if not mix.date:
            quality_report['issues'].append("Missing date")
        else:
            quality_report['score'] += 0.1
            
        if not mix.genres:
            quality_report['issues'].append("Missing genres")
        else:
            quality_report['score'] += 0.1
            
        if not mix.tracks:
            quality_report['issues'].append("Missing tracklist")
        else:
            quality_report['score'] += 0.2
            quality_report['details']['track_count'] = len(mix.tracks)
            
        # Additional quality checks
        if mix.duration:
            quality_report['score'] += 0.05
            quality_report['details']['has_duration'] = True
            
        if mix.metadata:
            quality_report['score'] += 0.05
            quality_report['details']['has_metadata'] = True
            
        # Final score calculation
        quality_report['score'] = min(quality_report['score'], 1.0)
        quality_report['details']['final_score'] = quality_report['score']
        
        return quality_report
    
    def assertMixQuality(self, mix: Mix, min_score: float = 0.5):
        """Assert that a mix meets minimum quality standards."""
        quality_report = self.validate_mix_quality(mix)
        
        self.assertTrue(
            quality_report['valid'],
            f"Mix {mix.id} failed validation: {quality_report['issues']}"
        )
        
        self.assertGreaterEqual(
            quality_report['score'],
            min_score,
            f"Mix {mix.id} quality score {quality_report['score']:.2f} below minimum {min_score}"
        )
    
    def assertGenreMatches(self, mix: Mix, expected_genre: str):
        """Assert that a mix belongs to the expected genre."""
        self.assertIn(
            expected_genre,
            mix.genres,
            f"Mix {mix.id} does not contain expected genre '{expected_genre}'. Found: {mix.genres}"
        )
    
    def log_test_progress(self, current: int, total: int, genre_name: str):
        """Log test progress."""
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"📊 {genre_name}: {current}/{total} ({percentage:.1f}%)") 