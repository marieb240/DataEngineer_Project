"""
seed_db.py
Orchestrateur Docker :
1) Scraping Top100 (video_scraper)
2) Enrichissement VidIQ (vidiq_enrich)

Garantit :
- Mongo prêt avant de lancer
- Vidiq scraper terminé avant vidiq_enrich scraper
- CSV raw bien présent
"""

import os
import sys
import time

sys.path.insert(0, ".")

from scrapers.vidiq_scraper import VideoScraper
from scrapers.db import get_db
import scrapers.vidiq_enrich as vidiq_enrich


def wait_for_mongo(retries=40, delay=2):
    """Attend que Mongo soit prêt avant de lancer le scraping."""
    last_error = None

    for i in range(retries):
        try:
            db = get_db()
            db.command("ping")
            print("[INIT] MongoDB accessible")
            return
        except Exception as e:
            last_error = e
            print(f"[INIT] Mongo pas prêt ({i+1}/{retries}) : {e}")
            time.sleep(delay)

    raise RuntimeError(f"Mongo inaccessible après {retries} tentatives : {last_error}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" Orchestration Vidiq scraper -> vidiq_enrich scraper")
    print("=" * 70 + "\n")


    # Attendre Mongo
    try:
        wait_for_mongo()
    except Exception as e:
        print(f"[FATAL] {e}")
        sys.exit(1)

    # Phase 1 : Top 100
    print("\n" + "-" * 70)
    print(" Phase 1 : video_scraper.py")
    print("-" * 70)

    scraper = VideoScraper()
    ok1 = scraper.scrape_and_store()

    if not ok1:
        print("\n Scraping Top100 échoué → arrêt")
        sys.exit(1)

    # Vérifie que le CSV raw existe (utilisé par l'enrichissement)
    raw_csv = os.path.join("data", "raw", "channels_top100.csv")
    if not os.path.exists(raw_csv):
        print(f"\n✗ CSV raw introuvable : {raw_csv}")
        sys.exit(1)

    print(f"\n[OK] CSV raw trouvé : {raw_csv}")

    # Phase 2 : Enrichissement
    print("\n" + "-" * 70)
    print(" Phase 2 : vidiq_enrich.py")
    print("-" * 70)

    # On appelle le main() directement
    sys.argv = ["vidiq_enrich"]  # pas de --limit
    exit_code = vidiq_enrich.main()

    if exit_code != 0:
        print("\n Enrichissement échoué")
        sys.exit(exit_code)

    print("\n Scraping complété avec succès !")
    print(" MongoDB prêt pour l'application web\n")

    sys.exit(0)
