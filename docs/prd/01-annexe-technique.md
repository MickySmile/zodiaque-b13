<!-- Source : PRD « Thème astral à 13 signes » (claude.ai, propriétaire : Micky), export du 2026-11-15. Fichier en lecture seule pour Claude Code (deny Edit sur docs/prd/**). Les schémas d'origine sont transcrits en blocs texte. -->

# Annexe technique — éléments extraits de l'étude

Cette annexe regroupe les éléments techniques de l'étude PDF qui précisent les exigences du PRD ; chaque section indique les exigences qu'elle sert. Les valeurs sont des conventions proposées par l'étude ; les frontières et positions citées en exemple sont fictives.

## A. État d'exécution

Seuls les noyaux mathématiques ont tourné ; aucune donnée astronomique réelle n'a été calculée. Sert : risques (§ 10), planning (§ 11).

| Élément livré par l'étude                                      | Statut                                                                                            | Exigences concernées |
|----------------------------------------------------------------|---------------------------------------------------------------------------------------------------|----------------------|
| Noyau de classement (normalisation, intervalles, attribution)  | Exécuté : 5 méthodes de test réussies                                                             | FR-02                |
| Contrôles du moteur de thème (maisons, aspects, cas du pôle)   | Exécuté : 8 contrôles réussis                                                                     | FR-07 à FR-09        |
| Démonstrateur d'interprétation                                 | Exécuté sur 10 longitudes fictives et 2 variantes contrôlées                                      | FR-19                |
| Prototype HTML de l'explorateur                                | 20 contrôles Python réussis, PDF de 3 pages généré ; JavaScript jamais exécuté dans un navigateur | FR-10 à FR-17        |
| Programme des frontières et des passages du Soleil             | Syntaxe vérifiée, jamais exécuté (Skyfield et DE440s indisponibles)                               | O1, porte G1         |
| Validation indépendante des frontières                         | Non effectuée                                                                                     | O1                   |
| Positions réelles des 10 objets, angles d'une naissance réelle | Non calculés                                                                                      | O2, porte G2         |
| Propagation de l'incertitude sur l'heure                       | Spécifiée ; le moteur livré refuse encore les heures incertaines                                  | FR-03 à FR-05        |
| Navigation clavier et lecteur d'écran                          | Prévue, non testée                                                                                | ENF Accessibilité    |

## B. Conventions de référence

Toutes les longitudes — frontières, astres, angles, maisons — sont exprimées avec la même matrice, enregistrée dans le manifeste. Sert : ENF Conventions, Reproductibilité, Plage temporelle.

| Paramètre              | Valeur retenue                                                                                                                                                           | Précision                                                                                      |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| Identifiant du modèle  | `model_b_iau_ecliptic_j2000_v1`                                                                                                                                          | Versionné à part du référentiel symbolique                                                     |
| Repère                 | Écliptique moyen J2000 fixe : R = Qₓ(−ε₀) · B, où B est la matrice ICRS_to_J2000 de Skyfield et Qₓ(−ε₀) = \[\[1, 0, 0\], \[0, cos ε₀, sin ε₀\], \[0, −sin ε₀, cos ε₀\]\] | ε₀ = 84 381,406″ (obliquité moyenne J2000) ; ne pas se fier au seul nom `ecliptic_J2000_frame` |
| Origine des longitudes | Axe x du repère, longitude croissante de x vers y                                                                                                                        | Une autre origine translate toutes les valeurs                                                 |
| Frontières             | UAI (Delporte) via Roman 1987, catalogue VI/42, grille intégrée à Skyfield                                                                                               | Annoncer « réalisation Skyfield / Roman », pas « reproduction exacte de Delporte »             |
| Version des frontières | Version de Skyfield + SHA-256 de `constellations.npz`                                                                                                                    | Enregistrées à l'exécution                                                                     |
| Coordonnées sources    | Grille équatoriale B1875, interrogée par `radec(epoch=B1875)`                                                                                                            | Utilise la matrice t.M de Skyfield (précession, nutation, biais)                               |
| Observateur            | Centre de la Terre (géocentrique)                                                                                                                                        | Le lieu ne sert qu'au fuseau, aux angles et aux maisons                                        |
| Positions              | Astrométriques : `.observe()` sans `.apparent()`                                                                                                                         | Temps de parcours de la lumière inclus                                                         |
| Éphéméride             | JPL DE440s (~32 Mo), fichier figé                                                                                                                                        | Couvre 1849–2150                                                                               |
| Échelles de temps      | Saisie et affichage en UTC ; TT / TDB pour les éphémérides ; UT1 pour l'orientation terrestre                                                                            | Sources UTC–TT et UT1 archivées ; mouvement du pôle non activé dans le moteur livré            |
| Fuseaux                | Identifiant historique IANA (`tzdata`), version enregistrée                                                                                                              | Jamais un simple « UTC+1 »                                                                     |
| Calendrier             | Grégorien proleptique par défaut                                                                                                                                         | Autre calendrier : sélection explicite                                                         |
| Classement             | Longitude seule ; latitude calculée et stockée, mais ignorée                                                                                                             | Avec la latitude, on passe au modèle C                                                         |
| Bornes                 | Début inclus, fin exclue ; frontière calculée une fois, partagée par les deux signes                                                                                     | Aucune « zone de cuspide »                                                                     |
| Ordre attendu          | Ari, Tau, Gem, Cnc, Leo, Vir, Lib, Sco, Oph, Sgr, Cap, Aqr, Psc                                                                                                          | Contrôlé après calcul, jamais imposé                                                           |

**Trois dates à ne pas confondre** : la date d'observation (ex. 14/11/2026 12 h UTC), l'époque du repère (J2000) et l'équinoxe des frontières sources (B1875).

**Contrôle externe** : JPL Horizons peut servir de seconde chaîne, à partir de vecteurs transformés par R. Sa colonne 31 donne une longitude apparente de date : elle n'est pas comparable telle quelle.

## C. Formules

Toutes les grandeurs se calculent sur les longitudes du repère B ; les angles sont en degrés, convertis en radians dans le code.

**Classement et progression** — sert FR-02, FR-10. wrap ramène un angle dans \[0°, 360°\[.

```latex
w_i = \operatorname{wrap}(b_{i+1} - b_i) \qquad d_i = \operatorname{wrap}(\lambda - b_i) \qquad 0 \le d_i < w_i \qquad p_i = \frac{d_i}{w_i}
```

**Changement de repère** — sert ENF Conventions. R est orthogonale : sa transposée est son inverse (test : RᵀR = I à 10⁻¹² près).

```latex
\mathbf{u}_{ecl}(\lambda) = (\cos\lambda,\ \sin\lambda,\ 0)^\top \qquad \mathbf{u}_{ecl} = R\,\mathbf{u}_{ICRS} \iff \mathbf{u}_{ICRS} = R^\top \mathbf{u}_{ecl}
```

**Passage du Soleil** — sert FR-06. Le Soleil appartient au signe i pour t ∈ \[tᵢ, tᵢ₊₁\[.

```latex
\lambda_\odot(t_i) = b_i \pmod{360^\circ}
```

**Repère local, Ascendant B et Milieu du Ciel B** — sert FR-08. φ : latitude géodésique ; L : longitude géographique ; T : matrice ICRS → ITRS à l'instant t.

```latex
\mathbf{U} = \begin{pmatrix}\cos\varphi\cos L\\ \cos\varphi\sin L\\ \sin\varphi\end{pmatrix} \quad \mathbf{E} = \begin{pmatrix}-\sin L\\ \cos L\\ 0\end{pmatrix} \quad \mathbf{M} = \begin{pmatrix}\cos L\\ \sin L\\ 0\end{pmatrix} \qquad \mathbf{X}_B = R\,T^\top \mathbf{X}
```

```latex
\mathbf{a} = \frac{\mathbf{k}_B \times \mathbf{U}_B}{\lVert \mathbf{k}_B \times \mathbf{U}_B \rVert},\ \mathbf{a}\cdot\mathbf{E}_B > 0,\ \lambda_{ASC} = \operatorname{atan2}(a_y, a_x) \qquad \mathbf{m} = \frac{\mathbf{k}_B \times \mathbf{E}_B}{\lVert \mathbf{k}_B \times \mathbf{E}_B \rVert},\ \mathbf{m}\cdot\mathbf{M}_B > 0,\ \lambda_{MC} = \operatorname{atan2}(m_y, m_x)
```

k_B = (0, 0, 1) est la normale du plan B. Norme nulle, branche indéterminée ou pôle géographique : angle absent avec statut explicite.

**Maisons égales** — sert FR-08. Une planète exactement sur une cuspide appartient à la maison qui commence.

```latex
c_k = \lambda_{ASC} + 30^\circ (k-1),\ k = 1 \dots 12 \qquad \text{maison } k \iff 0 \le \operatorname{wrap}(\lambda - c_k) < 30^\circ
```

**Aspects** — sert FR-09. Un aspect d'angle A et d'orbe O est retenu si l'écart à l'exact ne dépasse pas O.

```latex
\Delta = \left| \big((\lambda_1 - \lambda_2 + 180^\circ) \bmod 360^\circ\big) - 180^\circ \right| \qquad |\Delta - A| \le O
```

**Rétrogradation** — sert FR-07. Dérivée centrée avec deux pas, h = 1 h et h = 30 min ; \|vλ\| ≤ εᵥ donne le statut `stationary_or_undetermined`.

```latex
v_\lambda(t) \approx \frac{\operatorname{signedwrap}\big(\lambda(t+h) - \lambda(t-h)\big)}{2h} \qquad \varepsilon_v = \max\!\left(10^{-4}\ \text{deg/jour},\ 2\,|v_{1h} - v_{30min}|\right)
```

**Accents pondérés et effet de largeur** — sert la vue des accents (§ 8 du PRD). aⱼ : poids de l'objet j ; sⱼ : son signe.

```latex
C_i = \sum_j a_j\,\mathbf{1}(s_j = i) \qquad A_i = \frac{C_i}{\sum_j a_j} \qquad q_i = \frac{w_i}{360^\circ} \qquad D_i = \frac{C_i}{w_i}
```

**Opposition entre signes** — sert FR-14. L'opposé d'un point est unique ; celui d'un signe peut couvrir plusieurs signes.

```latex
L_{ij} = \operatorname{longueur}\big(O(I_i) \cap I_j\big) \qquad \sum_j L_{ij} = w_i \qquad L_{ij} = L_{ji}
```

**Projection sur la roue** — sert FR-10. Ascendant à gauche, longitudes croissantes dans le sens antihoraire ; sans heure, λ_ASC est remplacé par 0° B-J2000. Les aspects sont des cordes droites entre deux points de ce cercle.

```latex
\delta = (\lambda - \lambda_{ASC})\,\frac{\pi}{180} \qquad x = c_x - r\cos\delta \qquad y = c_y + r\sin\delta
```

## D. Algorithmes

Chaque algorithme s'arrête plutôt que de corriger un résultat incohérent en silence.

**1. Construire les 13 frontières** — sert O1, porte G1

1.  Énumérer les intersections du cercle B avec toutes les lignes d'ascension droite et de déclinaison de la grille Skyfield (solutions analytiques, cas dégénérés traités à part).

2.  Trier les longitudes candidates.

3.  Identifier la constellation au milieu de chaque arc.

4.  Supprimer les coupures sans changement de constellation.

5.  Vérifier les 13 noms et leur ordre cyclique.

6.  Contrôle complémentaire : échantillonner au pas de 0,1°, puis raffiner par dichotomie jusqu'à τ = 10⁻⁸°. Ce sondage ne prouve pas l'exhaustivité.

Arrêt du calcul si : nombre d'intervalles ≠ 13 ; une constellation sur deux arcs (jamais fusionnés à travers une autre) ; ordre différent ; largeur nulle, lacune ou chevauchement ; Σ wᵢ ≠ 360° ; classement erroné juste avant ou après une frontière ; sondage dense contradictoire. Une ligne de déclinaison constante est un petit cercle : la relier par un grand cercle serait une approximation injustifiée.

**2. Calculer les passages du Soleil** — sert FR-06

1.  Calculer la longitude solaire sur une grille journalière (échelle TT, date julienne en deux parties).

2.  Dérouler les longitudes pour supprimer le saut à 360°.

3.  Vérifier que la progression est monotone.

4.  Encadrer chaque franchissement de frontière.

5.  Raffiner par la méthode de Brent (tolérance 0,01 s).

6.  Vérifier le résidu angulaire.

7.  Vérifier qu'une seconde avant et après, le Soleil est de part et d'autre de la frontière.

Convention annuelle : la ligne « année N » décrit l'entrée survenue en N et la sortie qui suit. Pour couvrir l'année civile entière, on reprend la fin du séjour commencé en décembre N−1. Années prévues : 2000, 2025, 2026, 2027, 2050, soit 65 entrées. Mention d'affichage imposée : « Instant calculé en TT ; UTC selon la table de secondes intercalaires utilisée ; heure de Paris selon la version de la base des fuseaux. »

**3. Propager l'incertitude sur l'heure** — sert FR-03 à FR-05

1.  Recueillir l'heure locale et sa précision.

2.  Identifier le fuseau historique.

3.  Classer l'heure locale : unique, ambiguë ou inexistante.

4.  Construire les instants UTC possibles.

5.  Calculer les directions sur ces intervalles, dans le repère B.

6.  Rechercher les frontières franchies, en raffinant près des transitions et des changements de sens.

7.  Pour les angles et maisons, faire aussi varier la position géographique selon son incertitude.

8.  Retourner l'ensemble des signes, maisons et aspects possibles.

Ne jamais calculer seulement les deux extrémités : une longitude peut passer par un extremum à l'intérieur de l'intervalle. Aspects classés **certain** (critère vérifié partout), **possible** (sur une partie) ou **absent**. Aucune probabilité sans distribution déclarée sur les entrées. Une incertitude de mesure, une différence de convention (ex. centre de Pluton contre barycentre Pluton–Charon) et une erreur de calcul se traitent différemment : intervalle, scénarios nommés, correction du pipeline.

**4. Placer les étiquettes de la roue** — sert FR-10

1.  Trier les astres par longitude.

2.  Couper le cercle dans le plus grand intervalle vide.

3.  Mesurer les boîtes de texte à l'échelle d'affichage, après chargement des polices et à chaque zoom.

4.  Optimiser les positions : ordre circulaire conservé, aucun chevauchement, déplacement minimal, rangée secondaire si nécessaire.

5.  Dessiner les traits de rappel.

6.  Tester les collisions après rendu.

Deux longitudes par astre : `true_longitude_deg` commande le point, le classement et les aspects ; `display_longitude_deg` ne déplace que le glyphe. En cas de surcharge : rangée ou liste latérale, jamais de déformation de la roue.

## E. Thème natal

Version de référence proposée : `natal_b_j2000_equal12_v1` — 13 signes inégaux, Ascendant et MC sur le cercle B, 12 maisons égales depuis l'Ascendant B, ni réfraction ni relief. Sert : FR-04 à FR-09, FR-20.

**Cibles astronomiques avec DE440s seul.** Chaque résultat porte `target_kind = center | system_barycenter` ; aucune substitution silencieuse.

| Objet                             | Identifiant | Type de cible            |
|-----------------------------------|-------------|--------------------------|
| Soleil                            | 10          | Centre                   |
| Lune                              | 301         | Centre                   |
| Mercure, Vénus, Mars              | 1, 2, 4     | Barycentre du système    |
| Jupiter, Saturne, Uranus, Neptune | 5, 6, 7, 8  | Barycentre du système    |
| Pluton                            | 9           | Barycentre Pluton–Charon |

**Statut de l'heure et résultat autorisé**

| Situation                       | Résultat                                                                          |
|---------------------------------|-----------------------------------------------------------------------------------|
| Heure connue, instant unique    | Thème ponctuel, précision annoncée                                                |
| Heure à quelques minutes près   | Ensemble de positions et de classements possibles                                 |
| Heure ambiguë (recul d'horloge) | Deux scénarios, champ `fold` pour choisir                                         |
| Heure locale inexistante        | Erreur à résoudre, aucune correction silencieuse                                  |
| Heure inconnue                  | Positions sur la journée, ni Ascendant ni maisons ; « carte de référence à midi » |

**Aspects** (orbes = convention éditoriale du système)

| Aspect      | Angle | Orbe |
|-------------|-------|------|
| Conjonction | 0°    | 6°   |
| Sextile     | 60°   | 4°   |
| Carré       | 90°   | 5°   |
| Trigone     | 120°  | 5°   |
| Opposition  | 180°  | 6°   |

Règles associées : pas d'orbe élargi pour le Soleil ou la Lune ; objet–ASC et objet–MC limités à 3° ; pas d'aspect ASC–MC ni aux cuspides ; pas d'aspect fondé sur 360° / 13 ; pas de statut appliquant / séparant en v1. Chaque aspect conserve : objets, type, séparation réelle, écart à l'exact, orbe autorisé.

**Tableau des objets restitué** : objet, cible, type de cible, longitude B (non arrondie), latitude B, signe, degrés internes, progression, maison (1–12 ou absente), vitesse (°/jour), mouvement. Le MC est un angle indépendant, généralement distinct de la cuspide X ; DSC et IC sont opposés à l'ASC et au MC.

**Objets optionnels** (désactivés par défaut)

- **Chiron** : objet physique, éphéméride SPK identifiée et archivée ; sinon statut `ephemeris_unavailable`.

- **Nœud lunaire** : `lunar_ascending_node_osculating_relative_to_B`, calculé à partir des états géométriques simultanés de la Lune ; distinct du nœud moyen.

- **Lilith** : `lunar_apogee_osculating_two_body` ; distinct de l'apogée moyen et de l'astéroïde 1181 Lilith. Direction mal conditionnée : statut d'indétermination.

## F. Formats de données

Un même jeu de données alimente toutes les vues ; une valeur absente reste `null`, jamais un nombre inventé. Sert : FR-01, FR-16, FR-17, FR-19, ENF Reproductibilité.

**Saisie de naissance** (exemple fictif)

``` json
{
  "date_local": "2000-01-01",
  "time_local": "12:00:00",
  "time_status": "known | uncertain | unknown",
  "time_uncertainty_seconds": 0,
  "timezone": "Europe/Paris",
  "fold": null,
  "latitude_deg": 48.8566,
  "longitude_deg": 2.3522,
  "altitude_m": 35,
  "calendar": "proleptic_gregorian",
  "source": "fictional_demonstration"
}
```

**Enregistrement traçable d'un classement** (extrait). La latitude est stockée pour le contrôle et la comparaison avec le modèle C, jamais utilisée pour classer.

``` json
{
  "model": {
    "id": "model_b_iau_ecliptic_j2000_v1",
    "reference_frame": "Rx(-84381.406 arcsec) @ Skyfield.ICRS_to_J2000",
    "boundary_source_equinox": "B1875",
    "boundary_sha256": null,
    "interval_policy": "start_included_end_excluded",
    "validation_status": "not_executed"
  },
  "calculation": { "observer": "geocentric", "position_type": "astrometric", "ephemeris": null, "ephemeris_sha256": null, "timezone_database_version": null },
  "position": { "body": null, "body_identifier": null, "longitude_deg": null, "latitude_deg": null },
  "classification": { "sign_id": null, "degrees_in_sign": null, "fraction_in_sign": null, "status": "not_computed", "possible_signs": null },
  "uncertainty": { "time_interval_utc": null, "longitude_interval_deg": null, "input_probability_distribution": null },
  "interpretation": { "ruleset_id": null, "epistemic_status": "symbolic_proposal", "text": null }
}
```

**Proposition interprétative** : le moteur produit des unités de sens avant tout paragraphe. `input_status` dit si le placement est stable ; `epistemic_status` rappelle que sa signification reste une proposition.

``` json
{
  "claim_id": "communication_014",
  "dimension": "communication",
  "resource": "rendre_le_savoir_verifiable",
  "tension": "surjustifier_ou_se_rendre_indispensable",
  "conditions": ["Mercury.sign_id == Oph"],
  "placement_refs": ["natal.Mercury"],
  "rule_refs": ["planet.Mercury.function.v1", "sign.Oph.mastery_revisable.v1"],
  "provenance": "contemporary_symbolic_design",
  "input_status": "stable",
  "epistemic_status": "symbolic_proposal"
}
```

**Règle symbolique** : chaque règle porte sa provenance et ses inférences interdites.

``` json
{
  "rule_id": "oph_knowledge_responsibility",
  "sign_id": "Oph",
  "status": "contemporary_design",
  "mythological_basis": "Asclepius: knowledge, intervention and limits",
  "resources": ["explicit_limits", "responsible_transmission"],
  "tensions": ["savior_posture", "unjustified_authority"],
  "forbidden_inferences": ["medical_diagnosis", "therapeutic_vocation", "guaranteed_personality_trait"]
}
```

**Données de la roue** : le composant graphique reçoit un thème validé et ne recalcule rien. Champs : `status`, `reference_frame_id`, `boundary_model_id`, `boundary_validation_status`, `orientation` (`ascendant_left`, `counterclockwise`), `signs` (id, nom, glyphe, début, fin, largeur), `houses`, `bodies` (`true_longitude_deg`, `display_longitude_deg`, `motion_status`, `uncertainty`), `angles`, `aspects`.

**Versionnement minimal d'un portrait** : `calculation_engine_version`, `ephemeris_id_and_hash`, `time_data_version`, `timezone_database_version`, `boundary_model_id_and_hash`, `symbolic_ruleset_version` (ex. `b13_symbolic_v1`), `dominance_ruleset_version` (ex. `b13_weighted_accents_v1`), `synthesis_ruleset_version`, `text_generator_version`, `chart_input_hash`. Un changement de modèle de langage ne doit pas modifier en silence le sens des règles.

**Fichiers produits**

| Programme              | Sorties                                                                                                                                     |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| Frontières et passages | `frontieres.csv`, `passages_2026.csv`, `entrees_toutes_annees.csv`, `passages_toutes_annees.csv`, `comparaison_annees.csv`, `manifest.json` |
| Thème natal            | `theme.json`, `positions.csv`, `aspects.csv`, `maisons.csv`, `roue.png`                                                                     |
| Explorateur (session)  | Données source, mode simplifié ou détaillé, découpage, objets et familles d'aspects visibles, sélection, résultats des contrôles            |

## G. Architecture et modules

L'étude recommande 8 composants séparés ; un backend Python, une base SQLite ou PostgreSQL et une interface web SVG suffisent pour un premier outil. Sert : FR-10 à FR-19, schéma du § 5.

| Composant                 | Fonction                                                     |
|---------------------------|--------------------------------------------------------------|
| Moteur astronomique       | Temps, éphémérides, coordonnées, angles, maisons             |
| Référentiel géométrique   | Frontières B13, matrice, versions, contrôles                 |
| Base symbolique           | Fonctions planétaires, 13 signes, maisons, aspects           |
| Moteur de règles          | Conditions, propositions, relations, exclusions              |
| Planificateur de portrait | Priorités, fils conducteurs, chapitres                       |
| Générateur de texte       | Mise en langage des seules propositions autorisées           |
| Vérificateur              | Traçabilité, contradictions, répétitions, données manquantes |
| Interface                 | Roue, tableaux, portrait, explications                       |

**Modules Python déjà écrits dans l'étude** : `coordinates.py` (repère fixe, positions astrométriques), `boundaries.py` (construction et contrôle des frontières, empreintes), `classification.py` (normalisation, attribution, progression, incertitude angulaire), `interpretation.py` (interface des règles), `natal_core.py` (signes, maisons, angles, aspects), `calcul_theme_b.py`, `calcul_zodiaque_b.py` (frontières et passages), tests unitaires. Dépendances : `numpy`, `scipy`, `skyfield`, `tzdata`, `matplotlib` ; versions figées par `pip freeze > requirements.lock`.

**Contrat du constructeur de frontières** : `construct()` renvoie `model_id`, `reference_frame`, `boundary_source`, `boundary_equatorial_convention`, versions de Skyfield, NumPy et Python, `boundary_sha256`, `matrix_icrs_to_ecliptic`, `certification`, `intervals`. Le moteur de thème vérifie que la matrice du manifeste est celle qu'il utilise.

**Rôle du modèle de langage** : il ne décide ni des positions, ni des signes, ni des aspects, ni des orbes, ni des dominantes, ni de la présence d'une configuration. Il reçoit un plan et des propositions autorisées, rédige, puis le vérificateur contrôle qu'il n'a ajouté aucun placement, aucune règle, aucun événement.

**Gestion des flottants** : double précision ; aucun arrondi avant le classement ; bornes canoniques identiques partout ; début inclus / fin exclue strict ; voisins testés avec `math.nextafter()` ; aucun signe élargi d'un epsilon ; incertitude de position et de frontière représentées séparément. Si une valeur affichée semble égale à la frontière, l'interface augmente la précision d'affichage.

## H. Rendu de la roue

La roue est un SVG construit à partir des données, jamais une illustration : on déplace le texte, jamais une position ni une frontière. Sert : FR-10, FR-13, FR-16, ENF Accessibilité.

**Anneaux** (R = rayon extérieur de l'anneau zodiacal). Une frontière de signe s'arrête à son anneau, pour ne pas être lue comme une limite de maison.

| Zone               | Rayon            | Contenu                                                          |
|--------------------|------------------|------------------------------------------------------------------|
| Repères extérieurs | 1,00 R à 1,15 R  | ASC, DSC, MC, IC                                                 |
| Anneau des signes  | 0,855 R à 1,00 R | 13 secteurs proportionnels, glyphes, noms                        |
| Graduation         | 0,81 R à 0,855 R | Échelle continue de longitude, sans remise à zéro aux frontières |
| Anneau des maisons | 0,72 R à 0,80 R  | 12 maisons numérotées, limites en pointillé gris                 |
| Repères exacts     | ≈ 0,715 R        | Point et trait à la longitude réelle                             |
| Étiquettes         | 0,50 R à 0,69 R  | Glyphes, degrés internes, statut rétrograde                      |
| Disque des aspects | 0 à 0,46 R       | Cordes droites entre longitudes réelles                          |

**Interdits** : dessiner 13 secteurs égaux puis afficher les vraies valeurs dans un tableau ; élargir le Scorpion ou le Serpentaire pour y loger un nom ; contracter une portion de roue ; déplacer une frontière pour éviter une collision ; relier les aspects aux glyphes déplacés ; forcer le MC à midi ; orienter la roue sur un faux Ascendant quand l'heure est inconnue. Petit secteur : glyphe, puis abréviation, nom complet au survol et dans la légende.

**Familles d'aspects** : la couleur distingue des familles, jamais « bon » ou « mauvais » ; la longueur d'une corde ne signifie rien. Les conjonctions serrées figurent aussi dans le tableau.

| Aspect      | Couleur     | Trait               |
|-------------|-------------|---------------------|
| Conjonction | Violet      | Continu, très court |
| Sextile     | Bleu        | Pointillé court     |
| Carré       | Terre cuite | Continu             |
| Trigone     | Bleu        | Continu             |
| Opposition  | Terre cuite | Tirets longs        |

**Angles** : ASC et DSC en repères pleins plus épais ; MC et IC en tirets ; nom à l'extérieur, valeur exacte dans la fiche.

**Glyphe du Serpentaire** : caractère Unicode U+26CE « OPHIUCHUS » (⛎), rendu monochrome, sans présentation emoji ; repli « Oph » ; aucun caducée ni autre emblème ; aucune couronne, étoile ou couleur qui suggère un signe supérieur. Les glyphes sont convertis en tracés dans les exports SVG.

**Typographie** : sans sérif sobre, chiffres tabulaires, aucun texte essentiel en capitales décoratives.

| Élément                | Taille cible |
|------------------------|--------------|
| Glyphe de signe        | 24–30 px     |
| Glyphe d'astre         | 22–28 px     |
| Numéro de maison       | 13–16 px     |
| Valeur près d'un astre | 11–13 px     |
| Texte de panneau       | 14–16 px     |

Sur petit écran, on masque les détails secondaires plutôt que de réduire toute la typographie.

**Deux niveaux d'affichage** : la vue simplifiée montre signes, maisons, 10 objets, 4 angles, carrés, trigones et oppositions ; la vue détaillée ajoute graduations fines, degrés internes et les 5 familles d'aspects. Un élément masqué n'est pas absent du calcul.

**Ordre de rendu** : validation des données et du repère → orientation → secteurs → graduations et maisons → cordes d'aspects → repères exacts → placement des étiquettes → traits de rappel, glyphes et valeurs → angles, légende et avertissements. Chaque objet, maison, signe et aspect garde un identifiant SVG pour relier roue, tableaux et portrait.

## I. Moteur d'interprétation B13

Promesse de la v1 : « produire une lecture symbolique personnalisée par ses données d'entrée, explicable et cohérente avec un référentiel déclaré » — jamais une mesure de personnalité. Sert : FR-12, FR-15, FR-19, ENF Contenus.

**Trois contrats à valider séparément** : calcul (comparaisons numériques, tests), cohérence symbolique (traçabilité, variantes contrôlées), validité empirique (études avec protocole fixé à l'avance, hors produit).

**Référentiel B13 v1** : noms et certains motifs hérités conservés ; éléments, modalités, polarités, maîtrises et dignités désactivés, conservés comme métadonnées ; 13 fonctions symboliques distinctes. Provenance de chaque règle : **H** héritage documenté, **M** référence mythologique, **C** choix contemporain. Identité proposée du Serpentaire : « la maîtrise révisable ».

**Grammaire à quatre rôles**

| Composant | Rôle                              |
|-----------|-----------------------------------|
| Planète   | Fonction examinée                 |
| Signe     | Mode opératoire de cette fonction |
| Maison    | Domaine où la lecture se situe    |
| Aspect    | Relation entre deux fonctions     |

**Ordre d'application, par objet** : 1. fonction ; 2. mode du signe ; 3. maison si disponible ; 4. aspects significatifs ; 5. une ressource, une tension, une question ; 6. transmission au moteur de synthèse.

**Hiérarchie éditoriale**

| Niveau                      | Facteurs                       | Poids des accents                       |
|-----------------------------|--------------------------------|-----------------------------------------|
| Noyau                       | Soleil, Lune, Ascendant fiable | Soleil 3, Lune 3 (ASC hors score)       |
| Fonctionnement personnel    | Mercure, Vénus, Mars           | 2 chacun                                |
| Organisation et aspirations | Jupiter, Saturne               | 1 chacun                                |
| Contextualisation           | Uranus, Neptune, Pluton        | 0,5 chacun                              |
| Synthèse                    | Dominantes et configurations   | Résumé, jamais une confirmation de plus |

Accents : afficher les 3 premiers, garder les ex æquo, ne jamais désigner un signe « dominant » unique, ne pas majorer un signe pour sa largeur ; la concentration par degré (Dᵢ) reste un indicateur séparé. Une planète lente seule en signe ne justifie pas un long passage.

**Synthèse** : graphe de propositions reliées par 4 relations (renforcement, nuance, tension, contexte). Deux règles ne se renforcent que si elles portent sur le même thème, avec des facteurs distincts, et si leur relation est définie. La synthèse initiale contient au plus 3 fils majeurs, 1 tension structurante, 1 ressource d'articulation. Portrait court : 1 000 à 1 500 mots, 8 chapitres (expression, vie émotionnelle, communication, relations, manière d'agir, aspirations, tensions, introspection).

**Règles communes obligatoires**

- Un placement n'annule pas les autres ; une tension n'est pas un défaut moral ; une ressource n'est pas un talent garanti.

- Un aspect difficile n'annonce pas un événement malheureux ; un signe absent n'indique pas une incapacité.

- La progression dans un signe n'est pas un degré de maturité ; une frontière proche ne crée pas un mélange de signes.

- Classement incertain : scénarios distincts, jamais de probabilité non fondée.

- La personne peut refuser une lecture sans que ce refus serve de preuve.

- Aucun diagnostic, pronostic médical ou verdict sur une relation.

**Transition 12 → 13** : chaque différence est étiquetée D (découpage), S (symbolique), Y (synthèse) ou C (conventions de calcul). Phrase de référence : « Votre ancienne lecture mettait l'accent sur certains motifs. Notre référentiel en propose d'autres à partir des mêmes données ; il ne découvre pas que vous êtes soudain devenu quelqu'un d'autre. »

## J. Tests et critères d'acceptation

Ces contrôles vérifient une cohérence interne ; ils ne prouvent ni l'exactitude des données fictives ni la validité des interprétations. Sert : § 9 Métriques, portes G1 à G3.

**Tests unitaires du classement** (intervalle fictif Serpentaire 248°–267°)

| Entrée                      | Résultat attendu                            |
|-----------------------------|---------------------------------------------|
| λ = 256°                    | Oph, d = 8°, p = 8/19 ≈ 0,421               |
| λ = 248°                    | Oph (début inclus)                          |
| λ = nextafter(267, −∞)      | Oph                                         |
| λ = 267°                    | Signe suivant (fin exclue)                  |
| Intervalle 350°–20°, λ = 5° | p = 0,5                                     |
| λ = −355° ou 365°           | Même résultat que 5°                        |
| λ = 0° et λ = 360°          | Résultats identiques                        |
| Découpage invalide, NaN     | Rejet ; en production `expected_count = 13` |

**Contrôles de la roue avant publication** : Σ largeurs = 360° ; ni lacune ni chevauchement ; même transformation angulaire pour tous les calques ; ASC–DSC et MC–IC exactement opposés ; aucune longitude modifiée par l'anti-collision ; aspects ancrés sur les longitudes vraies ; ordre des étiquettes conservé ; repère du thème identique à celui des frontières ; ni angles ni maisons inventés sans heure ; avertissement visible pour les données fictives ou non vérifiées.

**Contrôles de correspondance de l'explorateur** (à chaque mise à jour) : classement des objets, présence des points selon les filtres, coordonnées rendues, séparations, présence et extrémités des cordes, référence de règle liée à la sélection, récupération de chaque longitude par projection inverse.

**Tests de mutation du portrait**

1.  Changer Mercure : les passages de communication réagissent.

2.  Retirer un aspect : sa synthèse disparaît ou est reformulée.

3.  Retirer l'heure : angles et maisons ne servent plus de justification.

4.  Sortir une planète d'un orbe : le lien est supprimé.

5.  Changer seulement un nom affiché : aucun calcul ne change.

**Critères pour annoncer un thème « effectivement calculé »**

- Frontières B exécutées et fichier archivé

- Statut de validation indépendante des frontières affiché

- Même matrice pour signes, positions, angles et maisons

- Cibles astronomiques identifiées, sans substitution silencieuse

- Fuseau et heure locale validés ; données UT1 et temporelles archivées

- Dix objets comparés à une seconde implémentation sur quelques cas

- Angles contrôlés par leurs équations de plan et leur branche

- Douze maisons couvrant le cercle une seule fois ; aspects vérifiés depuis les longitudes

- Roue utilisant les largeurs réelles des 13 signes

- Ni Ascendant ni maisons inventés pour une heure inconnue

- Résultats astronomiques séparés de toute interprétation

**Premier outil fonctionnel** quand : un thème de référence réel est calculé et vérifié ; son portrait est généré sans ajout non traçable ; les deux variantes contrôlées produisent les changements attendus ; le mode « heure inconnue » fonctionne ; roue et texte se référencent mutuellement ; fichiers de calcul et manifeste sont exportables.

**Évaluation empirique éventuelle** (hors produit) : portraits présentés à l'aveugle, textes témoins de longueur et de style comparables, critères fixés avant les résultats, données d'évaluation indépendantes de celles qui ajustent les règles.

## K. Points de vigilance pour les pistes visuelles

Sept règles de l'étude contredisent ou nuancent les planches actuelles ; aucune ne remet en cause les pistes, mais elles conditionnent leur passage dans le produit. Sert : § 5 du PRD, question Q3.

| Règle de l'étude                                                  | Écart dans les planches                                                                          | Proposition                                                                                                                                                                   |
|-------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Aucune couronne, étoile ou couleur qui suggère un signe supérieur | Pistes 1 et 2 : le Serpentaire est le seul secteur coloré (ambre, rouge)                         | Garder cet accent dans les contenus pédagogiques et de lancement, où il est le sujet ; dans la roue, même traitement que les 12 autres, l'accent ne marquant que la sélection |
| Glyphe U+26CE (⛎), aucun caducée ni autre emblème                | Piste 4 : pictogramme dessiné (bâton et serpent)                                                 | Remplacer par ⛎ en monochrome                                                                                                                                                |
| Identité retenue du Serpentaire : « la maîtrise révisable »       | Piste 4 : « Le savoir tenu avec responsabilité », formule de la première grille, ensuite élargie | Aligner la carte sur l'identité finale, ou trancher entre les deux                                                                                                            |
| Éléments et maîtrises désactivés dans B13                         | Piste 3 : le niveau « Interprétation » cite « éléments, maîtrises »                              | Reformuler en « fonctions symboliques, ressources, tensions »                                                                                                                 |
| Interface et valeurs en sans sérif sobre, chiffres tabulaires     | Piste 4 : question d'introspection en Cormorant Garamond                                         | Réserver le sérif aux titres de fiche ; valeurs et textes longs en sans sérif                                                                                                 |
| Aucun texte essentiel uniquement en capitales décoratives         | Pistes 1, 3, 4 : étiquettes en capitales espacées                                                | Acceptable pour des intitulés courts ; jamais pour une valeur ou une phrase                                                                                                   |
| Largeurs proportionnelles aux frontières calculées                | Pistes 1 et 2 : largeurs fictives (25° à 45°), bien signalées comme telles                       | Conserver la mention « fictif » jusqu'à la porte G1, puis régénérer depuis `frontieres.csv`                                                                                   |

Palette de référence de l'étude, à concilier avec la piste retenue : fond ivoire, texte bleu nuit, 13 teintes pastel non groupées par éléments, gris pour les structures, bleu, terre cuite et violet pour les aspects.
