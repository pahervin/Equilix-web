# appli.py

import dash
from dash import dcc, html, Input, Output, callback
from configuration import (
    COULEURS, AFFICHAGE, POLICE,
    INTERVALLE_INSTANTANE_MS, INTERVALLE_PREVISION_MS
)
from services import (
    obtenir_datation_puissance
)

from page_etat import mettre_a_jour_etat_global
from page_supervision import layout_tableau_de_bord

app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder='assets', routes_pathname_prefix='/equilix/')
server = app.server

PREFIXE_URL = AFFICHAGE.get("prefixe_url_appli", "").rstrip("/")
# Chemins absolus de l'application (préfixe inclus)
URL_TABLEAU_DE_BORD = f"{PREFIXE_URL}/suivi"
URL_ETAT_GLOBAL = f"{PREFIXE_URL}/"

LOGO = AFFICHAGE.get("logo")
LOGO_HAUTEUR = AFFICHAGE.get("logo_hauteur_px", 48)
TITRE = AFFICHAGE.get("titre")
ENERGIE_MAX_WH = AFFICHAGE.get("energie_max_wh", 50000)

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),

    # --- En-tête commun : logo + titre "Equilix - Suivi" ---
    html.Div([
        html.Img(
            src=app.get_asset_url(LOGO),
            style={"height": f"{LOGO_HAUTEUR}px", "width": "auto",
                   "verticalAlign": "middle", "marginRight": "10px"}
        ),
        html.H2(TITRE, style={"textAlign": "center", "marginRight": "10px", **POLICE}),
        html.Div("Dernière mise à jour : --:--", id="derniere-mise-a-jour",
                 style={"textAlign": "center", "verticalAlign": "bottom", "fontStyle": "italic", "fontSize": "16px", **POLICE}),
        html.Div([
            # Bouton de bascule vers le tableau de bord (visible partout)
            dcc.Link(
                html.Button("Supervision", style={
                    "padding": "6px 16px", "fontSize": "13px",
                    "backgroundColor": "white",
                    "border": "1px solid " + COULEURS["grille"],
                    "borderRadius": "6px", "cursor": "pointer",
                    "float": "right", "marginLeft": "8px"
                }),
                href=URL_TABLEAU_DE_BORD, refresh=False
            ),
            # Bouton vers l'état global
            dcc.Link(
                html.Button("État", style={
                    "padding": "6px 16px", "fontSize": "13px",
                    "backgroundColor": "white",
                    "border": "1px solid " + COULEURS["grille"],
                    "borderRadius": "6px", "cursor": "pointer",
                    "float": "right", "marginLeft": "8px"
                }),
                href=URL_ETAT_GLOBAL, refresh=False
            ),
        ], style={
            "marginLeft": "auto",           # <-- Alignement à droite
            "display": "flex", "alignItems": "center"
        }),
    ], style={
        "padding": "8px 20px",
        "borderBottom": f"1px solid {COULEURS['grille']}",
        "backgroundColor": "#f8f9fa",
        "display": "flex", "alignItems": "center"
    }),

    # --- Conteneur de page (contenu spécifique à chaque écran) ---
    html.Div(id="conteneur-page", style={
        "padding": "10px", "height": "calc(100vh - 55px)"
    }),

    # --- Intervalles (rafraîchissement 10 s, clé de config partagée) ---
    dcc.Interval(id="intervalle-instantane", interval=INTERVALLE_INSTANTANE_MS, n_intervals=0),
    dcc.Interval(id="intervalle-prevision", interval=INTERVALLE_PREVISION_MS, n_intervals=0),
])

# =============================================
# Routage : sélectionne la page selon l'URL
# =============================================
@callback(Output("conteneur-page", "children"), Input("url", "pathname"))
def afficher_page(pathname):
    if pathname == URL_ETAT_GLOBAL:
        return html.Div(id="conteneur-etat-global")
    return layout_tableau_de_bord()

# =============================================
# Fonction de mise en page commune
# (UNE SEULE instruction showlegend, passée en paramètre)
# =============================================

# =============================================
# Callback 1 : données instantanées (toutes les 10 s)
# =============================================
@callback(
    [
        Output("derniere-mise-a-jour", "children"),
    ],
    Input("intervalle-instantane", "n_intervals")
)
def derniere_mise_a_jour(periode):
    heure_maj = obtenir_datation_puissance()
    return [f"Dernière mise à jour (données : {heure_maj}"]


# =============================================
# Callback 2 : graphe inférieur (toutes les 15 min)
# =============================================

# =============================================
# Exécution
# =============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)