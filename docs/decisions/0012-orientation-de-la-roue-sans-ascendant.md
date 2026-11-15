# 0012 · Orientation de la roue quand aucun Ascendant n'est calculé

- Date : 15/11/2026
- Statut : acceptée pour le MVP (Micky, 15/11/2026) ; à revoir à l'ouverture de la V1 (FR-08)

## Contexte
L'annexe technique (§ F, « Données de la roue ») donne au champ `orientation` les valeurs `ascendant_left` et `counterclockwise` : la roue d'un thème place l'Ascendant à gauche. Le MVP « Mon signe B13 » ne calcule que le Soleil : ni Ascendant, ni Milieu du Ciel, ni maisons (FR-08 est en V1, décision 0004). L'annexe (§ H) interdit par ailleurs d'« orienter la roue sur un faux Ascendant quand l'heure est inconnue », et l'annexe (§ J) exige, parmi les contrôles de la roue : « ni angles ni maisons inventés sans heure ».

Les deux consignes ne se contredisent pas, mais l'annexe F ne dit pas quoi faire tant que l'Ascendant n'existe pas. Il faut une valeur, et elle n'est pas dans le PRD.

## Décision
- Au MVP, l'API rend `orientation = {"anchor": "zero_longitude_left", "direction": "counterclockwise"}` : la longitude 0° du repère B est à gauche, les longitudes croissent dans le sens inverse des aiguilles d'une montre.
- La légende de la roue le dit, ainsi que l'absence d'Ascendant : « Aucun Ascendant n'est calculé dans cette version : la roue n'est pas orientée sur lui. »
- Aucun repère ASC, DSC, MC ou IC n'est dessiné ; l'anneau des maisons reste vide.
- Le sens direct de l'annexe F est conservé : seul l'ancrage change.

## Conséquences
- `zero_longitude_left` est une valeur ajoutée au contrat de l'annexe F. À la V1, quand l'Ascendant B sera calculé, `ascendant_left` reviendra pour les thèmes dont l'heure est connue ; `zero_longitude_left` restera le repli pour l'heure inconnue et pour la roue sans naissance.
- Avec 0° à gauche, le signe qui traverse 0° (les Poissons dans le découpage candidat) se trouve à la place qu'occuperait l'Ascendant sur une roue de thème. Ce n'est pas un Ascendant : la légende et l'absence de repère ASC lèvent l'ambiguïté. Si des tests utilisateurs montrent une confusion, mettre 0° à droite ou en haut est un changement d'une ligne dans `web/src/roue/geometrie.ts` et dans l'API.
- Le PRD n'est pas modifié ici ; l'écart est à reporter par Micky à la prochaine révision de l'annexe F.
