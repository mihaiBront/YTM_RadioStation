#!/usr/bin/env python3
"""
Comprehensive test runner for MixesDB scraper.

This script runs all genre-specific tests with 3000 tracklists target each.
Can be run individually or as a full test suite.
"""

import sys
import os
import unittest
import argparse
from datetime import datetime
from pathlib import Path

# Add the parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import all test modules
from test_hip_hop import TestHipHopScraping
from test_deep_house import TestDeepHouseScraping
from test_tech_house import TestTechHouseScraping
from test_techno import TestTechnoScraping
from test_progressive_house import TestProgressiveHouseScraping
from test_progressive_trance import TestProgressiveTranceScraping
from test_minimal_house import TestMinimalHouseScraping
from test_drum_bass import TestDrumBassScraping
from test_chill_ambient import TestChillAmbientScraping
from test_house import TestHouseScraping
from test_pure_minimal import TestPureMinimalScraping


# Test suite registry
TEST_SUITES = {
    'hip_hop': TestHipHopScraping,
    'deep_house': TestDeepHouseScraping,
    'tech_house': TestTechHouseScraping,
    'techno': TestTechnoScraping,
    'progressive_house': TestProgressiveHouseScraping,
    'progressive_trance': TestProgressiveTranceScraping,
    'minimal_house': TestMinimalHouseScraping,
    'drum_bass': TestDrumBassScraping,
    'chill_ambient': TestChillAmbientScraping,
    'house': TestHouseScraping,
    'pure_minimal': TestPureMinimalScraping,
}

# Style code to test mapping
STYLE_CODE_MAPPING = {
    'HH': 'hip_hop',          # Hip Hop / R&B
    'DH': 'deep_house',       # Deep House
    'TH': 'tech_house',       # Tech House / Electro
    'TA': 'techno',           # Techno / Acid
    'PH': 'progressive_house', # Progressive House
    'PT': 'progressive_trance', # Progressive / Trance
    'MH': 'minimal_house',    # Minimal House
    'DB': 'drum_bass',        # Drum & Bass / Jungle
    'CA': 'chill_ambient',    # Chill Out / Ambient
    'H': 'house',             # House
    'PM': 'pure_minimal',     # Pure Minimal
}


def create_parser():
    """Create argument parser for test runner."""
    parser = argparse.ArgumentParser(
        description='Run MixesDB scraper tests for all genres with 3000 tracklists target',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available test suites:
{chr(10).join(f"  {key:<18} - {suite.__doc__.split('.')[0] if suite.__doc__ else 'No description'}" for key, suite in TEST_SUITES.items())}

Examples:
  python run_all_tests.py                    # Run all tests
  python run_all_tests.py --genre hip_hop   # Run Hip Hop tests only
  python run_all_tests.py --style-code TH   # Run Tech House tests by style code
  python run_all_tests.py --list            # List all available tests
  python run_all_tests.py --verbose         # Run with verbose output
        """
    )
    
    parser.add_argument(
        '--genre', '-g',
        choices=list(TEST_SUITES.keys()),
        help='Run tests for specific genre'
    )
    
    parser.add_argument(
        '--style-code', '-s',
        choices=list(STYLE_CODE_MAPPING.keys()),
        help='Run tests for specific style code'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available test suites'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose test output'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick tests only (skip large-scale scraping)'
    )
    
    parser.add_argument(
        '--target',
        type=int,
        default=3000,
        help='Target number of tracklists to scrape (default: 3000)'
    )
    
    return parser


def list_test_suites():
    """List all available test suites."""
    print("📋 Available Test Suites:")
    print("=" * 60)
    
    for key, suite in TEST_SUITES.items():
        style_code = getattr(suite, 'STYLE_CODE', 'N/A')
        genre_name = getattr(suite, 'GENRE_NAME', 'Unknown')
        expected_results = getattr(suite, 'EXPECTED_MIN_RESULTS', 'Unknown')
        
        print(f"🎵 {key:<18} - {genre_name}")
        print(f"   Style Code: {style_code}")
        print(f"   Expected Results: {expected_results:,} mixes")
        print()


def run_test_suite(test_class, verbose=False, quick=False):
    """Run a single test suite."""
    print(f"\n🧪 Running {test_class.__name__}")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    
    # Skip large-scale test if quick mode
    if quick:
        print("⚡ Quick mode: Skipping large-scale scraping test")
        filtered_tests = []
        for test in suite:
            if 'test_04_large_scale_scraping' not in test._testMethodName:
                filtered_tests.append(test)
        suite = unittest.TestSuite(filtered_tests)
    
    # Run tests
    runner = unittest.TextTestRunner(
        verbosity=2 if verbose else 1,
        stream=sys.stdout,
        buffer=False
    )
    
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    print("🎵 MixesDB Scraper Test Suite")
    print("=" * 60)
    print(f"🎯 Target: {args.target:,} tracklists per genre")
    print(f"⚡ Quick Mode: {'ON' if args.quick else 'OFF'}")
    print(f"🔍 Verbose: {'ON' if args.verbose else 'OFF'}")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Update target in test classes
    for test_class in TEST_SUITES.values():
        test_class.TARGET_TRACKLISTS = args.target
    
    # List test suites
    if args.list:
        list_test_suites()
        return
    
    # Determine which tests to run
    if args.genre:
        tests_to_run = [args.genre]
    elif args.style_code:
        tests_to_run = [STYLE_CODE_MAPPING[args.style_code]]
    else:
        tests_to_run = list(TEST_SUITES.keys())
    
    print(f"\n🚀 Running {len(tests_to_run)} test suite(s)")
    print("=" * 60)
    
    # Run tests
    start_time = datetime.now()
    all_results = []
    
    for test_name in tests_to_run:
        if test_name not in TEST_SUITES:
            print(f"❌ Unknown test suite: {test_name}")
            continue
        
        test_class = TEST_SUITES[test_name]
        success = run_test_suite(test_class, args.verbose, args.quick)
        all_results.append((test_name, success))
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n📊 Test Results Summary")
    print("=" * 60)
    print(f"⏱️  Total Duration: {duration}")
    print(f"🧪 Tests Run: {len(all_results)}")
    
    successful = sum(1 for _, success in all_results if success)
    failed = len(all_results) - successful
    
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print(f"\n🚨 Failed Tests:")
        for test_name, success in all_results:
            if not success:
                print(f"   - {test_name}")
    
    # Results by genre
    print(f"\n📈 Results by Genre:")
    for test_name, success in all_results:
        status = "✅ PASSED" if success else "❌ FAILED"
        test_class = TEST_SUITES[test_name]
        style_code = getattr(test_class, 'STYLE_CODE', 'N/A')
        genre_name = getattr(test_class, 'GENRE_NAME', 'Unknown')
        
        print(f"   {status} - {genre_name} ({style_code})")
    
    # Test data location
    print(f"\n💾 Test Data Location: Tests/test_data/")
    print(f"🗂️  Results are saved with timestamps for tracking")
    
    # Exit with appropriate code
    exit_code = 0 if failed == 0 else 1
    print(f"\n🏁 Exiting with code: {exit_code}")
    sys.exit(exit_code)


if __name__ == '__main__':
    main() 