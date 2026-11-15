#!/bin/bash
# .claude/hooks/ui-commandes.sh — hook PreToolUse du sous-agent verificateur-ui.
# N'autorise que les commandes de test de l'interface ; tout le reste est bloqué (code 2).
command -v jq >/dev/null 2>&1 || { echo "jq introuvable : brew install jq" >&2; exit 2; }

COMMAND=$(jq -r '.tool_input.command // empty')

# Un seul enchaînement autorisé : « cd web && ». Aucun autre opérateur (;, |, &&, $(, `).
CMD="${COMMAND#cd web && }"
case "$CMD" in
  *';'*|*'|'*|*'&&'*|*'$('*|*'`'*|*'>'*)
    echo "Bloqué : une seule commande de test, sans enchaînement ni redirection." >&2; exit 2 ;;
esac

case "$CMD" in
  "npm run "*|"npm --prefix web run "*|"npx playwright "*) exit 0 ;;
  *) echo "Bloqué : verificateur-ui ne lance que npm run …, npm --prefix web run … ou npx playwright …" >&2; exit 2 ;;
esac
