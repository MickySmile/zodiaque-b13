# Rapport pour la porte G1 — les 13 frontières du modèle B

- Date : 15/11/2026
- Statut des données : **candidat**. La porte G1 est fermée ; la franchir est une décision de Micky après l'avis de l'expert (question Q5 du PRD). Ce rapport ne la franchit pas, et le moteur inscrit lui-même `independent_validation: not_performed` dans le manifeste.
- Rédigé par Claude Code à partir des sorties du moteur. Aucune longitude, largeur ou date de ce document n'a été saisie à la main : les quatre tableaux sont produits par les scripts cités en fin de rapport.
- Modèle : `model_b_iau_ecliptic_j2000_v1`.

## 1. En bref, et ce qui est demandé à l'expert

| Ce qui est établi | Par quoi |
| --- | --- |
| Le calcul rend 13 intervalles contigus, dans l'ordre attendu, de somme 360° | Contrôles du moteur (section 6) |
| Le repère R est bien l'écliptique moyen J2000, à 0,05″ près | Repère écliptique J2000 de JPL Horizons (section 5.2) |
| La chaîne de positions concorde avec Horizons à 10⁻⁸° près | Vecteurs de Horizons aux 13 frontières (section 5.1) |

| Ce qui n'est pas établi | Pourquoi |
| --- | --- |
| La position des frontières elles-mêmes | La grille des constellations vient de Skyfield dans tout le calcul ; aucune seconde source n'a été consultée |
| La convention d'équateur à B1875 | Équateur vrai (retenu par le PRD) ou moyen : l'écart atteint 0,007° (section 7, limite 1) |

**Les 13 frontières ne sont donc pas encore « vérifiées indépendamment » au sens de la porte G1.** Il est demandé à l'expert de valider la méthode (section 2), de trancher la convention d'équateur, et de dire quelle seconde source de frontières il jugerait recevable (section 8).

## 2. Méthode

**Repère.** Toutes les longitudes sont exprimées dans l'écliptique moyen J2000 fixe, par la matrice R = Qₓ(−ε₀) · B, où B est la matrice `ICRS_to_J2000` de Skyfield (biais de repère) et ε₀ = 84 381,406″. R est construite depuis cette définition ; elle n'est pas lue dans le repère `ecliptic_J2000_frame` de Skyfield, qui ignore le biais. L'origine des longitudes est l'axe x, la longitude croît de x vers y. La matrice utilisée figure dans `generes/manifest.json`.

**Frontières sources.** Grille des constellations de l'UAI telle que Skyfield la réalise d'après Roman 1987 (catalogue CDS VI/42) : 235 lignes d'ascension droite et 199 lignes de déclinaison, à l'équinoxe B1875. Skyfield l'interroge par `radec(epoch=B1875)`, avec sa matrice `Time.M`, qui contient la précession, la nutation et le biais de repère. Il s'agit d'une **réalisation Skyfield / Roman**, pas d'une reproduction exacte du tracé de Delporte.

**Cercle étudié.** Le cercle B est le grand cercle de latitude nulle du repère. Le classement du modèle B ne dépend que de la longitude ; la latitude d'un astre est calculée et conservée, mais ignorée.

**Algorithme** (annexe technique du PRD, § D1) :

1. Intersections analytiques du cercle B avec chaque ligne de la grille. Dans le repère de la grille, le cercle s'écrit v(λ) = p₁ cos λ + p₂ sin λ. Une ligne d'ascension droite donne une équation linéaire en cos λ et sin λ, dont on garde la solution située sur la demi-droite de la ligne et non sur le méridien opposé. Une ligne de déclinaison est un petit cercle, traité comme tel : elle donne zéro, une (tangence) ou deux solutions. La ligne 0 h, couture de la grille, est incluse.
2. Tri des longitudes candidates.
3. Constellation au milieu de chaque arc, par la fonction de Skyfield.
4. Suppression des coupures qui ne séparent pas deux constellations.
5. Contrôle des 13 noms et de leur ordre cyclique.
6. Sondage dense indépendant : échantillonnage au pas de 0,1°, puis dichotomie jusqu'à 10⁻⁸°.

