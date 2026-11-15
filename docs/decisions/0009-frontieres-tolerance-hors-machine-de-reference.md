# 0009 · Hors de la machine de référence, les frontières se comparent à 10⁻¹¹° près

- Date : 15/11/2026
- Statut : acceptée (Micky)

## Contexte
`scripts/verifier.sh` (hook Git et intégration continue) lance `scripts/construire_frontieres.py --verifier`, qui régénère les frontières et les compare à `generes/frontieres.csv`. La skill `frontieres` demandait une comparaison octet par octet.

Constat du 15/11/2026, sur la branche d'essai `essai-phase-4` : sous Linux (Python 3.12.3), le fichier régénéré diffère de celui produit sur le Mac de Micky (Darwin x86_64, Python 3.12.16). L'étape « Frontières régénérées à l'identique » et le test qui la rejoue échouent ; tout le reste passe. La clé `model` du manifeste, qui porte la matrice R et l'écart de la somme des largeurs, est identique sur les deux machines : seul le dernier chiffre de certaines bornes change.

La cause est connue : les fonctions trigonométriques (`sin`, `cos`, `atan2`, `acos`) et l'algèbre matricielle ne sont pas arrondies de la même façon par toutes les bibliothèques système. Chaque borne est écrite avec ses 17 chiffres significatifs, donc un écart d'un seul bit change le fichier. `relecteur-astro` avait signalé ce risque avant le premier envoi.

## Décision
- **Sur la machine de référence**, celle que le manifeste note dans `versions.platform`, la comparaison reste **octet par octet**. Un seul chiffre de différence y est refusé.
- **Sur toute autre machine**, les deux fichiers sont comparés nombre par nombre : mêmes signes dans le même ordre, exigés exactement ; chaque début, fin et largeur à **10⁻¹¹° près**. L'écart maximal observé est affiché à chaque vérification. L'empreinte du fichier inscrite au manifeste reste celle de la machine de référence.
- Le reste du manifeste (modèle, matrice R, portes, statut des données, versions de Skyfield et de NumPy) reste comparé tel quel, partout. Seules la version corrective de Python et la plateforme sont signalées sans être refusées.

La tolérance est déclarée avant d'avoir vu l'écart réel sous Linux. 10⁻¹¹° valent 3,6 × 10⁻⁸ seconde d'arc : c'est cent fois le bruit attendu du dernier chiffre pour un angle de quelques centaines de degrés (10⁻¹³° environ), et très en dessous de tout effet mesurable. Si l'écart observé la dépasse, la vérification échoue et la question revient à Micky.

Voies écartées :
- arrondir les bornes dans le fichier : contraire à la règle « aucun arrondi avant le classement », et un arrondi peut lui aussi basculer d'un côté ou de l'autre ;
- rendre le calcul identique au bit près sur toutes les machines : cela demanderait de remplacer les fonctions mathématiques du système et celles de Skyfield, sans garantie ;
- retirer le contrôle de l'intégration continue : on perdrait le filet contre une édition manuelle de `generes/`.

## Conséquences
- `generes/frontieres.csv` **fait foi**. Le moteur classera un astre en lisant les bornes de ce fichier, jamais en recalculant les frontières : un résultat ne dépendra donc pas de la machine (à faire en phase 5).
- Les fichiers de `generes/` se régénèrent sur la machine de référence. Si elle change, ou si une mise à jour du système y déplace un dernier chiffre, la vérification stricte le signalera : il faudra régénérer et commiter.
- La phrase « compare octet par octet » de la skill `frontieres` ne décrit plus tout le comportement ; la skill est un fichier protégé, à mettre à jour par Micky s'il le souhaite.
- La tolérance ne dit rien de la justesse des frontières : elle ne concerne que la répétabilité du calcul. La précision réelle d'une frontière reste bornée par la décision 0008.
