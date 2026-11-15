# Rubriques manquantes des fiches B13 — pour le rédacteur du référentiel

État au 15/11/2026, référentiel `b13_symbolic_v1-t1`. Cette liste sort des fiches elles-mêmes (`referentiel/signes/*.yaml`) : un test vérifie qu'elle leur correspond.

Une rubrique est « manquante » quand le PRD ne donne aucun texte sous ce nom pour ce signe. Rien n'a été écrit à sa place : l'application affiche « non rédigé à ce jour ».

## Ce qu'il reste à écrire : **36 rubriques**

| Signe | Archétype | Ressources | Inférences interdites |
| --- | --- | --- | --- |
| Bélier | manquant | manquant | manquant |
| Taureau | manquant | manquant | manquant |
| Gémeaux | manquant | manquant | manquant |
| Cancer | manquant | manquant | manquant |
| Lion | manquant | manquant | manquant |
| Vierge | manquant | manquant | manquant |
| Balance | manquant | manquant | manquant |
| Scorpion | manquant | manquant | manquant |
| Serpentaire | transcrit | transcrit | transcrit |
| Sagittaire | manquant | manquant | manquant |
| Capricorne | manquant | manquant | manquant |
| Verseau | manquant | manquant | manquant |
| Poissons | manquant | manquant | manquant |

Les autres rubriques communes (opération, tensions, question d'introspection) sont transcrites pour les 13 signes.

## Ce que le PRD donne déjà, et qui pourrait aider
- **Archétype** : seul le Serpentaire en a un (« Le praticien qui reste apprenant »). Les 12 fiches révisées ont une opération (« Engager », « Consolider »…) et une « singularité », mais aucun archétype.
- **Ressources** : les 12 fiches révisées ont un « noyau conservé » (par exemple, pour le Bélier : « Initiative, décision, affirmation, courage d'essayer »). Micky a décidé qu'il ne tient pas lieu de ressources ; au rédacteur de dire s'il faut les écrire à part.
- **Inférences interdites** : le PRD en liste cinq pour le Serpentaire. Pour les 12 autres, seule existe la « politique générale » du § 3 de l'onglet Conséquences, transcrite dans `referentiel/regles.yaml`. Deux passages peuvent aider : « Ce qu'il ne faut pas faire » (onglet Conséquences § 6, trois signes) et « Ce qu'on ne doit pas conclure » (§ 8).

## Points à trancher par le rédacteur
1. **Coquille probable** : onglet Conséquences § 5, Taureau, « appéciation sensorielle ». Elle est transcrite telle quelle et s'affiche ainsi.
2. **Deux « besoins affectifs » pour le Serpentaire** : « Pouvoir être apprécié sans devoir être indispensable » (§ 1) et « Être apprécié sans devoir réparer, expliquer ou soutenir continuellement » (§ 6). La fiche reprend le § 6 ; la règle structurée du § 12 suit le § 1.
3. **Nom de l'opération** : « Structurer dans la durée », « Reconfigurer le collectif », « Accueillir ce qui déborde » et « Mettre au jour et traverser » (§ 3 et § 5) ou leurs formes courtes (§ 4 et séquence du cercle). La fiche reprend le § 3.
4. **Tension du Serpentaire** : sa fiche (§ 6) n'a pas de ligne « tension » ; la fiche reprend la « tension distinctive » du § 1.
5. **Fiches inégales** : celle du Serpentaire compte 17 rubriques complémentaires, celles des 12 autres en comptent 10, de nature différente. Les aligner demanderait d'écrire, pour chaque signe, les dimensions que l'autre groupe possède.
6. **Relations entre signes** : les deux onglets n'emploient pas les mêmes mots pour les quatre relations du Serpentaire. Elles ne sont pas encore transcrites.
7. **Trois questions pour le Serpentaire** : « question centrale » (§ 1), « question propre » (§ 5) et « question d'introspection » (§ 6). La fiche reprend le § 6 ; celle du § 1 est en rubrique complémentaire ; celle du § 5 n'est pas transcrite.
8. **« La maîtrise révisable »** : l'onglet Serpentaire (§ 12) demande que la carte du signe passe à cette formule. Elle figure dans sa fiche comme « identité symbolique » ; aucune des 12 autres fiches n'a de rubrique de ce nom.
9. **Bélier, chevauchements** : « Action avec Mars » nomme une planète parmi des signes.
10. **Nom du jeu de règles** : l'onglet Serpentaire (§ 5) appelle « Référentiel B13 v1 » une étape antérieure à « la maîtrise révisable », que l'annexe attache pourtant à `b13_symbolic_v1`.

Les choix de transcription sont détaillés dans `docs/decisions/0013-schema-des-fiches-de-signe.md`.
