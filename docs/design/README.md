# Pistes visuelles — ce que l'application en prend

Source : canevas « Zodiaque à 13 signes — pistes visuelles » (8 planches, claude.ai, propriétaire Micky), relu le 15/11/2026. Les planches fixent un ton ; les exigences viennent du PRD. **Quand une planche contredit le PRD, le PRD l'emporte.**

Ordre de priorité : 1. PRD v0.4 (`docs/prd/`) ; 2. planches 6 et 7, qui montrent des écrans ; 3. planches 1 à 5, qui fixent une identité.

## Planches à déposer
Micky exporte chaque planche en PNG dans `docs/design/planches/` sous ces noms :

| Fichier | Planche | Format |
| --- | --- | --- |
| `01-observatoire.png` | 1 · Observatoire | 1080 × 1350 |
| `02-suisse.png` | 2 · Suisse — Règle vs territoires | 1080 × 1350 |
| `03-pedagogique.png` | 3 · Pédagogique — Quatre niveaux | 1080 × 1350 |
| `04-carte-serpentaire.png` | 4 · Carte de signe — Serpentaire | 750 × 1050 |
| `05-banniere.png` | 5 · Bannière | 1200 × 630 |
| `06-formulaire.png` | 6 · Interface — formulaire de naissance | 1280 × 1180 |
| `07-roue-europeenne.png` | 7 · Roue européenne — modèle B13 | 1440 × 1240 |
| `08-astrocartographie.png` | 8 · Astrocartographie (hors périmètre) | 1440 × 900 |

## Répartition par surface
| Surface de l'application | Piste | Planche | Exigences |
| --- | --- | --- | --- |
| Thème par défaut (clair) : saisie, roue, tableaux | Roue européenne | 7, puis 6 pour la composition du formulaire | FR-01 à FR-11 |
| Mode sombre de l'explorateur | Observatoire | 1 | FR-10, FR-11 |
| Badges de statut, premier écran d'explication | Pédagogique | 3 | FR-18 |
| Fiches de signe et partage | Carte de signe | 4 | FR-15 |
| Comparateur témoin 12 × 30° / B13, contenus de lancement | Suisse | 2 | FR-14 |
| Bannière | — | 5 | Contenus de lancement seulement |
| Astrocartographie | — | 8 | Hors périmètre du PRD : backlog |

Valeurs relevées dans le code source des planches : `jetons.md`.

## Écarts à corriger
| # | Sur la planche | Où | Dans l'application |
| --- | --- | --- | --- |
| 1 | Le Serpentaire est le seul secteur coloré (ambre, rouge, or) | 1, 2, 5 | Même traitement que les 12 autres ; l'accent de couleur marque la sélection. L'accent reste permis dans les contenus de lancement |
| 2 | Pictogramme dessiné (bâton et serpent) | 4, 5 | Glyphe ⛎ (U+26CE) monochrome, repli « Oph » ; ni caducée ni emblème |
| 3 | Identité « Le savoir tenu avec responsabilité » | 4 | « La maîtrise révisable », identité retenue par l'étude (`docs/prd/02-serpentaire.md` § 5) |
| 4 | Le niveau 3 cite « éléments, maîtrises » | 3 | « Fonctions symboliques, ressources, tensions » |
| 5 | Question d'introspection en Cormorant Garamond | 4 | Sérif réservé au titre de la fiche ; valeurs et textes longs en sans sérif |
| 6 | Le témoin à 12 secteurs est appelé « tropical » | 1, 6, 7 | « Témoin 12 × 30° », jamais « thème tropical » |
| 7 | Formulaire sombre, roue claire | 6, 7 | Thème clair de la planche 7 par défaut ; Observatoire en mode sombre |
| 8 | Largeurs fictives (Serpentaire 248°–267°, « FICTIF ») | Toutes | Jamais dans le code : la roue est calculée depuis `generes/frontieres.csv` via l'API |
| 9 | Astrocartographie de l'Ascendant B | 8 | Hors périmètre : backlog |
| 10 | Textes de la carte (motif, ressources, tensions) | 4 | Illustration seulement : le contenu des fiches vient du PRD, transcrit dans `referentiel/` |
| 11 | Polices chargées depuis Google Fonts | Toutes | Polices auto-hébergées (Fontsource) : aucun appel à un tiers |
