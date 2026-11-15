---
paths:
  - "moteur/**"
  - "scripts/**"
---

# Moteur de calcul : conventions du modèle B

Détail et justification : `docs/prd/01-annexe-technique.md`, § B (conventions), C (formules), D (algorithmes), E (thème natal), G (flottants).

- **Un seul repère** : écliptique moyen J2000 fixe, R = Qₓ(−ε₀) · B, avec B la matrice `ICRS_to_J2000` de Skyfield et ε₀ = 84 381,406″. Enregistre la matrice dans le manifeste ; ne te fie pas au seul nom `ecliptic_J2000_frame`.
- **Positions astrométriques géocentriques** : `.observe()` sans `.apparent()`. Le lieu ne sert qu'au fuseau, aux angles et aux maisons.
- **Frontières** : grille UAI de Skyfield (`load_constellation_map`, Roman 1987, VI/42), interrogée par `radec(epoch=B1875)`. Annonce « réalisation Skyfield / Roman », jamais « reproduction exacte de Delporte ».
- **Identifiant du modèle** : `model_b_iau_ecliptic_j2000_v1`, versionné à part du référentiel symbolique.
- **Classement** : longitude seule (la latitude est calculée, stockée, ignorée) ; `wrap` ramène dans [0°, 360°[ ; début inclus, fin exclue ; une frontière calculée une fois, partagée par les deux signes ; aucune zone de cuspide.
- **Contrôles qui arrêtent le calcul** : 13 intervalles, ordre attendu Ari, Tau, Gem, Cnc, Leo, Vir, Lib, Sco, Oph, Sgr, Cap, Aqr, Psc (contrôlé, jamais imposé), Σ largeurs = 360° à 10⁻⁹° près, ni lacune ni chevauchement. En cas d'échec : erreur explicite, jamais de correction silencieuse.
- **Flottants** : double précision, aucun arrondi avant le classement, aucun signe élargi d'un epsilon ; teste les voisins d'une frontière avec `math.nextafter()` ; jamais `==` entre deux angles calculés sans tolérance déclarée.
- **Passages du Soleil** : méthode de Brent (`scipy.optimize.brentq`) en échelle TT, tolérance 0,01 s.
- **Plage** : DE440s couvre 1849–2150 ; hors plage, erreur explicite. Heures UTC futures marquées « conditionnelles ».
- **Valeurs absentes** : `None` reste `None` (pôles écliptiques, Ascendant indéfini, éphéméride manquante). Pas de valeur approchée, pas de système de substitution.
- **Manifeste** sur chaque résultat : moteur et versions (Skyfield, NumPy, Python), éphéméride + SHA-256, données de temps, version tzdata, modèle de frontières + SHA-256 de `constellations.npz`, versions des règles, empreinte de la saisie.
- **Treize signes, mêmes fonctions** : aucun cas particulier par signe ; un test couvre un thème sans aucun placement en Serpentaire (cas A de `docs/prd/03-consequences.md`).
- **Tests** : propriétés avec Hypothesis pour `wrap` et le classement (signe traversant 0°, λ = 365° → 5°, λ négatif) ; tests qui exigent `donnees/telechargees/` marqués `@pytest.mark.donnees`.
- **Relecture** : après toute modification de `moteur/` ou d'un script de calcul, demande la relecture du sous-agent `relecteur-astro` avant le commit.
- **Scripts** : `scripts/` écrit seulement dans `generes/` et `donnees/telechargees/`, et met à jour `generes/manifest.json` (empreinte de chaque fichier) à chaque génération.
