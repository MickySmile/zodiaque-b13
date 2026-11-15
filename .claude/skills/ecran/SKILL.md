---
name: ecran
description: Construit un écran de l'interface React à partir d'une planche des pistes visuelles, avec les jetons du thème et les écarts au PRD corrigés. À utiliser pour « fais l'écran de saisie », « monte la fiche de signe », « construis le comparateur ».
argument-hint: nom de l'écran
---

# Écran depuis une planche

1. Repère dans `docs/design/README.md` la planche et la piste de l'écran `$ARGUMENTS`, les exigences FR qu'il sert et les écarts à corriger. Ouvre la planche (`docs/design/planches/*.png`) avec Read pour la voir.
2. Reprends la composition et la hiérarchie de la planche ; prends couleurs, polices et espacements dans `web/src/styles/jetons.css` (créé depuis `docs/design/jetons.md`), jamais en dur.
3. N'importe aucune valeur astronomique de la planche : les données viennent de l'API ; en développement, d'un jeu d'essai marqué `"synthetic": true` et affiché « démonstrateur synthétique ».
4. Écris les tests Vitest du composant (badge de statut présent, libellés, états vides et d'erreur), puis le composant, puis un test Playwright de l'écran avec contrôle axe-core.
5. Lance `scripts/verifier.sh --complet` via la skill `verify`.
6. Délègue au sous-agent `verificateur-ui` la capture à 360 px et 1 280 px et le contrôle clavier ; compare sa capture à la planche et liste les différences voulues (écarts corrigés) et non voulues.
