# 0007 · Les scripts ajoutent la racine du dépôt à leur chemin d'import

- Date : 15/11/2026
- Statut : acceptée (Micky)

## Contexte
`pyproject.toml` n'a pas de `build-system` (phase 2) : les paquets `moteur` et `api` restent à la racine et ne sont pas installés dans l'environnement. pytest les trouve par `pythonpath = ["."]`, uvicorn et mypy parce qu'ils sont lancés depuis la racine.

Un script lancé par son chemin ne les trouve pas : avec `uv run python scripts/construire_frontieres.py`, Python met `scripts/` en tête du chemin d'import, pas la racine, et `import moteur` échoue. Or c'est exactement ainsi que `scripts/verifier.sh` (fichier protégé) lancera le script des frontières en phase 4. Constat de `relecteur-astro` à la relecture de la phase 2, écart 10 du journal.

## Décision
Tout script de `scripts/` qui importe `moteur` ajoute la racine du dépôt à `sys.path` avant cet import :

```python
RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import moteur
```

Un script qui n'importe pas `moteur` (aujourd'hui `scripts/telecharger.py`) n'a rien à ajouter.

Voie écartée : déclarer un `build-system` pour installer `moteur` et `api`. Plus propre, mais elle ajoute une dépendance de construction et une étape d'installation, pour une application qui n'est pas distribuée comme bibliothèque. Le motif retenu est déjà celui de `scripts/verifications/integrite.py`, qui calcule sa racine de la même façon.

## Conséquences
- Aucune exception de lint n'est nécessaire : avec la configuration de ruff du dépôt, l'import placé après ces lignes passe tel quel, et un `# noqa: E402` serait lui-même signalé comme inutile (essayé le 15/11/2026).
- Un test du socle lance chaque script de `scripts/` par son chemin, depuis un autre dossier, avec `--help` : un script qui oublierait ces lignes échoue au test, pas seulement dans `verifier.sh`. Chaque script accepte donc `--help`.
- `scripts/` reste sans `__init__.py` : les tests l'importent comme paquet implicite (`from scripts import telecharger`).
- Si l'application devait un jour être installée (déploiement, question Q4 du PRD), cette décision serait à revoir par une nouvelle décision.
