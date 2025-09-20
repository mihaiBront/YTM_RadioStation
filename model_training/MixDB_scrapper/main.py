#!/usr/bin/env python3
"""
MixesDB Scraper - Main Entry Point

A comprehensive scraper for mixesdb.com that extracts DJ mixes and their metadata
organized by music genres using the Explorer interface for fresh, relevant content.

Usage:
    python main.py --help
    python main.py --list-genres
    python main.py --genre "Techno" --limit 50 --time-filter "Fresh"
    python main.py --sample "Deep House" --size 10
    python main.py --fresh --limit 100
    python main.py --all --limit-per-genre 25 --time-filter "2025"
    python main.py --genres "all" --target 5000 --time-filter "Fresh"
    python main.py --genres "Hip Hop,Techno,House" --target 2000
"""

import argparse
import sys
from typing import List, Optional
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scrapers.mixesdb_scraper import MixesDBScraper
from models.mix_data import Mix


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="MixesDB Scraper - Extract DJ mix data from mixesdb.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-genres                    # List all available genres
  %(prog)s --fresh --limit 50               # Get 50 fresh mixes from all genres
  %(prog)s --genre "Techno" --limit 25      # Get 25 fresh Techno mixes
  %(prog)s --genre "House" --time-filter "2025" --limit 100  # Get House mixes from 2025
  %(prog)s --sample "Progressive House"     # Get 10 sample Progressive House mixes
  %(prog)s --all --limit-per-genre 20       # Get 20 fresh mixes from each genre
  %(prog)s --genres "all" --target 5000     # Get up to 5000 mixes from each confirmed genre
  %(prog)s --genres "Hip Hop,Techno" --target 2000  # Get up to 2000 mixes from specific genres

