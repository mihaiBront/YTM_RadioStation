import re
import time
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

# Optional imports - gracefully handle missing dependencies
try:
    from fake_useragent import UserAgent
    HAS_FAKE_USERAGENT = True
except ImportError:
    HAS_FAKE_USERAGENT = False

try:
    import lxml
    HAS_LXML = True
except ImportError:
    HAS_LXML = False


class ScraperUtils:
    """Utility class for common scraping operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        if HAS_FAKE_USERAGENT:
            self.ua = UserAgent()
        else:
            self.ua = None
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('mixesdb_scraper')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_session(self) -> requests.Session:
        """Create a configured requests session"""
        session = requests.Session()
        
        # Use fake user agent if available, otherwise use configured or default
        if self.ua:
            default_ua = self.ua.random
        else:
            default_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        session.headers.update({
            'User-Agent': self.config.get('user_agent', default_ua),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return session
    
    def make_request(self, session: requests.Session, url: str, 
                    max_retries: int = None) -> Optional[requests.Response]:
        """Make a HTTP request with retry logic"""
        max_retries = max_retries or self.config.get('max_retries', 3)
        timeout = self.config.get('timeout', 30)
        delay = self.config.get('delay_between_requests', 1.0)
        
        for attempt in range(max_retries):
            try:
                time.sleep(delay)
                response = session.get(url, timeout=timeout)
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt == max_retries - 1:
                    self.logger.error(f"All {max_retries} attempts failed for {url}")
                    return None
                time.sleep(delay * (attempt + 1))  # Exponential backoff
        
        return None
    
    def parse_html(self, html_content: str) -> Optional[BeautifulSoup]:
        """Parse HTML content with BeautifulSoup"""
        try:
            # Use lxml if available for faster parsing, otherwise use html.parser
            parser = 'lxml' if HAS_LXML else 'html.parser'
            return BeautifulSoup(html_content, parser)
        except Exception as e:
            self.logger.error(f"Failed to parse HTML: {str(e)}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters that might cause issues
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text
    
    def extract_duration(self, duration_text: str) -> Optional[str]:
        """Extract and normalize duration format"""
        if not duration_text:
            return None
            
        # Match various duration formats: HH:MM:SS, MM:SS, H:MM:SS
        duration_pattern = r'(\d{1,2}):(\d{2})(?::(\d{2}))?'
        match = re.search(duration_pattern, duration_text)
        
        if match:
            hours = int(match.group(1)) if len(match.group(1)) > 2 or ':' in duration_text[duration_text.index(match.group(1))+2:] else 0
            minutes = int(match.group(1)) if hours == 0 else int(match.group(2))
            seconds = int(match.group(2)) if hours == 0 else int(match.group(3)) if match.group(3) else 0
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        
        return None
    
    def parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse various date formats"""
        if not date_text:
            return None
            
        date_text = self.clean_text(date_text)
        
        # Common date patterns
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY or MM-DD-YYYY
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})', # DD.MM.YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    # Assume first format is MM/DD/YYYY for US format
                    if '/' in date_text:
                        month, day, year = match.groups()
                    else:
                        day, month, year = match.groups()
                    
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue
        
        return None
    
    def extract_numbers(self, text: str) -> List[int]:
        """Extract all numbers from text"""
        if not text:
            return []
        
        numbers = re.findall(r'\d+', text)
        return [int(num) for num in numbers]
    
    def build_url(self, base_url: str, path: str) -> str:
        """Build a complete URL from base and path"""
        return urljoin(base_url, path)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def save_json(self, data: Any, filepath: str) -> bool:
        """Save data to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save JSON to {filepath}: {str(e)}")
            return False
    
    def load_json(self, filepath: str) -> Optional[Any]:
        """Load data from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load JSON from {filepath}: {str(e)}")
            return None
    
    def extract_links(self, soup: BeautifulSoup, 
                     base_url: str, 
                     link_pattern: str = None) -> List[str]:
        """Extract links from soup with optional pattern matching"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href:
                full_url = self.build_url(base_url, href)
                
                if link_pattern:
                    if re.search(link_pattern, href):
                        links.append(full_url)
                else:
                    links.append(full_url)
        
        return list(set(links))  # Remove duplicates
    
    def rate_limit(self):
        """Apply rate limiting between requests"""
        delay = self.config.get('delay_between_requests', 1.0)
        time.sleep(delay) 