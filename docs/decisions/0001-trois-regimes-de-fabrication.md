# 0001 · Trois régimes de fabrication, un seul traitement pour les 13 signes

- Date : 15/11/2026
- Statut : acceptée (Micky)

## Contexte
Le code Python et le prototype de l'étude ne sont pas disponibles. Les bibliothèques d'astrologie existantes supposent un cercle de 12 × 30°, des éléments, des maîtrises et un signe opposé par le nom ; l'onglet « Conséquences sur les autres signes » désactive tout cela pour les 13 signes. Le Serpentaire déplace les 13 frontières : ce n'est pas une tranche ajoutée.

## Décision
1. **Mesure : télécharger tel quel.** Skyfield (avec sa grille des frontières UAI), éphéméride DE440s, données IERS, tzdata, timezonefinder, GeoNames, NumPy et SciPy. Rien n'est modifié ; versions et SHA-256 vont au manifeste.
2. **Convention B13 : écrire sur ces briques**, dans `moteur/` : frontières, classement, maisons, aspects, opposition par arcs, témoin 12 × 30°. Aucune bibliothèque d'astrologie.
3. **Interprétation : transcrire, jamais générer.** Les 13 fiches (12 révisées et le Serpentaire) sont recopiées du PRD dans `referentiel/`, avec leur provenance.
4. Les 13 signes passent par les mêmes fonctions et le même schéma ; les tests couvrent un thème sans placement en Serpentaire (cas A).

## Conséquences
- `scripts/verifications/contenus.py` refuse les dépendances d'astrologie et les listes d'angles codées en dur.
- Toute donnée téléchargée est déclarée dans `donnees/sources.toml` ; son empreinte est contrôlée à chaque commit.
- Un champ de fiche sans texte dans le PRD reste vide (`status: missing`) jusqu'à la relecture du rédacteur du référentiel.
