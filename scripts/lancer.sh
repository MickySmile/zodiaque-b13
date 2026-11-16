#!/usr/bin/env bash
# scripts/lancer.sh — lance l'application en local, en une commande : le serveur de calcul (API,
# port 8000) et l'interface (port 5173). Ouvrir ensuite http://localhost:5173.
# Ctrl+C arrête les deux. Ce script n'écrit rien : il ne fait que lancer les deux serveurs.

set -euo pipefail
cd "$(dirname "$0")/.."

uv run uvicorn api.main:app --port 8000 &
API=$!
# Le serveur de calcul s'arrête avec l'interface, quelle que soit la façon de quitter.
trap 'kill "$API" 2>/dev/null || true' EXIT INT TERM

echo "Serveur de calcul lancé. Interface : http://localhost:5173 (Ctrl+C pour tout arrêter)"
npm --prefix web run dev -- --port 5173 --strictPort
