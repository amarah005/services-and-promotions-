"""
New Optimized Product Scraper Framework
AI-powered, scalable web scraping framework for product aggregator
"""

__version__ = "2.0.0"
__author__ = "Product Aggregator Team"

# Intelligent scraping system with meaningful naming
from .base_scraper import BaseScraper, PlatformScraperInterface
from .scraper_factory import ScraperFactory
# from .almumtaz_scraper import AlmumtazScraper  # Removed - using dynamically generated scrapers
from .dynamic_scraper import DynamicScraper
from .ai_category_classifier import AICategoryClassifier
from .data_processor import DataProcessor
from .website_structure_analyzer import WebsiteStructureAnalyzer
from .scraper_config_generator import ScraperConfigGenerator
from .intelligent_scraper_runner import IntelligentScraperRunner
from .validation import DataValidator, validate_scraped_data

__all__ = [
    'BaseScraper',
    'PlatformScraperInterface',
    'ScraperFactory',
    # 'AlmumtazScraper',  # Removed - using dynamically generated scrapers
    'DynamicScraper',
    'AICategoryClassifier',
    'DataProcessor',
    'WebsiteStructureAnalyzer',
    'ScraperConfigGenerator',
    'IntelligentScraperRunner',
    'DataValidator',
    'validate_scraped_data'
]
