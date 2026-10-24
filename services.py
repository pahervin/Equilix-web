# services.py
import requests
from configuration import URL_API_BASE, ENDPOINTS, TIMEOUT_API
from datetime import datetime

def secondes_vers_hhmm(secondes_str):
    """Convertit une chaîne de secondes depuis minuit en HH:mm."""
    secondes = int(secondes_str)
    heures = secondes // 3600 % 24
    minutes = (secondes % 3600) // 60
    return f"{heures:02d}:{minutes:02d}"

def timestamp_vers_hhmmss(timestamp):
    """Convertit un timestamp Unix (secondes depuis 1970) en format HH:mm:ss (heure locale)."""
    return datetime.fromtimestamp(float(timestamp)).strftime("%H:%M:%S")

def _appeler(endpoint):
    """Appelle un endpoint de l'API et retourne le JSON, ou None."""
    try:
        reponse = requests.get(f"{URL_API_BASE}{endpoint}", timeout=TIMEOUT_API)
        if reponse.status_code == 200:
            return reponse.json()
    except Exception as e:
        print(f"Erreur {endpoint}: {e}")
    return None

def obtenir_etat_global():
    """Récupère l'état global (dictionnaire à 3 niveaux hiérarchiques)."""
    donnees = _appeler(ENDPOINTS["etat_global"])
    return donnees if isinstance(donnees, dict) else {}

def obtenir_datation_puissance():
    donnees = _appeler(ENDPOINTS["datation_puissance"])
    if donnees is None:
        return '--:--:--'
    else:
        return timestamp_vers_hhmmss(donnees)

def obtenir_puissances_installees():
    """Récupère les puissances installées : {nom: puissance}."""
    donnees = _appeler(ENDPOINTS["puissances_installees"])
    if donnees is None:
        return [],[]
    if isinstance(donnees, dict):
        return list(donnees.keys()), list(donnees.values())

def obtenir_puissances_instantanees():
    """Récupère les puissances instantanées : {nom: puissance}."""
    noms = []
    puissances = []
    donnees = _appeler(ENDPOINTS["puissances_instantanees"])
    if isinstance(donnees, dict):
        noms = list(donnees.keys())
        puissances = list(donnees.values())
    return noms, puissances

def obtenir_energies_instantanees():
    """
    Récupère les énergies instantanées.
    L'API fournit un unique dictionnaire de valeurs :
    les énergies prélevée, produite et injectée,
    ainsi que la datation (nombre réel de secondes depuis minuit).
    Format attendu :
    {
        "produite": 15000, "prelevee": 12000, "injectee": 3000, "datation": 45300.0
    }
    """
    noms = ['Compteur','Onduleur','Injection','Consommation']
    energies = [0,0,0,0]
    donnees = _appeler(ENDPOINTS["energies_instantanees"])

    # La datation est un nombre réel de secondes depuis minuit
    horodatage = timestamp_vers_hhmmss(donnees.get("datation", 0))
    energies = [donnees["prelevee"], donnees["produite"], donnees["injectee"]]
    energies.append(donnees["prelevee"] + donnees["produite"] - donnees["injectee"])
    return noms, energies

def obtenir_energie_estimee():
    """Récupère l'énergie estimée et convertit les horodatages en HH:mm."""
    donnees = _appeler(ENDPOINTS["energie_estimee"])
    if donnees is None:
        return []
    if isinstance(donnees, dict):
        # Parcours avec Dict.items()
        return [
            {"horodatage": secondes_vers_hhmm(cle), "energie": valeur}
            for cle, valeur in donnees.items()
        ]
    # Liste de paires/triplets
    return [
        {"horodatage": secondes_vers_hhmm(str(element[0])), "energie": element[1]}
        for element in donnees
    ]

def obtenir_dernieres_energies():
    """Récupère l'énergie estimée et convertit les horodatages en HH:mm."""
    donnees = _appeler(ENDPOINTS["dernieres_energies"])
    if donnees is None or len(donnees) == 0:
        return [],[],[],[]
    if isinstance(donnees, list):
        horodatages = [secondes_vers_hhmm(donnee['datation']) for donnee in donnees]
        produites = [donnee['produite'] for donnee in donnees]
        prelevees = [donnee['prelevee'] for donnee in donnees]
        injectees = [donnee['injectee'] for donnee in donnees]
        return horodatages, produites, prelevees, injectees

def obtenir_planification_eau_chaude():
    """Récupère la planification de l'eau chaude et convertit les horodatages en HH:mm."""
    donnees = _appeler(ENDPOINTS["planification_eau_chaude"])
    if donnees is None:
        return []
    if isinstance(donnees, dict):
        # Parcours avec Dict.items() : {horodatage: [temperature, puissance]}
        return [
            {"horodatage": secondes_vers_hhmm(cle), "temperature": valeur}
            for cle, valeur in donnees.items()
        ]
    