# 0004 · Périmètre : la feuille de route du PRD prime sur le tableau des exigences

- Date : 15/11/2026
- Statut : acceptée (Micky, 15/11/2026) ; à revoir si la réponse à Q6 du PRD change

## Contexte
Le tableau des exigences (PRD § 6) ne date pas FR-19 (portrait rédigé) et FR-20 (Chiron, nœud et apogée lunaires) ; la feuille de route (§ 8) les place en V2, après la porte G2. La planche 8 (astrocartographie) n'a pas d'exigence.

## Décision
- **MVP « Mon signe B13 »** : 13 frontières calculées, calendrier annuel du Soleil, signe solaire et incertitude, roue proportionnelle, 13 fiches de signe, badges. Détaillé dans `docs/PLAN.md` jusqu'à la porte G1.
- **V1 « Mon thème B13 »** : esquissée en jalons ; démarre après G1.
- **V2** : portrait rédigé (FR-19), Chiron, nœud et apogée (FR-20), comparaison avec un thème tropical de date ; démarre après G2.
- **Backlog** : astrocartographie, synastrie, transits.

## Conséquences
- Aucun appel à un modèle de langage ni aucune clé d'API avant la V2 ; `.env` reste illisible pour Claude dès maintenant.
- Les exigences FR-19 et FR-20 n'ont pas de test au MVP.
