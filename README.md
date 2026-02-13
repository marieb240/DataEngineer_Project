# 📊 DataEngineer_Project

ESIEE 2026 – Projet Data Engineering
Marie Bouëtel & Ghita Bensaleh

## 1️⃣ Introduction
Dans le cadre de l’unité de Data Engineering, nous avons développé une application web permettant de collecter, stocker et visualiser des statistiques YouTube à partir de données scrapées.

L’objectif du projet est de mettre en pratique :
- le web scraping
- le stockage en base de données
- le développement d’une application web en Python
- la conteneurisation avec Docker
- la rédaction d’une documentation technique et fonctionnelle

Notre application permet de consulter différentes statistiques du Top 100 des YouTubeurs mondiaux, notamment :
- 📈 Position (rank)
- 🎥 Nombre de vidéos
- 👥 Nombre d’abonnés
- 👁 Nombre total de vues

Les données sont récupérées depuis VidIQ, stockées dans MongoDB, puis affichées via une application web développée avec Flask.

## 2️⃣ Description du projet
Ce dépôt contient :
- 🖥️ Une application web Flask dans `app/`
- 🕷️ Des scrapers dans `scrapers/` (VidIQ & YouTube)
- 🗄️ Une base de données MongoDB
- 🐳 Des fichiers Docker pour exécution en conteneur
- 🌱 Un script `seed_db.py` pour initialiser la base de données
- 🧪 Un script `test_scraper.py` pour tester les scrapers

## 4️⃣ Architecture du projet
Le fonctionnement général est le suivant :
1. Les scrapers récupèrent les données depuis VidIQ.
2. Les données sont nettoyées et structurées.
3. Elles sont stockées dans MongoDB.
4. L’application Flask interroge la base.
5. Les statistiques sont affichées dans l’interface web.

## 5️⃣ Structure du projet
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

## 6️⃣ Technologies utilisées
### Backend
- flask==2.3.0 — Framework web
- gunicorn==21.2.0 — Serveur WSGI
- jinja2==3.1.2 — Templates HTML
- werkzeug==2.3.0

### Scraping
- requests==2.31.0
- beautifulsoup4==4.12.0
- playwright==1.41.2 (gestion du contenu dynamique)

### Base de données
- pymongo==4.6.0
- MongoDB

## 7️⃣ Justification des choix techniques
### 🔹 Pourquoi MongoDB ?
Les données scrapées sont semi-structurées et susceptibles d’évoluer.
MongoDB permet :
- une flexibilité de schéma
- une intégration simple avec Python
- un stockage adapté aux documents JSON

### 🔹 Pourquoi Playwright ?
VidIQ utilise du JavaScript pour générer dynamiquement le contenu.
Playwright permet :
- le rendu complet de la page
- l’automatisation d’un navigateur réel
- un scraping plus robuste

### 🔹 Pourquoi Docker ?
Docker garantit :
- la reproductibilité de l’environnement
- l’isolation des services
- un déploiement simplifié
- le respect des exigences du projet

## 8️⃣ Installation & Lancement
### Prérequis
- Docker
- Docker Compose

⚠️ Le projet est conçu pour être exécuté uniquement via Docker.

### Démarrage rapide
1. Construire et lancer les services :
   ```bash
   docker-compose up --build
   ```
2. Accéder à l’application :
   Ouvrir dans un navigateur :
   [http://localhost:8000](http://localhost:8000)
3. Arrêter les services :
   ```bash
   docker-compose down
   ```

## 9️⃣ Fonctionnalités principales
- Affichage du Top 100 mondial
- Consultation des statistiques individuelles
- Données stockées et persistées en base
- Architecture modulaire (scrapers séparés de l’app)

## 📄 Documentation technique
Le projet repose sur :
- Une architecture modulaire
- Une séparation claire entre scraping, stockage et visualisation
- Une conteneurisation complète via Docker Compose
- Une base de données persistante

## 👩‍💻 Auteurs
Marie Bouëtel
Ghita Bensaleh

ESIEE Paris — 2026
Projet Data Engineering