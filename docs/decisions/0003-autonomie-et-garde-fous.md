# 0003 · Mode auto, borné par des garde-fous posés et testés d'abord

- Date : 15/11/2026
- Statut : acceptée (Micky)

## Contexte
Micky veut faire confiance à Claude Code (mode auto) sur un projet où l'erreur la plus coûteuse est silencieuse : une frontière ou une largeur fausse, un texte interprétatif inventé, une donnée de naissance réelle. `CLAUDE.md` oriente Claude sans le contraindre.

## Décision
- **Mode auto** réglé par Micky dans `~/.claude/settings.json` (un dépôt ne peut pas s'accorder ce mode) ; `bypassPermissions` désactivé dans le projet.
- **Ce qui est garanti l'est par un garde-fou**, testé par une tentative de contournement avant toute écriture importante :
  - règles `deny` : secrets illisibles ; PRD, portes, réglages, hooks, contrôles et CI non modifiables par Claude ;
  - règles `ask` (actives même en mode auto) : envoi vers GitHub, nouvelle dépendance, nouvelle source de données, édition manuelle de `generes/`, sortie du sandbox ;
  - hook `PreToolUse` : suppressions récursives, envois forcés, contournement du hook Git, `curl | sh`, `sudo` ;
  - sandbox macOS : réseau limité aux sources déclarées, écriture limitée au dépôt et aux caches ;
  - hook Git `pre-commit` et GitHub Actions : `scripts/verifier.sh` bloque un commit, même fait à la main.
- **`generes/` est protégé par reproductibilité**, pas par un refus d'écriture : un `deny Edit` s'étendrait aux scripts sous sandbox. `verify` régénère les frontières et compare ; les empreintes du manifeste sont contrôlées.
- **Franchir une porte (G1, G2, G3) est une décision humaine** : `docs/portes.toml` n'est modifiable que par Micky.

## Conséquences
- Les règles d'autorisation s'ouvrent après les tests, jamais l'inverse.
- Toute évolution d'un garde-fou passe par Micky, avec une nouvelle décision datée.
- Limites connues du hook (commande passée par une variable, `find -delete`) : couvertes par le sandbox et le contrôle au commit.
