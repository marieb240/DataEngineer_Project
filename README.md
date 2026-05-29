# YouTube Statistics - Projet Data Engineering
ESIEE 2026 - Marie Bouëtel & Ghita Bensaleh

## 1. Introduction

Dans le cadre de l'unité de Data Engineering, nous avons développé une application web permettant de collecter, stocker et visualiser des statistiques YouTube à partir de données scrapées.

L'objectif du projet est de mettre en pratique :
- le web scraping sur du contenu dynamique
- le stockage en base de données NoSQL
- le développement d'une application web en Python
- la conteneurisation avec Docker
- la rédaction d'une documentation technique et fonctionnelle

Notre application permet de consulter différentes statistiques du Top 100 des YouTubeurs mondiaux, notamment le rang, le nombre de vidéos, d'abonnés et de vues totales.  
Les données sont récupérées depuis VidIQ, stockées dans MongoDB, puis affichées via une application Flask.

## 2. Description du projet

Ce dépôt contient :
- une application web Flask dans `app/`
- des scrapers dans `scrapers/` (VidIQ & YouTube)
- une base de données MongoDB
- des fichiers Docker pour exécution en conteneur
- un script `seed_db.py` pour initialiser la base de données
- un script `test_scraper.py` pour tester les scrapers

## 3. Architecture du projet

1. Les scrapers récupèrent les données depuis VidIQ
2. Les données sont nettoyées et structurées
3. Elles sont stockées dans MongoDB
4. L'application Flask interroge la base
5. Les statistiques sont affichées dans l'interface web

## 4. Structure du projet
```
DataEngineer_Project/
│
├── docker-compose.yml
├── entrypoint.sh
├── seed_db.py
├── test_scraper.py
│
├── app/
│   ├── main.py
│   ├── requirements.txt
│   └── templates/
│
└── scrapers/
    ├── vidiq_parser.py
    └── video_scraper.py
```

## 5. Technologies utilisées

**Backend** - Flask, Gunicorn, Jinja2  
**Scraping** - Requests, BeautifulSoup4, Playwright  
**Base de données** - MongoDB, PyMongo  
**Infrastructure** - Docker, Docker Compose

## 6. Justification des choix techniques

**MongoDB** - Les données scrapées sont semi-structurées et susceptibles d'évoluer. Son schéma flexible et son intégration naturelle avec Python en font le choix le plus adapté ici.

**Playwright** - VidIQ génère son contenu dynamiquement en JavaScript. Playwright permet un rendu complet de la page via un vrai navigateur, là où requests seul aurait renvoyé une page vide.

**Docker** - Garantit la reproductibilité de l'environnement et l'isolation des services, ce qui simplifie considérablement le déploiement.

## 7. Résultats & observations

Quelques tendances observées sur le Top 100 mondial :
- Les chaînes en tête cumulent plusieurs centaines de millions d'abonnés, avec un écart très marqué entre le top 10 et le reste du classement
- Le nombre de vidéos publiées n'est pas corrélé au rang — certaines chaînes atteignent le top avec peu de contenu, d'autres y sont avec des milliers de vidéos
- Les catégories divertissement et musique dominent largement le classement

## 8. Perspectives

Si nous avions eu plus de temps, nous aurions ajouté un historique des données pour observer l'évolution des classements dans le temps, ainsi qu'un système de mise à jour automatique périodique du scraping.

## 9. Installation & Lancement

Prérequis : Docker et Docker Compose. Le projet est conçu pour être exécuté uniquement via Docker.

```bash
# Construire et lancer les services
docker-compose up --build

# Accéder à l'application
http://localhost:8000

# Arrêter les services
docker-compose down
```

## Auteurs

Marie Bouëtel & Ghita Bensaleh  
ESIEE Paris — 2026  
Projet Data Engineering
ESIEE Paris — 2026
Projet Data Engineering
