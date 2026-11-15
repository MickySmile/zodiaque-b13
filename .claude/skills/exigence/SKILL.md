---
name: exigence
description: Implémente une exigence FR-xx du PRD de bout en bout — critères d'acceptation transformés en tests d'abord, puis code, puis vérification. À utiliser pour « implémente FR-07 », « fais l'exigence du calendrier ».
argument-hint: FR-xx
---

# Implémenter une exigence

1. Lis la ligne de l'exigence demandée (`$ARGUMENTS`) dans `docs/prd/00-prd.md` § 6, les cas limites du même paragraphe et les sections de l'annexe qui la servent (la mention « Sert : FR-… » les signale).
2. Écris d'abord les tests : un test par critère d'acceptation et par cas limite concerné, nommés `test_fr_xx_<cas>` en Python ou avec `FR-xx` dans le titre Vitest. Lance-les : ils doivent échouer pour la bonne raison.
3. Écris le code minimal qui les fait passer, dans la bonne couche (`moteur/`, `api/` ou `web/`), en respectant les règles ciblées chargées pour ces fichiers.
4. Si un critère est ambigu ou contredit l'annexe, écris l'écart dans `docs/decisions/` (nouveau fichier numéroté) et demande à Micky avant de trancher.
5. Lance la skill `verify`.
6. Compte rendu : critères couverts (liste), fichiers touchés, écarts ouverts.
