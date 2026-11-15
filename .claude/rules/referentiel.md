---
paths:
  - "referentiel/**"
---

# Référentiel symbolique B13 (données YAML)

Sources : `docs/prd/02-serpentaire.md` (§ 5, 6, 11), `docs/prd/03-consequences.md` (§ 3, 5, 7) et `docs/prd/01-annexe-technique.md` (§ I).

- **Transcrire, jamais rédiger** : chaque texte vient mot pour mot d'une fiche du PRD, avec la référence de sa source (fichier et section). Si un champ n'a pas de texte dans le PRD, il reste vide avec `status: missing` ; signale-le, n'écris rien à la place.
- **Un seul schéma pour les 13 fiches** : archétype, ressources, tensions, question d'introspection, règles, provenance. Le Serpentaire n'a ni champ en plus ni champ en moins.
- **Provenance** de chaque règle : `H` (historique), `M` (mythologique) ou `C` (proposition contemporaine), selon le PRD.
- **Catégories héritées inactives** : éléments, modalités, maîtrises, dignités figurent seulement sous `historical_correspondences`, avec `active: false`. Aucun code ne les lit pour classer ou interpréter. `scripts/verifications/contenus.py` refuse ces clés et le vocabulaire interdit hors de ce bloc.
- **Relations entre signes** : déclarées dans le référentiel, jamais déduites de la distance angulaire ni du nom (pas de « signe opposé »).
- **Inférences interdites** : la liste du PRD (§ 11 de l'onglet Serpentaire) est reprise en données, `forbidden_inferences`, et testée.
- **Version** : `referentiel/VERSION` change à chaque modification ; la version va au manifeste.
- Après toute modification, demande la relecture du sous-agent `gardien-contenus`.
