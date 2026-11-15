---
paths:
  - "web/**"
---

# Interface React

Sources : `docs/design/README.md` (répartition des pistes, écarts corrigés) et `docs/design/jetons.md` (valeurs relevées). Exigences : `docs/prd/00-prd.md`, § 5 à 7.

- **Thèmes** : clair par défaut, d'après la planche 7 ; sombre d'après la piste Observatoire. Toutes les couleurs et polices passent par les jetons CSS de `web/src/styles/jetons.css` ; aucune valeur de couleur en dur dans un composant.
- **Pistes par surface** : badges de statut et premier écran d'explication selon la piste Pédagogique ; fiches de signe selon la piste Carte (sérif réservé au titre de fiche) ; comparateur selon la piste Suisse.
- **Statut** sur chaque vue (FR-18) : réel vérifié, candidat ou démonstrateur synthétique, plus le niveau mesure, convention ou interprétation ; tout texte interprétatif porte « proposition symbolique ». Un test de rendu le vérifie pour chaque route.
- **Vocabulaire** : « témoin 12 × 30° », jamais « tropical » ; les différences du comparateur portent leur cause D, S, Y ou C (glossaire du PRD).
- **Accessibilité** : WCAG 2.2 AA ; contraste vérifié par axe-core dans les tests Playwright ; information jamais portée par la seule couleur ; tout au clavier ; largeur minimale 360 px.
- **Polices auto-hébergées** via Fontsource : aucun appel à un service de polices ni à aucun tiers à l'exécution. Pile des glyphes : `"Noto Sans Symbols", "Noto Sans Symbols 2"` avant toute police emoji (⛎ et les 12 autres glyphes sont dans Noto Sans Symbols, ☉ dans Symbols 2) ; repli « Oph » si le glyphe manque.
- **Saisie** (FR-01, FR-03 à FR-05) : heure inexistante → message bloquant ; heure ambiguë → deux scénarios ; heure inconnue → « carte de référence à midi », sans Ascendant ni maisons.
- **Lieu** : recherche dans GeoNames (localités de plus de 15 000 habitants). Lieu absent → saisie de la latitude et de la longitude, fuseau déduit par timezonefinder et affiché pour confirmation ; jamais la ville la plus proche en silence, car l'Ascendant et les maisons dépendent des coordonnées.
- **Attribution** GeoNames (CC BY 4.0) visible là où le lieu est saisi.
- **Scripts npm obligatoires** dans `web/package.json` : `lint`, `typecheck`, `test` (Vitest, sans mode veille), `e2e` (Playwright + axe-core). `scripts/verifier.sh` les appelle.
