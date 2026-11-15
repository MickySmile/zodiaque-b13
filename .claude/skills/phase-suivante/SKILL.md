---
name: phase-suivante
description: Avance d'une phase dans docs/PLAN.md, lance son contrôle et s'arrête pour validation.
disable-model-invocation: true
---

# Phase suivante

1. Lis `docs/PLAN.md` et repère la première phase non cochée. Lis aussi les sections du PRD et les fichiers que la phase cite.
2. Annonce en trois lignes son objectif, ses actions et son critère de passage. Si une action est marquée « Micky », donne-lui la commande exacte et attends sa confirmation.
3. Réalise les actions, dans l'ordre. Pour une exigence FR-xx, suis la skill `exigence` ; pour une fiche, `fiche-signe` ; pour un écran, `ecran`.
4. Lance le contrôle prévu, puis la skill `verify`, et compare le résultat au critère de passage.
5. Si le critère est atteint : coche la phase, ajoute une ligne au journal de `docs/PLAN.md` (date, phase, résultat, écarts), puis fais un commit en français `phase n : <objectif>`. Sinon : laisse la phase ouverte, note l'écart au journal, ne commite pas de code cassé.
6. Résume en cinq lignes : fait, contrôle, résultat, écarts, phase suivante. Arrête-toi là, même s'il reste du temps.
