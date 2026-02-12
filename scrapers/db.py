"""
Module centralisé pour la connexion MongoDB.
Utilisé par tous les scrapers et services.
"""

import os
from pymongo import MongoClient


def get_db():
    """
    Retourne la connexion à la database MongoDB.
    
    Variables d'environnement attendues :
    - MONGO_HOST : Host Mongo (par défaut "mongo" en Docker)
    - MONGO_PORT : Port Mongo (par défaut 27017)
    - MONGO_DB : Nom de la DB (par défaut "vidiq")
    - MONGO_USER : Utilisateur (par défaut "admin")
    - MONGO_PASSWORD : Mot de passe (par défaut "adminpass")
    
    Returns:
        Database MongoDB
        
    Raises:
        Exception: Si la connexion échoue
    """
    mongo_host = os.getenv("MONGO_HOST", "mongo")
    mongo_port = int(os.getenv("MONGO_PORT", "27017"))
    mongo_db = os.getenv("MONGO_DB", "vidiq")
    mongo_user = os.getenv("MONGO_USER", "admin")
    mongo_pwd = os.getenv("MONGO_PASSWORD", "adminpass")

    connection_string = (
        f"mongodb://{mongo_user}:{mongo_pwd}@"
        f"{mongo_host}:{mongo_port}/?authSource=admin"
    )
    
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")  # Vérifie la connexion immédiatement
    
    return client[mongo_db]
