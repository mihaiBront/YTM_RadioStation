# MixesDB Scraper Test Suite

Comprehensive unit tests for the MixesDB scraper with **3000 tracklists target** per genre, covering all supported music styles.

## 🎯 Overview

This test suite provides comprehensive validation of the MixesDB scraper across all supported music genres. Each test targets **3000 tracklists** to ensure robust large-scale scraping capabilities.

## 🧪 Test Architecture

### Base Test Class (`base_test.py`)
- **BaseMixesDBTest**: Common functionality for all genre tests
- **Quality validation**: Mix data integrity checks
- **Batch processing**: Efficient scraping with configurable batch sizes
- **Error handling**: Comprehensive error tracking and reporting
- **Data persistence**: Automatic JSON export with timestamps

### Test Configuration
- **Target**: 3000 tracklists per genre
- **Batch Size**: 100 mixes per batch
- **Max Retries**: 3 attempts per failed operation
- **Delay**: 2 seconds between batches (respectful scraping)
- **Quality Threshold**: 0.3 minimum score for mix validation

## 🎵 Supported Genres

| Genre | Style Code | Expected Results | Test File |
|-------|------------|------------------|-----------|
| Hip Hop / R&B | `HH` | ~2,934 mixes | `test_hip_hop.py` |
| Deep House | `DH` | ~16,089 mixes | `test_deep_house.py` |
| Tech House / Electro | `TH` | ~44,431 mixes | `test_tech_house.py` |
| Techno / Acid | `TA` | ~42,933 mixes | `test_techno.py` |
| Progressive House | `PH` | ~35,541 mixes | `test_progressive_house.py` |
| Progressive / Trance | `PT` | ~37,651 mixes | `test_progressive_trance.py` |
| Minimal House | `MH` | ~3,138 mixes | `test_minimal_house.py` |
| Drum & Bass / Jungle | `DB` | ~2,890 mixes | `test_drum_bass.py` |
| Chill Out / Ambient | `CA` | ~5,971 mixes | `test_chill_ambient.py` |
| House | `H` | ~10,000+ mixes | `test_house.py` |
| Pure Minimal | `PM` | ~617 mixes | `test_pure_minimal.py` |

## 🚀 Running Tests

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Ensure project structure
cd scrapperMixesDB/
```

### Run All Tests
```bash
# Run complete test suite (all genres, 3000 tracklists each)
python Tests/run_all_tests.py

# Run with verbose output
python Tests/run_all_tests.py --verbose

# Quick mode (skip large-scale scraping)
python Tests/run_all_tests.py --quick
```

### Run Specific Genre Tests
```bash
# Run by genre name
python Tests/run_all_tests.py --genre hip_hop
python Tests/run_all_tests.py --genre deep_house
python Tests/run_all_tests.py --genre tech_house

