---
paths:
  - "api/**"
---

# API FastAPI sans état

Contrats : `docs/prd/01-annexe-technique.md`, § F (formats de données).

- **Sans état** : aucune base, aucun fichier écrit, aucun cache des saisies. L'API appelle `moteur/` et renvoie le résultat.
- **Contrats** : champs JSON en anglais, conformes à l'annexe F ; modèles Pydantic pour chaque entrée et sortie ; schéma OpenAPI généré, jamais écrit à la main.
- **`null` jamais remplacé** : une valeur absente reste `null`, avec un statut explicite (ex. Ascendant indéfini, éphéméride indisponible).
- **Manifeste dans chaque réponse** de calcul, tel que le moteur le produit, plus le statut des données (`candidate` tant que `docs/portes.toml` porte `franchie = false` pour G1 ; l'état est recopié dans `generes/manifest.json`).
- **Erreurs** : codes HTTP explicites et message en français pour l'utilisateur (heure inexistante, date hors 1849–2150, lieu introuvable) ; jamais de trace Python dans la réponse.
- **Aucun appel sortant** à l'exécution : lieux, fuseaux et éphémérides viennent des fichiers locaux.
- **Tests** : `fastapi.testclient` ; un test par route vérifie la présence du manifeste et du statut.
