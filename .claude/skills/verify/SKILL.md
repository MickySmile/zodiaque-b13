---
name: verify
description: Contrôle le dépôt avant un commit ou à la fin d'une tâche — tests Python et front, types, intégrité des données et des fichiers générés, dépendances interdites, vocabulaire, angles codés en dur. À lancer juste avant chaque commit et quand on demande « vérifie », « est-ce que tout passe ? ».
allowed-tools: Bash(scripts/verifier.sh *)
---

# Vérifier avant de livrer

1. Lance `scripts/verifier.sh --commit`. Si la tâche touchait l'interface ou la roue, lance plutôt `scripts/verifier.sh --complet`.
2. Lis le résumé final. Pour chaque contrôle en échec, remonte à la cause dans la sortie (fichier, ligne, test).
3. Corrige la cause dans le code, les tests ou les données d'entrée. Ne modifie jamais un contrôle, un seuil ou un fichier de `scripts/verifications/` pour faire passer la vérification ; si un contrôle te semble faux, explique pourquoi à Micky et arrête-toi.
4. Relance jusqu'au vert, au plus trois tours. Au-delà, résume ce qui bloque et demande.
5. Compte rendu en trois lignes : contrôles passés, corrections faites, contrôles « sans objet » encore attendus.
