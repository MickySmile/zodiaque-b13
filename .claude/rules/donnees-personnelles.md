---
paths:
  - "api/**"
  - "tests/**"
  - "web/src/**"
---

# Données personnelles (RGPD)

Date, heure et lieu de naissance sont des données personnelles (PRD § 7, Confidentialité).

- **Jeux d'essai fictifs** : chaque fichier de test qui contient une clé `birth` porte `"synthetic": true` à la racine ; `scripts/verifications/contenus.py` le contrôle. N'utilise jamais une date de naissance réelle, même publique.
- **Aucune trace** : pas de saisie dans les journaux, les messages d'erreur, les noms de fichiers d'export par défaut ni les rapports de test.
- **Aucune conservation côté serveur** ; côté navigateur, rien n'est enregistré sans action explicite de la personne (export JSON, FR-17).
- **Aucun tiers** : ni analytique, ni police distante, ni carte en ligne.
