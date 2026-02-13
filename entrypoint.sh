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
echo " MongoDB est opérationnel"

# Vérifier si les données existent déjà
echo "Vérification des données..."
COLLECTION_COUNT=$(mongosh --host mongo --username $MONGO_USER --password $MONGO_PASSWORD --eval "use $MONGO_DB; db.channels.countDocuments({})" --quiet)

if [ "$COLLECTION_COUNT" -eq 0 ]; then
    echo " Lancement du scraper..."
    python seed_db.py
else
    echo "Données déjà présentes ($COLLECTION_COUNT documents)"
fi

echo " Initialisation terminée !"

