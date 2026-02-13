from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import os
import json
import statistics
import numpy as np
from jinja2 import Undefined
import collections.abc
from scipy import stats as scipy_stats



app = Flask(__name__)

# Configuration MongoDB
MONGO_CONFIG = {
    'host': os.getenv("MONGO_HOST", "mongo"),
    'port': int(os.getenv("MONGO_PORT", "27017")),
    'db': os.getenv("MONGO_DB", "vidiq"),
    'user': os.getenv("MONGO_USER", "admin"),
    'pwd': os.getenv("MONGO_PASSWORD", "adminpass")
}

def get_db():
    """Retourne la database MongoDB"""
    connection_string = f"mongodb://{MONGO_CONFIG['user']}:{MONGO_CONFIG['pwd']}@{MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}/?authSource=admin"
    client = MongoClient(connection_string)
    return client[MONGO_CONFIG['db']]


def add_derived_metrics(channels):
    """Ajoute des métriques dérivées pour les insights"""
    for ch in channels:
        subscribers = ch.get("subscribers", 0) or 0
        total_views = ch.get("total_views", 0) or 0
        videos = ch.get("videos", 0) or 0

        ch["views_per_subscriber"] = (total_views / subscribers) if subscribers else 0
        ch["views_per_video"] = (total_views / videos) if videos else 0
        ch["subs_per_video"] = (subscribers / videos) if videos else 0
    return channels

def gini_index(values):
    # Calcul de l'indice de Gini
    values = sorted([v for v in values if v > 0])
    n = len(values)
    if n == 0:
        return 0
    cumvals = [sum(values[:i+1]) for i in range(n)]
    total = cumvals[-1]
    gini = 1 - 2 * sum([(cumvals[i]/total) * (1/(n)) for i in range(n)])
    return round(gini, 3)

def lorenz_curve(values):
    # Calcul des points pour la courbe de Lorenz
    values = sorted([v for v in values if v > 0])
    n = len(values)
    cumvals = [0] + [sum(values[:i+1]) for i in range(n)]
    total = cumvals[-1]
    lorenz = [v/total for v in cumvals]
    x = [i/n for i in range(n+1)]
    return x, lorenz

# Jinja filter for humanizing large numbers (K, M, B)
def humanize_metric(value):
    try:
        value = float(value)
        if value >= 1_000_000_000:
            return f"{value/1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value/1_000:.1f}K"
        else:
            return f"{int(value)}"
    except Exception:
        return str(value)

app.jinja_env.filters['humanize_metric'] = humanize_metric

@app.route("/")
def home():
    """Accueil - affiche les stats générales."""
    try:
        db = get_db()
        collection = db['channels_enriched']
        
        # Stats globales
        total = collection.count_documents({})
        top_subscriber = collection.find_one(sort=[("subscribers", -1)])
        top_views = collection.find_one(sort=[("total_views", -1)])
        
        stats = {
            'total_channels': total,
            'top_subscriber': top_subscriber,
            'top_views': top_views
        }
        
        return render_template('accueil.html', stats=stats)
        
    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route("/channels")
def channels_list():
    """Affiche la liste de toutes les chaînes avec pagination."""
    try:
        # Paramètres de pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        skip = (page - 1) * per_page
        
        db = get_db()
        collection = db['channels_enriched']
        
        # Total de documents
        total = collection.count_documents({})
        total_pages = (total + per_page - 1) // per_page
        
        # Récupère les documents avec tri par rang
        channels = list(
            collection.find()
            .sort("rank", 1)
            .skip(skip)
            .limit(per_page)
        )
        
        # Convertit ObjectId en string pour JSON
        for ch in channels:
            ch['_id'] = str(ch['_id'])
            if 'scraped_at' in ch:
                ch['scraped_at'] = str(ch['scraped_at'])
        
        return render_template(
            'channels.html',
            channels=channels,
            page=page,
            total_pages=total_pages,
            total=total
        )
        
    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route("/search")
def search():
    """Moteur de recherche par nom de chaîne."""
    try:
        query = request.args.get('q', '', type=str).strip()
        
        db = get_db()
        collection = db['channels_enriched']
        
        if not query:
            channels = []
        else:
            # Recherche insensible à la casse
            channels = list(
                collection.find(
                    {"channel_name": {"$regex": query, "$options": "i"}}
                ).sort("rank", 1)
            )
            
            # Convertit ObjectId en string
            for ch in channels:
                ch['_id'] = str(ch['_id'])
        
        return render_template(
            'search.html',
            query=query,
            channels=channels,
            count=len(channels)
        )
        
    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route("/top10")
