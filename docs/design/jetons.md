# Jetons de design relevés dans les planches

Relevé le 15/11/2026 dans le code source des planches 1, 2, 3, 4 et 7. Ces valeurs alimentent `web/src/styles/jetons.css` (variables CSS) ; un composant n'utilise jamais une couleur ou une police en dur. ⚠️ = à confirmer sur la planche PNG.

## Polices de l'application (validées par Micky le 15/11/2026)
| Rôle | Police | Graisse |
| --- | --- | --- |
| Texte et interface | Inter | 400, 500, 600, 700 |
| Valeurs, degrés, étiquettes techniques | IBM Plex Mono (chiffres tabulaires) | 400, 500 |
| Glyphes des signes et des astres | Noto Sans Symbols, puis Noto Sans Symbols 2 | 400 |
| Titres du mode sombre | Space Grotesk | 500, 600 |
| Titre d'une fiche de signe seulement | Cormorant Garamond | 600 |

Archivo (planche 3), Inter Tight (planche 2) et IBM Plex Sans (planche 4) restent aux contenus de lancement, pour limiter le poids des polices. Toutes passent par Fontsource (`@fontsource/*`), sous licence SIL OFL 1.1.

**Couverture des glyphes, vérifiée le 15/11/2026** sur `@fontsource/noto-sans-symbols` et `@fontsource/noto-sans-symbols-2` 5.3.0 (sous-ensemble « symbols ») : Noto Sans Symbols contient ⛎ (U+26CE), les 12 glyphes ♈–♓, ☽, ♄, ♇, ⚷ et ☊ ; ☉ (U+2609) n'est que dans Noto Sans Symbols 2. D'où la pile `"Noto Sans Symbols", "Noto Sans Symbols 2", sans-serif`, placée avant toute police emoji, et U+FE0E après chaque glyphe.

## Thème clair — défaut (planche 7)
| Jeton | Valeur |
| --- | --- |
| `--fond` | `#EEF0F5` |
| `--surface` | `#FFFFFF` |
| `--bordure` | `#D5D9E4` |
| `--texte` | `#1E2233` |
| `--texte-secondaire` | `#5A6075` |
| `--lien` / `--lien-survol` | `#2F5FB0` / `#1E3F78` |
| `--rayon-controle` / `--rayon-carte` | `10px` / `14px` |
| `--trait-frontiere` | `#1E2233`, 2 px |

Couleurs de remplissage des 13 secteurs, dans l'ordre des signes ⚠️ (ordre déduit du tracé, à confirmer) : Bélier `#F4C7C3`, Taureau `#F6D7B0`, Gémeaux `#F3E6A6`, Cancer `#D9E8B0`, Lion `#BFE3C6`, Vierge `#B5E0DD`, Balance `#B9D3EE`, Scorpion `#C6C6F0`, Serpentaire `#D9C3EC`, Sagittaire `#EBC2DF`, Capricorne `#E8CFC0`, Verseau `#CFE0D8`, Poissons `#D6D9E4`. Elles identifient les signes et n'encodent aucune catégorie ; le glyphe et le nom les accompagnent toujours.

## Thème sombre — Observatoire (planche 1)
| Jeton | Valeur |
| --- | --- |
| `--fond` | `#0E1726` |
| `--texte` | `#E8ECF2` |
| `--texte-secondaire` | `#C9D2DF` |
| `--texte-discret` | `#9AA6B8` |
| `--trait` | `#33465F` |
| `--accent-selection` | ambre ⚠️ valeur à relever ; sert à la sélection, jamais à distinguer le Serpentaire |

Les 13 couleurs de secteur du mode sombre sont à définir pour un contraste AA sur `#0E1726` ⚠️.

## Jetons ajoutés en phase 6 — proposés par Claude, à confirmer par Micky ⚠️
Les planches ne donnent pas ces valeurs. Elles sont choisies pour tenir le contraste AA (rapport calculé, WCAG 2.2) et restent modifiables ici, puis dans `jetons.css`.

