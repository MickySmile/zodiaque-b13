---
name: frontieres
description: Construit les 13 frontières du modèle B, les compare à une seconde chaîne (JPL Horizons) et prépare le rapport de la porte G1.
disable-model-invocation: true
---

# Frontières B13 et dossier de la porte G1

Références : `docs/prd/01-annexe-technique.md` § B, C, D1 et J ; règle `.claude/rules/moteur.md`.

1. **Construire** : `uv run python scripts/construire_frontieres.py` écrit `generes/frontieres.csv` (signe, début, fin, largeur en degrés décimaux, double précision) et met à jour `generes/manifest.json` (identifiant du modèle, matrice R, versions, SHA-256 de `constellations.npz`, empreinte de chaque fichier, état des portes recopié de `docs/portes.toml`). Option `--verifier` : régénère dans un dossier temporaire et compare octet par octet, sans rien écrire.
2. **Contrôler** : 13 intervalles, ordre attendu, Σ = 360° à 10⁻⁹° près, ni lacune ni chevauchement ; en cas d'échec, arrêt sans écrire.
3. **Comparer** : `uv run python scripts/comparer_horizons.py` interroge l'API publique JPL Horizons (ssd.jpl.nasa.gov) pour des vecteurs transformés par R, archive chaque réponse brute dans `tests/fixtures/horizons/` avec sa date, puis rejoue la comparaison hors ligne. La colonne 31 d'Horizons (longitude apparente de date) n'est pas comparable telle quelle.
4. **Rapport** : écris `docs/portes/g1-rapport.md` : méthode, versions, tableau des 13 frontières (valeur, écart à la seconde chaîne, tolérance), limites connues (arrondi des données de Roman, réalisation Skyfield / Roman et non Delporte exacte), questions pour l'expert.
5. Ne touche jamais `docs/portes.toml` : franchir G1 est une décision de Micky après validation par l'expert (Q5).
6. Lance `verify`, puis rends les 13 largeurs, l'écart maximal et le chemin du rapport. Arrête-toi.
