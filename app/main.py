from flask import Flask, jsonify
from pymongo import MongoClient
import os

app = Flask(__name__)

# Config MongoDB - je récupère tout depuis les variables d'env
MONGO_CONFIG = {
    'host': os.getenv("MONGO_HOST", "mongo"),
    'port': int(os.getenv("MONGO_PORT", "27017")),
    'db': os.getenv("MONGO_DB", "numbeo"),
    'user': os.getenv("MONGO_USER", "admin"),
    'pwd': os.getenv("MONGO_PASSWORD", "adminpass")
}

def get_db():
    # Construction de l'URI de connexion
    connection_string = f"mongodb://{MONGO_CONFIG['user']}:{MONGO_CONFIG['pwd']}@{MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}/?authSource=admin"
    client = MongoClient(connection_string)
    return client[MONGO_CONFIG['db']]

@app.route("/")
def home():
    return "Numbeo project is running"

@app.route("/health")
def health():
    try:
        db = get_db()
        db.command("ping")
        return jsonify({"status": "ok", "db": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
