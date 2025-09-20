"""
Scrapers package for MixesDB scraper

This package contains the base scraper class and specific
implementations for different music databases and websites.
"""

from .base_scraper import BaseScraper
from .mixesdb_scraper import MixesDBScraper

__all__ = ['BaseScraper', 'MixesDBScraper'] 