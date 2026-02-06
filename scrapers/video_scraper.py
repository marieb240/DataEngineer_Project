"""
Module principal du scraper VidIQ.
Récupère les données, les parse et les stocke dans MongoDB.
"""

import os
from pymongo import MongoClient
from datetime import datetime
from scrapers.http_client import HttpClient
from scrapers.vidiq_parser import VidIQParser


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
        
        # Client HTTP
        self.http_client = HttpClient()
        
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
        1. Récupère la page
        2. Parse les données
        3. Stocke dans Mongo
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            print("\n" + "="*60)
            print("🚀 Démarrage du scraping VidIQ Top 100")
            print("="*60)
            
            # Step 1 : Récupère la page
            print(f"\n📥 Étape 1 : Récupération de {self.url}")
            response = self.http_client.get(self.url)
            
            # Step 2 : Parse le HTML
            print("\n📊 Étape 2 : Parsing du HTML")
            channels = VidIQParser.parse_top_100(response.text)
            
            if not channels:
                print("✗ Aucune donnée extraite")
                return False
            
            # Step 3 : Ajoute timestamp et stocke dans Mongo
            print("\n💾 Étape 3 : Stockage dans MongoDB")
            db = self.get_db()
            collection = db['channels']
            
            # Marque chaque document avec la date de scraping
            for channel in channels:
                channel['scraped_at'] = datetime.utcnow()
                channel['_id'] = f"{channel['rank']}_{datetime.utcnow().strftime('%Y%m%d')}"
            
            # Insère les données (remplace si déjà existantes)
            result = collection.insert_many(channels, ordered=False)
            
            print(f"[VideoScraper] ✓ {len(result.inserted_ids)} documents insérés")
            
            # Affiche un résumé
            print("\n📈 Résumé des top 5 :")
            for channel in channels[:5]:
                print(f"  #{channel['rank']} - {channel['name']}")
                print(f"     Abonnés: {channel['subscribers']:,}")
                print(f"     Vues: {channel['total_views']:,}")
            
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
