---
name: fiche-signe
description: Transcrit l'une des 13 fiches de signe du PRD (12 fiches révisées ou le Serpentaire) en YAML dans referentiel/, avec provenance, inférences interdites et correspondances historiques inactives. À utiliser pour « ajoute la fiche du Taureau », « transcris la fiche du Serpentaire ».
argument-hint: nom du signe
---

# Transcrire une fiche de signe

1. Trouve la fiche de `$ARGUMENTS` : le Serpentaire dans `docs/prd/02-serpentaire.md` § 6, les 12 autres dans `docs/prd/03-consequences.md` § 5 (fiches révisées) et § 4 (tableau comparatif).
2. Copie le schéma commun `referentiel/schema/fiche.schema.json` (à créer à la première fiche, puis inchangé) et remplis `referentiel/signes/<id>.yaml` (`id` en anglais à trois lettres : ari, tau, gem, cnc, leo, vir, lib, sco, oph, sgr, cap, aqr, psc).
3. Chaque texte est recopié mot pour mot, avec `source: <fichier> § <section>`. Un champ sans texte dans le PRD reste vide avec `status: missing`.
4. Renseigne la provenance (`H`, `M` ou `C`) de chaque règle selon le PRD ; place éléments, modalités, maîtrises et dignités sous `historical_correspondences` avec `active: false`.
5. Lance les tests du référentiel (schéma valide, 13 fiches au même schéma, aucun champ propre à un signe), puis la skill `verify`.
6. Demande la relecture du sous-agent `gardien-contenus` et rends son verdict avec la liste des champs `missing`.
