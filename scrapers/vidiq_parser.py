"""
Module pour parser la page VidIQ top 100 et extraire les données.
Utilise BeautifulSoup comme dans le cours Part4.
"""

from bs4 import BeautifulSoup
from typing import List, Dict
import re


class VidIQParser:
    """
    Parseur pour extraire les données du top 100 YouTubers depuis VidIQ.
    
    Utilise BeautifulSoup pour parser le HTML et récupérer :
    - Rang
    - Nom de la chaîne
    - Nombre de vidéos
    - Nombre d'abonnés
    - Nombre de vues totales
    """
    
    @staticmethod
    def parse_top_100(html_content: str) -> List[Dict]:
        """
        Parse le contenu HTML de la page VidIQ top 100 et extrait les données.
        
        Args:
            html_content (str): Contenu HTML de la page
            
        Returns:
            List[Dict]: Liste des chaînes YouTube avec leurs données
            
        Exemple de retour :
        [
            {
                'rank': 1,
                'name': 'MrBeast',
                'videos': 942,
                'subscribers': 465000000,
                'total_views': 110070000000,
                'url': 'https://www.youtube.com/@MrBeast'
            },
            ...
        ]
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        channels = []
        
        # Cherche la table HTML (balise <table>)
        table = soup.find('table')
        
        if not table:
            print("[VidIQParser] ✗ Aucune table trouvée dans le HTML")
            return channels
        
        # Récupère les lignes de la table (<tr>)
        rows = table.find_all('tr')[1:]  # Skip le header
        print(f"[VidIQParser] Trouvé {len(rows)} chaînes à parser")
        
        for idx, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                
                if len(cells) < 5:
                    continue
                
                # Extrait les colonnes
                rank_text = cells[0].get_text(strip=True)
                name = cells[1].get_text(strip=True)
                videos = cells[2].get_text(strip=True)
                subscribers = cells[3].get_text(strip=True)
                total_views = cells[4].get_text(strip=True)
                
                # Nettoie et convertit les nombres
                rank = int(rank_text.replace('#', ''))
                videos = VidIQParser._parse_number(videos)
                subscribers = VidIQParser._parse_number(subscribers)
                total_views = VidIQParser._parse_number(total_views)
                
                channel = {
                    'rank': rank,
                    'name': name,
                    'videos': videos,
                    'subscribers': subscribers,
                    'total_views': total_views,
                    'url': f'https://www.youtube.com/@{name.replace(" ", "")}'
                }
                
                channels.append(channel)
                
                if (idx + 1) % 10 == 0:
                    print(f"[VidIQParser] ✓ {idx + 1}/{len(rows)} chaînes parsées")
                    
            except Exception as e:
                print(f"[VidIQParser] ⚠ Erreur lors du parsing ligne {idx}: {e}")
                continue
        
        print(f"[VidIQParser] ✓ {len(channels)} chaînes extraites avec succès")
        return channels
    
    @staticmethod
    def _parse_number(text: str) -> int:
        """
        Convertit un nombre avec suffixes (M = millions, B = milliards) en int.
        
        Examples:
            "465M" -> 465000000
            "110.07B" -> 110070000000
            "1.54K" -> 1540
            
        Args:
            text (str): Texte contenant le nombre avec suffixe
            
        Returns:
            int: Nombre convertit en entier
        """
        text = text.strip()
        
        # Multiplieur selon le suffixe
        multipliers = {
            'K': 1000,
            'M': 1000000,
            'B': 1000000000,
        }
        
        # Cherche le dernier caractère (le suffixe)
        for suffix, multiplier in multipliers.items():
            if suffix in text:
                # Enlève le suffixe et convertit
                number_str = text.replace(suffix, '').strip()
                try:
                    number = float(number_str) * multiplier
                    return int(number)
                except ValueError:
                    print(f"[VidIQParser] ⚠ Impossible de parser '{text}'")
                    return 0
        
        # Si pas de suffixe, essaie de convertir directement
        try:
            return int(float(text))
        except ValueError:
            print(f"[VidIQParser] ⚠ Impossible de parser '{text}'")
            return 0
