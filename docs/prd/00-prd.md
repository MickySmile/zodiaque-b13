<!-- Source : PRD « Thème astral à 13 signes » (claude.ai, propriétaire : Micky), export du 2026-11-15. Fichier en lecture seule pour Claude Code (deny Edit sur docs/prd/**). Les schémas d'origine sont transcrits en blocs texte. -->

# PRD — Thème astral à 13 signes

2026-11-15 · Micky

**Statut** : Brouillon · **Version** : 0.4 · **Propriétaire** : Micky

## 1. Résumé

Le Soleil traverse 13 constellations, mais sans conventions déclarées un placement dans un zodiaque à 13 signes n'est ni reproductible ni séparé de son interprétation. Nous construisons une application web qui calcule le thème natal dans le modèle B (13 intervalles inégaux, écliptique J2000 fixe, frontières UAI), l'affiche sur une roue proportionnelle et le lit avec un référentiel symbolique traçable, B13. Résultat attendu : 13 frontières vérifiées, 10 thèmes de référence concordants et 100 % des textes reliés à leurs règles. MVP visé 3 à 8 semaines après validation des objectifs ; aucune frontière réelle n'est encore calculée.

## 2. Contexte et problème

**Problème.** Une personne qui apprend que le Soleil traverse 13 constellations ne peut pas obtenir son placement dans un zodiaque à 13 signes de façon reproductible : sans repère, frontières et conventions déclarés, un même instant peut recevoir des signes différents, et rien ne sépare ce qui est mesuré de ce qui est interprété.

**Preuves (étude PDF, 13 questions-réponses)**

- Les 12 signes sont un découpage conventionnel : 12 secteurs égaux de 30°, hérités des Babyloniens (calendrier de 12 mois lunaires, attesté vers le Ve siècle av. J.-C.).

- Les 13 constellations sont les régions réellement traversées, de tailles inégales. Le Serpentaire (Ophiuchus) se situe entre le Scorpion et le Sagittaire ; ce n'est pas une découverte récente.

- L'astrologie tropicale définit les signes par les saisons (Bélier à l'équinoxe de mars), et la précession les a décalés des constellations. Ajouter le Serpentaire revient donc à adopter **un autre système**, pas à corriger l'ancien.

- Un calcul fiable exige de figer au moins 10 conventions (repère écliptique, réalisation des frontières UAI, positions astrométriques, observateur, bornes). Changer l'une d'elles déplace les instants de passage.

- **Preuve manquante** : aucune donnée utilisateur (entretiens, usage, support). À collecter avant la v1.0 (voir Questions ouvertes).

**État actuel et contournements.** On trouve des listes de dates de naissance fixes, présentées comme un calendrier perpétuel. L'étude les écarte : les instants de passage varient d'une année à l'autre et une naissance proche d'une frontière exige l'heure et le fuseau.

**Coût de l'inaction.** Non chiffré faute de données. Qualitativement : des personnes reçoivent un signe faux ou instable, et la précision astronomique sert d'argument d'autorité à des interprétations qu'elle ne valide pas.

## 3. Objectifs et non-objectifs

Les cibles ci-dessous sont des propositions : le sponsor les valide avant la phase de conception. Le départ est zéro partout, car l'étude n'a exécuté aucun calcul astronomique réel.

| Objectif                              | Métrique                                                                                                     | Départ                              | Cible    | Échéance     |
|---------------------------------------|--------------------------------------------------------------------------------------------------------------|-------------------------------------|----------|--------------|
| O1 — Référentiel astronomique vérifié | Frontières B13 calculées puis comparées à une réduction indépendante, écart publié                           | 0 / 13                              | 13 / 13  | Fin du MVP   |
| O2 — Calcul de thème exact            | Thèmes de référence concordant avec une seconde chaîne harmonisée (signe identique, écart de longitude ≤ 1″) | 0                                   | 10 / 10  | Fin de la V1 |
| O3 — Interprétation traçable          | Passages du portrait reliés à au moins une règle et un placement                                             | Démonstrateur synthétique seulement | 100 %    | Fin de la V1 |
| O4 — Compréhension du système         | Testeurs capables d'expliquer « signe ≠ constellation » après une session                                    | Non mesuré                          | ≥ 7 / 10 | Pilote V1    |

**Lien stratégique** : à préciser par le sponsor (question ouverte Q1).

**Non-objectifs**

- Démontrer ou suggérer la validité de l'astrologie : la précision du calcul n'est jamais présentée comme une preuve.

- Mesurer la personnalité, prédire des événements, établir un diagnostic médical ou un score de compatibilité.

- Corriger l'astrologie tropicale à 12 signes ou la déclarer fausse.

- Reproduire les textes, maîtrises ou dignités d'un service existant (Astrotheme cité comme niveau de profondeur, pas comme modèle).

- Proposer 13 secteurs égaux, 13 maisons ou un calendrier perpétuel de dates.

## 4. Utilisateurs et scénarios

Aucun persona ne repose encore sur une observation réelle : ce sont des hypothèses déduites de l'étude, à confirmer par 5 entretiens chacun avant la v1.0.

| Persona                                 | Contexte                                                        | Besoin                                                     | Frustration                                    | Niveau        | Source                                     |
|-----------------------------------------|-----------------------------------------------------------------|------------------------------------------------------------|------------------------------------------------|---------------|--------------------------------------------|
| **Principal — Le curieux du 13e signe** | Connaît son signe traditionnel, a entendu parler du Serpentaire | Savoir « où il tombe » et pourquoi                         | Réponses contradictoires, dates approximatives | Débutant      | Hypothèse (question fondatrice de l'étude) |
| Secondaire — Le praticien explorateur   | Pratique l'astrologie, teste un système alternatif              | Thème complet, conventions explicites, exports             | Outils opaques sur leurs calculs               | Avancé        | Hypothèse                                  |
| Secondaire — Le médiateur               | Enseigne ou vulgarise (astronomie, esprit critique)             | Montrer la différence mesure / convention / interprétation | Supports qui mélangent les niveaux             | Intermédiaire | Hypothèse                                  |

**Utilisateur principal** : le curieux du 13e signe. Le parcours par défaut est conçu pour lui ; le détail technique reste accessible au praticien.

**Scénarios clés** (déclencheur → actions → résultat)

1.  **Connaître son signe B13** : il lit « il existe 13 signes » → saisit date, heure et lieu de naissance → obtient son signe solaire B13, sa position dans le signe et, s'il est né près d'une frontière, les deux possibilités.

2.  **Explorer son thème** : il veut comprendre son thème → sélectionne une planète sur la roue → voit sa ligne de tableau, ses aspects et sa lecture symbolique avec les règles qui la justifient.

3.  **Comparer 12 et 13** : son signe a changé → bascule vers le découpage à 12 secteurs → voit quels placements changent et pourquoi (découpage, symbolique ou synthèse).

4.  **Heure inconnue** : il ignore son heure → coche « heure inconnue » → obtient les positions de la journée, sans Ascendant ni maisons, sous le nom « carte de référence à midi ».

5.  **Partager ou enseigner** : le médiateur prépare un support → exporte la roue et ses conventions → obtient un SVG, un PNG ou un PDF légendé et daté.

**Parties prenantes non utilisatrices** : expert astronome (validation des frontières), rédacteur du référentiel symbolique, juriste RGPD (données de naissance).

## 5. Solution proposée

**Concept.** Une application web qui calcule un thème natal dans le **modèle B** — 13 intervalles de longitude inégaux, obtenus en croisant l'écliptique J2000 fixe avec les frontières UAI — et le lit avec un référentiel symbolique déclaré, **B13**. Trois principes : un seul jeu de données alimente toutes les vues ; chaque texte reste relié à la configuration qui le justifie ; chaque résultat affiche son niveau (mesure, convention, interprétation).

**Règle centrale.** Pour un signe i de début bᵢ et un astre de longitude λ :

```latex
w_i = \operatorname{wrap}(b_{i+1} - b_i), \quad d_i = \operatorname{wrap}(\lambda - b_i), \quad \text{astre} \in i \iff 0 \le d_i < w_i, \quad p_i = d_i / w_i
```

wrap(x) ramène un angle dans \[0°, 360°\[. La règle gère un signe qui traverse 0° ; pᵢ est une position géométrique, pas une intensité psychologique.

```text
Le calcul alimente l'interprétation, jamais l'inverse
(chaîne de traitement par niveau de connaissance ; [*] = dépendance critique, pas encore calculée)

01 MESURE / CALCUL   Saisie de naissance ──────► Positions des astres ─────────┐
                     date, heure locale, lieu     Skyfield + DE440s              │
                     fuseau et incertitude        astrométrique, J2000 fixe      │
                                                        │                        ▼
02 CONVENTION        13 frontières B13 [*] ─────► Classement ──────────────► EXPLORATEUR
                     écliptique × limites UAI     signe, degrés, progression   roue proportionnelle
                     versionnées, Σ = 360°        maison, aspects, orbes       tableaux, comparateur
                                                        │                      fiches de signe
                                                        ▼                      exports SVG, PNG, PDF
03 INTERPRÉTATION    Base symbolique B13 ───────► Règles et portrait ───────►  badge de niveau
                     13 fonctions de signe        propositions traçables       sur chaque vue
                     provenance H, M ou C         rédaction + vérificateur
                                                        ┆
04 ÉVALUATION        ┆ Évaluation empirique — hors produit
                     ┆ La précision du calcul ne valide pas une lecture
```

Chaque niveau ne consomme que les résultats du niveau au-dessus ; l'explorateur affiche, sur chaque vue, le niveau de ce qu'il montre.

**Pistes visuelles** ([canevas « Zodiaque à 13 signes — pistes visuelles »](https://claude.ai/artifact/YEuxhAydd1oWooFKojqPY1)). Les quatre pistes ne sont pas concurrentes : chacune couvre une surface du produit.

| Piste                             | Intention                                                                                    | Signature                                                           | Usage recommandé                                                    |
|-----------------------------------|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------|---------------------------------------------------------------------|
| 1 · Observatoire                  | Planche d'étude scientifique : 2 roues côte à côte (12 égaux / 13 inégaux) et les 4 formules | Fond nuit, Space Grotesk + IBM Plex Mono, Serpentaire seul en ambre | **Identité de l'explorateur** : roue, tableaux, mode sombre         |
| 2 · Suisse — Règle vs territoires | « 12 ≠ 13 » : barres de 30° face à 13 barres proportionnelles                                | Blanc, Inter Tight, noir, accent rouge                              | **Comparateur 12 / 13** et contenus de lancement                    |
| 3 · Pédagogique — Quatre niveaux  | Mesure → Convention → Interprétation → Évaluation                                            | Vert pâle, Archivo, 4 blocs numérotés                               | **Vocabulaire des badges de statut** et premier écran d'explication |
| 4 · Carte de signe — Serpentaire  | Fiche façon carte : motif, ressources, tensions, question d'introspection                    | Violet profond, or, Cormorant Garamond, format 750 × 1050           | **Gabarit des 13 fiches de signe** et partage                       |

Contraintes communes issues de l'étude :

- Les secteurs sont proportionnels aux largeurs calculées. Les largeurs actuelles des planches (Serpentaire 248°–267°, 19°) sont **fictives** et ne doivent pas être réutilisées.

- Les couleurs identifient les signes ; elles ne réintroduisent ni éléments, ni modalités, ni dignités.

- Aucune information n'est portée par la seule couleur (symbole, nom ou motif en plus).

- Les planches 1 à 3 sont au format 1080 × 1350 (portrait réseaux sociaux) : elles fixent un ton, pas encore les écrans de l'application.

- Risque de la piste 4 : son registre ésotérique peut contredire le cadrage rigoureux. À équilibrer par la mention « proposition contemporaine » déjà présente.

**Alternatives écartées**

| Alternative                                                     | Raison                                                                                |
|-----------------------------------------------------------------|---------------------------------------------------------------------------------------|
| 13 secteurs égaux de 27,7°                                      | Ne décrit plus les constellations traversées ; c'est un autre modèle                  |
| Ajouter le Serpentaire au zodiaque tropical                     | Le tropical est défini par les saisons, pas par les constellations                    |
| Liste fixe de dates de naissance                                | Les passages varient selon l'année ; faux près des frontières                         |
| Modèle C : constellation effective de chaque planète            | Utilise la latitude et les contours complets ; modèle distinct                        |
| 13 maisons                                                      | Le nombre de maisons est indépendant du nombre de signes                              |
| Transférer éléments, modalités, maîtrises, dignités             | Répartition impossible ou arbitraire sur 13 ; remplacés par 13 fonctions symboliques  |
| Laisser un modèle de langage calculer ou choisir les placements | Le modèle rédige à partir de propositions autorisées ; il ne décide d'aucune position |

## 6. Exigences fonctionnelles

20 exigences, dont 6 « Must » (30 %). « Je » désigne le curieux sauf mention contraire.

| ID    | En tant que… je veux… afin de…                                                                                                      | Critères d'acceptation                                                                                                                                                                                                      | Priorité |
|-------|-------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-01 | Je veux saisir mes données de naissance (date, heure locale, statut de l'heure, lieu) afin d'obtenir mon thème.                     | Étant donné une heure inexistante (passage à l'heure d'été), quand je valide, alors un message bloquant s'affiche et aucun thème n'est calculé.                                                                             | Must     |
| FR-02 | Je veux connaître le signe B13 de chaque objet afin de me situer dans le zodiaque à 13 signes.                                      | Étant donné λ = bᵢ, quand le classement s'exécute, alors le signe i est retourné (début inclus, fin exclue). λ = 365° est classé comme 5°.                                                                                  | Must     |
| FR-03 | Je veux voir les signes possibles quand l'incertitude de mon heure chevauche une frontière, afin de ne pas recevoir un signe faux.  | Étant donné une heure à ±10 min dont l'intervalle contient un franchissement, quand le thème s'affiche, alors les deux signes sont présentés comme possibilités, sans probabilité.                                          | Must     |
| FR-04 | Je veux être averti d'une heure ambiguë afin de choisir la bonne occurrence.                                                        | Étant donné 02:30 le jour du passage à l'heure d'hiver, quand je valide, alors deux scénarios sont proposés jusqu'à ce que je précise l'occurrence.                                                                         | Should   |
| FR-05 | Je veux calculer un thème sans heure afin d'explorer malgré tout mes positions.                                                     | Étant donné « heure inconnue », quand le thème s'affiche, alors aucun Ascendant ni aucune maison n'apparaît et le titre est « carte de référence à midi ».                                                                  | Should   |
| FR-06 | Je veux consulter les dates d'entrée du Soleil dans chaque signe pour une année choisie afin de découvrir le système.               | Étant donné l'année 2026, quand j'ouvre le calendrier, alors 13 entrées s'affichent en UTC et en heure de Paris, avec la mention « indicatif : près d'une frontière, l'heure de naissance compte ».                         | Should   |
| FR-07 | Je veux les positions des 10 objets principaux afin de lire mon thème.                                                              | Étant donné un thème calculé, quand j'ouvre le tableau, alors chaque objet affiche longitude, signe, position interne, maison, mouvement (direct, rétrograde, stationnaire ou indéterminé) et cible (centre ou barycentre). | Must     |
| FR-08 | Je veux mon Ascendant B, mon Milieu du Ciel B et 12 maisons égales de 30° depuis l'Ascendant afin de situer mes placements.         | Étant donné un lieu où l'Ascendant est indéfini, quand le thème est calculé, alors Ascendant et maisons sont absents avec un statut explicite, sans système de substitution.                                                | Should   |
| FR-09 | Je veux les aspects entre objets afin de voir leurs relations.                                                                      | Étant donné Mercure et Mars séparés de 91,8°, quand les aspects sont calculés, alors un carré est retenu (écart 1,8°, orbe 5°). Orbes : conjonction 6°, sextile 4°, carré 5°, trigone 5°, opposition 6°, objet–angle 3°.    | Should   |
| FR-10 | Je veux une roue à 13 secteurs proportionnels afin de voir la taille réelle de chaque signe.                                        | Étant donné des largeurs calculées, quand la roue est rendue, alors chaque secteur couvre sa largeur à 0,1° près, chaque point est à sa longitude, et une étiquette déplacée est reliée à son point par un trait.           | Must     |
| FR-11 | Je veux sélectionner un astre, un signe, une maison ou un aspect afin de voir tout ce qui s'y rapporte.                             | Étant donné que je sélectionne Mercure, quand la sélection s'applique, alors son point, sa ligne de tableau et son panneau de détail sont mis en évidence, avec les identifiants des règles.                                | Should   |
| FR-12 | Je veux cliquer sur une phrase du portrait afin de voir les facteurs qui la justifient.                                             | Étant donné une phrase, quand je clique dessus, alors ses facteurs sont surlignés sur la roue.                                                                                                                              | Should   |
| FR-13 | Je veux masquer des objets ou des familles d'aspects afin d'alléger la roue.                                                        | Étant donné Neptune masqué, quand la roue se met à jour, alors son point disparaît mais ses données et les accents pondérés restent inchangés.                                                                              | Could    |
| FR-14 | Je veux comparer le découpage 12 secteurs au découpage B13 afin de comprendre ce qui change.                                        | Étant donné le mode 12 secteurs, quand je bascule, alors positions, maisons et aspects restent identiques ; seuls signes et degrés internes changent, chaque différence portant sa cause (D, S, Y ou C, voir glossaire).    | Should   |
| FR-15 | Je veux ouvrir la fiche de chaque signe afin de comprendre sa lecture symbolique.                                                   | Étant donné le Serpentaire, quand j'ouvre sa fiche, alors s'affichent archétype, ressources, tensions, question d'introspection et provenance de chaque règle (H, M ou C).                                                  | Should   |
| FR-16 | En tant que médiateur, je veux exporter la roue en SVG, PNG ou PDF afin de l'utiliser dans un support.                              | Étant donné un export, quand le fichier est produit, alors il contient légende, données de naissance (ou leur absence signalée), conventions et statut des données. Le PNG mesure 2 000 × 2 140 px.                         | Should   |
| FR-17 | En tant que praticien, je veux exporter ma session en JSON afin de la recharger.                                                    | Étant donné un export JSON, quand je le recharge, alors le thème et l'état d'affichage (filtres, sélection, découpage) sont restitués séparément.                                                                           | Could    |
| FR-18 | Je veux savoir à tout moment quel est le statut de ce que je lis afin de ne pas confondre calcul et interprétation.                 | Étant donné n'importe quelle vue, quand elle s'affiche, alors le statut des données (réel vérifié, candidat, démonstrateur synthétique) est visible, et tout texte interprétatif porte « proposition symbolique ».          | Must     |
| FR-19 | Je veux un portrait rédigé de mon thème afin d'en avoir une lecture d'ensemble.                                                     | Étant donné un portrait généré, quand le vérificateur s'exécute, alors aucun placement, règle ni événement absent des propositions autorisées n'est détecté ; sinon le passage est bloqué.                                  | Should   |
| FR-20 | En tant que praticien, je veux activer Chiron, le nœud lunaire osculateur ou l'apogée lunaire osculateur afin d'enrichir mon thème. | Étant donné Chiron activé sans éphéméride, quand le thème est calculé, alors son statut est « éphéméride indisponible », sans valeur approchée.                                                                             | Could    |

**Cas limites à couvrir**

- Signe qui traverse 0° (ex. début 350°, fin 20°, astre à 5° → w = 30°, d = 15°, p = 0,5).

- Longitude négative ou supérieure à 360° ; astre exactement au début ou à la fin d'un signe.

- Longitude indéfinie aux pôles écliptiques : rejet, jamais de signe « le plus proche ».

- Découpage invalide (lacune, chevauchement, somme ≠ 360°) : classement refusé.

- Date hors de l'éphéméride DE440s (avant 1849, après 2150) : message explicite.

- Collisions d'étiquettes autour de 0° sur la roue ; export PNG refusé par le navigateur : message d'erreur.

- Objet ou aspect masqué puis sélectionné depuis un tableau : le panneau indique qu'il est masqué, sans réactiver le filtre.

## 7. Exigences non fonctionnelles

Les seuils marqués « proposé » sont à confirmer par le développeur référent ; les autres viennent de l'étude.

| Domaine                | Exigence                                                                                                                                                                                                       | Seuil                                                                                                       |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| Conventions            | Repère écliptique moyen J2000 fixe défini par sa matrice ; positions géocentriques astrométriques ; frontières annoncées « UAI, réalisation Skyfield / Roman VI/42 »                                           | Aucun mélange de repères dans un même thème                                                                 |
| Cohérence du découpage | 13 intervalles, ordre Bélier → Poissons avec Serpentaire entre Scorpion et Sagittaire, sans lacune ni chevauchement                                                                                            | Σ largeurs = 360° à 10⁻⁹° près (proposé) ; calcul arrêté sinon                                              |
| Précision numérique    | Recherche des instants de passage du Soleil (méthode de Brent, échelle TT)                                                                                                                                     | Tolérance du solveur 0,01 s                                                                                 |
| Reproductibilité       | Chaque résultat porte un manifeste : moteur, éphéméride + empreinte, données de temps, base des fuseaux, modèle de frontières + empreinte, versions des règles, du générateur de texte, empreinte de la saisie | 100 % des thèmes régénérables à l'identique                                                                 |
| Plage temporelle       | Éphéméride DE440s                                                                                                                                                                                              | 1849–2150 ; heures UTC futures marquées « conditionnelles » (secondes intercalaires, règles d'heure légale) |
| Performance            | Calcul d'un thème complet puis affichage de la roue                                                                                                                                                            | \< 2 s sur ordinateur, \< 4 s sur mobile 4G (proposé)                                                       |
| Accessibilité          | Contraste des textes ; information jamais portée par la seule couleur ; éléments de la roue atteignables au clavier ; tableaux textuels équivalents                                                            | WCAG 2.2 niveau AA ; test clavier + lecteur d'écran avant la V1                                             |
| Compatibilité          | Ordinateur et téléphone ; roue lisible sur petit écran                                                                                                                                                         | 3 derniers navigateurs majeurs ; largeur min. 360 px (proposé)                                              |
| Confidentialité (RGPD) | Date, heure et lieu de naissance sont des données personnelles : calcul possible sans compte, aucune conservation côté serveur par défaut                                                                      | 0 donnée de naissance stockée sans consentement explicite ; validation juriste avant le pilote              |
| Contenus               | Aucune affirmation déterministe, médicale ou prédictive                                                                                                                                                        | 0 occurrence détectée par le vérificateur sur le corpus de test                                             |
| Observabilité          | Contrôles de correspondance données ↔ roue ↔ aspects ↔ textes exécutés à chaque mise à jour et visibles                                                                                                        | 100 % des contrôles au vert pour publier                                                                    |
| Langue                 | Interface et référentiel en français                                                                                                                                                                           | V1 en français uniquement                                                                                   |

## 8. Périmètre

Le produit avance en 3 jalons ; chacun ne démarre qu'une fois la porte du précédent franchie.

```text
Aucune version ne démarre avant que la précédente ait passé sa porte
(bandes de même largeur, pas à l'échelle du temps ; [*] = la porte qui conditionne tout le reste)

MVP · Mon signe B13           V1 · Mon thème B13             V2 · Mon portrait
3 à 8 semaines                9 à 20 semaines de plus        non estimé
– 13 frontières calculées     – 10 objets, ASC, MC, maisons  – portrait rédigé et vérifié
– calendrier annuel du Soleil – aspects et orbes             – lien phrase → roue
– signe solaire et incertitude– explorateur synchronisé      – Chiron, nœud, apogée
– roue proportionnelle        – comparateur 12 / 13          – comparaison tropicale
– 13 fiches de signe, badges  – exports SVG, PNG, PDF, JSON
                             ◆ G1 [*]                       ◆ G2                          ◆ G3
                  13 / 13 frontières vérifiées  10 / 10 thèmes de référence   portrait 100 % traçable
                           indépendamment              concordants             5 / 5 tests de mutation
```

G1 est la porte critique : tant qu'elle n'est pas franchie, l'application reste un démonstrateur.

**Dans le scope (MVP + V1)** : calcul et vérification des 13 frontières ; calendrier annuel des passages du Soleil ; thème natal des 10 objets principaux avec Ascendant B, MC B, 12 maisons égales et 5 aspects ; roue proportionnelle et vues complémentaires (positions, matrice des aspects, cartes Soleil–Lune–Ascendant, accents pondérés, comparateur 12 / 13) ; 13 fiches de signe B13 ; exports ; statut épistémique.

**Hors scope (exclu du modèle)**

- 13 maisons, aspects fondés sur 360° / 13, modèle C (constellation effective), positions topocentriques.

- Systèmes de maisons Placidus, Koch, Campanus, Regiomontanus.

- Études de validité empirique des interprétations.

- Comptes utilisateurs, paiement, autres langues que le français (sauf décision contraire, Q4).

**Reporté (backlog)**

- Synastrie et transits : extensions séparées, avec leurs propres orbes et règles.

- Comparaison complète avec un thème tropical de date (deux manifestes de calcul).

- Aspects « appliquants » ou « séparants » ; zoom tactile de la roue ; solveur complet de collisions d'étiquettes.

## 9. Métriques de succès

Les seuils sont figés à la validation de ce PRD (v1.0), avant tout lancement. La satisfaction mesure l'utilité ressentie, jamais la justesse des interprétations.

| Indicateur                           | Source                                                                                             | Fréquence                       | Responsable          | Seuil de décision                                             |
|--------------------------------------|----------------------------------------------------------------------------------------------------|---------------------------------|----------------------|---------------------------------------------------------------|
| Frontières vérifiées (O1)            | Manifeste + rapport de comparaison indépendante                                                    | À chaque version du référentiel | Développeur référent | Succès 13 / 13 ; sinon aucune date publiée comme « vérifiée » |
| Thèmes de référence concordants (O2) | Suite de tests contre une seconde chaîne harmonisée                                                | À chaque release                | Développeur référent | Succès 10 / 10 ; itération 8–9 ; échec \< 8 (V1 bloquée)      |
| Traçabilité du portrait (O3)         | Vérificateur automatique                                                                           | À chaque génération             | Testeur / QA         | Succès 100 % ; tout passage non traçable est bloqué           |
| Tests de mutation (O3)               | 5 mutations : Mercure modifié, aspect retiré, heure retirée, planète hors orbe, nom affiché changé | À chaque release                | Testeur / QA         | Succès 5 / 5                                                  |
| Compréhension (O4)                   | Test utilisateur : « expliquez la différence entre signe et constellation »                        | Fin du pilote                   | Micky                | Succès ≥ 7 / 10 ; itération 5–6 ; échec \< 5                  |
| Utilité perçue                       | Questionnaire de fin de session (1 à 5)                                                            | Fin du pilote                   | Micky                | Succès ≥ 4 / 5 en moyenne ; itération 3–4 ; échec \< 3        |

**Mode de lancement** : pilote fermé de 10 testeurs (les 3 personas représentés), puis bêta publique. Tant que la porte G1 n'est pas franchie, tout affichage porte le statut « démonstrateur ».

## 10. Hypothèses, dépendances, risques

Le risque principal est astronomique : aucune frontière réelle n'a encore été calculée, et tout le produit en dépend.

| Type       | Description                                                                                           | Probabilité / impact | Atténuation                                                                                          | Responsable          |
|------------|-------------------------------------------------------------------------------------------------------|----------------------|------------------------------------------------------------------------------------------------------|----------------------|
| Hypothèse  | Le calcul produit exactement 13 intervalles simples, dans l'ordre attendu                             | Moyenne / fort       | Le script s'arrête sinon ; une convention explicite est alors proposée, jamais une correction cachée | Développeur référent |
| Hypothèse  | Le public préfère un calcul exact à une liste de dates                                                | Inconnue / fort      | 5 entretiens par persona avant la v1.0                                                               | Micky                |
| Dépendance | Skyfield, éphéméride DE440s (~32 Mo), base des fuseaux IANA, données IERS (UT1)                       | Faible / fort        | Versions et empreintes figées dans le manifeste                                                      | Développeur référent |
| Dépendance | Expert astronome pour la réduction indépendante des frontières                                        | Moyenne / fort       | L'identifier dès le cadrage (Q5)                                                                     | Micky                |
| Dépendance | Rédacteur du référentiel B13 (13 fiches, règles, provenance H / M / C)                                | Moyenne / moyen      | Partir des 13 fiches déjà esquissées dans l'étude                                                    | Micky                |
| Risque     | Écart entre la réalisation Skyfield / Roman et les frontières d'origine : instants de passage décalés | Moyenne / fort       | Annoncer « réalisation Skyfield / Roman » ; mesurer et publier l'écart (O1)                          | Développeur référent |
| Risque     | Le produit est lu comme « le nouvel horoscope officiel »                                              | Forte / moyen        | Badges de statut, piste pédagogique, phrase de transition « les catégories changent, pas vous »      | Micky                |
| Risque     | Le modèle de langage ajoute un placement ou un événement                                              | Moyenne / fort       | Propositions autorisées seulement, vérificateur, tests de mutation                                   | Testeur / QA         |
| Risque     | Données de naissance traitées sans base légale                                                        | Faible / fort        | Calcul sans compte, pas de stockage par défaut, revue RGPD                                           | Juriste (à nommer)   |
| Risque     | Signes étroits (ex. Scorpion) illisibles sur mobile                                                   | Moyenne / moyen      | Largeur minimale de roue, tableaux équivalents, test sur 3 téléphones                                | Designer (à nommer)  |

## 11. Planning

Estimation initiale : MVP en 3 à 8 semaines après validation des objectifs, V1 en 9 à 20 semaines de plus. Aucune date n'est fixée tant que le sponsor et l'expert astronome ne sont pas nommés.

| Étape                                                                             | Jalon | Durée (fourchette)       | Confiance                                 |
|-----------------------------------------------------------------------------------|-------|--------------------------|-------------------------------------------|
| Cadrage : sponsor, objectifs, entretiens utilisateurs                             | —     | 1 à 3 sem.               | Moyenne                                   |
| Exécution du programme de frontières et des passages 2000, 2025, 2026, 2027, 2050 | MVP   | 1 à 2 sem.               | Moyenne (programme écrit, jamais exécuté) |
| Validation indépendante des frontières (porte G1)                                 | MVP   | 2 à 6 sem.               | Faible                                    |
| Choix de la piste visuelle dominante, maquettes des écrans                        | MVP   | 2 à 4 sem., en parallèle | Moyenne                                   |
| Moteur de thème natal + 10 thèmes de référence (porte G2)                         | V1    | 3 à 6 sem.               | Faible                                    |
| Référentiel B13 : 13 fiches, règles, provenance                                   | V1    | 3 à 8 sem., en parallèle | Faible                                    |
| Explorateur et exports, à partir du prototype HTML existant                       | V1    | 4 à 8 sem.               | Moyenne                                   |
| Tests navigateurs, accessibilité, bout en bout ; pilote fermé                     | V1    | 2 à 4 sem.               | Moyenne                                   |

**Contraintes externes** : aucune échéance réglementaire ou commerciale connue. Les heures UTC et de Paris au-delà de quelques années restent conditionnelles (secondes intercalaires, règles d'heure légale).

## 12. Questions ouvertes

Trois questions bloquent le démarrage (Q1, Q2, Q5) ; les échéances sont proposées et modifiables.

| Question                                                                                                                | Responsable                                                                                | Échéance   | Réponse |
|-------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|------------|---------|
| Q1 — Qui est le sponsor, et quel objectif stratégique ce produit sert-il ? *(bloquante)*                                | Micky | 2026-11-27 |         |
| Q2 — Quel usage prime : grand public, praticiens ou support pédagogique ? Il fixe le parcours par défaut. *(bloquante)* | Micky | 2026-11-27 |         |
| Q3 — La répartition des 4 pistes visuelles (§ 5) convient-elle, ou une piste doit-elle dominer ?                        | Micky | 2026-11-27 |         |
| Q4 — Modèle économique et hébergement : gratuit sans compte, avec compte, payant ?                                      | Micky | 2026-12-11 |         |
| Q5 — Qui réalise la validation astronomique indépendante (porte G1) ? *(bloquante)*                                     | Micky | 2026-11-27 |         |
| Q6 — Le portrait rédigé par un modèle de langage entre-t-il en V1 ou en V2 ?                                            | Micky | 2026-12-11 |         |
| Q7 — Quel nom public pour le produit (B13 est le nom interne du référentiel) ?                                          | Micky | 2026-12-11 |         |
| Q8 — Comment chiffrer le coût de l'inaction (recherches sur le 13e signe, demandes reçues) ?                            | Micky | 2026-12-11 |         |

## 13. Glossaire et annexes

| Terme                | Définition retenue                                                                                                                          |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| Signe                | Intervalle de longitude défini par convention ; ne se confond pas avec la constellation du même nom                                         |
| Constellation        | Région du ciel délimitée par l'UAI ; ses frontières sont conventionnelles, pas physiques                                                    |
| Modèle B             | 13 intervalles inégaux obtenus en croisant l'écliptique J2000 fixe avec les frontières UAI ; classement par la longitude seule              |
| Modèle C             | Classement par la constellation effective de l'astre (latitude comprise) ; hors scope                                                       |
| B13                  | Référentiel symbolique v1 associé au modèle B : 13 fonctions symboliques, sans éléments, modalités, polarités, maîtrises ni dignités actifs |
| Longitude λ          | Angle de l'astre mesuré le long de l'écliptique de référence, de 0° à 360°                                                                  |
| Progression p        | Part du signe déjà parcourue (0 à 1) ; position géométrique, pas une intensité                                                              |
| Astrométrique        | Position corrigée du temps de parcours de la lumière, sans les autres corrections de la position apparente                                  |
| Ascendant B, MC B    | Intersections de l'écliptique J2000 fixe avec l'horizon (côté est) et avec le méridien local                                                |
| Orbe                 | Tolérance angulaire admise autour de l'angle exact d'un aspect ; convention éditoriale                                                      |
| Provenance H / M / C | Héritage astrologique documenté / référence mythologique / choix de conception contemporain                                                 |
| Causes D / S / Y / C | Une lecture change par le découpage (D), la symbolique (S), la synthèse (Y) ou les conventions de calcul (C)                                |
| Statut des données   | Réel vérifié / candidat / démonstrateur synthétique                                                                                         |

**Annexes**

- Étude source : « Pourquoi on a fait une astrologie à 12 signes alors qu'il en existe 13 ? » (PDF, 196 p., 13 questions-réponses : formalisation, frontières, thème natal, référentiel, Serpentaire, interprétation, roue, vues, interface, transition).

- Livrables décrits dans l'étude mais non joints ici : noyau Python de classement, programme de calcul des frontières, moteur de thème, prototype HTML de l'explorateur.

- [Pistes visuelles — canevas](https://claude.ai/artifact/YEuxhAydd1oWooFKojqPY1) · [Procédure — Créer un bon PRD](https://claude.ai/artifact/18EwriTEu6evLRwdWZt67T)

Conventions, formules, formats de données, algorithmes et tests extraits de l'étude : [Annexe technique](01-annexe-technique.md)

Dossier complet sur le 13e signe (astronomie, mythe, identité, fiche, placements, transition, règles) : [Le Serpentaire](02-serpentaire.md)

Effets du 13e signe sur les douze autres (géométrie, catégories, fiches révisées, relations, lecture des personnes) : [Conséquences sur les autres signes](03-consequences.md)

**Historique**

| Version | Date       | Auteur                               | Changement                                                                  |
|---------|------------|--------------------------------------|-----------------------------------------------------------------------------|
| 0.4     | 15/11/2026 | Micky (brouillon rédigé avec Claude) | Ajout de l'onglet « Conséquences sur les autres signes »                    |
| 0.3     | 15/11/2026 | Micky (brouillon rédigé avec Claude) | Ajout de l'onglet « Le Serpentaire » : tout ce que l'étude dit du 13e signe |
| 0.2     | 15/11/2026 | Micky (brouillon rédigé avec Claude) | Ajout de l'annexe technique extraite de l'étude (onglet séparé)             |
| 0.1     | 15/11/2026 | Micky (brouillon rédigé avec Claude) | Création à partir de l'étude, de la procédure et des 4 pistes visuelles     |
