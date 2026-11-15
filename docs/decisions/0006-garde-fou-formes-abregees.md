# 0006 · Le garde-fou reconnaît les formes abrégées, collées et en autre casse

- Date : 15/11/2026
- Statut : acceptée (Micky) ; rédigée par Claude à sa demande, hook appliqué par Micky le 15/11/2026

## Contexte
La phase 1 éprouve chaque garde-fou par une tentative de contournement. Les dix formes de T4, T5 et T6 sont bloquées par `.claude/hooks/garde-fou.sh`. Un examen hors ligne (commandes données au script sur son entrée, jamais exécutées) a montré que le hook laisse passer trois familles que le plan de test ne listait pas :

1. **Option collée à autre chose qu'une espace.** Le motif exigeait une espace ou une fin de ligne après `--no-verify` ou `-n`. Passent donc `bash -c 'git commit -m x --no-verify'`, `git commit -m x --no-verify; echo fait`, `(git commit -m x -n)`. C'est la forme exacte de T5, placée en fin de commande.
2. **Option longue abrégée.** Git accepte tout préfixe non ambigu : `git commit --no-veri` et `--no-verif` valent `--no-verify`. Vérifié le 15/11/2026 avec Git 2.39.0 dans un dépôt jetable vide, en `--dry-run` : `--no-veri` est acceptée ; `--no-ver` et `--no-v` sont rejetées comme ambiguës (`--no-verbose` ou `--no-verify`).
3. **Clé de configuration en autre casse.** Git ignore la casse des clés : `git -c core.hookspath=…` et `CORE.HOOKSPATH` valent `core.hooksPath`. Vérifié de même : la clé relue est `core.hookspath`.

Ce qui restait derrière le hook pour ces formes : le classifieur du mode auto (non garanti) et la CI au moment de l'envoi (T14, étape 2). Le commit local, lui, passait sans `scripts/verifier.sh`.

Contrôle fait et écarté : `git push --forc` n'est pas un trou. Git la rejette comme ambiguë (`--force-with-lease` ou `--force-if-includes`), et toute abréviation plus longue contient `--force`, déjà bloqué.

## Décision
Trois changements dans `.claude/hooks/garde-fou.sh`, préparés dans `tmp-test/garde-fou.sh` puis copiés par Micky :
- le motif du contournement reconnaît `--no-v` suivi de n'importe quoi, sans exiger d'espace après ;
- une option courte contenant `n` se termine à la fin de la ligne ou à tout caractère qui ne la prolonge pas (espace, guillemet, `;`, `&`, `)`) ;
- la chaîne `hookspath` est cherchée sans tenir compte de la casse, où qu'elle soit dans la commande (option `-c`, `git config`, variables `GIT_CONFIG_KEY_n`).

Les motifs de suppression récursive, d'envoi forcé, de script téléchargé et de `sudo` ne changent pas. `settings.json` ne change pas : ses règles `deny` visent les formes exactes, le hook porte la garantie.

## Ce que la décision ne change pas
- **Faux positifs gardés.** Toute commande qui cite `.git/hooks` reste bloquée, même une lecture ; une commande qui contient `git`, puis le mot `commit`, puis une option courte avec `n` aussi (un `git log` filtré sur « commit » suivi de `tail -n 3`). Les distinguer d'une écriture demanderait de lire les guillemets du shell, ce qu'une expression régulière ne fait pas ; tout assouplissement essayé ouvrait un faux négatif. Pour lire, Claude passe par les outils Read et Grep ; pour écrire un texte qui cite ces formes, par l'outil d'édition.
- **Nouveaux faux positifs, rares** : `--no-verbose` et `--no-verify-signatures` sur `commit`, `merge`, `push`, `am` et `rebase`.
- **Limites acceptées**, couvertes par une autre couche (décision 0003) : `find … -delete` ; `cd .git` suivi d'une commande dans `hooks/` (sandbox, à observer : voir ci-dessous) ; commande passée par une variable ; plomberie Git qui crée un commit sans lancer de hook (`git commit-tree`, `git update-ref`), rattrapée par la CI à l'envoi.

## Conséquences
- Micky compare et applique, dans son terminal :
  `diff -u .claude/hooks/garde-fou.sh tmp-test/garde-fou.sh` puis `cp tmp-test/garde-fou.sh .claude/hooks/garde-fou.sh`.
- Contrôle hors ligne rejouable : `bash tmp-test/jouer-cas.sh "$PWD/.claude/hooks/garde-fou.sh" tmp-test/cas-garde-fou.txt` (46 commandes : 14 écarts avec le hook actuel, 0 avec le hook proposé).
- T5 est rejoué par Claude avec les formes nouvelles, pour de vrai cette fois : chacune doit revenir « Bloqué par .claude/hooks/garde-fou.sh ».
- Point laissé à Micky : la protection de `.git/hooks` par le sandbox n'a jamais été observée, le hook ayant toujours arrêté la commande avant. Un essai inoffensif (`cd .git` puis `touch hooks/essai`) le dirait ; Claude ne le lance pas sans accord.
- Le fichier de cas mérite peut-être une place durable dans le dépôt plutôt que dans `tmp-test/` ; à décider en phase 2, quand `tests/` existera.
