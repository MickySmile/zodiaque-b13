# 0002 · Pile Python + React, API sans état

- Date : 15/11/2026
- Statut : acceptée (Micky) ; gestionnaires de paquets à confirmer ⚠️

## Contexte
L'annexe technique (§ G) cite un backend Python, une base SQLite ou PostgreSQL et une interface SVG. Le PRD (§ 7, Confidentialité) exige un calcul possible sans compte et aucune conservation des données de naissance côté serveur par défaut. Le calcul de référence repose sur Skyfield, en Python.

## Décision
- **Moteur** : paquet Python `moteur/` (Skyfield, NumPy, SciPy), géré par uv.
- **API** : FastAPI, Pydantic, Uvicorn ; **sans état** : ni base, ni fichier, ni journal des saisies.
- **Interface** : React, Vite, TypeScript, gérée par npm ; roue en SVG calculée depuis les données de l'API.
- **Hors ligne à l'exécution** : lieux (GeoNames), fuseaux (tzdata, timezonefinder) et éphémérides sont locaux ; l'application n'appelle aucun service tiers ; polices auto-hébergées.
- **Exécution locale** au MVP ; l'hébergement sera décidé avec la question Q4 du PRD.

## Conséquences
- Pas de base de données au MVP ; l'export JSON (FR-17) est le seul moyen de garder une session, côté navigateur.
- Une donnée de naissance ne quitte jamais la machine qui calcule.
- La CI rejoue les contrôles sans données téléchargées (`scripts/verifier.sh --ci`).
