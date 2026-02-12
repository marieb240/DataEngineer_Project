"""
seed_db.py
Orchestrateur Docker :
1) Scraping Top100 (video_scraper)
2) Enrichissement VidIQ (vidiq_enrich)

Garantit :
- Mongo prêt avant de lancer
- Scraping 1 terminé avant Scraping 2
- CSV raw bien présent
"""

import os
import sys
import time

sys.path.insert(0, ".")

from scrapers.video_scraper import VideoScraper
import scrapers.vidiq_enrich as vidiq_enrich


def wait_for_mongo(retries=40, delay=2):
    """Attend que Mongo soit prêt avant de lancer le scraping."""
    scraper = VideoScraper()
    last_error = None

    for i in range(retries):
        try:
            db = scraper.get_db()
            db.command("ping")
            print("[INIT] ✓ MongoDB accessible")
            return
        except Exception as e:
            last_error = e
            print(f"[INIT] Mongo pas prêt ({i+1}/{retries}) : {e}")
            time.sleep(delay)

    raise RuntimeError(f"Mongo inaccessible après {retries} tentatives : {last_error}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 ORCHESTRATION SCRAPING 1 -> SCRAPING 2")
    print("=" * 70 + "\n")


    # 1️⃣ Attendre Mongo
    try:
        wait_for_mongo()
    except Exception as e:
        print(f"[FATAL] {e}")
        sys.exit(1)

    # 2️⃣ Phase 1 : Top 100
    print("\n" + "-" * 70)
    print("▶ Phase 1 : video_scraper.py")
    print("-" * 70)

    scraper = VideoScraper()
    ok1 = scraper.scrape_and_store()

    if not ok1:
        print("\n✗ Scraping Top100 échoué → arrêt")
        sys.exit(1)

    # Vérifie que le CSV raw existe (utilisé par l'enrichissement)
    raw_csv = os.path.join("data", "raw", "channels_top100.csv")
    if not os.path.exists(raw_csv):
        print(f"\n✗ CSV raw introuvable : {raw_csv}")
        sys.exit(1)

    print(f"\n[OK] CSV raw trouvé : {raw_csv}")

    # 3️⃣ Phase 2 : Enrichissement
    print("\n" + "-" * 70)
    print("▶ Phase 2 : vidiq_enrich.py")
    print("-" * 70)

    # On appelle le main() directement
    sys.argv = ["vidiq_enrich"]  # pas de --limit
    exit_code = vidiq_enrich.main()

    if exit_code != 0:
        print("\n✗ Enrichissement échoué")
        sys.exit(exit_code)

    print("\n✅ SCRAPING COMPLET TERMINÉ AVEC SUCCÈS")
    print("🎉 MongoDB prêt pour l'application web\n")

    sys.exit(0)
