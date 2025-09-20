import re
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from tqdm import tqdm

from models.mix_data import Mix, Genre, Track
from scrapers.base_scraper import BaseScraper


class MixesDBScraper(BaseScraper):
    """MixesDB-specific scraper implementation using the Explorer interface"""
    
    def __init__(self, config_path: str = "config/genres_config.json"):
        super().__init__(config_path)
        self.base_url = self.config['base_url']
        self.explorer_url = f"{self.base_url}/w/MixesDB:Explorer/Mixes"
        
    def scrape_genre(self, genre: Genre, limit: int = None, time_filter: str = "Fresh", require_tracks: bool = True) -> List[Mix]:
        """
        Scrape mixes for a specific genre using the Explorer interface
        
        Args:
            genre: Genre object to scrape
            limit: Maximum number of mixes to scrape
            time_filter: Time filter ("Fresh", "2025", "2024", "2020s", etc.)
            require_tracks: If True, only include mixes with tracks (default: True)
            
        Returns:
            List of Mix objects
        """
        try:
            mixes = []
            offset = 0
            page_size = 25  # MixesDB Explorer uses 25 results per page
            
            # Initialize cumulative counters for progress tracking
            total_found_cumulative = 0
            total_valid_cumulative = 0
            total_discarded_cumulative = 0
            
            while len(mixes) < (limit or float('inf')):
                # Build Explorer URL with exact MixesDB parameter structure
                params = {
                    'offset': str(offset),
                    'tlC': '1',    # Complete tracklists
                    'tlI': '1'     # Incomplete tracklists
                }
                
                # Map genre to appropriate parameter (style code or category)
                genre_style_code = self._get_genre_style_code(genre.name)
                if genre_style_code:
                    params['style'] = genre_style_code
                else:
                    params['cat1'] = genre.name
                
                # Set time filter if specified
                if time_filter and time_filter != "Fresh":
                    params['year'] = time_filter
                
                # Note: Removed automatic minHotnessLevel filter to get all available results
                # Users can manually add filters if needed
                
                url = self._build_explorer_url(params)
                self.utils.logger.info(f"Scraping {genre.name} - Page {offset//page_size + 1}: {url}")
                
                # Get page content
                response = self.session.get(url)
                if response.status_code != 200:
                    self.utils.logger.error(f"Failed to fetch page: {response.status_code}")
                    break
                    
                soup = self.utils.parse_html(response.text)
                if not soup:
                    break

                # Parse mix entries from Explorer results
                page_mixes, stats = self._parse_explorer_results(soup, genre, require_tracks)
                
                # Update cumulative counters
                total_found_cumulative += stats['total_found']
                total_valid_cumulative += stats['valid_processed']
                total_discarded_cumulative += stats['discarded']
                
                # Print detailed progress for this cycle
                self.utils.logger.info(
                    f"🔄 Page {offset//page_size + 1} Results: "
                    f"Found {stats['total_found']}, "
                    f"Valid {stats['valid_processed']}, "
                    f"Discarded {stats['discarded']} | "
                    f"📊 Cumulative: "
                    f"Total {total_found_cumulative}, "
                    f"Valid {total_valid_cumulative}, "
                    f"Discarded {total_discarded_cumulative}"
                )
                
                if not page_mixes:
                    self.utils.logger.info("No more results found")
                    break
                
                mixes.extend(page_mixes)
                
                # Check if we've reached the limit
                if limit and len(mixes) >= limit:
                    mixes = mixes[:limit]
                    self.utils.logger.info(f"✅ Reached target limit of {limit} mixes")
                    break
                    
                # Check for pagination - look for "next" link
                if not self._has_next_page(soup):
                    self.utils.logger.info("No more pages available")
                    break
                    
                offset += page_size
                self.utils.rate_limit()
                
            self.utils.logger.info(f"Successfully scraped {len(mixes)} mixes for {genre.name}")
            return mixes
            
        except Exception as e:
            self.utils.logger.error(f"Error scraping genre {genre.name}: {str(e)}")
            return []

    def get_all_style_code_genres(self) -> List[str]:
        """Get all unique genres from STYLE_CODE_MAPPING with their expected result counts"""
        # Get the mapping dictionary
        mapping = {
            # Confirmed working style codes
            "Hip Hop": "HH",          # Hip Hop / R&B (2,934 results)
            "Hip Hop / R&B": "HH",    # Hip Hop / R&B (2,934 results)
            "Deep House": "DH",       # Deep House (16,089 results)
            "Techno": "TA",           # Techno / Acid (42,933 results)
            "Techno / Acid": "TA",    # Techno / Acid (42,933 results)
            "Progressive": "PT",      # Progressive / Trance (37,651 results)
            "Progressive / Trance": "PT",    # Progressive / Trance (37,651 results)
            "Trance": "PT",           # Progressive / Trance (37,651 results)
            "Progressive House": "PH", # Progressive House (35,541 results)
            "Minimal House": "MH",    # Minimal House (3,138 results)
            "Tech House": "TH",       # Tech House / Electro (44,431 results)
            "Tech House / Electro": "TH",    # Tech House / Electro (44,431 results)
            "Electro": "TH",          # Tech House / Electro (44,431 results)
            "Pure Minimal": "PM",     # Pure Minimal (617 results)
            "Minimal": "PM",          # Pure Minimal (617 results)
            "Drum & Bass": "DB",      # Drum & Bass / Jungle (2,890 results)
            "Drum & Bass / Jungle": "DB",    # Drum & Bass / Jungle (2,890 results)
            "Jungle": "DB",           # Drum & Bass / Jungle (2,890 results)
            "Chill Out": "CA",        # Chill Out / Ambient (5,971 results)
            "Chill Out / Ambient": "CA",     # Chill Out / Ambient (5,971 results)
            "Ambient": "CA",          # Chill Out / Ambient (5,971 results)
            "House": "H",             # House (shows specific House results)
        }
        
        # Get unique style codes and their representative names
        unique_codes = {}
        for genre_name, style_code in mapping.items():
            if style_code not in unique_codes:
                unique_codes[style_code] = genre_name
        
        # Return the representative genre names
        return list(unique_codes.values())
    
    def get_style_code_genre_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about each unique genre from STYLE_CODE_MAPPING"""
        genre_info = {
            "HH": {"name": "Hip Hop", "estimated_count": 2934, "aliases": ["Hip Hop", "Hip Hop / R&B"]},
            "DH": {"name": "Deep House", "estimated_count": 16089, "aliases": ["Deep House"]},
            "TA": {"name": "Techno", "estimated_count": 42933, "aliases": ["Techno", "Techno / Acid"]},
            "PT": {"name": "Progressive / Trance", "estimated_count": 37651, "aliases": ["Progressive", "Progressive / Trance", "Trance"]},
            "PH": {"name": "Progressive House", "estimated_count": 35541, "aliases": ["Progressive House"]},
            "MH": {"name": "Minimal House", "estimated_count": 3138, "aliases": ["Minimal House"]},
            "TH": {"name": "Tech House", "estimated_count": 44431, "aliases": ["Tech House", "Tech House / Electro", "Electro"]},
            "PM": {"name": "Pure Minimal", "estimated_count": 617, "aliases": ["Pure Minimal", "Minimal"]},
            "DB": {"name": "Drum & Bass", "estimated_count": 2890, "aliases": ["Drum & Bass", "Drum & Bass / Jungle", "Jungle"]},
            "CA": {"name": "Chill Out / Ambient", "estimated_count": 5971, "aliases": ["Chill Out", "Chill Out / Ambient", "Ambient"]},
            "H": {"name": "House", "estimated_count": 0, "aliases": ["House"]},  # Count varies
        }
        return genre_info

    def _get_genre_style_code(self, genre_name: str) -> Optional[str]:
        """
        Map genre names to MixesDB style codes
        
        Args:
            genre_name: Name of the genre
            
        Returns:
            Style code if available, None otherwise
        """
        # MixesDB style code mapping (discovered through systematic testing)
        STYLE_CODE_MAPPING = {
            # Confirmed working style codes
            "Hip Hop": "HH",          # Hip Hop / R&B (2,934 results)
            "Hip Hop / R&B": "HH",    # Hip Hop / R&B (2,934 results)
            "Deep House": "DH",       # Deep House (16,089 results)
            "Techno": "TA",           # Techno / Acid (42,933 results)
            "Techno / Acid": "TA",    # Techno / Acid (42,933 results)
            "Progressive": "PT",      # Progressive / Trance (37,651 results)
            "Progressive / Trance": "PT",    # Progressive / Trance (37,651 results)
            "Trance": "PT",           # Progressive / Trance (37,651 results)
            "Progressive House": "PH", # Progressive House (35,541 results)
            "Minimal House": "MH",    # Minimal House (3,138 results)
            "Tech House": "TH",       # Tech House / Electro (44,431 results)
            "Tech House / Electro": "TH",    # Tech House / Electro (44,431 results)
            "Electro": "TH",          # Tech House / Electro (44,431 results)
            "Pure Minimal": "PM",     # Pure Minimal (617 results)
            "Minimal": "PM",          # Pure Minimal (617 results)
            "Drum & Bass": "DB",      # Drum & Bass / Jungle (2,890 results)
            "Drum & Bass / Jungle": "DB",    # Drum & Bass / Jungle (2,890 results)
            "Jungle": "DB",           # Drum & Bass / Jungle (2,890 results)
            "Chill Out": "CA",        # Chill Out / Ambient (5,971 results)
            "Chill Out / Ambient": "CA",     # Chill Out / Ambient (5,971 results)
            "Ambient": "CA",          # Chill Out / Ambient (5,971 results)
            "House": "H",             # House (shows specific House results)
            
            # Note: The following codes were tested but show all styles (237,761+ results):
            # These indicate invalid style codes or generic searches
            # "Old School House": No valid style code found
            # "Minimal Tech House": No valid style code found  
            # "Hard Techno / Hardcore": No valid style code found
            # "Dubstep / Breakbeat": No valid style code found
            # "Disco / Pop": No valid style code found
            # "Various": No valid style code found
            # "No Progressive / Trance": No valid style code found
        }
        
        return STYLE_CODE_MAPPING.get(genre_name, None)
    
    def _build_explorer_url(self, params: Dict[str, str]) -> str:
        """Build Explorer URL with parameters using exact MixesDB structure"""
        # Define the exact parameter order and structure as used by MixesDB
        base_params = {
            'do': 'mx',
            'mode': '',
            'cat1': '',
            'cat2': '',
            'jnC': '',
            'style': '',
            'year': '',
            'tlC': '1',      # Complete tracklists
            'tlI': '1',      # Incomplete tracklists  
            'so': '',
            'tmatch1': '',
            'tmatch2': '',
            'jnTm': '',
            'usesFile': '',
            'minHotnessLevel': '',
            'count': '25',
            'order': 'hotness',
            'sort': 'desc',
            'offset': '0'
        }
        
        # Update with provided parameters
        base_params.update(params)
        
        # Build parameter string maintaining the exact order
        param_pairs = []
        param_order = [
            'do', 'mode', 'cat1', 'cat2', 'jnC', 'style', 'year', 'tlC', 'tlI', 'so',
            'tmatch1', 'tmatch2', 'jnTm', 'usesFile', 'minHotnessLevel',
            'count', 'order', 'sort', 'offset'
        ]
        
        for param in param_order:
            if param in base_params:
                param_pairs.append(f"{param}={base_params[param]}")
        
        # Build complete URL
        param_string = '&'.join(param_pairs)
        return f"https://www.mixesdb.com/w/MixesDB:Explorer/Mixes?{param_string}"
    
    def _parse_explorer_results(self, soup: BeautifulSoup, genre: Genre, require_tracks: bool = True) -> Tuple[List[Mix], Dict[str, int]]:
        """Parse mix entries from Explorer results page with detailed tracklists
        
        Returns:
            Tuple of (mixes_list, stats_dict) where stats contains:
            - total_found: Total mix links found on page
            - valid_processed: Number of mixes successfully processed with tracks
            - discarded: Number of mixes discarded (no tracks or errors)
        """
        mixes = []
        total_found = 0
        valid_processed = 0
        discarded = 0
        
        try:
            # Find all mix title links (they have the pattern /w/YYYY-MM-DD_-_...)
            mix_links = soup.find_all('a', href=re.compile(r'^/w/\d{4}-\d{2}-\d{2}_-_'))
            total_found = len(mix_links)
            
            for link in mix_links:
                try:
                    # Extract basic info from the link
                    href = link.get('href')
                    title = link.get_text(strip=True)
                    
                    if not href or not title:
                        discarded += 1
                        continue
                    
                    # Build full URL
                    mix_url = f"https://www.mixesdb.com{href}"
                    
                    # Parse additional details from the surrounding elements
                    mix_details = self._extract_mix_details_from_explorer_section(link, title, mix_url, genre, require_tracks)
                    if mix_details:
                        mixes.append(mix_details)
                        valid_processed += 1
                    else:
                        discarded += 1
                        
                except Exception as e:
                    self.utils.logger.warning(f"Failed to parse mix link {link}: {e}")
                    discarded += 1
                    
        except Exception as e:
            self.utils.logger.error(f"Failed to parse Explorer results: {e}")
            
        stats = {
            'total_found': total_found,
            'valid_processed': valid_processed,
            'discarded': discarded
        }
        
        return mixes, stats

    def _extract_mix_id_from_url(self, url: str) -> Optional[str]:
        """Extract unique mix ID from URL pattern /w/YYYY-MM-DD_-_mix_name.html"""
        try:
            # Extract the part after /w/ and before .html (if present)
            match = re.search(r'/w/([^/?]+)', url)
            if match:
                mix_id = match.group(1)
                # Remove .html extension if present
                if mix_id.endswith('.html'):
                    mix_id = mix_id[:-5]
                return mix_id
            return None
        except Exception as e:
            self.utils.logger.warning(f"Failed to extract mix ID from URL {url}: {e}")
            return None

    def _has_tracks(self, mix_content: Dict) -> bool:
        """Check if a mix has tracks (tracklist) to ensure it's a valid mix"""
        try:
            tracks = mix_content.get('tracks', [])
            return len(tracks) > 0
        except Exception:
            return False
    
    def _extract_mix_details_from_explorer_section(self, link_element, title: str, mix_url: str, genre: Genre, require_tracks: bool = True) -> Optional[Mix]:
        """Extract detailed mix information from the Explorer page section"""
        try:
            # Find the parent element that contains this mix's complete information
            # We need to search in the HTML for the tracklist and metadata that follows this link
            soup = link_element.find_parent()
            page_soup = soup
            while page_soup and page_soup.name != 'html':
                page_soup = page_soup.find_parent()
            
            if not page_soup:
                page_soup = soup
            
            # Convert the link href to use as identifier
            href = link_element.get('href', '')
            
            # Extract mix ID from URL
            mix_id = self._extract_mix_id_from_url(mix_url)
            
            # Find this mix's data by looking for elements after the link
            mix_content = self._find_mix_content_after_link(page_soup, href, title)
            
            # Check if mix has tracks - skip if no tracks found
            if require_tracks and not self._has_tracks(mix_content):
                self.utils.logger.info(f"Skipping mix '{title}' - no tracks found")
                return None
            
            # Extract metadata and tracklist from found content
            duration = mix_content.get('duration')
            file_size = mix_content.get('file_size')
            bitrate = mix_content.get('bitrate')
            platform_links = mix_content.get('platforms', [])
            tracklist = mix_content.get('tracks', [])
            
            # Extract date from URL or title
            date = self._extract_date_from_url_or_title(mix_url, title)
            
            # Extract DJ name from title
            dj_name = self._extract_dj_name_from_title(title)
            
            # Create mix object
            mix = Mix(
                id=mix_id,
                title=title,
                url=mix_url,
                dj_name=dj_name,
                date=date,
                duration=duration,
                genres=[genre.name] if genre else [],
                tracks=tracklist,
                metadata={
                    'platforms': platform_links,
                    'file_size': file_size,
                    'bitrate': bitrate,
                    'track_count': len(tracklist)
                }
            )
            
            return mix
            
        except Exception as e:
            self.utils.logger.warning(f"Failed to extract mix details for {title}: {e}")
            return None

    def _find_mix_content_after_link(self, soup: BeautifulSoup, href: str, title: str) -> Dict:
        """Find mix content (metadata table and tracklist) that appears after the mix link"""
        content = {
            'duration': None,
            'file_size': None,
            'bitrate': None,
            'platforms': [],
            'tracks': []
        }
        
        try:
            # Look for text patterns in the HTML that match our mix
            html_text = soup.get_text()
            
            # Find the position of our mix title in the text
            title_pos = html_text.find(title)
            if title_pos == -1:
                return content
            
            # Look for duration pattern (HH:MM:SS) after the title
            text_after_title = html_text[title_pos:title_pos + 2000]  # Look in next 2000 chars
            
            # Extract duration (format: H:MM:SS or HH:MM:SS)
            duration_match = re.search(r'(\d{1,2}:\d{2}:\d{2})', text_after_title)
            if duration_match:
                content['duration'] = duration_match.group(1)
            
            # Extract file size (format: XXX.XX)
            filesize_match = re.search(r'(\d+\.\d+)', text_after_title)
            if filesize_match:
                content['file_size'] = f"{filesize_match.group(1)} MB"
            
            # Extract bitrate (3-digit number)
            bitrate_match = re.search(r'\b(\d{3})\b', text_after_title)
            if bitrate_match:
                content['bitrate'] = f"{bitrate_match.group(1)} kbps"
            
            # Look for platform mentions
            platforms = []
            for platform in ['SoundCloud', 'Mixcloud', 'YouTube', 'Spotify', 'Apple Podcasts']:
                if platform in text_after_title:
                    platforms.append(platform)
            content['platforms'] = platforms
            
            # Extract tracklist - look for timestamp patterns
            tracklist = self._extract_tracklist_from_text(text_after_title)
            content['tracks'] = tracklist
            
        except Exception as e:
            self.utils.logger.warning(f"Failed to find mix content: {e}")
        
        return content

    def _extract_tracklist_from_text(self, text: str) -> List[Track]:
        """Extract tracklist from text using multiple patterns to handle different MixesDB formats"""
        tracks = []
        
        try:
            # Pattern 1: Tracks with full timestamps [HH:MM:SS] or [MM:SS]
            timestamp_pattern = r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*([^\[\n]+?)(?=\[|\n|$)'
            timestamp_matches = re.findall(timestamp_pattern, text, re.MULTILINE | re.DOTALL)
            
            # Pattern 2: Tracks with simple timestamps [000] or [0??]
            simple_timestamp_pattern = r'\[([0-9?]+)\]\s*([^\[\n]+?)(?=\[|\n|$)'
            simple_matches = re.findall(simple_timestamp_pattern, text, re.MULTILINE | re.DOTALL)
            
            # Pattern 3: Numbered tracks without timestamps (1. Artist - Title)
            numbered_pattern = r'\n\s*(\d+)\.?\s+([^\n]+?)(?=\n\d+\.|\n\s*$|\Z)'
            numbered_matches = re.findall(numbered_pattern, text, re.MULTILINE | re.DOTALL)
            
            # Pattern 4: Fallback - lines that look like "Artist - Title [Label]"
            artist_title_pattern = r'\n\s*([A-Za-z0-9][^\n]*?)\s+\-\s+([^\n]+?)(?=\n|$)'
            fallback_matches = re.findall(artist_title_pattern, text, re.MULTILINE)
            
            # Process Pattern 1: Full timestamps
            for i, (timestamp, track_info) in enumerate(timestamp_matches):
                track = self._parse_track_info(track_info.strip(), i + 1, timestamp)
                if track:
                    tracks.append(track)
            
            # Process Pattern 2: Simple timestamps (only if no full timestamps found)
            if not tracks:
                for i, (timestamp, track_info) in enumerate(simple_matches):
                    track = self._parse_track_info(track_info.strip(), i + 1, timestamp)
                    if track:
                        tracks.append(track)
            
            # Process Pattern 3: Numbered tracks (only if no timestamped tracks found)
            if not tracks:
                for i, (track_num, track_info) in enumerate(numbered_matches):
                    track = self._parse_track_info(track_info.strip(), i + 1, None)
                    if track:
                        tracks.append(track)
            
            # Process Pattern 4: Fallback artist-title pattern (only if nothing else worked)
            if not tracks:
                for i, (artist_part, title_part) in enumerate(fallback_matches[:20]):  # Limit to 20 to avoid false positives
                    # Combine and parse as single track info
                    track_info = f"{artist_part.strip()} - {title_part.strip()}"
                    track = self._parse_track_info(track_info, i + 1, None)
                    if track:
                        tracks.append(track)
                        
        except Exception as e:
            self.utils.logger.warning(f"Failed to extract tracklist from text: {e}")
        
        return tracks

    def _parse_track_info(self, track_info: str, track_number: int, timestamp: str = None) -> Optional[Track]:
        """Parse track information from text with enhanced quality validation"""
        try:
            if not track_info or not isinstance(track_info, str):
                return None
            
            track_info = track_info.strip()
            
            # Enhanced filtering for placeholder/junk tracks
            invalid_patterns = [
                '...',           # Ellipsis placeholder
                '???',           # Question mark placeholder  
                '?',             # Single question mark
                'unknown',       # Unknown placeholder
                'n/a',           # Not available
                'tba',           # To be announced
                'tbd',           # To be determined
                '---',           # Dash placeholder
                '***',           # Asterisk placeholder
                'id',            # Just "ID"
                'edit',          # Just "Edit"
                'remix',         # Just "Remix"
                'mix',           # Just "Mix"
                'track',         # Just "Track"
                'untitled',      # Untitled
                'noname',        # No name
                'blank'          # Blank
            ]
            
            # Check if track_info is just a placeholder
            if track_info.lower() in invalid_patterns:
                return None
            
            # Check for very short or clearly invalid entries
            if len(track_info) < 3:
                return None
                
            # Check for entries that are just numbers or single characters repeated
            if re.match(r'^[\d\s\.\-_]*$', track_info) or re.match(r'^(.)\1*$', track_info):
                return None
            
            # Parse Artist - Title format
            if ' - ' in track_info:
                parts = track_info.split(' - ', 1)
                artist = parts[0].strip()
                track_title = parts[1].strip()
                
                # Remove any label info in brackets from title (but don't store it)
                if '[' in track_title and ']' in track_title:
                    track_title = re.sub(r'\s*\[[^\]]+\]', '', track_title).strip()
                    
                # Enhanced validation for artist and title
                if not self._is_valid_track_component(artist) or not self._is_valid_track_component(track_title):
                    return None
                    
            else:
                # If no " - " separator, check if it's a reasonable standalone title
                if not self._is_valid_standalone_title(track_info):
                    return None
                    
                artist = "Unknown"
                track_title = track_info
            
            # Final quality check - ensure we have meaningful content
            if not artist or not track_title:
                return None
                
            # Create Track object
            track = Track(
                track_number=track_number,
                title=track_title,
                artist=artist,
                start_time=timestamp,
                original_text=f"[{timestamp}] {track_info}" if timestamp else track_info
            )
            
            return track
            
        except Exception as e:
            self.utils.logger.warning(f"Failed to parse track info '{track_info}': {e}")
            return None
    
    def _is_valid_track_component(self, component: str) -> bool:
        """Check if an artist name or track title is valid and meaningful"""
        if not component or not isinstance(component, str):
            return False
            
        component = component.strip().lower()
        
        # Too short
        if len(component) < 2:
            return False
            
        # Common placeholder values
        invalid_values = [
            '?', '??', '???', '...',
            'unknown', 'n/a', 'tba', 'tbd',
            '---', '***', 'blank', 'untitled',
            'noname', 'id', 'edit', 'remix', 'mix', 'track'
        ]
        
        if component in invalid_values:
            return False
            
        # Just numbers or special characters
        if re.match(r'^[\d\s\.\-_\(\)\[\]]*$', component):
            return False
            
        # Single character repeated
        if re.match(r'^(.)\1*$', component):
            return False
            
        return True
    
    def _is_valid_standalone_title(self, title: str) -> bool:
        """Check if a standalone title (no artist separator) is valid and meaningful"""
        if not title or not isinstance(title, str):
            return False
            
        title = title.strip()
        
        # Must be at least 5 characters for standalone titles
        if len(title) < 5:
            return False
            
        # Check if it's a valid track component
        if not self._is_valid_track_component(title):
            return False
            
        # Additional checks for standalone titles
        # Should contain some alphabetic characters
        if not re.search(r'[a-zA-Z]', title):
            return False
            
        # Should not be just a single word unless it's long enough
        words = title.split()
        if len(words) == 1 and len(title) < 8:
            return False
            
        return True

    def _extract_date_from_url_or_title(self, url: str, title: str) -> str:
        """Extract date from URL or title"""
        # Try to extract from URL pattern /w/YYYY-MM-DD_-_...
        url_date_match = re.search(r'/w/(\d{4}-\d{2}-\d{2})_', url)
        if url_date_match:
            return url_date_match.group(1)
        
        # Try to extract from title
        title_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', title)
        if title_date_match:
            return title_date_match.group(1)
            
        return ""

    def _extract_dj_name_from_title(self, title: str) -> str:
        """Extract DJ name from mix title - common patterns"""
        try:
            # Remove common patterns like dates, venues, etc.
            cleaned = title
            
            # Extract DJ name before " - " if present
            if " - " in cleaned:
                return cleaned.split(" - ")[0].strip()
            
            return cleaned.strip()
        except Exception:
            return "Unknown DJ"

    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """Check if there are more pages to scrape based on pagination controls"""
        try:
            # Look for pagination controls - MixesDB typically shows page numbers
            # and a "next" link when there are more results
            
            # Method 1: Look for pagination links like "next", "2", "3", etc.
            pagination_links = soup.find_all('a', href=re.compile(r'offset=\d+'))
            if pagination_links:
                # Check if any pagination link has an offset higher than current
                current_offset = 0
                for link in pagination_links:
                    href = link.get('href', '')
                    offset_match = re.search(r'offset=(\d+)', href)
                    if offset_match:
                        offset_value = int(offset_match.group(1))
                        if offset_value > current_offset:
                            return True
            
            # Method 2: Look for "Next" or "»" navigation buttons
            next_buttons = soup.find_all(['a', 'button'], string=re.compile(r'(?i)(next|»|more)'))
            if next_buttons:
                for button in next_buttons:
                    href = button.get('href', '')
                    if 'offset=' in href:
                        return True
            
            # Method 3: Check if we have exactly 25 results (page_size) which suggests more pages
            # This is a fallback method - if we got a full page, there might be more
            mix_links = soup.find_all('a', href=re.compile(r'^/w/\d{4}-\d{2}-\d{2}_-_'))
            if len(mix_links) >= 25:  # Full page suggests there might be more
                return True
                
            return False
            
        except Exception as e:
            self.utils.logger.warning(f"Error checking for next page: {e}")
            return False

    def scrape_mix_details(self, mix_url: str) -> Optional[Mix]:
        """
        Scrape detailed information for a specific mix
        
        Args:
            mix_url: Full URL to the mix page
            
        Returns:
            Mix object with detailed information
        """
        try:
            response = self.utils.make_request(mix_url)
            if not response:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title from page
            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            # Extract mix ID from URL
            mix_id = self._extract_mix_id_from_url(mix_url)
            
            # Create Mix object
            mix = Mix(
                id=mix_id,
                title=title,
                url=mix_url,
                dj_name=self._extract_artist(soup),
                date=self._extract_date(soup, mix_url),
                duration=self._extract_duration(soup),
                genres=self._extract_genres(soup),
                description=self._extract_description(soup),
                tracks=self._extract_tracklist(soup),
                metadata=self._extract_mix_metadata(soup)
            )
            
            return mix
            
        except Exception as e:
            self.utils.logger.error(f"Failed to scrape mix details for {mix_url}: {e}")
            return None
    
    def _extract_mix_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract mix title from the page"""
        try:
            # Try different selectors for the title
            title_selectors = [
                'h1',
                '.firstHeading',
                '#firstHeading',
                'title'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    # Clean up the title
                    title = re.sub(r'\s*-\s*MixesDB$', '', title)
                    if title:
                        return title
            
            return None
            
        except Exception as e:
            self.utils.logger.warning(f"Error extracting title: {str(e)}")
            return None
    
    def _extract_artist(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract artist/DJ name from the page"""
        try:
            # Look for artist information in various places
            artist_patterns = [
                r'(?i)dj[:\s]+([^,\n]+)',
                r'(?i)artist[:\s]+([^,\n]+)',
                r'(?i)by[:\s]+([^,\n]+)'
            ]
            
            page_text = soup.get_text()
            for pattern in artist_patterns:
                match = re.search(pattern, page_text)
                if match:
                    return match.group(1).strip()
            
            return None
            
        except Exception as e:
            self.utils.logger.warning(f"Error extracting artist: {str(e)}")
            return None
    
    def _extract_date(self, soup: BeautifulSoup, mix_url: str) -> Optional[str]:
        """Extract mix date from page or URL"""
        try:
            # First try to extract from URL (YYYY-MM-DD format)
            date_match = re.search(r'/w/(\d{4}-\d{2}-\d{2})_-_', mix_url)
            if date_match:
                return date_match.group(1)
            
            # Try to find date in page content
            page_text = soup.get_text()
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}\.\d{1,2}\.\d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, page_text)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            self.utils.logger.warning(f"Error extracting date: {str(e)}")
            return None
    
    def _extract_duration(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract mix duration from the page"""
        try:
            page_text = soup.get_text()
            
            # Look for duration patterns
            duration_patterns = [
                r'(\d+:\d{2}:\d{2})',  # H:MM:SS or HH:MM:SS
                r'(\d{1,2}:\d{2})',    # MM:SS
                r'(?i)duration[:\s]+(\d+:\d{2}(?::\d{2})?)',
                r'(?i)length[:\s]+(\d+:\d{2}(?::\d{2})?)'
            ]
            
            for pattern in duration_patterns:
                match = re.search(pattern, page_text)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            self.utils.logger.warning(f"Error extracting duration: {str(e)}")
            return None
    
    def _extract_genres(self, soup: BeautifulSoup) -> List[str]:
        """Extract genres from the page"""
        try:
            genres = []
            
            # Look for genre links or text
            genre_links = soup.find_all('a', href=re.compile(r'/genre/|/category/'))
            for link in genre_links:
                genre_text = link.get_text(strip=True)
                if genre_text and genre_text not in genres:
                    genres.append(genre_text)
            
            # If no genre links found, look for genre keywords in text
            if not genres:
                page_text = soup.get_text().lower()
                common_genres = [
                    'house', 'techno', 'trance', 'progressive', 'deep house',
                    'tech house', 'minimal', 'electro', 'drum and bass', 'dubstep',
                    'ambient', 'downtempo', 'breaks', 'garage', 'disco'
                ]
                
                for genre in common_genres:
                    if genre in page_text:
                        genres.append(genre.title())
            
            return genres[:5]  # Limit to 5 genres
            
        except Exception as e:
            self.utils.logger.warning(f"Error extracting genres: {str(e)}")
            return []
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract mix description from the page"""
        try:
            # Look for description in various elements
            desc_selectors = [
                '.description',
                '#description',
                '.summary',
                'meta[name="description"]'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    if desc_elem.name == 'meta':
                        return desc_elem.get('content', '').strip()
                    else:
                        desc_text = desc_elem.get_text(strip=True)
                        if len(desc_text) > 20:  # Only return if substantial
                            return desc_text
            
            return None
            
        except Exception as e:
            self.utils.logger.warning(f"Error extracting description: {str(e)}")
            return None
    
    def _extract_tracklist(self, soup: BeautifulSoup) -> List[Track]:
        """Extract tracklist from the page"""
        try:
            tracks = []
            
            # Look for tracklist table or list
            tracklist_elem = soup.find(['table', 'ol', 'ul'], class_=re.compile(r'tracklist|track'))
            
            if tracklist_elem:
                track_rows = tracklist_elem.find_all(['tr', 'li'])
                
                for row in track_rows:
                    track_text = row.get_text(strip=True)
                    if track_text and len(track_text) > 5:  # Filter out empty or very short entries
                        # Try to parse track info
                        track_match = re.match(r'(\d+)[\.\)]\s*(.+?)(?:\s*-\s*(.+))?$', track_text)
                        if track_match:
                            track_number = int(track_match.group(1))
                            artist = track_match.group(3) if track_match.group(3) else "Unknown"
                            title = track_match.group(2)
                            
                            track = Track(
                                track_number=track_number,
                                title=title,
                                artist=artist,
                                original_text=track_text
                            )
                            tracks.append(track)
            
            return tracks
            
        except Exception as e:
            self.utils.logger.warning(f"Error extracting tracklist: {str(e)}")
            return []
    
    def _extract_mix_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract additional metadata from the page"""
        try:
            metadata = {}
            page_text = soup.get_text()
            
            # Extract file size
            size_match = re.search(r'(\d+\.?\d*)\s*(MB|GB)', page_text)
            if size_match:
                metadata['file_size'] = f"{size_match.group(1)} {size_match.group(2)}"
            
            # Extract bitrate
            bitrate_match = re.search(r'(\d+)\s*kbps', page_text)
            if bitrate_match:
                metadata['bitrate'] = f"{bitrate_match.group(1)} kbps"
            
            # Find platform links
            platforms = []
            platform_links = soup.find_all('a', href=True)
            for link in platform_links:
                href = link.get('href', '').lower()
                if 'soundcloud.com' in href:
                    platforms.append('SoundCloud')
                elif 'mixcloud.com' in href:
                    platforms.append('Mixcloud')
                elif 'youtube.com' in href or 'youtu.be' in href:
                    platforms.append('YouTube')
                elif 'spotify.com' in href:
                    platforms.append('Spotify')
            
            if platforms:
                metadata['platforms'] = list(set(platforms))  # Remove duplicates
            
            # Extract view count or popularity metrics
            view_match = re.search(r'(\d+)\s*(?:views?|plays?)', page_text, re.IGNORECASE)
            if view_match:
                metadata['views'] = int(view_match.group(1))
            
            return metadata
            
        except Exception as e:
            self.utils.logger.warning(f"Error extracting metadata: {str(e)}")
            return {} 