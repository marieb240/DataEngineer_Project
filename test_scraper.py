"""
Script de test pour valider le parsing sans MongoDB.
Utile pour déboguer avant de lancer le scraper complet.
"""

from scrapers.http_client import HttpClient
from scrapers.vidiq_parser import VidIQParser
import json


def test_scraper():
    """Teste le scraping et parsing sans MongoDB."""
    
    print("\n" + "="*70)
    print("🧪 TEST DU SCRAPER VIDIQ - SANS MONGODB")
    print("="*70)
    
    try:
        # Step 1 : Récupère la page
        print("\n[TEST] Step 1 : Récupération de la page VidIQ...")
        http_client = HttpClient()
        url = "https://vidiq.com/fr/youtube-stats/top/100/"
        response = http_client.get(url, timeout=15.0, retries=2)
        
        print(f"[TEST] ✓ Status code: {response.status_code}")
        print(f"[TEST] ✓ Taille du contenu: {len(response.text)} bytes")
        
        # Step 2 : Parse le HTML
        print("\n[TEST] Step 2 : Parsing du HTML...")
        channels = VidIQParser.parse_top_100(response.text)
        
        if not channels:
            print("[TEST] ✗ Aucune donnée parsée!")
            return False
        
        print(f"[TEST] ✓ {len(channels)} chaînes extraites")
        
        # Step 3 : Affiche les résultats
        print("\n[TEST] Step 3 : Affichage des résultats")
        print("\n📊 Top 5 des chaînes :")
        print("-" * 70)
        
        for channel in channels[:5]:
            print(f"\n  #{channel['rank']} - {channel['name']}")
            print(f"     Vidéos: {channel['videos']:,}")
            print(f"     Abonnés: {channel['subscribers']:,}")
            print(f"     Vues totales: {channel['total_views']:,}")
        
        # Affiche aussi les 3 derniers pour vérifier
        print("\n📊 Les 3 derniers (rangs 98-100) :")
        print("-" * 70)
        
        for channel in channels[-3:]:
            print(f"\n  #{channel['rank']} - {channel['name']}")
            print(f"     Abonnés: {channel['subscribers']:,}")
        
        print("\n" + "="*70)
        print("✅ TEST RÉUSSI !")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n[TEST] ✗ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_scraper()
    exit(0 if success else 1)
