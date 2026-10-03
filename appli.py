# app.py
import locale
from datetime import datetime, timezone
import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from configuration import (
    COULEURS, AFFICHAGE,
    INTERVALLE_INSTANTANE_MS, INTERVALLE_PREVISION_MS
)
from services import (
    obtenir_puissances_installees,
    obtenir_puissances_instantanees,
    obtenir_energies_instantanees,
    obtenir_energie_estimee,
    obtenir_planification_eau_chaude
)

app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder='assets')
server = app.server

HAUTEUR_HAUT = AFFICHAGE.get("hauteur_graphe_haut_vh", 42)
HAUTEUR_BAS = AFFICHAGE.get("hauteur_graphe_bas_vh", 42)
ENERGIE_MAX_WH = AFFICHAGE.get("energie_max_wh", 50000)
PERIODE_ESTIMATION_H = AFFICHAGE.get("periode_estimation_h", 0.25)  # 15 minutes
CONFIG_GRAPHE = {"displayModeBar": False}

# =============================================
# Layout : contraint dans la vue, deux intervalles
# =============================================
app.layout = html.Div([
    html.Div([
        html.H2(AFFICHAGE.get("titre", "Tableau de bord"),
                style={"textAlign": "center", "margin": "0 0 4px 0", "fontSize": "20px"}),
        html.Div("Dernière mise à jour : --:--", id="derniere-mise-a-jour",
                 style={"textAlign": "center", "marginBottom": "8px", "fontStyle": "italic", "fontSize": "12px"}),
    ]),

    html.Div([
        html.Div([dcc.Graph(id="graphe-puissances", style={"height": f"{HAUTEUR_HAUT}vh", "width": "100%"},
                   config=CONFIG_GRAPHE)],
                 style={"width": "65%", "display": "inline-block", "verticalAlign": "top"}),

        # Indicateurs (centre, empilés verticalement)
        html.Div([
            dcc.Graph(id="indicateur-autoconsommation",
                      style={"height": f"{HAUTEUR_HAUT * 0.45}vh", "width": "100%"},
                      config=CONFIG_GRAPHE),
            dcc.Graph(id="indicateur-autonomie",
                      style={"height": f"{HAUTEUR_HAUT * 0.45}vh", "width": "100%"},
                      config=CONFIG_GRAPHE),
        ], style={"width": "15%", "display": "inline-block", "verticalAlign": "top",
                  "textAlign": "center"}),

        html.Div([dcc.Graph(id="graphe-energies", style={"height": f"{HAUTEUR_HAUT}vh", "width": "100%"},
                   config=CONFIG_GRAPHE)],
                 style={"width": "20%", "display": "inline-block", "verticalAlign": "top"}),
    ]),

    html.Div([
        dcc.Graph(id="graphe-energie-eau-chaude", style={"height": f"{HAUTEUR_BAS}vh", "width": "100%"},
                   config=CONFIG_GRAPHE)
    ]),

    # Deux intervalles : instantané (10 s) et prévisions (15 min)
    dcc.Interval(id="intervalle-instantane", interval=INTERVALLE_INSTANTANE_MS, n_intervals=0),
    dcc.Interval(id="intervalle-prevision", interval=INTERVALLE_PREVISION_MS, n_intervals=0),
], style={
    "height": "100vh", "overflow": "hidden", "padding": "10px",
    "boxSizing": "border-box", "display": "flex", "flexDirection": "column",
})

# =============================================
# Fonction de mise en page commune
# (UNE SEULE instruction showlegend, passée en paramètre)
# =============================================
def mise_en_page(titre, titre_x, titre_y, afficher_legende=False, plage_y=None, plage_y2=None):
    return dict(
        title=dict(text=titre, font=dict(size=14, color=COULEURS["texte"])),
        xaxis=dict(
            title=titre_x, linecolor=COULEURS["texte"], linewidth=1, mirror=True,
            gridcolor=COULEURS["grille"], showgrid=True,
            tickfont=dict(size=10, color=COULEURS["texte"])
        ),
        yaxis=dict(
            title=titre_y, linecolor=COULEURS["texte"], linewidth=1, mirror=True,
            gridcolor=COULEURS["grille"], showgrid=True,
            tickfont=dict(size=10, color=COULEURS["texte"]),
            **({"range": plage_y} if plage_y else {})
        ),
        plot_bgcolor=COULEURS["fond_axes"],
        paper_bgcolor=COULEURS["fond_axes"],
        font=dict(family="Segoe UI, sans-serif", size=10, color=COULEURS["texte"]),
        margin=dict(t=36, b=40, l=50, r=20),
        showlegend=afficher_legende,  # <-- instruction unique
        legend=dict(orientation="h", y=1.05, x=1, xanchor="right", font=dict(size=10))
    )