def top10():
    """Affiche le top 10 avec sélection de tri : salaire, vidéos ou vues."""
    try:
        db = get_db()
        collection = db['channels_enriched']
        
        # Paramètre de tri (salary, videos, views)
        sort_by = request.args.get('sort_by', 'rank', type=str)
        
        # Récupère tous les canaux et trie en Python
        if sort_by == 'salary':
            # Pour le tri par salaire, parse la chaîne "$6M - $18M"
            all_channels = list(collection.find().sort('rank', 1))
            
            def extract_salary(s):
                """Extrait le nombre du format '$6M - $18M' ou '$865K - $3M'"""
                if not s:
                    return 0
                # Enlève le '$' et récupère la première partie
                parts = s.split(' - ')
                first_part = parts[0].replace('$', '').strip()
                # Convertit 'K' et 'M' en nombres
                if 'M' in first_part:
                    return float(first_part.replace('M', '')) * 1000000
                elif 'K' in first_part:
                    return float(first_part.replace('K', '')) * 1000
                return 0
            
            # Trie par salaire estimé (descendant)
            all_channels.sort(key=lambda x: extract_salary(x.get('estimated_monthly_earnings', '')), reverse=True)
            top_channels = all_channels[:10]
        
        else:
            # Pour les autres tris, utilise MongoDB sort
            sort_field_map = {
                'videos': 'videos',
                'views': 'total_views',
                'rank': 'rank'
            }
            sort_field = sort_field_map.get(sort_by, 'rank')
            sort_order = 1 if sort_by == 'rank' else -1
            
            top_channels = list(
                collection.find()
                .sort(sort_field, sort_order)
                .limit(10)
            )
        
        # Convertit ObjectId en string
        for ch in top_channels:
            ch['_id'] = str(ch['_id'])
        
        return render_template(
            'top10.html',
            channels=top_channels,
            sort_by=sort_by
        )
        
    except Exception as e:
        return render_template('error.html', error=str(e))


# ============================================================================
# API JSON (pour appels AJAX ou externes)
# ============================================================================

@app.route("/api/channels")
def api_channels():
    """API pour récupérer les chaînes en JSON."""
    try:
        db = get_db()
        collection = db['channels_enriched']
        
        # Paramètres
        limit = request.args.get('limit', 100, type=int)
        sort_by = request.args.get('sort', 'rank', type=str)
        order = request.args.get('order', 'asc', type=str)
        
        # Valide les paramètres
        limit = min(limit, 1000)
        sort_order = 1 if order == 'asc' else -1
        
        channels = list(
            collection.find()
            .sort(sort_by, sort_order)
            .limit(limit)
        )
        
        # Convertit ObjectId
        for ch in channels:
            ch['_id'] = str(ch['_id'])
            if 'scraped_at' in ch:
                ch['scraped_at'] = str(ch['scraped_at'])
        
        return jsonify({
            'status': 'success',
            'count': len(channels),
            'data': channels
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route("/health")
def health():
    """Vérify que l'app et MongoDB sont fonctionnels."""
    try:
        db = get_db()
        db.command("ping")
        collection_count = db['channels_enriched'].count_documents({})
        
        return jsonify({
            "status": "ok",
            "db": "connected",
            "channels_count": collection_count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/insights")
def insights():
    """Insights et chaînes sous-cotées."""
    try:
        db = get_db()
        collection = db['channels_enriched']

        channels = list(collection.find())
        channels = add_derived_metrics(channels)

        # Statistiques globales
        subscribers_list = [c.get("subscribers", 0) for c in channels]
        views_list = [c.get("total_views", 0) for c in channels]
        videos_list = [c.get("videos", 0) for c in channels]

        stats = {
            "avg_subscribers": int(statistics.mean(subscribers_list)) if subscribers_list else 0,
            "median_subscribers": int(statistics.median(subscribers_list)) if subscribers_list else 0,
            "avg_views": int(statistics.mean(views_list)) if views_list else 0,
            "median_views": int(statistics.median(views_list)) if views_list else 0,
            "avg_videos": int(statistics.mean(videos_list)) if videos_list else 0,
        }

        # Chaînes sous-cotées : ratio vues/abonnés élevé
        underrated = sorted(
            channels,
            key=lambda c: c.get("views_per_subscriber", 0),
            reverse=True
        )[:10]

        # Top par vues/vidéo
        top_views_per_video = sorted(
            channels,
            key=lambda c: c.get("views_per_video", 0),
            reverse=True
        )[:10]

        # Convertit ObjectId en string
        for ch in underrated + top_views_per_video:
            ch['_id'] = str(ch['_id'])

        return render_template(
            'insights.html',
            stats=stats,
            underrated=underrated,
            top_views_per_video=top_views_per_video
        )

    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route("/quiz")
def quiz():
    try:
        db = get_db()
        collection = db['channels_enriched']
        channels = list(collection.find())
        subscribers = [c.get("subscribers", 0) for c in channels]
        views = [c.get("total_views", 0) for c in channels]
        # Corrélation
        if subscribers and views and len(subscribers) > 1 and len(views) > 1 and sum(subscribers) > 0 and sum(views) > 0:
            correlation = round(statistics.correlation(subscribers, views), 3)
        else:
            correlation = 0
        # Insight
        interpretation = f"La corrélation entre abonnés et vues est de {correlation}. Cela montre une relation modérée entre la popularité et l'audience."
        return render_template(
            "quiz.html",
            correlation=correlation,
            interpretation=interpretation
        )
    except Exception as e:
        return render_template("error.html", error=str(e))

# ============================================================================
# ERREURS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Gère les pages non trouvées."""
    return render_template('error.html', error="Page non trouvée (404)"), 404


@app.errorhandler(500)
def internal_error(error):
    """Gère les erreurs serveur."""
    return render_template('error.html', error="Erreur serveur (500)"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
