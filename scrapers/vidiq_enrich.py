"""
Phase 2 - Enrichissement VidIQ avec Playwright.
Lit data/raw/channels_top100.csv, visite chaque channel_url,
extrait revenus mensuels estimés et durée moyenne des vidéos,
upsert Mongo et exporte data/enriched/channels_enriched.csv.
"""

import os
import csv
import time
import random
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from scrapers.db import get_db


RAW_CSV_PATH = os.path.join("data", "raw", "channels_top100.csv")
ENRICHED_DIR = os.path.join("data", "enriched")
ENRICHED_CSV_PATH = os.path.join(ENRICHED_DIR, "channels_enriched.csv")


def _to_int(value):
    """Convertit une valeur en int si possible, sinon retourne None."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None
        

def read_channels(limit: Optional[int] = None) -> List[Dict]:
    """Lit le CSV source et retourne la liste des chaînes."""
    if not os.path.exists(RAW_CSV_PATH):
        raise FileNotFoundError(f"CSV introuvable: {RAW_CSV_PATH}")

    channels = []
    with open(RAW_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in ("rank", "videos", "subscribers", "total_views"):
                if key in row:
                    row[key] = _to_int(row.get(key))
            channels.append(row)
            if limit and len(channels) >= limit:
                break
    return channels


def extract_labeled_value(lines: List[str], labels: List[str]) -> Optional[str]:
    """Extrait une valeur textuelle à partir d'un label dans le texte."""
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        for label in labels:
            if label.lower() in line.lower():
                value = line.replace(label, "").strip(" :–-\t")
                if value:
                    return value
                # Si la valeur est sur la ligne suivante
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if next_line:
                        return next_line
    return None


def parse_channel_page(page) -> Dict[str, Optional[str]]:
    """Parse la page d'une chaîne VidIQ et extrait les infos d'enrichissement."""
    labels_monthly = [
        "Estimated Monthly Earnings",
        "Monthly Earnings",
        "Revenus mensuels estimés",
        "Revenus mensuels",
        "Gains mensuels",
    ]
    labels_duration = [
        "Average Video Duration",
        "Avg. Video Duration",
        "Durée moyenne des vidéos",
        "Durée moyenne",
    ]

    try:
        body_text = page.locator("body").inner_text(timeout=15000)
    except PlaywrightTimeoutError:
        body_text = ""

    lines = [line.strip() for line in body_text.splitlines() if line.strip()]

    monthly_earnings = extract_labeled_value(lines, labels_monthly)
    avg_video_duration = extract_labeled_value(lines, labels_duration)

    return {
        "estimated_monthly_earnings": monthly_earnings,
        "avg_video_duration": avg_video_duration,
    }


def enrich_channels(channels: List[Dict]) -> List[Dict]:
    """Enrichit les chaînes via Playwright."""
    enriched = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for idx, ch in enumerate(channels, start=1):
            channel_url = ch.get("channel_url")
            if not channel_url:
                print(f"[Enrich] ⚠ URL manquante (ligne {idx})")
                continue

            print(f"[Enrich] ({idx}/{len(channels)}) {channel_url}")
            try:
                page.goto(channel_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)

                extracted = parse_channel_page(page)
                enriched_at = datetime.now(timezone.utc).isoformat()

                enriched_doc = {
                    **ch,
                    **extracted,
                    "enriched_at": enriched_at,
                }
                enriched.append(enriched_doc)
            except Exception as e:
                print(f"[Enrich] ⚠ Erreur sur {channel_url}: {e}")
                enriched_doc = {
                    **ch,
                    "estimated_monthly_earnings": None,
                    "avg_video_duration": None,
                    "enriched_at": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                }
                enriched.append(enriched_doc)
            finally:
                time.sleep(random.uniform(1, 3))

        browser.close()

    return enriched


def export_csv(rows: List[Dict]):
    """Export du CSV enrichi."""
    os.makedirs(ENRICHED_DIR, exist_ok=True)

    if not rows:
        return

    # Union de toutes les clés pour éviter les champs manquants
    fieldnames_set = set()
    for row in rows:
        fieldnames_set.update(row.keys())
    fieldnames = list(fieldnames_set)

    with open(ENRICHED_CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def upsert_mongo(rows: List[Dict]):
    """Upsert des données enrichies dans MongoDB (clé channel_url)."""
    db = get_db()
    collection = db["channels_enriched"]

    for row in rows:
        channel_url = row.get("channel_url")
        if not channel_url:
            continue
        row.pop("_id", None)
        collection.update_one(
            {"channel_url": channel_url},
            {"$set": row},
            upsert=True,
        )


def main():
    parser = argparse.ArgumentParser(description="Enrichissement VidIQ (Phase 2)")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de chaînes")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🚀 Démarrage enrichissement VidIQ")
    print("=" * 60)

    channels = read_channels(limit=args.limit)
    if not channels:
        print("✗ Aucun channel dans le CSV")
        return 1

    enriched = enrich_channels(channels)
    export_csv(enriched)
    upsert_mongo(enriched)

    print(f"\n CSV enrichi: {ENRICHED_CSV_PATH}")
    print(" MongoDB: collection channels_enriched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
