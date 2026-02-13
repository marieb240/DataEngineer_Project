"""Package pour les scrapers du projet VidIQ."""

from scrapers.vidiq_scraper import VideoScraper
from .db import get_db

__all__ = [ 'VideoScraper','get_db' ]
