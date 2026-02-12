"""Package pour les scrapers du projet VidIQ."""

from scrapers.video_scraper import VideoScraper
from .db import get_db

__all__ = [ 'VideoScraper','get_db' ]
