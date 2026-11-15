---
name: donnees
description: Télécharge les données déclarées dans donnees/sources.toml, contrôle leurs empreintes SHA-256 et met à jour le manifeste.
disable-model-invocation: true
---

# Données téléchargées (régime « mesure »)

Contrat de `scripts/telecharger.py` (à écrire en phase 3 s'il n'existe pas, puis à tester) :
- lit `donnees/sources.toml` ; ne télécharge rien qui n'y figure pas ;
- télécharge en HTTPS vers un fichier temporaire, essaie `miroir` si `url` échoue, puis déplace dans `$B13_DONNEES` (par défaut `donnees/telechargees/`) ;
- calcule le SHA-256 ; si une empreinte est déclarée et diffère, supprime le fichier temporaire et s'arrête en erreur ;
- n'écrase jamais un fichier existant dont l'empreinte est correcte ;
- option `--source <id>` pour une seule source, `--verifier` pour contrôler sans télécharger.

Procédure :
1. Lance `uv run python scripts/telecharger.py --verifier` et montre l'état de chaque source.
2. Télécharge ce qui manque : `uv run python scripts/telecharger.py`.
3. Pour une source sans empreinte : montre à Micky l'URL, la taille et le SHA-256 obtenus, puis propose la ligne `sha256 = "…"` dans `donnees/sources.toml` (la modification demande son accord).
4. Pour ajouter une source : nom, URL officielle, licence, usage ; Micky valide avant toute écriture dans `sources.toml`, et le domaine doit être dans `sandbox.network.allowedDomains` (que seul Micky modifie).
5. Lance la skill `verify` et rends un tableau : source, fichier, taille, empreinte, état.