**Arrêt plutôt que correction.** Le calcul s'arrête sans rien écrire si : le nombre d'intervalles n'est pas 13 ; une constellation occupe deux arcs ; l'ordre diffère de Ari, Tau, Gem, Cnc, Leo, Vir, Lib, Sco, Oph, Sgr, Cap, Aqr, Psc ; une largeur est nulle ; il y a lacune ou chevauchement ; la somme des largeurs s'écarte de 360° de 10⁻⁹° ou plus ; le classement juste avant ou juste après une frontière n'est pas celui attendu ; le sondage dense contredit les intersections analytiques. Chacun de ces arrêts a son test. L'ordre attendu est contrôlé après le calcul, jamais imposé.

**Un seul traitement.** Les treize signes passent par les mêmes fonctions. Le Serpentaire n'est pas ajouté à douze signes préexistants : il sort du même calcul que les autres, et sa présence déplace les frontières de ses voisins.

**Bornes.** Début inclus, fin exclue. Chaque frontière est calculée une fois : la fin d'un signe est exactement le même nombre que le début du suivant. Aucune zone de cuspide.

## 3. Versions et empreintes

| Élément | Valeur |
| --- | --- |
| Moteur | 0.1.0 |
| Python | 3.12.16 (Darwin x86_64) |
| Skyfield | 1.55 |
| NumPy | 2.5.4 |
| Grille des frontières | `constellations.npz` de Skyfield, SHA-256 `febb2947d9062443c2c4803d2c6a5427e3ea381f0f8f00413d710ba588a54b13` |
| Éphéméride (section 5.1 seulement) | JPL DE440s, `de440s.bsp`, SHA-256 `c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2` |
| Réponse de Horizons, ICRF | `tests/fixtures/horizons/sun-boundaries-2026_20261115T145809Z.txt`, reçue le 2026-11-15 à 14:58:09 UTC, SHA-256 `b6a101ff4643e47be218b6b3d7530a9fac06798a86e3dd88c1f98881cb5c2def` |
| Réponse de Horizons, écliptique J2000 | `tests/fixtures/horizons/sun-ecliptic-2026_20261115T145809Z.txt`, reçue au même instant, SHA-256 `475b7c7095adb168b4844e1c2913e2d5d583bc8c989d691ba892aa40c70fb6aa` |

Les frontières ne dépendent que de Skyfield et de sa grille. L'éphéméride n'intervient que dans la comparaison de la section 5.1.

## 4. Résultat : les 13 frontières

Degrés décimaux, double précision, sans arrondi. Source : `generes/frontieres.csv`.

| Signe | Début (°) | Fin (°) | Largeur (°) | Ligne de la grille B1875 qui porte le début |
| --- | --- | --- | --- | --- |
| Ari | 28.6888895268867 | 53.4192334469643 | 24.730343920077598 | ascension droite 1.6666666666666667 h |
| Tau | 53.4192334469643 | 90.14167034656523 | 36.722436899600936 | ascension droite 3.283333333333333 h |
| Gem | 90.14167034656523 | 117.9891894472838 | 27.84751910071857 | ascension droite 5.883333333333334 h |
| Cnc | 117.9891894472838 | 138.03950306917864 | 20.05031362189483 | ascension droite 7.883333333333334 h |
| Leo | 138.03950306917864 | 173.85221512784494 | 35.81271205866631 | ascension droite 9.25 h |
| Vir | 173.85221512784494 | 217.81213913048083 | 43.95992400263589 | ascension droite 11.516666666666667 h |
| Lib | 217.81213913048083 | 241.04026420019215 | 23.228125069711325 | ascension droite 14.25 h |
| Sco | 241.04026420019215 | 247.6397003345401 | 6.59943613434794 | déclinaison -20.0° |
| Oph | 247.6397003345401 | 266.23932905939057 | 18.599628724850476 | ascension droite 16.266666666666666 h |
| Sgr | 266.23932905939057 | 299.6572869054095 | 33.41795784601891 | ascension droite 17.6 h |
| Cap | 299.6572869054095 | 327.4887144499743 | 27.831427544564804 | ascension droite 20.0 h |
| Aqr | 327.4887144499743 | 351.65260676101593 | 24.16389231104165 | ascension droite 21.866666666666667 h |
| Psc | 351.65260676101593 | 28.6888895268867 | 37.036282765870794 | déclinaison -4.0° |

