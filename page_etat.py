from dash import callback, Output, Input, html

from configuration import (
    POLICE,
    COULEURS_GROUPES,
    COULEUR_GROUPE_DEFAUT,
    COULEURS
)

from services import (
    obtenir_etat_global,
)


#  Rendu générique de l'état global

@callback(
    Output("conteneur-etat-global", "children"),
    Input("intervalle-instantane", "n_intervals")
)
def mettre_a_jour_etat_global(n):
    donnees = obtenir_etat_global()
    return construire_page_etat_global(donnees)


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
