# 0010 · Avant 1972, l'heure civile est lue comme du temps universel

- Date : 15/11/2026
- Statut : acceptée (Micky)

## Contexte
Pour calculer une position, le moteur convertit l'heure locale en un instant, puis cet instant dans l'échelle des éphémérides (TT). Le PRD écrit : « Saisie et affichage en UTC ; TT / TDB pour les éphémérides ; UT1 pour l'orientation terrestre » (annexe technique, § B).

L'UTC actuel, avec ses secondes intercalaires, n'existe que depuis le 1ᵉʳ janvier 1972. Avant, l'heure civile suivait le temps universel, lié à la rotation de la Terre. La table des secondes intercalaires de Skyfield commence en 1972 ; pour une date antérieure, sa méthode `utc` prolonge simplement vers le passé le décalage de 1972.

Mesuré le 15/11/2026 avec Skyfield 1.55 : entre cet « UTC prolongé » et le temps universel, l'écart est de 33,0 s en 1849, 43,6 s en 1900, 9,0 s en 1960 et 0,6 s en 1971. Le Soleil parcourt environ 0,04″ par seconde : 43,6 s représentent 1,8″, soit 0,0005°. C'est peu, mais c'est une erreur systématique, et elle est évitable.

## Décision
- **À partir du 1ᵉʳ janvier 1972 (UTC)** : l'instant est de l'UTC, converti en TT par la table des secondes intercalaires.
- **Avant le 1ᵉʳ janvier 1972** : l'heure civile, ramenée au méridien de Greenwich par le décalage historique du fuseau, est lue comme du temps universel (UT1), converti en TT par le modèle ΔT de Skyfield.
- Chaque résultat indique l'échelle utilisée : `utc` ou `ut1_before_1972`.
- La jonction se fait à 0,04 s près : au 1ᵉʳ janvier 1972, les deux conversions diffèrent de 39,5 millisecondes (mesuré avec Skyfield 1.55), très en deçà de la tolérance de tout calcul du moteur. Le sens inverse, d'un instant TT vers une date civile, utilise le même seuil, exprimé en TT.

Voies écartées : garder la convention de Skyfield (plus simple, mais décalée du temps universel de l'époque) ; refuser toute naissance antérieure à 1972 (le MVP perdrait une grande part de ses utilisateurs).

## Conséquences
- Le manifeste d'un résultat porte l'échelle de temps et la source des données de temps (tables intégrées à Skyfield, version de Skyfield).
- ΔT avant 1972 vient d'un modèle historique : son incertitude est de l'ordre de la seconde au XXᵉ siècle, de quelques secondes au XIXᵉ. Elle est très inférieure à l'incertitude habituelle d'une heure de naissance.
- Les fuseaux d'avant les heures légales modernes sont des temps locaux moyens (Paris en 1900 : 9 min 21 s d'avance sur Greenwich) ; ils viennent de la base IANA, sans correction.
- Instants futurs : au-delà de la dernière date des tables de temps de Skyfield, les secondes intercalaires à venir ne sont pas connues ; le résultat est marqué « conditionnel », comme le demande le PRD (§ 7, Plage temporelle).
- Point à soumettre à l'expert avec le reste du dossier : la convention retenue avant 1972 et le modèle ΔT.