- Coupures candidates examinées : 364, dont 13 séparent deux constellations. Aucune ligne de la grille n'est tangente au cercle.
- Somme des 13 largeurs : écart à 360° de 0,0° en double précision (tolérance 10⁻⁹°).
- Onze frontières sont portées par une ligne d'ascension droite, deux par une ligne de déclinaison (début du Scorpion et début des Poissons).
- Un seul intervalle traverse 0° : celui des Poissons.
- Précision de ces nombres : ils sont cohérents avec la grille de Skyfield à 10⁻⁹° près, c'est ce que le contrôle des voisins certifie. Leur justesse par rapport au ciel est bornée par les limites de la section 7, bien plus grandes.

## 5. Seconde chaîne : JPL Horizons

Pour chaque frontière, on cherche l'instant de 2026 où la longitude astrométrique géocentrique du Soleil, dans le repère B, égale la frontière (DE440s, `.observe()` sans `.apparent()`, méthode de Brent en échelle TT, arrêt à 0,01 s). À ces 13 instants, deux réponses de Horizons sont archivées. La colonne 31 de Horizons, longitude apparente de date, n'est pas utilisée : elle n'est pas comparable telle quelle.

### 5.1 Chaîne de positions

Horizons donne le vecteur géocentrique du Soleil dans l'ICRF, corrigé du temps de lumière, d'après son éphéméride DE441. On le compare à celui du moteur au même instant.

