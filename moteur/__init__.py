"""Moteur de calcul du modèle B : écliptique moyen J2000 fixe × frontières UAI.

Paquet autonome : il ne dépend ni de `api/` ni de `web/`. Les conventions sont dans
`docs/prd/01-annexe-technique.md` (§ B à G) et `.claude/rules/moteur.md`.
"""

__version__ = "0.1.0"
"""Version du moteur : source unique, reprise par l'API et par le manifeste."""

MODEL_ID = "model_b_iau_ecliptic_j2000_v1"
"""Identifiant du modèle de frontières, versionné à part du référentiel symbolique."""

__all__ = ["MODEL_ID", "__version__"]
