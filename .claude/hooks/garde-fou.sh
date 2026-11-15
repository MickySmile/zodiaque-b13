#!/bin/bash
# .claude/hooks/garde-fou.sh — hook PreToolUse sur Bash (gabarit G7, étendu).
# Bloque, y compris sous les formes /bin/rm, bash -c '…', 'rm' ou git -C . … :
#   1. les suppressions récursives ;
#   2. les envois forcés vers le dépôt distant (l'envoi simple reste soumis à la règle ask) ;
#   3. le contournement du hook Git pre-commit (--no-verify, -n, SKIP=, core.hooksPath, .git/hooks) ;
#   4. l'exécution directe d'un script téléchargé (curl … | sh) ;
#   5. sudo.
# Code de sortie 2 : l'appel est bloqué et le message revient à Claude, même si une règle allow correspond.

# Sans jq, le hook ne peut pas lire la commande : il bloque plutôt que de tout laisser passer.
command -v jq >/dev/null 2>&1 || { echo "Garde-fou inactif : jq est introuvable. Installe jq (brew install jq), puis relance." >&2; exit 2; }

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$COMMAND" ] && exit 0

# Début de mot : début de ligne ou caractère qui n'est ni lettre, ni chiffre, ni « _ », ni « / » final d'un chemin.
B='(^|[^[:alnum:]_.-])'
Q="[\"']?"

RM_RE="${B}rm${Q}[[:space:]](.*[[:space:]])?${Q}(-[[:alpha:]]*[rR]|--recursive)"
FORCE_PUSH_RE="${B}git${Q}[[:space:]](.*[[:space:]])?${Q}push${Q}[[:space:]](.*[[:space:]])?(--force|--force-with-lease|-[[:alpha:]]*f|\+[[:alnum:]_/.-]+)"
NO_VERIFY_RE="${B}git${Q}[[:space:]](.*[[:space:]])?${Q}(commit|merge|push|am|rebase)${Q}[[:space:]](.*[[:space:]])?(--no-verify|-[[:alpha:]]*n[[:alpha:]]*)([[:space:]]|$)"
HOOKS_RE="(core\.hooksPath|\.git/hooks|pre-commit${Q}[[:space:]]+uninstall|(^|[[:space:];&|])SKIP=|PRE_COMMIT_ALLOW_NO_CONFIG)"
PIPE_SH_RE="${B}(curl|wget)${Q}[[:space:]].*\|[[:space:]]*(sudo[[:space:]]+)?((ba|z|da)?sh|python3?|node)([[:space:]]|$)"
SUDO_RE="${B}sudo${Q}([[:space:]]|$)"

bloque() { echo "Bloqué par .claude/hooks/garde-fou.sh : $1" >&2; exit 2; }

printf '%s\n' "$COMMAND" | grep -Eq "$RM_RE" && bloque "suppression récursive interdite dans ce dépôt. Supprime fichier par fichier, ou demande à Micky."
printf '%s\n' "$COMMAND" | grep -Eq "$FORCE_PUSH_RE" && bloque "envoi forcé interdit. Micky gère l'historique distant."
printf '%s\n' "$COMMAND" | grep -Eq "$NO_VERIFY_RE" && bloque "le hook pre-commit ne se contourne pas. Corrige ce que scripts/verifier.sh signale."
printf '%s\n' "$COMMAND" | grep -Eq "$HOOKS_RE" && bloque "le hook Git pre-commit et sa configuration ne se modifient pas depuis Claude Code."
printf '%s\n' "$COMMAND" | grep -Eq "$PIPE_SH_RE" && bloque "pas d'exécution directe d'un script téléchargé. Passe par scripts/telecharger.py et donnees/sources.toml."
printf '%s\n' "$COMMAND" | grep -Eq "$SUDO_RE" && bloque "sudo interdit. Demande à Micky de lancer la commande lui-même."

exit 0