**Tolérance, déclarée avant le calcul : 10⁻⁶°** (3,6 millièmes de seconde d'arc). Elle couvre l'arrêt de Brent (0,01 s, soit environ 1,2 × 10⁻⁷° de mouvement solaire), la transmission des instants à 10⁻⁹ jour près et l'écart attendu entre DE440s et DE441.

| Signe | Frontière (°) | Instant du passage (JD TDB) | Écart entre chaînes (°) | Séparation (″) | Écart à la frontière (°) | Tolérance (°) | Latitude du Soleil (°) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ari | 28.6888895268867 | 2461149.599696506 | +1.057e-11 | 3.808e-08 | +5.696e-10 | 1e-06 | -0.001788 |
| Tau | 53.4192334469643 | 2461175.077399056 | +9.265e-12 | 3.339e-08 | -4.364e-10 | 1e-06 | -0.002841 |
| Gem | 90.14167034656523 | 2461213.383457430 | +1.364e-12 | 5.786e-09 | +9.834e-12 | 1e-06 | -0.003501 |
| Cnc | 117.9891894472838 | 2461242.580568803 | +6.821e-13 | 3.262e-09 | -3.502e-10 | 1e-06 | -0.002998 |
| Leo | 138.03950306917864 | 2461263.542377430 | +1.037e-11 | 3.744e-08 | +1.604e-10 | 1e-06 | -0.001949 |
| Vir | 173.85221512784494 | 2461300.589269841 | +3.723e-12 | 1.334e-08 | -1.029e-10 | 1e-06 | -0.000188 |
| Lib | 217.81213913048083 | 2461345.107379160 | -3.610e-12 | 1.331e-08 | -8.949e-09 | 1e-06 | +0.002519 |
| Sco | 241.04026420019215 | 2461368.207190530 | -1.236e-11 | 4.458e-08 | -2.732e-09 | 1e-06 | +0.003423 |
| Oph | 247.6397003345401 | 2461374.731528084 | -3.240e-12 | 1.211e-08 | +2.180e-10 | 1e-06 | +0.003419 |
| Sgr | 266.23932905939057 | 2461393.041226124 | -4.547e-12 | 1.657e-08 | -3.664e-10 | 1e-06 | +0.003712 |
| Cap | 299.6572869054095 | 2461060.590705314 | +9.493e-12 | 3.442e-08 | +5.766e-10 | 1e-06 | +0.002741 |
| Aqr | 327.4887144499743 | 2461088.032210967 | +1.131e-11 | 4.088e-08 | +4.362e-10 | 1e-06 | +0.001502 |
| Psc | 351.65260676101593 | 2461112.099856870 | +1.876e-12 | 7.095e-09 | -1.086e-10 | 1e-06 | +0.000022 |

- Écart maximal entre les deux chaînes au même instant : 1,236 × 10⁻¹¹°, soit une séparation angulaire de 4,458 × 10⁻⁸″.
- Écart maximal entre la longitude selon Horizons et la frontière : 8,949 × 10⁻⁹°.

**Portée.** Ce contrôle établit que l'éphéméride, la correction du temps de lumière et les échelles de temps du moteur donnent le même Soleil que Horizons. La matrice R étant appliquée aux deux chaînes, il ne dit **rien de R**, ni des frontières : une erreur sur l'une ou l'autre s'y annulerait. Un test montre qu'un vecteur décalé de 0,01″ le ferait échouer.

**Dernière colonne.** Le Soleil n'est pas sur le cercle B : sa latitude dans le repère atteint quelques millièmes de degré en 2026. Le modèle B classe par la longitude seule ; un classement par la position complète (modèle C) changerait de constellation à un instant légèrement différent, surtout aux deux frontières portées par une ligne de déclinaison.

### 5.2 Repère R

Horizons donne aussi les mêmes vecteurs dans son propre repère écliptique J2000, qu'il définit dans sa réponse : obliquité IAU 1976 de 84 381,448″ par rapport au plan de l'ICRF, axe x de l'ICRF. On applique R aux vecteurs ICRF de Horizons et on compare à ses vecteurs écliptiques. Seules des données de Horizons entrent dans ce contrôle : il confronte R à une définition écrite ailleurs.

**Tolérance, déclarée avant le calcul : 0,1″.** L'écart attendu est connu : la différence d'obliquité entre les deux conventions (84 381,448″ − 84 381,406″ = 0,042″) et le biais de repère de l'ICRS, que R applique et que Horizons n'applique pas (au plus 0,023″).

| Signe | Instant (JD TDB) | Séparation R / Horizons (″) | Tolérance (″) | Écart en longitude (°) | Écart en latitude (°) | Résidu expliqué (″) |
| --- | --- | --- | --- | --- | --- | --- |
| Ari | 2461149.599696506 | 0.006968 | 0.1 | +1.885e-06 | -4.389e-07 | 7.688e-12 |
| Tau | 2461175.077399056 | 0.017108 | 0.1 | +1.885e-06 | +4.362e-06 | 3.364e-11 |
| Gem | 2461213.383457430 | 0.035880 | 0.1 | +1.885e-06 | +9.787e-06 | 7.765e-12 |
| Cnc | 2461242.580568803 | 0.041505 | 0.1 | +1.885e-06 | +1.137e-05 | 6.699e-12 |
| Leo | 2461263.542377430 | 0.039761 | 0.1 | +1.885e-06 | +1.088e-05 | 2.292e-11 |
| Vir | 2461300.589269841 | 0.025615 | 0.1 | +1.885e-06 | +6.861e-06 | 5.926e-12 |
| Lib | 2461345.107379160 | 0.008392 | 0.1 | +1.885e-06 | -1.371e-06 | 9.208e-13 |
| Sco | 2461368.207190530 | 0.021678 | 0.1 | +1.885e-06 | -5.719e-06 | 2.369e-11 |
| Oph | 2461374.731528084 | 0.025448 | 0.1 | +1.885e-06 | -6.813e-06 | 1.032e-11 |
| Sgr | 2461393.041226124 | 0.034400 | 0.1 | +1.885e-06 | -9.368e-06 | 1.211e-11 |
| Cap | 2461060.590705314 | 0.041547 | 0.1 | +1.885e-06 | -1.139e-05 | 5.917e-12 |
| Aqr | 2461088.032210967 | 0.037285 | 0.1 | +1.885e-06 | -1.018e-05 | 2.483e-11 |
| Psc | 2461112.099856870 | 0.026811 | 0.1 | +1.885e-06 | -7.205e-06 | 4.815e-12 |

- Séparation maximale entre R et l'écliptique J2000 de Horizons : 0,041547″.
- Résidu maximal une fois refait le calcul avec l'obliquité de Horizons et sans biais : 3,364 × 10⁻¹¹″ (tolérance 10⁻⁶″).

**Portée.** R est l'écliptique moyen J2000 à mieux que 0,05″, et tout l'écart avec Horizons s'explique par deux conventions documentées. Des tests montrent qu'une obliquité fausse d'une seconde d'arc, ou une rotation dans le mauvais sens, ferait échouer le contrôle.

### 5.3 Ce que Horizons ne dit pas

Aucune de ces deux comparaisons ne porte sur la grille des constellations. Si la grille de Skyfield était décalée, ou lue dans la mauvaise convention, les deux resteraient d'accord.

## 6. Contrôles internes

| Contrôle | Résultat |
| --- | --- |
| RᵀR = I | à 10⁻¹² près |
| R égale à sa définition Qₓ(−ε₀) · B | exactement |
| R distincte de la matrice du repère nommé de Skyfield | oui, écart inférieur à 10⁻⁶ et non nul |
| 13 intervalles, ordre attendu | oui |
| Fin d'un signe = début du suivant | exactement, 13 fois sur 13 |
| Chaque coupure candidate, réinjectée, est sur sa ligne de la grille | 364 sur 364, résidu inférieur à 10⁻¹⁰° |
| Nombre de coupures conforme à la grille | 236 lignes d'ascension droite, couture comprise, et 2 par déclinaison atteinte |
| Classement à 10⁻⁹° avant et après chaque frontière | conforme, 13 fois sur 13 |
| Sondage dense (0,1°, dichotomie à 10⁻⁸°) | 13 changements, chacun encadre une frontière analytique |
| Milieux et voisins des intervalles par le repère nommé de Skyfield | même constellation, 13 fois sur 13 |
| Régénération sur la machine de calcul | CSV identique octet pour octet (`--verifier`) |
| Régénération sur une autre machine | bornes comparées à 10⁻¹¹° près, signes et ordre exacts (décision 0009) |

Ces contrôles vérifient la cohérence interne. Le sondage dense et le repère nommé reposent sur la même grille que le calcul principal : ils écartent une erreur d'algèbre, pas une erreur de la grille. Le sondage au pas de 0,1° ne prouve pas l'exhaustivité : une constellation plus étroite que le pas pourrait lui échapper, et seule l'énumération analytique de toutes les lignes la garantit.

## 7. Limites connues

1. **Équateur vrai ou moyen de B1875.** Skyfield interroge sa grille avec `Time.M`, qui inclut la nutation : c'est l'équateur vrai de l'époque. Le PRD retient cette convention et le moteur la suit. Le tracé de Delporte se réfère à l'équinoxe 1875,0, ce qui s'entend d'ordinaire comme l'équateur moyen ; cela n'a pas été vérifié sur une source primaire. Les deux repères diffèrent d'une rotation de 10,07″. Déplacement de chaque frontière si la grille était lue à l'équateur moyen (précession et biais, sans nutation) :

| Signe | Début, équateur vrai (°) | Déplacement à l'équateur moyen (°) | Déplacement (″) | Ligne de la grille |
   | --- | --- | --- | --- | --- |
   | Ari | 28.6888895268867 | -0.002094 | -7.54 | ascension droite 1.6666666666666667 h |
   | Tau | 53.4192334469643 | -0.002173 | -7.82 | ascension droite 3.283333333333333 h |
   | Gem | 90.14167034656523 | -0.001733 | -6.24 | ascension droite 5.883333333333334 h |
   | Cnc | 117.9891894472838 | -0.001325 | -4.77 | ascension droite 7.883333333333334 h |
   | Leo | 138.03950306917864 | -0.001226 | -4.41 | ascension droite 9.25 h |
   | Vir | 173.85221512784494 | -0.001575 | -5.67 | ascension droite 11.516666666666667 h |
   | Lib | 217.81213913048083 | -0.002163 | -7.79 | ascension droite 14.25 h |
   | Sco | 241.04026420019215 | +0.006899 | +24.84 | déclinaison -20.0° |
   | Oph | 247.6397003345401 | -0.002064 | -7.43 | ascension droite 16.266666666666666 h |
   | Sgr | 266.23932905939057 | -0.001798 | -6.47 | ascension droite 17.6 h |
   | Cap | 299.6572869054095 | -0.001309 | -4.71 | ascension droite 20.0 h |
   | Aqr | 327.4887144499743 | -0.001259 | -4.53 | ascension droite 21.866666666666667 h |
   | Psc | 351.65260676101593 | -0.002617 | -9.42 | déclinaison -4.0° |

   L'écart va de 4,4″ à 24,8″. Le Soleil parcourt 0,0069° en dix minutes environ : près du début du Scorpion, la convention peut changer le signe solaire d'une naissance. La question est consignée dans `docs/decisions/0008-equateur-vrai-ou-moyen-de-b1875.md`. Tant qu'elle est ouverte, c'est elle qui borne la précision d'une frontière, pas les 10⁻⁹° du calcul.
2. **Réalisation Skyfield / Roman.** Les frontières officielles de l'UAI sont celles de Delporte (1930). La grille de Skyfield en est une réalisation numérique d'après les données de Roman (1987). Aucune comparaison au tracé d'origine ni à une autre numérisation n'a été faite.
3. **Arrondi des données de Roman.** Le catalogue VI/42 donne ses coordonnées avec un nombre fini de décimales. Les lignes de la grille de Skyfield qui portent les 13 frontières ont des valeurs en fractions simples d'heure ou de degré (dernière colonne du tableau de la section 4), ce qui suggère que l'arrondi a été levé en amont ; cela n'a pas été vérifié ici.
4. **Modèle de précession.** Skyfield ramène les directions à B1875 par sa précession moderne. Delporte et Roman travaillaient avec celle de leur temps. L'effet de cet écart sur un siècle et quart n'a pas été chiffré.
5. **Seconde chaîne partielle.** Voir la section 5.3 : Horizons valide les positions et le repère, pas la grille.
6. **Une seule année, un seul astre.** La comparaison de positions porte sur le Soleil en 2026. Les frontières elles-mêmes ne dépendent pas de la date, le repère étant fixe.
7. **Reproductibilité entre machines.** La régénération est identique octet pour octet sur la machine de calcul (macOS, x86_64). Sous Linux, où tourne l'intégration continue, le fichier régénéré diffère au dernier chiffre de certaines bornes : constaté le 15/11/2026, la matrice R et la somme des largeurs restant identiques. Le dernier chiffre d'un résultat en double précision dépend de la bibliothèque mathématique du système. Décision 0009 : hors de la machine de référence, les bornes sont comparées à 10⁻¹¹° près (3,6 × 10⁻⁸″), signes et ordre restant exacts. Le fichier `generes/frontieres.csv` fait foi : le classement d'un astre lira ses bornes, sans les recalculer.
8. **Bornes exactes.** La convention « début inclus, fin exclue » est celle du moteur, appliquée à la longitude. La fonction de Skyfield a ses propres conventions sur les lignes de la grille (à gauche pour l'ascension droite, à droite pour la déclinaison) ; elles n'interviennent qu'en un point isolé et ne changent aucune largeur. Le classement d'un astre se fera sur les bornes du fichier, pas en rappelant la grille.

## 8. Questions pour l'expert

1. **Convention d'équateur.** Pour interroger la grille à l'équinoxe B1875, faut-il l'équateur vrai (avec nutation, convention de Skyfield et du PRD) ou l'équateur moyen ? Et avec quel modèle de précession ?
2. **Source des frontières.** La réalisation Skyfield / Roman est-elle acceptable pour cet usage, ou faut-il une seconde réalisation indépendante, par exemple la numérisation du tracé de Delporte par P. Barbier, prévue en option dans `donnees/sources.toml` ?
3. **Tolérance.** Quelle tolérance retenir pour déclarer une frontière « vérifiée indépendamment » : la seconde d'arc, le millième de degré, autre chose ?
4. **Chaîne indépendante pour la grille.** Une vérification par l'identifiant de constellation que Horizons attribue à un astre (table d'observateur) serait-elle recevable, sachant qu'elle classe la position complète et non la longitude seule ?
5. **Repère.** La définition retenue (ε₀ = 84 381,406″, biais de repère de Skyfield, écliptique moyen J2000 fixe) appelle-t-elle une réserve, au vu de la section 5.2 ?
6. **Lignes de déclinaison.** Les deux frontières portées par une ligne de déclinaison (Scorpion, Poissons) sont les plus sensibles à la convention d'équateur, le cercle les coupant sous un angle faible. Méritent-elles un traitement ou un avertissement particulier ?

## 9. Reproduire

```text
uv run python scripts/construire_frontieres.py               écrit generes/frontieres.csv et le manifeste
uv run python scripts/construire_frontieres.py --verifier    régénère et compare, sans rien écrire
uv run python scripts/construire_frontieres.py --sensibilite tableau de la section 7, limite 1
uv run python scripts/comparer_horizons.py --tableau         rejoue hors ligne les deux comparaisons archivées
uv run python scripts/comparer_horizons.py --interroger      interroge de nouveau Horizons
uv run pytest tests/test_coordinates.py tests/test_boundaries.py tests/test_construire_frontieres.py tests/test_comparer_horizons.py
```

Code : `moteur/coordinates.py`, `moteur/boundaries.py`, `scripts/construire_frontieres.py`, `scripts/comparer_horizons.py`.
