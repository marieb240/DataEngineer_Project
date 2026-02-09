#!/bin/bash
# Script d'initialisation pour orchestrer le scraping avant le web

set -e

echo "=================================================="
echo "🚀 Initialisation VidIQ Project"
echo "=================================================="

# Attendre que MongoDB soit prêt
echo "⏳ Attente de MongoDB..."
while ! mongosh --host mongo --username $MONGO_USER --password $MONGO_PASSWORD --eval "db.adminCommand('ping')" &> /dev/null; do
    echo "  MongoDB pas encore prêt, attente 2s..."
    sleep 2
done
echo "✓ MongoDB est opérationnel"

# Vérifier si les données top100 existent déjà
echo "🔍 Vérification des données Top100..."
TOP100_COUNT=$(mongosh --host mongo --username $MONGO_USER --password $MONGO_PASSWORD --eval "use $MONGO_DB; db.channels_top100.countDocuments({})" --quiet)

if [ "$TOP100_COUNT" -eq 0 ]; then
    echo "📥 Lancement du scraping Top100..."
    python seed_db.py
else
    echo "✓ Top100 déjà présent ($TOP100_COUNT documents)"
fi

# Vérifier si les données enrichies existent déjà
echo "🔍 Vérification des données enrichies..."
ENRICHED_COUNT=$(mongosh --host mongo --username $MONGO_USER --password $MONGO_PASSWORD --eval "use $MONGO_DB; db.channels_enriched.countDocuments({})" --quiet)

if [ "$ENRICHED_COUNT" -eq 0 ]; then
    echo "✨ Lancement de l'enrichissement..."
    python scrapers/vidiq_enrich.py
else
    echo "✓ Enrichissement déjà présent ($ENRICHED_COUNT documents)"
fi

echo "=================================================="
echo "✅ Initialisation terminée !"
echo "=================================================="
