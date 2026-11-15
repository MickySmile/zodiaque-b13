# 0013 · Schéma commun des 13 fiches de signe

- Date : 15/11/2026
- Statut : acceptée (Micky, 15/11/2026) ; à revoir quand le rédacteur du référentiel aura complété les rubriques manquantes

## Contexte
FR-15 demande, pour chaque signe : archétype, ressources, tensions, question d'introspection et provenance de chaque règle (H, M ou C). La règle du référentiel impose un seul schéma pour les 13 fiches et interdit de rédiger ou de compléter un texte.

Or le PRD ne décrit pas les 13 signes avec les mêmes rubriques :

| Source | Signes | Rubriques |
| --- | --- | --- |
| Onglet Serpentaire § 6 (et carte d'identité du § 1) | Serpentaire | Archétype, motivation, besoin fondamental, besoin affectif, ressources, cinq « rapports à », peur symbolique, contradiction centrale, question d'introspection, excès possibles, relations, trajectoires de maturation |
| Onglet Conséquences § 5 (et § 3, § 4) | Les 12 autres | Opération, noyau conservé, reformulation, tension, singularité, question ; couches historiques, chevauchements, verdict |

Les 12 fiches révisées n'ont ni « archétype » ni « ressources » ; la fiche du Serpentaire n'a pas de ligne « tension ».

## Décision
1. **Rubriques communes aux 13 fiches** : `operation`, `archetype`, `resources`, `tensions`, `introspection_question`, `forbidden_inferences`. Une rubrique ne reçoit un texte que si le PRD emploie ce nom de rubrique pour ce signe ; sinon elle porte `status: missing`. Choix de Micky : « ressources » reste manquant pour les 12 signes ; le « noyau conservé » n'en tient pas lieu.
2. **Rubriques complémentaires** (`additional_sections`) : toutes les autres rubriques du PRD sont transcrites mot pour mot, sous leur nom d'origine, dans une liste étiquetée. C'est le même champ pour les 13 fiches ; son contenu suit le PRD, plus long pour le Serpentaire. Choix de Micky.
3. **Chaque texte cite sa source** (`docs/prd/<fichier> § <section>`) et sa provenance. Un test vérifie que chaque texte est une cellule entière, une ligne entière ou une puce entière de la section citée, et, dans un tableau, de la ligne de son propre signe ou de sa propre rubrique. Les libellés des rubriques complémentaires sont eux aussi des intitulés du PRD.
4. **Réserve et clôture** : quand le PRD place une réserve à côté du titre d'une rubrique (« Excès possibles — des impasses narratives à explorer, jamais des diagnostics »), ou la clôt par une phrase, la fiche les reprend dans les champs `caveat` et `closing`. Les omettre changerait la lecture du texte ; un test refuse leur oubli.
5. **Correspondances historiques** (`historical_correspondences`) : élément, modalité et domicile ancien du § 3 de l'onglet Conséquences, avec `active: false`, pour les 13 signes ; les trois valeurs, ou aucune. Le Serpentaire n'en a aucune : les trois valeurs sont nulles et la source citée est le tableau « Aucune catégorie héritée » du § 9 de son onglet. À l'écran, une valeur absente est un tiret, par la même règle pour tout signe.
6. **Format** : un fichier YAML par signe dans `referentiel/signes/`, lu par `moteur/referentiel.py` et validé par un modèle Pydantic ; `referentiel/schema/fiche.schema.json` est dérivé de ce modèle. Micky a accepté PyYAML comme dépendance.
7. **Version et empreinte** : `referentiel/VERSION` vaut `b13_symbolic_v1-t1`, soit le jeu de règles nommé par le PRD suivi du numéro de la transcription. `referentiel/EMPREINTE` consigne cette version et l'empreinte SHA-256 des fiches et des règles : le lecteur refuse un contenu modifié sans nouvelle version. Après une modification : changer `VERSION`, puis recopier dans `EMPREINTE` la ligne affichée par `uv run python -m moteur.referentiel`. La version va au manifeste des réponses qui servent les fiches.
8. **À l'écran** : le sous-titre de la carte est l'opération du signe, pour les 13. « La maîtrise révisable » figure dans la fiche du Serpentaire comme rubrique « Identité symbolique », seule rubrique de ce nom dans le PRD. Les rubriques dont la provenance contient H ou M sont montrées à part, sous le titre « Héritage historique » suivi du statut que le PRD lui donne, « Consultable, sans automatisme actif » (onglet Conséquences § 7) ; le titre ne paraît que s'il a un contenu, par la même règle pour tout signe. Dans la vue des correspondances historiques, une valeur absente est un tiret, légendé « non renseigné dans le référentiel ».

## Choix de transcription faits par Claude, à confirmer
Aucun de ces choix n'écrit un mot : chacun dit quelle cellule du PRD va dans quelle rubrique.

| Rubrique | Choix | Autre lecture possible |
| --- | --- | --- |
| Opération des 12 signes | Colonne « Opération B13 (active) » du § 3 (« Structurer dans la durée ») | La forme courte du § 4 et de la séquence du cercle (« Structurer ») |
| Tensions du Serpentaire | « Tension distinctive » de la carte d'identité (§ 1), seule rubrique nommée « tension » | « Contradiction centrale » ou « Excès possibles » du § 6, transcrits en rubriques complémentaires |
| Question du Serpentaire | « Question d'introspection » du § 6 | « Question centrale » du § 1, transcrite en rubrique complémentaire |
| Besoin affectif du Serpentaire | Texte du § 6 | Le § 1 en donne un autre : « Pouvoir être apprécié sans devoir être indispensable » |
| Opération du Serpentaire | « Opération centrale » de la carte d'identité (§ 1) | — |
| Élément et modalité | La cellule « Élément · modalité » du § 3 est scindée en deux champs, sans changer un mot | Un seul champ |
| Provenance des fiches | C, d'après la mention « proposition contemporaine (C) » en tête des § 4, 5 et 6 | — |
| Provenance des textes dont le niveau annoncé est « décision » ou « règle du référentiel », ou qui n'en annoncent aucun (§ 3 et § 9, § 11, annexe § I, statut « Héritage historique » du § 7) | C : le PRD ne connaît que H, M et C, et une décision du référentiel est un choix contemporain | Une quatrième provenance, que le PRD ne définit pas |
| Provenance des correspondances historiques | H pour les 13 signes, y compris le bloc à trois valeurs nulles du Serpentaire : c'est une convention, sans effet à l'écran | — |
| Provenance de « Interprétation héritée ou courante » | H | — |
| Provenance de « Ce que disent les couches historiques » | H et M : la cellule mêle récits mythologiques et domiciles | Scinder la cellule, ce qui reviendrait à la réécrire |
| Provenance de « Affinités mythologiques » du Serpentaire | M, comme l'indique le PRD | — |
| Inférences interdites | Les cinq du § 11 de l'onglet Serpentaire, pour ce signe ; manquantes pour les 12 autres | La « politique générale pour les 12 signes » (§ 3) est transcrite à part, dans `referentiel/regles.yaml` |

## Ce qui n'est pas transcrit à ce stade
- Les relations entre signes (onglet Conséquences § 7) : elles serviront FR-11, en V1. Les deux onglets n'emploient pas les mêmes mots pour les quatre relations du Serpentaire (« puis » au § 9 de l'un, « et » au § 7 de l'autre).
- Les six motifs fondateurs et les placements du Serpentaire (onglet Serpentaire § 5 et § 7), les dix règles de génération (§ 11) : ils serviront le portrait, en V2.
- Le « texte de présentation proposé » du § 1 de l'onglet Serpentaire, prévu « pour l'écran d'accueil ou la fiche du signe » : à placer avec l'écran d'accueil.
- La phrase « Plus largement : aucun diagnostic… » qui suit la liste des inférences interdites (§ 11) ; les règles communes de l'annexe § I disent la même chose pour les 13 signes.
- La « question propre » du Serpentaire (§ 5), troisième question après celles des § 1 et § 6.
- Les « règles devenues inapplicables » et les « phrases à remplacer » : elles citent des formulations interdites et ne doivent figurer ni dans le référentiel ni dans l'interface (jeu F8).

## Anomalies du PRD relevées, non corrigées
- Onglet Conséquences § 5, Taureau : « appéciation sensorielle » (coquille probable). Transcrit tel quel.
- Les deux textes du « besoin affectif » du Serpentaire, cités plus haut. La règle structurée du § 12 (`affective_need`) suit celui du § 1 ; la fiche suit le § 6.
- Onglet Serpentaire § 5 : l'étape « Répondre de son savoir » est appelée « Référentiel B13 v1 », alors que l'annexe § I et le § 12 attachent « la maîtrise révisable » à `b13_symbolic_v1`. Le nom de `referentiel/VERSION` suit l'annexe.
- Onglet Serpentaire § 12, FR-15 : « la carte de la piste 4 doit passer à "la maîtrise révisable" ». Avec un sous-titre commun aux 13 fiches (l'opération), cette formule est une rubrique de la fiche et non son sous-titre : à trancher par Micky.
- Onglet Conséquences § 5, Bélier : « Action avec Mars » nomme une planète parmi des chevauchements entre signes.

## Conséquences
- Le rédacteur du référentiel reçoit la liste des rubriques manquantes : `docs/referentiel/champs-manquants.md`.
- Quand une rubrique manquante sera écrite dans le PRD, la fiche changera, `referentiel/VERSION` aussi.
