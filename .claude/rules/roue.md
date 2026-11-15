---
paths:
  - "web/src/roue/**"
---

# Roue SVG

Détail : `docs/prd/01-annexe-technique.md`, § H (rendu de la roue) et K (vigilance sur les pistes visuelles).

- La roue est construite à partir des données de l'API, jamais une illustration : on déplace une étiquette, jamais une position ni une frontière.
- **Anneaux** (R = rayon extérieur de l'anneau des signes) : repères ASC/DSC/MC/IC 1,00–1,15 R ; signes 0,855–1,00 R ; graduation continue 0,81–0,855 R ; maisons 0,72–0,80 R (limites en pointillé gris) ; repères exacts ≈ 0,715 R ; étiquettes 0,50–0,69 R ; aspects 0–0,46 R. Une frontière de signe s'arrête à son anneau.
- **Interdits** : 13 secteurs égaux avec les vraies valeurs dans un tableau ; secteur élargi pour loger un nom ; portion contractée ; frontière déplacée pour éviter une collision ; aspect relié à un glyphe déplacé. Une étiquette déplacée est reliée à son point par un trait.
- **Précision** : chaque secteur couvre sa largeur à 0,1° près (FR-10) ; un test le vérifie à partir du SVG rendu.
- **Aspects** : la couleur distingue des familles, jamais « bon » ou « mauvais » ; conjonction violet continu très court, sextile bleu pointillé court, carré terre cuite continu, trigone bleu continu, opposition terre cuite tirets longs.
- **Serpentaire** : glyphe ⛎ (U+26CE) suivi de U+FE0E, police `"Noto Sans Symbols"` en tête de pile, monochrome, repli « Oph » ; même traitement graphique que les 12 autres signes (l'accent de couleur marque la sélection, pas le Serpentaire) ; ni caducée, ni couronne, ni étoile.
- **Couleurs des signes** : elles identifient, elles ne réintroduisent ni éléments, ni modalités, ni dignités ; jamais seules (glyphe ou nom en plus).
- **Deux niveaux** : vue simplifiée (signes, maisons, 10 objets, 4 angles, carrés, trigones, oppositions) et vue détaillée (graduations fines, degrés internes, 5 familles). Un élément masqué reste dans les données (FR-13).
- **Accessibilité** : chaque secteur, objet, maison et aspect est atteignable au clavier, a un nom accessible et un équivalent dans un tableau.
- **Exports** (FR-16) : glyphes convertis en tracés ; légende, données de naissance (ou leur absence signalée), conventions et statut des données ; PNG 2 000 × 2 140 px.
