"""Package pour les scrapers du projet VidIQ."""

from scrapers.http_client import HttpClient
from scrapers.video_scraper import VideoScraper

__all__ = ['HttpClient', 'VideoScraper']
