# configuration.py
import json

def charger_configuration(chemin="config.json"):
    with open(chemin, "r", encoding="utf-8") as fichier:
        return json.load(fichier)

CONFIG = charger_configuration()

URL_API_BASE = CONFIG["api"]["url_base"]
ENDPOINTS = CONFIG["api"]["endpoints"]
COULEURS = CONFIG["couleurs"]
AFFICHAGE = CONFIG["affichage"]
TIMEOUT_API = CONFIG["api"].get("timeout", 5)
INTERVALLE_INSTANTANE_MS = CONFIG["api"].get("intervalle_instantane_ms", 10000)
INTERVALLE_PREVISION_MS = CONFIG["api"].get("intervalle_prevision_ms", 900000)