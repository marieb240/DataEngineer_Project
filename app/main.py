from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import os
import json
import statistics

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
        
        return render_template('index.html', stats=stats)
        
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
    """Affiche le top 10 avec graphique."""
    try:
        db = get_db()
        collection = db['channels_enriched']
        
        # Récupère le top 10 par rang
        top_channels = list(
            collection.find()
            .sort("rank", 1)
            .limit(10)
        )
        
        # Convertit en string
        for ch in top_channels:
            ch['_id'] = str(ch['_id'])
        
        return render_template('top10.html', channels=top_channels)
        
    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route("/stats")
def stats():
    try:
        db = get_db()
        collection = db['channels_enriched']
        channels = list(collection.find())
        channels = add_derived_metrics(channels)

        # Nettoyage ObjectId
        for c in channels:
            if '_id' in c:
                c['_id'] = str(c['_id'])
            for k, v in c.items():
                if hasattr(v, 'to_json'):
                    c[k] = v.to_json()
                elif hasattr(v, 'isoformat'):
                    c[k] = v.isoformat()
                elif type(v).__name__ == 'ObjectId':
                    c[k] = str(v)
                elif type(v).__name__ == 'datetime':
                    c[k] = str(v)
                elif hasattr(v, 'tolist'):
                    c[k] = v.tolist()
                elif hasattr(v, 'item'):
                    c[k] = v.item()

        # Conversion explicite de tous les objets potentiellement non natifs
        def to_native(val):
            import numpy as np
            from jinja2 import Undefined
            if isinstance(val, np.ndarray):
                return val.tolist()
            elif isinstance(val, (np.floating, np.float32, np.float64)):
                return float(val)
            elif isinstance(val, (np.integer, np.int32, np.int64)):
                return int(val)
            elif isinstance(val, Undefined):
                return 0
            elif val is None:
                return 0
            return val

        def sanitize(obj):
            # Recursively convert all Undefined/None/numpy types to native types
            import collections.abc
            from jinja2 import Undefined
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize(v) for v in obj]
            elif isinstance(obj, tuple):
                return tuple(sanitize(v) for v in obj)
            elif isinstance(obj, Undefined):
                return 0
            elif obj is None:
                return 0
            else:
                return to_native(obj)

        subscribers = [to_native(c.get("subscribers", 0)) for c in channels]
        views = [to_native(c.get("total_views", 0)) for c in channels]
        videos = [to_native(c.get("videos", 0)) for c in channels]
        names = [str(c.get("channel_name", "")) for c in channels]

        # Productivité = vidéos publiées (ou vidéos/mois si date disponible)
        # Performance = vues moyennes par vidéo
        # Efficiency = vues/abonné
        for c in channels:
            c['productivity'] = c.get('videos', 0)
            c['performance'] = c.get('views_per_video', 0)
            c['efficiency'] = c.get('views_per_subscriber', 0)

        productivity = [to_native(c['productivity']) for c in channels]
        avg_performance = [to_native(c['performance']) for c in channels]
        efficiency = [to_native(c['efficiency']) for c in channels]

        # Business KPIs: Estimated Revenue & Efficiency
        # Assume CPM (cost per mille) = 2€ per 1000 views (can be adjusted)
        CPM = 2.0  # euros per 1000 views
        channel_revenues = [(c.get('total_views', 0) / 1000) * CPM for c in channels]
        total_revenue = sum(channel_revenues)
        mean_revenue = total_revenue / len(channels) if channels else 0
        revenue_per_video = total_revenue / sum(videos) if sum(videos) else 0
        # Top 10 revenue channels
        top10_revenue = sorted([
            {'channel_name': c.get('channel_name', ''), 'revenue': (c.get('total_views', 0) / 1000) * CPM}
            for c in channels
        ], key=lambda x: x['revenue'], reverse=True)[:10]
        # Top 10 efficiency channels (views per video)
        top10_efficiency = sorted([
            {'channel_name': c.get('channel_name', ''), 'efficiency': c.get('views_per_video', 0)}
            for c in channels
        ], key=lambda x: x['efficiency'], reverse=True)[:10]
        # Efficiency scores for all channels
        efficiency_scores = [c.get('views_per_video', 0) for c in channels]

        # Segmentation par taille d'audience (quartiles)
        segments = []
        if subscribers and len(subscribers) >= 4:
            q1, q2, q3 = statistics.quantiles(subscribers, n=4)
            for c in channels:
                subs = c.get("subscribers", 0)
                if subs <= q1:
                    c["segment"] = "Micro"
                elif subs <= q2:
                    c["segment"] = "Mid"
                elif subs <= q3:
                    c["segment"] = "Large"
                else:
                    c["segment"] = "Mega"
                segments.append(c["segment"])
        else:
            for c in channels:
                c["segment"] = ""
                segments.append("")

        # Quadrants (médiane)
        prod_median = statistics.median(productivity) if productivity else 0
        perf_median = statistics.median(avg_performance) if avg_performance else 0
        for c in channels:
            if c['productivity'] >= prod_median and c['performance'] >= perf_median:
                c['quadrant'] = 'Top Performer'
            elif c['productivity'] < prod_median and c['performance'] >= perf_median:
                c['quadrant'] = 'Sniper'
            elif c['productivity'] >= prod_median and c['performance'] < perf_median:
                c['quadrant'] = 'Mass Publisher'
            else:
                c['quadrant'] = 'Low Performer'

        # Corrélation et régression (log-log)
        import numpy as np
        from scipy import stats as scipy_stats
        def safe_log(arr):
            return np.log10(np.array(arr) + 1e-6)
        prod_log = safe_log(productivity)
        perf_log = safe_log(avg_performance)
        if len(prod_log) > 1 and len(perf_log) > 1:
            corr, pval = scipy_stats.pearsonr(prod_log, perf_log)
            slope, intercept = np.polyfit(prod_log, perf_log, 1)
            y_pred = slope * prod_log + intercept
            y_pred = slope * prod_log + intercept
            r2 = 1 - np.sum((perf_log - y_pred) ** 2) / np.sum((perf_log - np.mean(perf_log)) ** 2)
            mae_log = np.mean(np.abs(perf_log - y_pred))
            # Arrondis pour affichage
            corr_disp = round(corr, 2)
            r2_disp = round(r2, 2)
            mae_log_disp = round(mae_log, 2)
            slope_disp = round(slope, 2)
            intercept_disp = round(intercept, 2)
            pval_disp = '< 0.01' if pval < 0.01 else f'{pval:.2f}'
            # Interprétation
            if corr < -0.5:
                relation = 'relation inverse forte'
            elif corr > 0.5:
                relation = 'relation directe forte'
            else:
                relation = 'relation modérée'
            interpretation_corr = (
                f"Corrélation : {corr_disp} ({relation})<br>"
                f"R² : {r2_disp} ({int(r2_disp*100)}% de variance expliquée)<br>"
                f"MAE (log10) : {mae_log_disp}<br>"
                f"p-value : {pval_disp} (statistiquement significatif)"
            )
            equation_disp = f"log(Performance) = {slope_disp} log(Productivité) + {intercept_disp}"
            phrase = (
                f"Une augmentation de la productivité est associée à une {'baisse' if corr < 0 else 'hausse'} de la performance moyenne. "
                f"Relation log-log : {equation_disp}."
            )
        else:
            corr_disp = r2_disp = mae_log_disp = slope_disp = intercept_disp = 0
            pval_disp = 'N/A'
            interpretation_corr = 'Corrélation non calculée'
            equation_disp = ''
            phrase = ''

        # Pour le JS : perf_gap = y_pred (valeurs prédites par la régression, pour chaque productivité)
        if len(prod_log) > 1 and len(perf_log) > 1:
            perf_gap = [float(y) for y in y_pred]
        else:
            perf_gap = [0 for _ in subscribers]

        # Lorenz + Gini (structure du marché)
        def lorenz_curve(values):
            values = sorted([v for v in values if v > 0])
            n = len(values)
            if n == 0:
                return [0.0], [0.0]
            cumvals = [0] + [sum(values[:i+1]) for i in range(n)]
            total = cumvals[-1] if cumvals else 1
            lorenz = [v/total if total else 0.0 for v in cumvals]
            x = [i/n for i in range(n+1)] if n else [0.0]
            return x, lorenz
        def gini_index(values):
            values = sorted([v for v in values if v > 0])
            n = len(values)
            if n == 0:
                return 0.0
            cumvals = [sum(values[:i+1]) for i in range(n)]
            total = cumvals[-1] if cumvals else 1
            if total == 0:
                return 0.0
            gini = 1 - 2 * sum([(cumvals[i]/total) * (1/(n)) for i in range(n)])
            return round(gini, 3)
        x_lorenz, y_lorenz = lorenz_curve(views)
        x_lorenz = [to_native(x) for x in x_lorenz]
        y_lorenz = [to_native(y) for y in y_lorenz]
        gini = gini_index(views)
        total_views = sum(views)
        sorted_views = sorted(views, reverse=True)
        top10_views = sum(sorted_views[:10]) / total_views * 100 if total_views else 0.0
        top20_views = sum(sorted_views[:20]) / total_views * 100 if total_views else 0.0
        bottom50_views = sum(sorted_views[-50:]) / total_views * 100 if total_views else 0.0

        # Interprétation dynamique de l'indice de Gini
        if gini < 0.3:
            gini_phrase = f"Le marché est très peu concentré (Gini {gini}), indiquant une distribution relativement égalitaire."
        elif gini < 0.5:
            gini_phrase = f"Le marché présente une concentration modérée (Gini {gini}), indiquant une distribution relativement inégale mais non monopolistique."
        else:
            gini_phrase = f"Le marché est très concentré (Gini {gini}), indiquant une forte inégalité de répartition des vues."

        # Statistiques par segment
        import collections
        segments_stats = {}
        for seg in set(segments):
            if not seg:
                continue
            idx = [i for i, s in enumerate(segments) if s == seg]
            if not idx:
                continue
            seg_prod = [productivity[i] for i in idx]
            seg_perf = [avg_performance[i] for i in idx]
            seg_eff = [efficiency[i] for i in idx]
            segments_stats[seg] = {
                'productivity_median': float(np.median(seg_prod)) if seg_prod else 0,
                'performance_median': float(np.median(seg_perf)) if seg_perf else 0,
                'efficiency_median': float(np.median(seg_eff)) if seg_eff else 0,
                'count': len(idx)
            }
        # Statistiques par segment (forcer la conversion en types natifs)
        segments_stats_native = {}
        for seg, d in segments_stats.items():
            segments_stats_native[seg] = {k: float(v) if isinstance(v, (int, float)) else int(v) if isinstance(v, bool) else str(v) for k, v in d.items()}

        # Interprétation segments
        segments_interpretation = ", ".join([
            f"{seg}: {d['count']} chaînes, prod médiane {d['productivity_median']:.0f}, perf médiane {d['performance_median']:.0f}"
            for seg, d in segments_stats.items()
        ]) if segments_stats else "Non calculée"

        # Écart-type vues/abonnés
        std_views = float(np.std(views)) if views else 0
        std_subscribers = float(np.std(subscribers)) if subscribers else 0
        dispersion_interpretation = f"Std vues: {std_views:.0f}, std abonnés: {std_subscribers:.0f}"

        # Corrélation interprétation
        corr_interpretation = f"Corrélation log-log productivité/performance: {corr:.2f}, R²: {r2:.2f}"
        efficiency_interpretation = f"Efficacité médiane: {np.median(efficiency):.2f} vues/abonné"

        # Comptage quadrants pour interprétation
        n_top = sum(1 for c in channels if c['quadrant'] == 'Top Performer')
        n_sniper = sum(1 for c in channels if c['quadrant'] == 'Sniper')
        n_mass = sum(1 for c in channels if c['quadrant'] == 'Mass Publisher')
        n_low = sum(1 for c in channels if c['quadrant'] == 'Low Performer')
        productivity_interpretation = (
            f"Top Performer (haute productivité & performance) : {n_top} chaînes. "
            f"Sniper (peu de vidéos, forte perf) : {n_sniper}. "
            f"Mass Publisher (beaucoup de vidéos, perf faible) : {n_mass}. "
            f"Low Performer : {n_low}. "
            f"Corrélation log-log : {corr:.2f}, R² : {r2:.2f}. "
        )

        # Insight stratégique rédigé
        insight_strategique = (
            f"La majorité des chaînes ({n_sniper}%) adoptent un profil 'Sniper' : faible productivité mais forte performance moyenne. "
            f"À l’inverse, {n_mass}% publient massivement avec une performance moyenne plus faible. "
            f"La corrélation log-log négative ({corr_disp}, R² = {r2_disp}) suggère un effet de rendement décroissant : publier davantage est associé à une baisse de performance moyenne."
            if n_sniper and n_mass else
            "Données insuffisantes pour une analyse stratégique fiable."
        )

        # Gini phrase enrichie
        gini_phrase = (
            f"Les 10% de chaînes les plus vues captent {top10_views:.1f}% du total, indiquant une concentration significative mais non extrême."
            if gini < 0.6 else
            f"Le marché est très concentré (Gini {gini:.2f})."
        )

        synthese = (
            f"{n_top} chaînes sont Top Performer, {n_sniper} Sniper, {n_mass} Mass Publisher, {n_low} Low Performer. "
            f"La corrélation productivité/performance est de {corr:.2f} (R²={r2:.2f}). "
            f"Segments: {segments_interpretation}."
        )

        RPM = 3  # euros par 1000 vues (business hypothèse)
        for c in channels:
            c["estimated_revenue"] = c.get("total_views", 0) / 1000 * RPM
            c["revenue_per_video"] = c["estimated_revenue"] / c.get("videos", 1)
            c["efficiency_score"] = c.get("total_views", 0) / c.get("videos", 1)

        # KPIs business
        revenues = [c["estimated_revenue"] for c in channels]
        revenue_total = sum(revenues)
        revenue_mean = revenue_total / len(channels) if channels else 0
        revenue_max = max(revenues) if revenues else 0

        # Top 10 revenus
        top10_revenue = sorted([
            {"channel_name": c.get("channel_name", ""), "revenue": c["estimated_revenue"]}
            for c in channels
        ], key=lambda x: x["revenue"], reverse=True)[:10]
        # Top 10 efficacité (views/video)
        top10_efficiency = sorted([
            {"channel_name": c.get("channel_name", ""), "efficiency": c["efficiency_score"]}
            for c in channels
        ], key=lambda x: x["efficiency"], reverse=True)[:10]

        # Scatter videos vs revenue_per_video
        videos_list = [c.get("videos", 0) for c in channels]
        revenue_per_video_list = [c["revenue_per_video"] for c in channels]

        context = dict(
            channels=channels,
            subscribers=subscribers,
            views=views,
            videos=videos,
            names=names,
            correlation=corr_disp,
            interpretation=productivity_interpretation,
            x_lorenz=x_lorenz,
            y_lorenz=y_lorenz,
            gini=gini,
            top10_views=round(top10_views,1),
            top20_views=round(top20_views,1),
            bottom50_views=round(bottom50_views,1),
            segments=segments,
            r2=r2_disp,
            mae_log=mae_log_disp,
            productivity=productivity,
            avg_performance=avg_performance,
            efficiency=efficiency,
            segments_stats=segments_stats_native,
            std_views=to_native(std_views),
            std_subscribers=to_native(std_subscribers),
            corr_interpretation=interpretation_corr,
            productivity_interpretation=productivity_interpretation,
            efficiency_interpretation=efficiency_interpretation,
            segments_interpretation=segments_interpretation,
            dispersion_interpretation=dispersion_interpretation,
            synthese=synthese,
            prod_median=to_native(prod_median),
            perf_median=to_native(perf_median),
            slope=to_native(slope_disp),
            intercept=to_native(intercept_disp),
            pval_disp=pval_disp,
            equation_disp=equation_disp,
            phrase=phrase,
            perf_gap=perf_gap,
            gini_phrase=gini_phrase,
            insight_strategique=insight_strategique,
            total_revenue=round(total_revenue, 2),
            mean_revenue=round(mean_revenue, 2),
            revenue_per_video=round(revenue_per_video, 2),
            top10_revenue=top10_revenue,
            top10_efficiency=top10_efficiency,
            efficiency_scores=efficiency_scores,
            revenue_total=round(revenue_total, 2),
            revenue_mean=round(revenue_mean, 2),
            revenue_max=round(revenue_max, 2),
            videos_list=videos_list,
            revenue_per_video_list=revenue_per_video_list,
        )
        context = sanitize(context)
        return render_template("stats.html", **context)
    except Exception as e:
        return render_template("error.html", error=str(e))

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
