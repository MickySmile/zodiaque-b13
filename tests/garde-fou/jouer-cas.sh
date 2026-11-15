#!/bin/bash
# Donne chaque commande du fichier de cas à un hook, sur son entrée standard, sans jamais l'exécuter.
# Usage : bash tests/garde-fou/jouer-cas.sh "$PWD/.claude/hooks/garde-fou.sh" tests/garde-fou/cas.txt
# Format d'une ligne : attendu|commande, avec attendu parmi
#   passe      le hook doit laisser passer
#   bloque     le hook doit bloquer
#   connu-fp   faux positif accepté (lecture bloquée à tort) : doit bloquer
#   connu-fn   limite acceptée (décision 0003 ou 0006) : passe, couverte par une autre couche
# Code de sortie : 0 si tout est conforme, 1 sinon.
HOOK="$1"
CAS="$2"
ECARTS=0
while IFS='|' read -r attendu commande; do
  [ -z "$commande" ] && continue
  jq -n --arg c "$commande" '{tool_name:"Bash",tool_input:{command:$c}}' | "$HOOK" >/dev/null 2>&1
  code=$?
  if [ "$code" -eq 2 ]; then observe="bloque"; else observe="passe"; fi
  case "$attendu" in
    connu-fp) voulu="bloque" ;;
    connu-fn) voulu="passe" ;;
    *) voulu="$attendu" ;;
  esac
  if [ "$observe" = "$voulu" ]; then verdict="ok   "; else verdict="ECART"; ECARTS=$((ECARTS+1)); fi
  printf '%s %-8s observe=%-6s  %s\n' "$verdict" "$attendu" "$observe" "$commande"
done < "$CAS"
echo "Écarts : $ECARTS"
[ "$ECARTS" -eq 0 ]