Time filters: Fresh, 2025, 2024, 2023, 2020s, 2010s, 2000s, 1990s, etc.
        """
    )
    
    # Main action arguments (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    
    action_group.add_argument(
        '--list-genres', '-l',
        action='store_true',
        help='List all available genres and their categories'
    )
    
    action_group.add_argument(
        '--fresh', '-f',
        action='store_true',
        help='Scrape fresh/recent mixes across all genres'
    )
    
    action_group.add_argument(
        '--genre', '-g',
        type=str,
        help='Scrape mixes from a specific genre'
    )
    
    action_group.add_argument(
        '--sample', '-s',
        type=str,
        help='Scrape a small sample from a specific genre (for testing)'
    )
    
    action_group.add_argument(
        '--all', '-a',
        action='store_true',
        help='Scrape mixes from all genres'
    )
    
    action_group.add_argument(
        '--genres',
        type=str,
        help='Scrape mixes from specific genres. Use "all" to scrape all confirmed genres from STYLE_CODE_MAPPING, or comma-separated genre names'
    )
    
    # Configuration arguments
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Maximum number of mixes to scrape (default: 50)'
    )
    
    parser.add_argument(
        '--target',
        type=int,
        default=5000,
        help='Target number of mixes per genre when using --genres "all" (default: 5000)'
    )
    
    parser.add_argument(
        '--limit-per-genre',
        type=int,
        default=25,
        help='Maximum number of mixes per genre when using --all (default: 25)'
    )
    
    parser.add_argument(
        '--size',
        type=int,
        default=10,
        help='Sample size when using --sample (default: 10)'
    )
    
    parser.add_argument(
        '--time-filter', '-t',
        type=str,
        default='Fresh',
        choices=['Fresh', '2025', '2024', '2023', '2022', '2021', '2020', 
                '2020s', '2019', '2018', '2017', '2016', '2015', '2014', '2013', 
                '2012', '2011', '2010', '2010s', '2009', '2008', '2007', '2006', 
                '2005', '2004', '2003', '2002', '2001', '2000', '2000s', '1990s'],
        help='Time filter for scraping (default: Fresh)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (optional, defaults to output/data/mixes_TIMESTAMP.json)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/genres_config.json',
        help='Path to genre configuration file (default: config/genres_config.json)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--require-tracks',
        action='store_true',
        default=True,
        help='Only include mixes with tracklists (default: True). Use --no-require-tracks for higher quantity.'
    )
    
    parser.add_argument(
        '--no-require-tracks',
        dest='require_tracks',
        action='store_false',
        help='Include mixes without tracklists for higher quantity (lower quality)'
    )
    
    return parser


def list_genres(scraper: MixesDBScraper) -> None:
    """List all available genres grouped by category"""
    print("\n🎵 Available Genres by Category:\n")
    
    config = scraper.config
    genre_groups = config.get('genre_groups', {})
    
    total_genres = 0
    total_mixes = 0
    
    for group_name, group_data in genre_groups.items():
        print(f"📁 {group_data.get('description', group_name.title())}")
        print("=" * 50)
        
        genres = group_data.get('genres', [])
        for genre in genres:
            name = genre.get('name', 'Unknown')
            count = genre.get('count', 0)
            print(f"  • {name:<25} ({count:,} mixes)")
            total_genres += 1
            total_mixes += count
        
        print()
    
    print(f"📊 Total: {total_genres} genres with {total_mixes:,} mixes")
    print(f"🌐 Base URL: {config.get('base_url', 'Unknown')}")
    
    # Also show confirmed genres from STYLE_CODE_MAPPING
    print("\n🎯 Confirmed Genres from STYLE_CODE_MAPPING (--genres \"all\"):")
    print("=" * 65)
    
    genre_info = scraper.get_style_code_genre_info()
    style_total = 0
    
    for style_code, info in genre_info.items():
        name = info["name"]
        count = info["estimated_count"]
        style_total += count
        print(f"  • {name:<25} ({count:,} mixes) - Style Code: {style_code}")
    
    print(f"\n📊 Style Code Total: {len(genre_info)} genres with ~{style_total:,} mixes")
    print(f"💡 Use --genres \"all\" --target 5000 to scrape all confirmed genres")


def scrape_fresh_mixes(scraper: MixesDBScraper, limit: int, output_file: Optional[str]) -> None:
    """Scrape fresh mixes across all genres"""
    print(f"\n🎵 Scraping {limit} fresh mixes from all genres...")
    
    mixes = scraper.scrape_fresh_mixes(limit=limit)
    
    if mixes:
        print(f"✅ Successfully scraped {len(mixes)} fresh mixes")
        save_results(mixes, output_file, "fresh_mixes")
    else:
        print("❌ No mixes found")


def scrape_genre_mixes(scraper: MixesDBScraper, genre_name: str, limit: int, 
                      time_filter: str, output_file: Optional[str]) -> None:
    """Scrape mixes from a specific genre"""
    print(f"\n🎵 Scraping {limit} {time_filter} mixes from {genre_name}...")
    
    genre = scraper.get_genre_by_name(genre_name)
    if not genre:
        print(f"❌ Genre '{genre_name}' not found. Use --list-genres to see available genres.")
        sys.exit(1)
    
    mixes = scraper.scrape_genre(genre, limit=limit, time_filter=time_filter)
    
    if mixes:
        print(f"✅ Successfully scraped {len(mixes)} mixes from {genre_name}")
        save_results(mixes, output_file, f"{genre_name}_{time_filter}")
    else:
        print(f"❌ No mixes found for {genre_name}")


def scrape_sample(scraper: MixesDBScraper, genre_name: str, size: int, 
                 output_file: Optional[str]) -> None:
    """Scrape a sample of mixes from a genre"""
    print(f"\n🎵 Scraping {size} sample mixes from {genre_name}...")
    
    genre = scraper.get_genre_by_name(genre_name)
    if not genre:
        print(f"❌ Genre '{genre_name}' not found. Use --list-genres to see available genres.")
        sys.exit(1)
    
    mixes = scraper.scrape_genre(genre, limit=size, time_filter="Fresh")
    
    if mixes:
        print(f"✅ Successfully scraped {len(mixes)} sample mixes from {genre_name}")
        save_results(mixes, output_file, f"{genre_name}_sample")
    else:
        print(f"❌ No sample mixes found for {genre_name}")


def scrape_genres(scraper: MixesDBScraper, genres_input: str, target: int, 
                 time_filter: str, output_file: Optional[str], require_tracks: bool = True) -> None:
    """Scrape mixes from specified genres (all or comma-separated list)"""
    
    if genres_input.lower() == "all":
        # Use confirmed genres from STYLE_CODE_MAPPING
        print(f"\n🎵 Scraping up to {target} {time_filter} mixes from each confirmed genre...")
        
        genre_info = scraper.get_style_code_genre_info()
        all_mixes = []
        successful_genres = 0
        total_expected = 0
        
        print(f"\n📊 Available genres from STYLE_CODE_MAPPING:")
        for style_code, info in genre_info.items():
            expected_count = info["estimated_count"]
            actual_target = min(target, expected_count) if expected_count > 0 else target
            total_expected += actual_target
            print(f"  • {info['name']:<25} (up to {actual_target:,} mixes)")
        
        print(f"\n🎯 Total expected: up to {total_expected:,} mixes from {len(genre_info)} genres")
        print("=" * 70)
        
        for style_code, info in genre_info.items():
            genre_name = info["name"]
            expected_count = info["estimated_count"]
            actual_target = min(target, expected_count) if expected_count > 0 else target
            
            print(f"\n🎵 Scraping {genre_name} (up to {actual_target:,} mixes)...")
            
            # Create a simple genre object for the scraper
            from models.mix_data import Genre
            genre = Genre(name=genre_name, slug=genre_name.lower().replace(" ", "-"), 
                         description=f"Style Code: {style_code}", mix_count=expected_count, category="Style Code")
            
            try:
                mixes = scraper.scrape_genre(genre, limit=actual_target, time_filter=time_filter, require_tracks=require_tracks)
                if mixes:
                    all_mixes.extend(mixes)
                    successful_genres += 1
                    print(f"  ✅ Found {len(mixes)} mixes")
                else:
                    print(f"  ⚠️  No mixes found")
            except Exception as e:
                print(f"  ❌ Error scraping {genre_name}: {str(e)}")
        
        if all_mixes:
            print(f"\n✅ Successfully scraped {len(all_mixes)} mixes from {successful_genres}/{len(genre_info)} genres")
            save_results(all_mixes, output_file, f"all_confirmed_genres_{time_filter}")
        else:
            print("\n❌ No mixes found from any genre")
    
    else:
        # Handle comma-separated genre names
        genre_names = [name.strip() for name in genres_input.split(",")]
        print(f"\n🎵 Scraping up to {target} {time_filter} mixes from each specified genre...")
        
        all_mixes = []
        successful_genres = 0
        
        for genre_name in genre_names:
            print(f"\n🎵 Scraping {genre_name} (up to {target} mixes)...")
            
            # Try to get genre from config first
            genre = scraper.get_genre_by_name(genre_name)
            if not genre:
                # Create a simple genre object for confirmed style codes
                from models.mix_data import Genre
                genre = Genre(name=genre_name, slug=genre_name.lower().replace(" ", "-"), 
                             description="User specified genre", mix_count=0, category="Style Code")
            
            try:
                mixes = scraper.scrape_genre(genre, limit=target, time_filter=time_filter, require_tracks=require_tracks)
                if mixes:
                    all_mixes.extend(mixes)
                    successful_genres += 1
                    print(f"  ✅ Found {len(mixes)} mixes")
                else:
                    print(f"  ⚠️  No mixes found")
            except Exception as e:
                print(f"  ❌ Error scraping {genre_name}: {str(e)}")
        
        if all_mixes:
            print(f"\n✅ Successfully scraped {len(all_mixes)} mixes from {successful_genres}/{len(genre_names)} genres")
            save_results(all_mixes, output_file, f"selected_genres_{time_filter}")
        else:
            print("\n❌ No mixes found from any genre")


def scrape_all_genres(scraper: MixesDBScraper, limit_per_genre: int, 
                     time_filter: str, output_file: Optional[str]) -> None:
    """Scrape mixes from all genres"""
    print(f"\n🎵 Scraping {limit_per_genre} {time_filter} mixes from each genre...")
    
    config = scraper.config
    genre_groups = config.get('genre_groups', {})
    all_mixes = []
    successful_genres = 0
    
    for group_name, group_data in genre_groups.items():
        print(f"\n📁 Processing {group_data.get('description', group_name)}...")
        
        genres = group_data.get('genres', [])
        for genre_data in genres:
            genre_name = genre_data.get('name', '')
            if not genre_name:
                continue
                
            print(f"  🎵 Scraping {genre_name}...")
            
            genre = scraper.get_genre_by_name(genre_name)
            if genre:
                mixes = scraper.scrape_genre(genre, limit=limit_per_genre, time_filter=time_filter)
                if mixes:
                    all_mixes.extend(mixes)
                    successful_genres += 1
                    print(f"    ✅ Found {len(mixes)} mixes")
                else:
                    print(f"    ⚠️  No mixes found")
            else:
                print(f"    ❌ Genre not found")
    
    if all_mixes:
        print(f"\n✅ Successfully scraped {len(all_mixes)} mixes from {successful_genres} genres")
        save_results(all_mixes, output_file, f"all_genres_{time_filter}")
    else:
        print("\n❌ No mixes found from any genre")


def save_results(mixes: List[Mix], output_file: Optional[str], prefix: str) -> None:
    """Save scraping results to JSON file"""
    import json
    from datetime import datetime
    
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"output/data/{prefix}_{timestamp}.json"
    
    # Create output directory if it doesn't exist
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Convert mixes to dictionaries
    data = {
        'timestamp': datetime.now().isoformat(),
        'total_mixes': len(mixes),
        'prefix': prefix,
        'mixes': [mix.to_dict() for mix in mixes]
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {output_file}")
        print(f"📊 Total mixes: {len(mixes)}")
        
        # Show some stats
        if mixes:
            genres = set()
            years = set()
            for mix in mixes:
                if hasattr(mix, 'genres') and mix.genres:
                    genres.update(mix.genres)
                if hasattr(mix, 'date') and mix.date:
                    year = mix.date[:4] if len(mix.date) >= 4 else None
                    if year and year.isdigit():
                        years.add(year)
            
            if genres:
                print(f"🎭 Genres: {', '.join(sorted(genres))}")
            if years:
                print(f"📅 Years: {', '.join(sorted(years, reverse=True))}")
        
    except Exception as e:
        print(f"❌ Error saving results: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    import logging
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    print("🎵 MixesDB Scraper")
    print("=" * 50)
    
    try:
        # Initialize scraper
        scraper = MixesDBScraper(config_path=args.config)
        
        # Execute requested action
        if args.list_genres:
            list_genres(scraper)
            
        elif args.fresh:
            scrape_fresh_mixes(scraper, args.limit, args.output)
            
        elif args.genre:
            scrape_genre_mixes(scraper, args.genre, args.limit, args.time_filter, args.output)
            
        elif args.sample:
            scrape_sample(scraper, args.sample, args.size, args.output)
            
        elif args.all:
            scrape_all_genres(scraper, args.limit_per_genre, args.time_filter, args.output)
            
        elif args.genres:
            scrape_genres(scraper, args.genres, args.target, args.time_filter, args.output, args.require_tracks)
            
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 