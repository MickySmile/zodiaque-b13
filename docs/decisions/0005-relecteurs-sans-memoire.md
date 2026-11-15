# 0005 · Les sous-agents relecteurs n'ont pas de mémoire de projet

- Date : 15/11/2026
- Statut : acceptée (Micky)

## Contexte
Le test T19 de la phase 1 attend que `relecteur-astro` n'ait « aucun outil d'écriture ». Les en-têtes de `relecteur-astro` et de `gardien-contenus` déclarent `tools: Read, Grep, Glob`, mais aussi `memory: project`. Cette ligne fait ajouter par Claude Code les outils Write et Edit, prévus pour le dossier de mémoire de l'agent, sans les limiter à ce dossier. Constat du 15/11/2026 : sollicité pour le test, `relecteur-astro` a modifié un fichier jetable de `tmp-test/` sans hook, sans demande d'accord et sans refus. « Tu ne modifies rien » n'était donc qu'une consigne.

## Décision
- La ligne `memory: project` est retirée de `.claude/agents/relecteur-astro.md` et de `.claude/agents/gardien-contenus.md`. Leurs outils se réduisent à Read, Grep et Glob.
- Un relecteur rend un verdict ; il ne garde pas de notes d'une session à l'autre. Ce qui doit durer s'écrit dans le dépôt, par la session principale : journal de `docs/PLAN.md`, `docs/decisions/`.
- Voie écartée : garder la mémoire et ajouter un hook `PreToolUse` sur Write et Edit qui refuse tout chemin hors du dossier de mémoire. Plus fine, mais c'est un garde-fou de plus à écrire et à éprouver pour un gain faible à ce stade.

## Conséquences
- T19 est rejoué après la modification : aucun des deux relecteurs ne doit disposer de Write ni d'Edit.
- `verificateur-ui` n'est pas concerné : il n'a pas de mémoire, et son hook `ui-commandes.sh` a bloqué `rm` lors du même test.
- Si un besoin de mémoire d'agent apparaît plus tard, il passera par une nouvelle décision et par le hook écarté ci-dessus, testé avant d'être activé.
