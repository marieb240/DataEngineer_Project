"""
Module principal du scraper VidIQ.
Récupère les données, les parse et les stocke dans MongoDB.
"""

import os
import csv
from pymongo import MongoClient
from datetime import datetime
from scrapers.vidiq_playwright_parser import VidIQPlaywrightParser


class VideoScraper:
    """
    Scraper complet pour VidIQ :
    1. Récupère la page top 100 via HTTP
    2. Parse le HTML avec BeautifulSoup
    3. Stocke dans MongoDB
    """
    
    def __init__(self):
        """Initialise le scraper avec les config."""
        # Config MongoDB depuis variables d'environnement
        self.mongo_host = os.getenv("MONGO_HOST", "localhost")
        self.mongo_port = int(os.getenv("MONGO_PORT", "27017"))
        self.mongo_db = os.getenv("MONGO_DB", "vidiq")
        self.mongo_user = os.getenv("MONGO_USER", "admin")
        self.mongo_pwd = os.getenv("MONGO_PASSWORD", "adminpass")
        
        # URL à scraper
        self.url = "https://vidiq.com/fr/youtube-stats/top/100/"
        
    def get_db(self):
        """Connecte à MongoDB."""
        connection_string = (
            f"mongodb://{self.mongo_user}:{self.mongo_pwd}@"
            f"{self.mongo_host}:{self.mongo_port}/?authSource=admin"
        )
        client = MongoClient(connection_string)
        return client[self.mongo_db]
    
    def scrape_and_store(self):
        """
        Effectue le scraping complet :
        1. Scrape avec Playwright
        2. Stocke dans Mongo
        3. Exporte CSV
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            print("\n" + "="*60)
            print("🚀 Démarrage du scraping VidIQ Top 100")
            print("="*60)
            
            # Step 1 : Scrape avec Playwright
            print(f"\n📥 Étape 1 : Scraping avec Playwright")
            channels = VidIQPlaywrightParser.scrape_top100(self.url)
            
            if not channels:
                print("✗ Aucune donnée extraite")
                return False
            
            # Step 2 : Ajoute timestamp et stocke dans Mongo
            print("\n💾 Étape 2 : Stockage dans MongoDB")
            db = self.get_db()
            collection = db['channels_top100']

            scraped_at = datetime.utcnow()
            for channel in channels:
                channel['scraped_at'] = scraped_at

                # Upsert par rang
                channel.pop("_id", None)
                collection.update_one(
                    {"rank": channel.get("rank")},
                    {"$set": channel},
                    upsert=True
                )

            print(f"[VideoScraper] ✓ {len(channels)} documents insérés / mis à jour")

            # Step 3 : Export CSV (checkpoint)
            print("\n🧾 Étape 3 : Export CSV")
            raw_dir = os.path.join("data", "raw")
            os.makedirs(raw_dir, exist_ok=True)
            csv_path = os.path.join(raw_dir, "channels.csv")

            with open(csv_path, mode="w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=[
                        "rank",
                        "channel_name",
                        "channel_url",
                        "videos",
                        "subscribers",
                        "total_views",
                        "scraped_at",
                    ],
                )
                writer.writeheader()
                for channel in channels:
                    writer.writerow({
                        "rank": channel.get("rank"),
                        "channel_name": channel.get("channel_name") or channel.get("name"),
                        "channel_url": channel.get("channel_url"),
                        "videos": channel.get("videos"),
                        "subscribers": channel.get("subscribers"),
                        "total_views": channel.get("total_views"),
                        "scraped_at": scraped_at.isoformat(),
                    })

            print(f"[VideoScraper] ✓ CSV exporté: {csv_path}")
            
            # Affiche un résumé
            print("\n📈 Résumé des top 5 :")
            for channel in channels[:5]:
                print(f"  #{channel['rank']} - {channel['name']}")
                print(f"     Abonnés: {channel['subscribers']:,}")
                print(f"     Vues: {channel['total_views']:,}")
                print(f"     URL: {channel.get('channel_url', 'N/A')}")
            
            print("\n" + "="*60)
            print("✅ Scraping terminé avec succès !")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Erreur lors du scraping : {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Point d'entrée pour lancer le scraper."""
    scraper = VideoScraper()
    success = scraper.scrape_and_store()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