| Jeton | Clair | Sombre | Contraste visé |
| --- | --- | --- | --- |
| `--surface` | `#FFFFFF` (planche 7) | `#16233A` | texte sombre 13,3 : 1 |
| `--bordure` | `#D5D9E4` (planche 7) | `#33465F` (le `--trait` de la planche 1) | décor |
| `--bordure-controle` (champs de saisie) | `#6B7288` | `#7F8DA3` | 4,8 : 1 et 4,7 : 1 sur la surface |
| `--lien` / `--lien-survol` | planche 7 | `#8FB8F0` / `#B9D3F7` | 7,7 : 1 sur la surface |
| `--bouton-fond` / `--bouton-texte` | `#2F5FB0` / `#FFFFFF` | `#8FB8F0` / `#0E1726` | 6,2 : 1 et 8,8 : 1 |
| `--alerte` (message bloquant, toujours avec un intitulé) | `#A3341F` | `#FFB4A3` | 6,8 : 1 et 9,2 : 1 |
| `--accent-selection` | `#2F5FB0` | `#F2B441` (ambre relevé sur la planche 1) | 9,7 : 1 sur le fond sombre |
| `--trait-frontiere` | `#1E2233` (planche 7) | `#E8ECF2` | délimite les secteurs |

Secteurs du mode sombre : la teinte de chaque couleur claire, ramenée à une clarté de 27 % et une saturation plafonnée à 38 % ; le texte `#E8ECF2` y tient entre 5,9 : 1 et 11 : 1. Bélier `#5F2F2B`, Taureau `#5F482B`, Gémeaux `#5F562B`, Cancer `#515F2B`, Lion `#2B5F35`, Vierge `#2B5F5B`, Balance `#2B445F`, Scorpion `#2B2B5F`, Serpentaire `#472B5F`, Sagittaire `#5F2B50`, Capricorne `#5F3E2B`, Verseau `#365446`, Poissons `#373D53`. Même règle pour les 13 : aucune ne distingue le Serpentaire.

## Badges de statut — Pédagogique (planche 3)
| Niveau | Fond | Texte | Texte secondaire |
| --- | --- | --- | --- |
| 01 Mesure / calcul | `#0F2A24` | `#FFFFFF` | `#C7D9D2` |
| 02 Convention | `#1F5A4C` | `#FFFFFF` | `#C7D9D2` |
| 03 Interprétation | `#CFE3DA` | `#0F2A24` | `#36524A` |
| 04 Évaluation (hors produit) | `#FFFFFF`, bordure 2 px `#0F2A24` | `#0F2A24` | `#36524A` |

Fond de page de la piste `#EEF2EF`, accent `#9FD3C1`, rayon `6px`. Le libellé du niveau 03 devient « Fonctions symboliques, ressources, tensions » (écart 4). Chaque badge porte un numéro et un libellé : jamais la couleur seule.

## Fiches de signe — Carte (planche 4)
| Jeton | Valeur |
| --- | --- |
| `--carte-fond` | `#1E1630` |
| `--carte-encart` | `#2A2042` |
| `--carte-or` (bordure 1,5 px, intertitres) | `#D9B56A` |
| `--carte-texte` | `#EFE8F5` |
| `--carte-texte-secondaire` | `#CFC4DC` |
| `--carte-texte-discret` | `#A99CBD` |
| `--carte-filet` | `#4A3D63` |
| Rayons | carte `14px`, encart `10px` |
| Format de partage | 750 × 1050 |

Même gabarit pour les 13 signes ; la mention « Proposition contemporaine · clé de lecture choisie, non une description des personnes » reste en pied de carte.

## Comparateur — Suisse (planche 2)
| Jeton | Valeur |
| --- | --- |
| `--suisse-fond` | `#FFFFFF` |
| `--suisse-texte` | `#111111` |
| `--suisse-accent` | `#E4502A` (marque une différence, jamais un signe) |
| `--suisse-filet` | 3 px `#111111` |
