"""
Script pour scraper et remplir MongoDB avec les vraies données.
Peut être lancé avant de tester l'app Flask.
"""

import sys
sys.path.insert(0, '.')

from scrapers.video_scraper import VideoScraper


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 SCRAPE ET REMPLISSAGE DE MONGODB")
    print("="*70 + "\n")
    
    # Lance le scraper
    scraper = VideoScraper()
    
    try:
        # Essaie de se connecter à Mongo
        db = scraper.get_db()
        db.command("ping")
        print("[INIT] ✓ MongoDB accessible")
    except Exception as e:
        print(f"[INIT] ⚠️ MongoDB non disponible: {e}")
        print("[INIT] Pour tester localement, lancez MongoDB d'abord:")
        print("[INIT]   docker run -d -p 27017:27017 mongo:7")
        sys.exit(1)
    
    # Lance le scraping
    success = scraper.scrape_and_store()
    
    if success:
        print("\n✅ Données scraped et stockées dans MongoDB !")
    else:
        print("\n✗ Erreur lors du scraping")
        sys.exit(1)
