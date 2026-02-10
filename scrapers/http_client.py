"""
Module pour faire des requêtes HTTP avec gestion des retries.
Basé sur le cours Part4_Simple_Web_Scraping.ipynb
"""

import requests


class HttpClient:
    """
    Client HTTP pour scraper les données.
    
    Caractéristiques :
    - User-Agent stable pour toutes les requêtes
    - Timeout configurable
    - Système de retry récursif en cas d'erreur
    """
    
    def __init__(self, user_agent: str = "VidIQScraper/1.0"):
        """
        Initialise le client HTTP.
        
        Args:
            user_agent (str): Identifiant du scraper envoyé au serveur
        """
        self.user_agent = user_agent
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def get(self, url: str, timeout: float = 10.0, retries: int = 3) -> requests.Response:
        """
        Effectue une requête HTTP GET avec retry automatique.
        
        Args:
            url (str): URL à récupérer
            timeout (float): Temps maximum d'attente en secondes
            retries (int): Nombre de tentatives restantes
            
        Returns:
            requests.Response: Réponse du serveur si succès, None sinon
            
        Raises:
            Exception: Si les retries sont épuisés
        """
        try:
            print(f"[HttpClient] GET {url} (timeout={timeout}s)")
            
            # Effectue la requête
            response = requests.get(
                url,
                headers=self.headers,
                timeout=timeout
            )
            
            # Vérifie que le code HTTP indique un succès (2xx)
            response.raise_for_status()
            
            print(f"[HttpClient] ✓ Réponse OK ({response.status_code})")
            return response
            
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            print(f"[HttpClient] ✗ Erreur : {e}")
            
            if retries > 0:
                print(f"[HttpClient] Nouvelle tentative... ({retries} retry(s) restant(s))")
                # Appel récursif avec un retry en moins
                return self.get(url, timeout=timeout, retries=retries - 1)
            else:
                print(f"[HttpClient] ✗ Abandon après {3 - retries} tentatives")
                raise Exception(f"Impossible de récupérer {url} après plusieurs tentatives")