# Run by style code
python Tests/run_all_tests.py --style-code HH
python Tests/run_all_tests.py --style-code DH
python Tests/run_all_tests.py --style-code TH
```

### Run Individual Test Files
```bash
# Run specific test file directly
python Tests/test_hip_hop.py
python Tests/test_deep_house.py
python Tests/test_tech_house.py
```

### Custom Target
```bash
# Run with custom tracklist target
python Tests/run_all_tests.py --target 5000
python Tests/run_all_tests.py --genre hip_hop --target 1000
```

## 📋 Test Structure

Each genre test includes **5 comprehensive test methods**:

### 1. `test_01_genre_exists`
- ✅ Verifies genre exists in configuration
- ✅ Validates style code mapping
- ✅ Confirms scraper can locate genre

### 2. `test_02_small_batch_scraping`
- ✅ Scrapes 10 mixes as proof of concept
- ✅ Validates data quality on each mix
- ✅ Ensures genre matching is correct

### 3. `test_03_medium_batch_scraping`
- ✅ Scrapes 50 mixes for reliability testing
- ✅ Spot-checks sample mixes for quality
- ✅ Validates pagination handling

### 4. `test_04_large_scale_scraping`
- 🎯 **Main test**: Scrapes 3000 tracklists
- ✅ Batched processing with progress tracking
- ✅ Error handling and retry logic
- ✅ Comprehensive quality validation
- ✅ Automatic data export to JSON

### 5. `test_05_track_quality_validation`
- ✅ Validates individual track data
- ✅ Checks artist and title completeness
- ✅ Calculates track quality metrics

## 📊 Quality Metrics

### Mix Quality Score (0.0 - 1.0)
- **0.2**: Mix ID present
- **0.2**: Title present
- **0.1**: URL present
- **0.1**: DJ name present
- **0.1**: Date present
- **0.1**: Genres present
- **0.2**: Tracklist present
- **0.05**: Duration present
- **0.05**: Metadata present

### Track Quality Rate
- Percentage of tracks with both title and artist
- Minimum threshold: 50%

## 💾 Output Data

### Test Data Location
```
Tests/test_data/
├── Hip Hop_large_scale_20250112_123456.json
├── Deep House_large_scale_20250112_124567.json
├── Tech House_large_scale_20250112_125678.json
└── ...
```

### JSON Structure
```json
{
  "timestamp": "2025-01-12T12:34:56",
  "genre": "Hip Hop",
  "test_type": "large_scale",
  "total_mixes": 3000,
  "target_count": 3000,
  "success_rate": 1.0,
  "test_duration": "0:45:23",
  "mixes": [
    {
      "id": "2025-01-12_-_dj_name_mix_title",
      "title": "Mix Title",
      "url": "https://www.mixesdb.com/w/2025-01-12_-_dj_name_mix_title",
      "dj_name": "DJ Name",
      "date": "2025-01-12",
      "genres": ["Hip Hop"],
      "tracks": [
        {
          "title": "Track Title",
          "artist": "Artist Name",
          "position": 1
        }
      ],
      "metadata": {
        "platforms": [],
        "file_size": null,
        "bitrate": null,
        "track_count": 10
      }
    }
  ]
}
```

## 🔧 Configuration

### Environment Variables
```bash
# Optional: Set custom delays
export SCRAPER_DELAY=3.0  # Seconds between requests
export SCRAPER_RETRIES=5  # Max retry attempts
```

### Test Customization
```python
# In base_test.py
class BaseMixesDBTest:
    TARGET_TRACKLISTS = 3000  # Can be overridden
    BATCH_SIZE = 100
    MAX_RETRIES = 3
    DELAY_BETWEEN_BATCHES = 2.0
```

## 📈 Performance Expectations

### Estimated Runtime per Genre
- **Small genres** (Pure Minimal ~617): 5-10 minutes
- **Medium genres** (Hip Hop ~2,934): 15-30 minutes
- **Large genres** (Tech House ~44,431): 45-90 minutes

### Full Test Suite Runtime
- **All 11 genres**: 4-8 hours (depends on network speed)
- **Quick mode**: 30-60 minutes (skips large-scale scraping)

## 🛠️ Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Ensure you're in the project root
cd scrapperMixesDB/
python Tests/run_all_tests.py
```

#### 2. Missing Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Network Issues
```bash
# Run with longer delays
python Tests/run_all_tests.py --genre hip_hop --target 100
```

#### 4. Memory Issues
```bash
# Run genres individually
python Tests/run_all_tests.py --genre hip_hop
```

### Debug Mode
```bash
# Run individual tests with verbose output
python Tests/test_hip_hop.py -v
```

## 🎯 Test Results Interpretation

### Success Criteria
- ✅ All 5 test methods pass
- ✅ 3000 tracklists scraped successfully
- ✅ Average quality score > 0.3
- ✅ Track quality rate > 50%
- ✅ No critical errors during scraping

### Failure Analysis
- **Genre not found**: Check configuration files
- **Style code mismatch**: Verify style code mapping
- **Network failures**: Check internet connection
- **Quality failures**: Review scraping logic
- **Pagination issues**: Check `_has_next_page` method

## 📚 Additional Resources

### Key Files
- **`base_test.py`**: Common test functionality
- **`run_all_tests.py`**: Test runner and orchestration
- **`test_*.py`**: Individual genre test files
- **`../scrapers/mixesdb_scraper.py`**: Core scraper implementation
- **`../config/genres_config.json`**: Genre configuration

### Style Code Discovery
The style codes were discovered through systematic browser testing of the MixesDB Explorer interface, ensuring accurate mapping to the correct genre filters.

### Data Validation
All scraped data undergoes comprehensive validation to ensure:
- Correct genre classification
- Complete mix metadata
- Valid tracklist information
- Proper URL formatting
- Accurate ID extraction

---

**🎵 Happy Testing!** 

This test suite ensures the MixesDB scraper can reliably handle large-scale scraping operations across all supported music genres with high data quality standards. 