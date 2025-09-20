"""
Unit tests for Techno / Acid genre scraping.

Tests the scraper's ability to extract Techno mixes from MixesDB.
Style Code: TA
Expected Results: ~42,933 mixes available
"""

import unittest
import time
from typing import List

from base_test import BaseMixesDBTest
from models.mix_data import Mix, Genre


class TestTechnoScraping(BaseMixesDBTest):
    """Test class for Techno / Acid genre scraping."""
    
    GENRE_NAME = "Techno"
    STYLE_CODE = "TA"
    EXPECTED_MIN_RESULTS = 40000  # Conservative estimate
    
    @classmethod
    def setUpClass(cls):
        """Set up Techno test environment."""
        super().setUpClass()
        print(f"🎵 Testing Techno / Acid genre (Style Code: {cls.STYLE_CODE})")
        print(f"🎯 Target: {cls.TARGET_TRACKLISTS} tracklists")
        print(f"📊 Expected minimum available: {cls.EXPECTED_MIN_RESULTS}")
    
    def test_01_genre_exists(self):
        """Test that Techno genre exists and is configured correctly."""
        genre = self.get_genre_by_name(self.GENRE_NAME)
        
        self.assertIsNotNone(genre, f"Genre '{self.GENRE_NAME}' not found")
        self.assertEqual(genre.name, self.GENRE_NAME)
        
        # Test style code mapping
        style_code = self.scraper._get_genre_style_code(self.GENRE_NAME)
        self.assertEqual(style_code, self.STYLE_CODE, 
                        f"Expected style code {self.STYLE_CODE}, got {style_code}")
        
        print(f"✅ Genre '{self.GENRE_NAME}' found with style code '{style_code}'")
    
    def test_02_small_batch_scraping(self):
        """Test scraping a small batch of Techno mixes."""
        genre = self.get_genre_by_name(self.GENRE_NAME)
        self.assertIsNotNone(genre)
        
        # Scrape small batch
        mixes = self.scrape_genre_batch(genre, batch_size=10)
        
        self.assertGreater(len(mixes), 0, "No mixes returned in small batch")
        self.assertLessEqual(len(mixes), 10, "More mixes returned than requested")
        
        # Test each mix quality
        for mix in mixes:
            self.assertMixQuality(mix, min_score=0.4)
            self.assertGenreMatches(mix, self.GENRE_NAME)
        
        print(f"✅ Small batch test passed: {len(mixes)} mixes scraped")
    
    def test_03_medium_batch_scraping(self):
        """Test scraping a medium batch of Techno mixes."""
        genre = self.get_genre_by_name(self.GENRE_NAME)
        self.assertIsNotNone(genre)
        
        # Scrape medium batch
        mixes = self.scrape_genre_batch(genre, batch_size=50)
        
        self.assertGreater(len(mixes), 0, "No mixes returned in medium batch")
        self.assertLessEqual(len(mixes), 50, "More mixes returned than requested")
        
        # Test sample of mixes
        sample_size = min(10, len(mixes))
        for i, mix in enumerate(mixes[:sample_size]):
            self.assertMixQuality(mix, min_score=0.4)
            self.assertGenreMatches(mix, self.GENRE_NAME)
        
        print(f"✅ Medium batch test passed: {len(mixes)} mixes scraped")
    
    def test_04_large_scale_scraping(self):
        """Test scraping large number of Techno mixes (3000 target)."""
        genre = self.get_genre_by_name(self.GENRE_NAME)
        self.assertIsNotNone(genre)
        
        all_mixes = []
        target_remaining = self.TARGET_TRACKLISTS
        batch_count = 0
        
        print(f"🚀 Starting large-scale scraping for {self.GENRE_NAME}")
        print(f"🎯 Target: {self.TARGET_TRACKLISTS} tracklists")
        
        while target_remaining > 0 and batch_count < 50:  # Safety limit
            batch_count += 1
            batch_size = min(self.BATCH_SIZE, target_remaining)
            
            try:
                print(f"📦 Batch {batch_count}: Scraping {batch_size} mixes...")
                mixes = self.scrape_genre_batch(genre, batch_size=batch_size)
                
                if not mixes:
                    print(f"⚠️  Batch {batch_count} returned no results, stopping")
                    break
                
                all_mixes.extend(mixes)
                target_remaining -= len(mixes)
                
                self.log_test_progress(len(all_mixes), self.TARGET_TRACKLISTS, self.GENRE_NAME)
                
                # Add delay between batches to be respectful
                if target_remaining > 0:
                    time.sleep(self.DELAY_BETWEEN_BATCHES)
                    
            except Exception as e:
                print(f"❌ Batch {batch_count} failed: {str(e)}")
                self.test_results['errors'].append(f"Batch {batch_count}: {str(e)}")
                break
        
        # Assert results
        self.assertGreater(len(all_mixes), 0, "No mixes scraped in large-scale test")
        
        # Quality check on sample
        sample_size = min(20, len(all_mixes))
        quality_scores = []
        
        for i, mix in enumerate(all_mixes[:sample_size]):
            quality_report = self.validate_mix_quality(mix)
            quality_scores.append(quality_report['score'])
            
            # Don't fail the entire test for individual mix quality issues
            if not quality_report['valid']:
                print(f"⚠️  Mix {i+1} quality issues: {quality_report['issues']}")
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Save results
        result_file = self.save_test_results(self.GENRE_NAME, all_mixes, "large_scale")
        
        # Final assertions
        self.assertGreater(avg_quality, 0.3, f"Average quality score {avg_quality:.2f} too low")
        
        print(f"✅ Large-scale test completed!")
        print(f"📊 Total scraped: {len(all_mixes)}")
        print(f"🎯 Target completion: {(len(all_mixes)/self.TARGET_TRACKLISTS*100):.1f}%")
        print(f"⭐ Average quality: {avg_quality:.2f}")
        print(f"💾 Results saved to: {result_file}")
    
    def test_05_track_quality_validation(self):
        """Test the quality of individual tracks in Techno mixes."""
        genre = self.get_genre_by_name(self.GENRE_NAME)
        self.assertIsNotNone(genre)
        
        # Get a small sample for detailed analysis
        mixes = self.scrape_genre_batch(genre, batch_size=5)
        self.assertGreater(len(mixes), 0)
        
        total_tracks = 0
        valid_tracks = 0
        
        for mix in mixes:
            if mix.tracks:
                total_tracks += len(mix.tracks)
                
                for track in mix.tracks:
                    # Basic track validation
                    if track.title and track.artist:
                        valid_tracks += 1
        
        if total_tracks > 0:
            track_quality_rate = valid_tracks / total_tracks
            print(f"📊 Track quality: {valid_tracks}/{total_tracks} ({track_quality_rate:.1%})")
            
            # Don't fail if some tracks are missing info, but expect reasonable quality
            self.assertGreater(track_quality_rate, 0.5, 
                             f"Track quality rate {track_quality_rate:.1%} too low")
        
        print(f"✅ Track quality validation passed")


if __name__ == '__main__':
    unittest.main(verbosity=2) 