# =============================================
# Callback 1 : données instantanées (toutes les 10 s)
# =============================================
@callback(
    [
        Output("graphe-puissances", "figure"),
        Output("graphe-energies", "figure"),
        Output("indicateur-autoconsommation", "figure"),
        Output("indicateur-autonomie", "figure"),
        Output("derniere-mise-a-jour", "children"),
    ],
    Input("intervalle-instantane", "n_intervals")
)
def mettre_a_jour_instantanes(n):
    puissances_installees = obtenir_puissances_installees()
    noms_p, puissances_instantanees,heure_maj = obtenir_puissances_instantanees()
    noms_e, energies = obtenir_energies_instantanees()

    # --- 1. Puissances installées vs instantanées (légende affichée) ---
    fig_puissances = go.Figure()
    fig_puissances.add_trace(go.Bar(
        x=noms_p,
        y=puissances_instantanees,
        name="Instantanée",
        marker_color=[COULEURS["prelevee"], COULEURS["produite"], COULEURS["injectee"], COULEURS["consommee"], COULEURS["consommee"]],
        text=[f"{p:,.0f} W" for p in puissances_instantanees],  # <-- Valeurs affichées
        textposition="outside",  # <-- Au-dessus des barres
        # hovermode = False,
        hovertemplate="<b>%{x}</b><br>Instantanée: %{y} W<extra></extra>"
    ))
    fig_puissances.add_trace(go.Bar(
        x = noms_p,
        y = puissances_installees,
        name="Installée",
        marker_color=COULEURS["puissance_installee"],
        hovertemplate="%{x} - %{y} W<extra></extra>"
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
        arrangement="snap",
        node=dict(
            pad=15,
            thickness=20,
            label=noms_e,
            color=[COULEURS["prelevee"], COULEURS["produite"], COULEURS["injectee"], COULEURS["consommee"]],
            line=dict(color=COULEURS["texte"], width=1)
        ),
        link=dict(
            source=sources,
            target=cibles,
            value=valeurs,
            color=COULEURS['puissance_installee'],
            hovertemplate="<b>%{source.label} → %{target.label}</b><br>Énergie: %{value} Wh<extra></extra>"
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

    fig_autoconsommation = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(taux_autoconsommation, 1),
        number=dict(suffix=" %", valueformat=".1f"),
        title=dict(text="Autoconsommation", font=dict(size=13)),
        domain=dict(x=[0, 1], y=[0, 1]),
        gauge=dict(
            axis=dict(range=[0, 100], tickfont=dict(size=9)),
            bar=dict(color=COULEURS["produite"]),      # Orange pâle
            steps=[
                dict(range=[0, 50], color="rgba(231, 76, 60, 0.15)"),   # Rouge pâle : faible
                dict(range=[50, 100], color="rgba(46, 204, 113, 0.15)") # Vert pâle : bon
            ],
            threshold=dict(line=dict(color=COULEURS["texte"], width=2), value=taux_autoconsommation)
        )
    ))
    fig_autoconsommation.update_layout(
        height=HAUTEUR_HAUT * 4, margin=dict(t=40, b=10, l=25, r=25),
        paper_bgcolor=COULEURS["fond_axes"],
        font=dict(family="Segoe UI, sans-serif", size=12, color=COULEURS["texte"])
    )

    # --- Taux d'autonomie ---
    taux_autonomie = 0.0
    if (energies[3] > 0):
        taux_autonomie = energie_autoconsommee / energies[3] * 100

    fig_autonomie = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(taux_autonomie, 1),
        number=dict(suffix=" %", valueformat=".1f"),
        title=dict(text="Autonomie", font=dict(size=13)),
        domain=dict(x=[0, 1], y=[0, 1]),
        gauge=dict(
            axis=dict(range=[0, 100], tickfont=dict(size=9)),
            bar=dict(color=COULEURS["consommee"]),  # Rouge
            steps=[
                dict(range=[0, 50], color="rgba(231, 76, 60, 0.15)"),
                dict(range=[50, 100], color="rgba(46, 204, 113, 0.15)")
            ],
            threshold=dict(line=dict(color=COULEURS["texte"], width=2), value=taux_autonomie)
        )
    ))
    fig_autonomie.update_layout(
        height=HAUTEUR_HAUT * 4, margin=dict(t=40, b=10, l=25, r=25),
        paper_bgcolor=COULEURS["fond_axes"],
        font=dict(family="Segoe UI, sans-serif", size=12, color=COULEURS["texte"])
    )


    derniere_maj = f"Dernière mise à jour (données : {heure_maj})"
    return fig_puissances, fig_energies, fig_autoconsommation, fig_autonomie, derniere_maj

# =============================================
# Callback 2 : graphe inférieur (toutes les 15 min)
# =============================================
@callback(
    Output("graphe-energie-eau-chaude", "figure"),
    Input("intervalle-prevision", "n_intervals")
)
def mettre_a_jour_prevision(n):
    puissances_installees = obtenir_puissances_installees()
    energie_estimee = obtenir_energie_estimee()
    planification_eau_chaude = obtenir_planification_eau_chaude()

    # Échelle de l'énergie estimée :
    # puissance installée de l'onduleur × période d'échantillonnage (0,25 h)
    puissance_onduleur = puissances_installees[1]
    energie_max_estimee = puissance_onduleur * PERIODE_ESTIMATION_H
    # Petite marge de 10 % au-dessus du maximum théorique
    plage_energie = [0, energie_max_estimee * 1.1] if energie_max_estimee > 0 else None

    fig_combine = go.Figure()

    if energie_estimee:
        fig_combine.add_trace(go.Bar(
            x=[d["horodatage"] for d in energie_estimee],
            y=[d["energie"] for d in energie_estimee],
            name="Énergie estimée (Wh)",
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
        barmode='relative',
        **mise_en_page_combine)

    if not energie_estimee and not planification_eau_chaude:
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