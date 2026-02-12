"""
Parser VidIQ utilisant directement Playwright pour extraire les données.
Les liens sont dans le DOM virtuel React.
"""

from typing import List, Dict
import re
from playwright.sync_api import sync_playwright


class VidIQPlaywrightParser:
    """
    Parseur VidIQ utilisant Playwright directement.
    
    Extrait :
    - rank
    - channel_name  
    - channel_url (lien VidIQ vers la page détail)
    - subscribers, videos, total_views
    """
    
    @staticmethod
    def scrape_top100(url: str = "https://vidiq.com/fr/youtube-stats/top/100/") -> List[Dict]:
        """
        Scrape le Top 100 VidIQ avec Playwright.
        
        Args:
            url: URL du classement VidIQ
            
        Returns:
            Liste de dictionnaires avec les données des chaînes
            
        Exemple:
        [
            {
                'rank': 1,
                'channel_name': 'MrBeast',
                'channel_url': 'https://vidiq.com/fr/youtube-stats/channel/UCX6OQ3DkcsbYNE6H8uQQuVA/',
                'subscribers': 466000000,
                'videos': 941,
                'total_views': 110420000000
            },
            ...
        ]
        """
        channels = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"[VidIQPlaywrightParser] 🌐 Navigation vers {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Attendre explicitement la table
            print("[VidIQPlaywrightParser] ⏳ Attente de la table...")
            page.wait_for_selector('table tbody tr', timeout=30000)
            
            # Petit délai pour laisser React charger complètement
            page.wait_for_timeout(5000)
            
            print("[VidIQPlaywrightParser] ⏳ Extraction des liens de chaînes...")

            # Extraire les données de la table pour connaître la cible
            rows = page.query_selector_all('table tbody tr')
            target_count = len(rows)
            print(f"[VidIQPlaywrightParser] 📋 {target_count} lignes trouvées")

            # Créer un mapping rank -> URL depuis les liens (les liens sont dans des DIV en dehors de la table)
            url_by_rank = {}

            def collect_links() -> int:
                channel_links = page.query_selector_all('a[href*="/youtube-stats/channel/"]')
                for link in channel_links:
                    href = link.get_attribute('href')
                    text = link.inner_text().strip()

                    # Le texte contient le rank au début (ex: "#1MrBeast941466M110.42B")
                    if text.startswith('#'):
                        rank_str = text[1:].split(' ')[0]
                        rank_match = re.match(r'(\d+)', rank_str)
                        if rank_match:
                            rank = int(rank_match.group(1))
                            if href:
                                if href.startswith('/'):
                                    full_url = f"https://vidiq.com{href}"
                                else:
                                    full_url = href
                                url_by_rank[rank] = full_url
                return len(url_by_rank)

            # Détecter le conteneur scrollable des cartes/liens
            scroll_handle = page.evaluate_handle(
                """
                () => {
                    const link = document.querySelector('a[href*="/youtube-stats/channel/"]');
                    if (!link) return null;
                    let el = link.parentElement;
                    while (el) {
                        const style = window.getComputedStyle(el);
                        if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
                            return el;
                        }
                        el = el.parentElement;
                    }
                    return document.scrollingElement || document.documentElement;
                }
                """
            )
            scroll_element = scroll_handle.as_element() if scroll_handle else None

            # Collecte initiale
            current_count = collect_links()
            print(f"[VidIQPlaywrightParser] ✓ {current_count} liens trouvés")

            # Scroll pour charger tous les liens si nécessaire
            scroll_attempts = 0
            max_scroll_attempts = 25
            last_count = current_count
            while current_count < target_count and scroll_attempts < max_scroll_attempts:
                scroll_attempts += 1
                if scroll_element:
                    page.evaluate("(el) => el.scrollTo(0, el.scrollHeight)", scroll_element)
                else:
                    page.evaluate("() => window.scrollBy(0, document.body.scrollHeight)")

                page.wait_for_timeout(1200)
                current_count = collect_links()
                print(f"[VidIQPlaywrightParser] ⏳ Liens: {current_count}/{target_count} (scroll {scroll_attempts})")

                if current_count == last_count:
                    page.wait_for_timeout(1200)
                last_count = current_count

            print(f"[VidIQPlaywrightParser] ✓ {len(url_by_rank)} URLs mappées par rank")
            
            # Extraire d'abord toutes les données textuelles des lignes
            row_data = []
            for idx, row in enumerate(rows):
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) < 5:
                        continue

                    rank_text = cells[0].inner_text().strip()
                    name = cells[1].inner_text().strip()
                    videos = cells[2].inner_text().strip()
                    subscribers = cells[3].inner_text().strip()
                    total_views = cells[4].inner_text().strip()

                    rank = int(rank_text.replace('#', ''))

                    row_data.append({
                        "row_index": idx,
                        "rank": rank,
                        "name": name,
                        "videos_raw": videos,
                        "subscribers_raw": subscribers,
                        "total_views_raw": total_views,
                    })
                except Exception as e:
                    print(f"[VidIQPlaywrightParser] ⚠ Erreur lecture ligne {idx+1}: {e}")

            # Résoudre les URLs manquantes en cliquant sur chaque ligne
            def resolve_url_by_click(row_index: int) -> str | None:
                try:
                    rows_now = page.query_selector_all('table tbody tr')
                    if row_index >= len(rows_now):
                        return None
                    row_now = rows_now[row_index]
                    with page.expect_navigation(timeout=30000):
                        row_now.click()
                    url = page.url
                    page.go_back(wait_until="domcontentloaded")
                    page.wait_for_selector('table tbody tr', timeout=30000)
                    page.wait_for_timeout(500)
                    return url
                except Exception as e:
                    print(f"[VidIQPlaywrightParser] ⚠ Erreur navigation ligne {row_index+1}: {e}")
                    return None

            # Construire les objets finaux
            for item in row_data:
                try:
                    rank = item["rank"]
                    name = item["name"]

                    channel_url = url_by_rank.get(rank)
                    if not channel_url:
                        channel_url = resolve_url_by_click(item["row_index"])

                    videos_count = VidIQPlaywrightParser._parse_number(item["videos_raw"])
                    subscribers_count = VidIQPlaywrightParser._parse_number(item["subscribers_raw"])
                    views_count = VidIQPlaywrightParser._parse_number(item["total_views_raw"])

                    channel = {
                        'rank': rank,
                        'name': name,
                        'channel_name': name,
                        'channel_url': channel_url,
                        'videos': videos_count,
                        'subscribers': subscribers_count,
                        'total_views': views_count,
                    }

                    channels.append(channel)
                except Exception as e:
                    print(f"[VidIQPlaywrightParser] ⚠ Erreur ligne rank {item.get('rank')}: {e}")
            
            browser.close()
            
        print(f"[VidIQPlaywrightParser] ✓ {len(channels)} chaînes extraites avec succès")
        return channels
    
    @staticmethod
    def _parse_number(text: str) -> int:
        """
        Convertit un nombre formaté (ex: '1.5M', '500K', '1.2B') en entier.
        
        Args:
            text: Nombre formaté avec K/M/B
            
        Returns:
            Nombre entier
        """
        text = text.strip().upper().replace(',', '')
        
        multipliers = {
            'K': 1_000,
            'M': 1_000_000,
            'B': 1_000_000_000
        }
        
        for suffix, multiplier in multipliers.items():
            if suffix in text:
                try:
                    num = float(text.replace(suffix, ''))
                    return int(num * multiplier)
                except ValueError:
                    return 0
        
        try:
            return int(float(text))
        except ValueError:
            return 0
