# app.py
import locale
from datetime import datetime, timezone
from operator import pos

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from configuration import (
    COULEURS, AFFICHAGE,
    INTERVALLE_INSTANTANE_MS, INTERVALLE_PREVISION_MS
)
from services import (
    obtenir_etat_global,
    obtenir_datation_puissance,
    obtenir_puissances_installees,
    obtenir_puissances_instantanees,
    obtenir_energies_instantanees,
    obtenir_energie_estimee,
    obtenir_dernieres_energies,
    obtenir_planification_eau_chaude
)

app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder='assets', routes_pathname_prefix='/equilix/')
server = app.server

PREFIXE_URL = AFFICHAGE.get("prefixe_url_appli", "").rstrip("/")
# Chemins absolus de l'application (préfixe inclus)
URL_TABLEAU_DE_BORD = f"{PREFIXE_URL}/suivi"
URL_ETAT_GLOBAL = f"{PREFIXE_URL}/"

LOGO = AFFICHAGE.get("logo")
LOGO_HAUTEUR = AFFICHAGE.get("logo_hauteur_px", 48)
COULEURS_GROUPES = COULEURS
COULEUR_GROUPE_DEFAUT = COULEURS["couleur_defaut"]
HAUTEUR_HAUT = AFFICHAGE.get("hauteur_graphe_haut_vh", 42)
HAUTEUR_BAS = AFFICHAGE.get("hauteur_graphe_bas_vh", 42)
ENERGIE_MAX_WH = AFFICHAGE.get("energie_max_wh", 50000)
PERIODE_ESTIMATION_H = AFFICHAGE.get("periode_estimation_h", 0.25)  # 15 minutes
CONFIG_GRAPHE = {"displayModeBar": False}
# Configuration (déjà définie) :
LOGO = AFFICHAGE.get("logo")                       # "logo_equilix.png"
LOGO_HAUTEUR = AFFICHAGE.get("logo_hauteur_px", 48)
POLICE = {"fontFamily": "Segoe UI, sans-serif"}

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),

    # --- En-tête commun : logo + titre "Equilix - Suivi" ---
    html.Div([
        html.Img(
            src=app.get_asset_url(LOGO),
            style={"height": f"{LOGO_HAUTEUR}px", "width": "auto",
                   "verticalAlign": "middle", "marginRight": "10px"}
        ),
        html.H2("Equilix - Suivi", style={"textAlign": "center", "marginRight": "10px", **POLICE}),
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
        "padding": "10px", "height": "calc(100vh - 55px)", "overflowY": "auto"
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

@callback(
    Output("conteneur-etat-global", "children"),
    Input("intervalle-instantane", "n_intervals")
)
def mettre_a_jour_etat_global(n):
    donnees = obtenir_etat_global()
    return construire_page_etat_global(donnees)

#  Rendu générique de l'état global
def construire_page_etat_global(donnees):
    """
    Niveau 1 : regroupements empilés verticalement (titre = clé)
    Niveau 2 : groupes affichés horizontalement, COULEUR = FOND DE LA CARTE
    Niveau 3 : couples clé/valeur alignés verticalement (valeurs en taille 16)
    """

    if not donnees:
        return html.Div("Aucune donnée d'état global disponible",
                         style={"textAlign": "center", "marginTop": "50px",
                                "fontSize": "16px", **POLICE})

    sections = []
    for nom_section, groupes in donnees.items():

        # --- Groupes du 2e niveau : alignement HORIZONTAL ---
        cartes = []
        for nom_groupe, valeurs in groupes.items():
            # Couleur du groupe (clé de config = clé du regroupement) -> FOND de carte
            couleur = COULEURS_GROUPES.get(nom_groupe, COULEUR_GROUPE_DEFAUT)

            if isinstance(valeurs, dict):
                # --- Données du 3e niveau : alignement vertical des valeurs ---
                lignes = [
                    html.Div([
                        html.Span(cle, style={
                            "flex": "1", "textAlign": "left",
                            "fontSize": "16px",                  # Clé
                            "color": COULEURS["texte"]           # Police neutre
                        }),
                        html.Span(rendre_valeur_texte(val), style={
                            "flex": "1", "textAlign": "right",
                            "fontSize": "16px",                  # <-- VALEUR en taille 16
                            "fontWeight": "bold",
                            "color": COULEURS["texte"]           # Police neutre
                        }),
                    ], style={
                        "display": "flex", "justifyContent": "space-between",
                        "margin": "3px 0"
                    })
                    for cle, val in valeurs.items()
                ]
            else:
                lignes = [html.Div(rendre_valeur_texte(valeurs),
                                   style={"fontSize": "16px", "textAlign": "right",
                                          "fontWeight": "bold",
                                          "color": COULEURS["texte"]})]

            # Carte : couleur en FOND, polices neutres, police Segoe UI
            cartes.append(html.Div([
                html.Div(nom_groupe, style={
                    "fontWeight": "bold", "fontSize": "18px",
                    "color": COULEURS["texte"],                 # <-- Pas de couleur sur la police
                    "borderBottom": f"1px solid {COULEURS['grille']}",
                    "paddingBottom": "4px", "marginBottom": "6px"
                }),
                html.Div(lignes),
            ], style={
                "backgroundColor": couleur,                     # <-- COULEUR EN FOND DE CARTE
                "borderRadius": "8px",
                "padding": "10px",
                "minWidth": "200px",
                "flex": "1",
                "margin": "5px",
                **POLICE                                        # <-- Segoe UI, comme les figures
            }))

        # --- Regroupement du 1er niveau : empilé VERTICALEMENT ---
        sections.append(html.Div([
            html.H3(nom_section, style={
                "margin": "10px 0 5px 5px", "fontSize": "20px",
                "color": COULEURS["texte"],
                "backgroundcolor": COULEURS["couleur_defaut"],
                "borderLeft": f"4px solid {COULEURS['grille']}",
                "paddingLeft": "8px", **POLICE
            }),
            html.Div(cartes, style={
                "display": "flex", "flexDirection": "row",
                "flexWrap": "wrap"
            }),
        ], style={
            "margin": "5px",
            "backgroundColor": COULEURS["couleur_defaut"],
            "paddingLeft": "8px",
            "borderRadius": "8px",
        }
        ))

    return html.Div(sections)

def rendre_valeur_texte(valeur):
    """Convertit une valeur du 3e niveau en texte affichable."""
    if isinstance(valeur, bool):
        return "✅" if valeur else "❌"
    if isinstance(valeur, float):
        return formater_nombre(valeur, 1)
    if isinstance(valeur, (int,)):
        return formater_nombre(valeur)
    if isinstance(valeur, dict):
        return "; ".join(f"{k}={v}" for k, v in valeur.items())
    if isinstance(valeur, list):
        return ", ".join(str(v) for v in valeur)
    return str(valeur)

# =============================================
# Layout : contraint dans la vue, deux intervalles
# =============================================
def layout_tableau_de_bord():
    return html.Div([
        html.Div([
            html.Div([dcc.Graph(id="graphe-puissances", style={"height": f"{HAUTEUR_HAUT}vh", "width": "100%"},
                       config=CONFIG_GRAPHE)],
                     style={"width": "65%", "display": "inline-block", "verticalAlign": "top"}),

            # Indicateurs (centre, empilés verticalement)
            html.Div(
                [dcc.Graph(id="indicateurs", style={"height": f"{HAUTEUR_HAUT}vh", "width": "100%"},
                          config=CONFIG_GRAPHE)],
                    style={"width": "15%", "display": "inline-block", "verticalAlign": "top"}),

            html.Div([dcc.Graph(id="graphe-energies", style={"height": f"{HAUTEUR_HAUT}vh", "width": "100%"},
                       config=CONFIG_GRAPHE)],
                     style={"width": "20%", "display": "inline-block", "verticalAlign": "top"}),
        ]),

        html.Div([
            dcc.Graph(id="graphe-energie-eau-chaude", style={"height": f"{HAUTEUR_BAS}vh", "width": "100%"},
                       config=CONFIG_GRAPHE)]),
    ])

# =============================================
# Fonction de mise en page commune
# (UNE SEULE instruction showlegend, passée en paramètre)
# =============================================
def mise_en_page(titre, titre_x, titre_y, afficher_legende=False, plage_y=None, plage_y2=None):
    return dict(
        title=dict(text=titre, font=dict(size=16, color=COULEURS["texte"])),
        xaxis=dict(
            title=titre_x, linecolor=COULEURS["texte"], linewidth=1, mirror=True,
            gridcolor=COULEURS["grille"], showgrid=True,
            tickfont=dict(size=12, color=COULEURS["texte"])
        ),
        yaxis=dict(
            title=titre_y, linecolor=COULEURS["texte"], linewidth=1, mirror=True,
            gridcolor=COULEURS["grille"], showgrid=True,
            tickfont=dict(size=12, color=COULEURS["texte"]),
            **({"range": plage_y} if plage_y else {})
        ),
        plot_bgcolor=COULEURS["fond_axes"],
        paper_bgcolor=COULEURS["fond_axes"],
        font=dict(family="Segoe UI, sans-serif", size=12, color=COULEURS["texte"]),
        margin=dict(t=36, b=40, l=50, r=20),
        showlegend=afficher_legende,  # <-- instruction unique
        legend=dict(orientation="h", y=1.05, x=1, xanchor="right", font=dict(size=10))
    )

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

@callback(
    [
        Output("graphe-puissances", "figure"),
        Output("graphe-energies", "figure"),
        Output("indicateurs", "figure"),
    ],
    Input("intervalle-instantane", "n_intervals")
)
def mettre_a_jour_instantanes(periode):
    noms_p1, puissances_installees = obtenir_puissances_installees()
    noms_p2, puissances_instantanees = obtenir_puissances_instantanees()
    noms_e, energies = obtenir_energies_instantanees()

    # --- 1. Puissances installées vs instantanées (légende affichée) ---
    fig_puissances = go.Figure()
    fig_puissances.add_trace(go.Bar(
        x=noms_p2,
        y=puissances_instantanees,
        name="Instantanée",
        marker_color=[COULEURS["prelevee"], COULEURS["injectee"], COULEURS["produite"], COULEURS["consommee"], COULEURS["consommee"]],
        text=[f"{p:,.0f} W" for p in puissances_instantanees],  # <-- Valeurs affichées
        textposition="outside",  # <-- Au-dessus des barres
        # hovermode = False,
        hovertemplate="%{x}: %{y} W<extra></extra>"
    ))
    fig_puissances.add_trace(go.Bar(
        x = noms_p1,
        y = puissances_installees,
        name="Installée",
        marker_color=COULEURS["puissance_installee"],
        hovertemplate="%{x}: max %{y} W<extra></extra>"
    ))

    fig_puissances.update_layout(
        barmode="group",
        **mise_en_page("Puissances installées / instantanées (W)",
                       None, "Puissance (W)", afficher_legende=False)
    )

    # --- 2. Énergies instantanées (échelle fixée à 50 000 Wh max, pas de légende) ---
    energie_compteur = energies[0]
    energie_autoconsommee = energies[1]-energies[2]
    energie_injection = energies[2]
    # Liens (source, cible, valeur)
    sources = [0, 1, 1]   # Compteur, Onduleur, Onduleur
    cibles  = [3, 3, 2]   # Consommation, Consommation, Injection
    valeurs = [energie_compteur, energie_autoconsommee, energie_injection]

    fig_energies = go.Figure(data=[go.Sankey(
        arrangement="fixed",
        node=dict(
            pad=10,
            thickness=40,
            label=noms_e,
            color=[COULEURS["prelevee"], COULEURS["produite"], COULEURS["injectee"], COULEURS["consommee"]],
            line=dict(color=COULEURS["texte"], width=0)
        ),
        link=dict(
            source=sources,
            target=cibles,
            value=valeurs,
            color=COULEURS['puissance_installee'],
            hovertemplate="Énergie: %{value} Wh<extra></extra>"
        )
    )])
    fig_energies.update_layout(
        title_text="Energies aujourd'hui (Wh)",
        font=dict(family="Segoe UI, sans-serif", size=12, color=COULEURS["texte"]),
        plot_bgcolor=COULEURS["fond_axes"],
        paper_bgcolor=COULEURS["fond_axes"],
        margin=dict(t=36, b=36, l=20, r=20),
        # height=HAUTEUR_HAUT * 4,  # adaptation selon le vh du graphe
    )

    # --- Taux d'autoconsommation ---
    taux_autoconsommation = 0.0
    if (energies[1] > 0):
        taux_autoconsommation = energie_autoconsommee / energies[1] * 100
    # --- Taux d'autonomie ---
    taux_autonomie = 0.0
    if (energies[3] > 0):
        taux_autonomie = energie_autoconsommee / energies[3] * 100
    valeurs_indicateur = [taux_autoconsommation, taux_autonomie]
    noms_indicateur = ['Autoconsommation', 'Autonomie']
    fig_indicateurs = go.Figure()
    fig_indicateurs.add_trace(go.Bar(
        x=noms_indicateur,
        y=valeurs_indicateur,
        # name=noms_indicateur,
        marker_color=[COULEURS["produite"], COULEURS["consommee"], COULEURS["consommee"]],
        text=[f"{p:,.0f} %" for p in valeurs_indicateur],  # <-- Valeurs affichées
        textposition="outside",  # <-- Au-dessus des barres
        # hovermode = False,
        hovertemplate="%{x}: %{y:,.1f} %<extra></extra>"
    ))
    fig_indicateurs.update_layout(
        **mise_en_page('Performances', None, None, plage_y=[0,105]),
    )

    return fig_puissances, fig_energies, fig_indicateurs

# =============================================
# Callback 2 : graphe inférieur (toutes les 15 min)
# =============================================
@callback(
    Output("graphe-energie-eau-chaude", "figure"),
    Input("intervalle-prevision", "n_intervals")
)
def mettre_a_jour_prevision(n):
    # puissances_installees = obtenir_puissances_installees()
    energie_estimee = obtenir_energie_estimee()
    horodatages,energies_produites,energies_prelevees,energies_injectees = obtenir_dernieres_energies()
    planification_eau_chaude = obtenir_planification_eau_chaude()

    # Échelle de l'énergie estimée :
    # puissance installée de l'onduleur × période d'échantillonnage (0,25 h)
    # puissance_onduleur = puissances_installees[1]
    puissance_onduleur = 6000.0
    energie_max_estimee = puissance_onduleur * PERIODE_ESTIMATION_H
    # Petite marge de 10 % au-dessus du maximum théorique
    plage_energie = [0, energie_max_estimee * 1.1] if energie_max_estimee > 0 else None

    fig_combine = go.Figure()

    if energie_estimee:
        fig_combine.add_trace(go.Bar(
            x=[d["horodatage"] for d in energie_estimee],
            y=[d["energie"] for d in energie_estimee],
            name="Énergie estimée (Wh)",
            marker_color=COULEURS["estimee"],
            hovertemplate="%{x} - %{y:,.0f} Wh<extra></extra>"
        ))

    if energies_produites:
        fig_combine.add_trace(go.Bar(
            x=horodatages,
            y=energies_produites,
            name="Énergie produite (Wh)",
            marker_color=COULEURS["produite"],
            hovertemplate="%{x} - %{y:,.0f} Wh<extra></extra>"
        ))

    if planification_eau_chaude:
        fig_combine.add_trace(go.Bar(
            x=[d["horodatage"] for d in planification_eau_chaude],
            y=[d["temperature"] for d in planification_eau_chaude],
            # mode="lines+markers",
            # line=dict(color=COULEURS["eau_chaude"], width=3),
            # marker=dict(color=COULEURS["eau_chaude"], size=6),
            marker_color=COULEURS["consommee"],
            name="Température eau chaude (°C)",
            yaxis="y2",
            hovertemplate="%{x} - %{y:.1f} °C<extra></extra>"
        ))

    mise_en_page_combine = mise_en_page(
        "Énergie estimée et température de l'eau chaude",
        "Heure UTC", "Énergie (Wh)",
        afficher_legende=True,        # légende unique pour ce graphe
        plage_y=plage_energie         # échelle dérivée de la puissance installée
    )
    mise_en_page_combine["yaxis2"] = dict(
        title="Température (°C)",
        overlaying="y", side="right",
        linecolor=COULEURS["texte"], linewidth=1,
        tickfont=dict(size=10, color=COULEURS["consommee"]),
        showgrid=False,
        range=[47.0, 65.0],
        tick0=50.0,
        dtick=5.0
    )
    mise_en_page_combine["margin"]["r"] = 50
    mise_en_page_combine["xaxis"]["tickangle"] = -45
    fig_combine.update_layout(
        barmode="group",
        **mise_en_page_combine)

    if not energie_estimee and energies_produites and not planification_eau_chaude:
        fig_combine.add_annotation(
            text="Aucune donnée disponible",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=COULEURS["texte"])
        )

    return fig_combine

# =============================================
# Exécution
# =============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)