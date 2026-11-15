# Zodiaque B13

Application web qui calcule un thème natal à 13 signes (modèle B : écliptique J2000 fixe × frontières UAI), l'affiche sur une roue proportionnelle et le lit avec le référentiel symbolique B13. Statut : en construction, données « candidates » tant que la porte G1 n'est pas franchie.

## Prérequis (macOS)
- Claude Code 2.1.286 ou plus récent (`claude --version`)
- `jq`, `uv`, Node.js LTS et `pre-commit` : `brew install jq uv node pre-commit`
- Git, et un dépôt GitHub privé pour la CI

## Démarrer
1. Suivre la section « Démarrage » de `docs/PLAN.md` (prérequis, `git init`, `pre-commit install`, premier message), puis avancer phase par phase avec `/phase-suivante`.
2. Une seule commande de contrôle : `scripts/verifier.sh`. Elle tourne avant chaque commit (hook `pre-commit`) et dans GitHub Actions.

## Où trouver quoi
| Dossier | Contenu |
| --- | --- |
| `docs/prd/` | PRD v0.4 et ses trois onglets, en lecture seule |
| `docs/design/` | Planches des pistes visuelles, jetons, écarts avec le PRD |
| `docs/decisions/` | Décisions d'architecture datées |
| `docs/PLAN.md` | Plan de mise en place et journal |
| `moteur/`, `api/`, `web/` | Calcul, API sans état, interface |
| `referentiel/` | Référentiel B13 (13 fiches, règles, provenance) |
| `donnees/` | Sources téléchargées et leurs empreintes |
| `generes/` | Frontières, passages, manifeste : produits par les scripts |

## Données tierces
- Éphéméride JPL DE440s, données IERS, base IANA des fuseaux : voir `donnees/sources.toml`.
- Lieux : GeoNames, licence CC BY 4.0 (attribution affichée dans l'application).
- Frontières des constellations : UAI (Delporte), réalisation Skyfield / Roman 1987, catalogue VI/42.
