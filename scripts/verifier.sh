#!/usr/bin/env bash
# scripts/verifier.sh — point d'entrée unique des contrôles.
# Rejoué par la skill verify (avant chaque commit), le hook Git pre-commit et la CI GitHub Actions.
# Usage : scripts/verifier.sh [--commit | --complet | --ci]
#   --commit  (défaut) contrôles rapides, sans tests de bout en bout
#   --complet ajoute les tests Playwright et d'accessibilité
#   --ci      comme --commit, sans les contrôles qui exigent donnees/telechargees/
# Une étape dont l'outillage n'existe pas encore (avant la phase qui le crée) est notée « sans objet ».
# Fichier protégé : Claude Code ne peut pas le modifier (deny Edit + sandbox). Toute évolution passe par Micky.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

MODE="${1:---commit}"
case "$MODE" in --commit|--complet|--ci) ;; *) echo "Usage : $0 [--commit|--complet|--ci]" >&2; exit 64 ;; esac

ECHECS=0
RESUME=()

etape() { # etape "Nom" commande…
  local nom="$1"; shift
  echo "── $nom"
  if "$@"; then RESUME+=("✔ $nom"); else RESUME+=("✘ $nom"); ECHECS=$((ECHECS+1)); fi
}
sans_objet() { RESUME+=("– $1 (sans objet : $2)"); }

command -v uv >/dev/null 2>&1 || { echo "uv est introuvable : brew install uv" >&2; exit 1; }
if [ -f pyproject.toml ]; then PY=(uv run python); else PY=(uv run --no-project python); fi

# 1. Garde-fous du kit présents et actifs
kit() {
  local ok=0
  for f in CLAUDE.md .claude/settings.json .claude/hooks/garde-fou.sh .pre-commit-config.yaml donnees/sources.toml docs/portes.toml; do
    [ -f "$f" ] || { echo "Manquant : $f"; ok=1; }
  done
  [ -x .claude/hooks/garde-fou.sh ] || { echo "Non exécutable : .claude/hooks/garde-fou.sh"; ok=1; }
  if [ -f CLAUDE.md ] && [ "$(wc -l < CLAUDE.md)" -gt 200 ]; then echo "CLAUDE.md dépasse 200 lignes"; ok=1; fi
  return $ok
}
etape "Kit et garde-fous" kit

# 2. Contenus : dépendances interdites, vocabulaire, angles codés en dur, jeux d'essai
etape "Contenus et dépendances" "${PY[@]}" scripts/verifications/contenus.py

# 3. Intégrité : empreintes des données téléchargées et des fichiers générés
if [ "$MODE" = "--ci" ]; then
  etape "Intégrité (sans données téléchargées)" "${PY[@]}" scripts/verifications/integrite.py --sans-donnees
else
  etape "Intégrité" "${PY[@]}" scripts/verifications/integrite.py
fi

# 4. Python : style, types, tests
if [ -f pyproject.toml ]; then
  etape "Ruff (lint)" uv run ruff check .
  etape "Ruff (format)" uv run ruff format --check .
  CIBLES=(); for d in moteur api scripts; do [ -d "$d" ] && CIBLES+=("$d"); done
  if [ ${#CIBLES[@]} -gt 0 ]; then etape "mypy" uv run mypy "${CIBLES[@]}"; else sans_objet "mypy" "aucun paquet"; fi
  if [ -d tests ]; then
    if [ "$MODE" = "--ci" ]; then etape "pytest" uv run pytest -q -m "not donnees"; else etape "pytest" uv run pytest -q; fi
  else sans_objet "pytest" "pas de dossier tests/"; fi
else
  sans_objet "Python" "pyproject.toml absent"
fi

# 5. Frontières reproductibles : générées à nouveau et comparées à generes/
if [ -f scripts/construire_frontieres.py ]; then
  etape "Frontières régénérées à l'identique" "${PY[@]}" scripts/construire_frontieres.py --verifier
else
  sans_objet "Frontières" "scripts/construire_frontieres.py absent"
fi

# 6. Front : lint, types, tests unitaires (scripts npm obligatoires : lint, typecheck, test)
if [ -f web/package.json ]; then
  [ -d web/node_modules ] || etape "npm ci" npm ci --prefix web
  etape "Front (lint)" npm --prefix web run lint
  etape "Front (types)" npm --prefix web run typecheck
  etape "Front (tests)" npm --prefix web test
  if [ "$MODE" = "--complet" ]; then
    etape "Front (bout en bout et accessibilité)" npm --prefix web run e2e
  fi
else
  sans_objet "Front" "web/package.json absent"
fi

echo
echo "Résumé ($MODE)"
printf '  %s\n' "${RESUME[@]}"
if [ "$ECHECS" -gt 0 ]; then
  echo "$ECHECS contrôle(s) en échec : corrige la cause, ne contourne pas le contrôle." >&2
  exit 1
fi
echo "Tous les contrôles applicables sont au vert."
