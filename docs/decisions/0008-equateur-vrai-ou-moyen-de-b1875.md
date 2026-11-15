# 0008 · Écart à trancher : équateur vrai ou moyen de B1875 pour interroger la grille

- Date : 15/11/2026
- Statut : **ouverte**. Écart signalé par Claude pendant la phase 4 ; à trancher par Micky après l'avis de l'expert (question Q5 du PRD). Aucun changement de calcul n'est fait en attendant.

## Contexte
Les frontières des constellations sont des lignes d'ascension droite et de déclinaison constantes à l'équinoxe B1875. Pour savoir dans quelle constellation tombe une direction, il faut l'exprimer dans le repère équatorial de cette époque.

Le PRD fixe la façon de le faire (annexe technique, § B, « Coordonnées sources ») : grille de Skyfield « interrogée par `radec(epoch=B1875)` », qui « utilise la matrice t.M de Skyfield (précession, nutation, biais) ». La règle `.claude/rules/moteur.md` reprend cette convention. Le moteur la suit : `moteur/boundaries.py` calcule ses intersections avec `Time.M` et identifie les constellations par la fonction de Skyfield.

`Time.M` contient la nutation : elle donne l'équateur **vrai** de l'époque, pas l'équateur **moyen**. À B1875, les deux diffèrent d'une rotation de 10,07 secondes d'arc.

## Constat
Calcul du 15/11/2026 : mêmes lignes de la grille, mêmes équations, mais matrice de précession seule (`Time.P` et biais de repère) à la place de `Time.M`. Il se rejoue par `uv run python scripts/construire_frontieres.py --sensibilite` (fonction `mean_equator_shifts` du moteur, testée). Déplacement de chaque frontière par rapport aux valeurs de `generes/frontieres.csv` :

- les onze frontières portées par une ligne d'ascension droite reculent de 4,4″ à 7,8″ (0,0012° à 0,0022°) ;
- le début des Poissons, porté par une ligne de déclinaison, recule de 9,4″ (0,0026°) ;
- le début du Scorpion, porté par une ligne de déclinaison, avance de 24,8″ (0,0069°).

À titre d'ordre de grandeur, le Soleil parcourt 0,0069° en dix minutes environ : près de cette frontière, la convention retenue peut changer le signe solaire d'une naissance dont l'heure tombe dans cette fenêtre.

Le tableau complet, frontière par frontière, est dans le rapport G1 (section 7, limite 1). C'est une mesure de sensibilité, pas un second jeu de frontières : les constellations ne sont pas réidentifiées avec cette variante. `relecteur-astro` a relevé le même écart de son côté, sans le chiffrer.

## Ce qui n'est pas établi
Laquelle des deux conventions est la bonne. Le tracé de Delporte est défini par rapport à l'équinoxe 1875,0, ce qui s'entend d'ordinaire comme l'équateur et l'équinoxe moyens ; je ne l'ai pas vérifié sur une source primaire. Skyfield, que le PRD prend pour référence, applique la nutation.

## Options
- **A. Garder la convention du PRD** (équateur vrai, fonction de Skyfield telle quelle). Rien ne change ; le rapport G1 mentionne l'écart et son ampleur.
- **B. Passer à l'équateur moyen.** Le moteur n'utiliserait plus `radec(epoch=B1875)` tel quel : il lirait la grille de Skyfield avec sa propre matrice. Cela demande une révision de l'annexe B du PRD par Micky, un nouvel identifiant de modèle (les 13 frontières changent), et la régénération de `generes/`.

## Conséquences immédiates
- Le calcul reste celui du PRD. `generes/frontieres.csv` n'est pas modifié.
- Le rapport `docs/portes/g1-rapport.md` pose la question à l'expert (section 8, question 2) et renvoie à cette décision.
- Tant que la question est ouverte, la précision annoncée d'une frontière ne peut pas être meilleure que cet écart : de l'ordre de 0,002° en général, 0,007° pour le début du Scorpion.
