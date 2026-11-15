"""Noms d'affichage des 13 signes : nom français et glyphe Unicode.

Référence : annexe technique § F (« Données de la roue » : id, nom, glyphe) et § H (glyphe du
Serpentaire : U+26CE, sans présentation emoji). Les 13 signes ont la même forme ; l'ordre et les
bornes ne sont pas ici : ils viennent du découpage calculé.

Abréviation : l'identifiant du signe lui-même, c'est-à-dire le code UAI de sa constellation
(Ari … Oph … Psc), choisi par Micky le 15/11/2026. Les abréviations françaises des planches
(« Ser » pour le Serpentaire) sont écartées : « Ser » est le code UAI du Serpent, une autre
constellation (écart 12 de docs/design/README.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from moteur.boundaries import EXPECTED_ORDER


@dataclass(frozen=True)
class SignLabel:
    name: str
    glyph: str  # un seul caractère ; l'interface ajoute U+FE0E pour refuser la forme emoji


SIGN_LABELS: dict[str, SignLabel] = {
    "Ari": SignLabel("Bélier", "\u2648"),
    "Tau": SignLabel("Taureau", "\u2649"),
    "Gem": SignLabel("Gémeaux", "\u264a"),
    "Cnc": SignLabel("Cancer", "\u264b"),
    "Leo": SignLabel("Lion", "\u264c"),
    "Vir": SignLabel("Vierge", "\u264d"),
    "Lib": SignLabel("Balance", "\u264e"),
    "Sco": SignLabel("Scorpion", "\u264f"),
    "Oph": SignLabel("Serpentaire", "\u26ce"),
    "Sgr": SignLabel("Sagittaire", "\u2650"),
    "Cap": SignLabel("Capricorne", "\u2651"),
    "Aqr": SignLabel("Verseau", "\u2652"),
    "Psc": SignLabel("Poissons", "\u2653"),
}

if set(SIGN_LABELS) != set(EXPECTED_ORDER):
    raise RuntimeError("le catalogue des noms ne couvre pas exactement les 13 signes du moteur")
