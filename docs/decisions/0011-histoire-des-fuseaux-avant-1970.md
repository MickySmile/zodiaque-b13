# 0011 · Écart à trancher : l'histoire de certains fuseaux est fusionnée avant 1970

- Date : 15/11/2026
- Statut : **ouverte**. Écart signalé par `relecteur-astro` pendant la phase 5, vérifié par Claude ; à trancher par Micky.

## Contexte
Le PRD demande, pour chaque naissance, un « identifiant historique IANA (`tzdata`), version enregistrée », « jamais un simple UTC+1 » (annexe technique, § B). Le moteur lit les fuseaux dans le paquet `tzdata` (version 2026f), comme prévu par la décision 0002.

Or la base IANA ne garantit l'histoire d'un fuseau que depuis 1970. Pour les dates antérieures, elle range dans un fichier séparé, `backzone`, l'histoire propre des villes qui ont aujourd'hui la même heure qu'une voisine. Le paquet `tzdata` de PyPI est compilé sans ce fichier : avant 1970, ces identifiants renvoient l'histoire de la ville à laquelle ils sont rattachés.

## Constat
Vérifié le 15/11/2026 avec `tzdata` 2026.6 :

- `Europe/Amsterdam`, le 1ᵉʳ juin 1930 à midi : décalage rendu **+1 h 00**, le même que `Europe/Brussels`. Amsterdam avait alors son heure propre, en avance d'une vingtaine de minutes sur Greenwich, soit environ une heure et vingt minutes en été (de mémoire : cette valeur ne vient pas des données du dépôt et reste à confirmer sur une base compilée avec `backzone`). L'écart serait de l'ordre de vingt minutes.
- `Europe/Amsterdam`, le 1ᵉʳ juin 1900 : décalage rendu **0 h 00**, celui de Bruxelles.
- `Europe/Oslo` et `Europe/Copenhagen`, en 1900 et en 1930 : mêmes décalages que `Europe/Berlin`.
- `Europe/Paris` garde son histoire propre : +0 h 09 min 21 s en 1900.

Je n'ai pas la liste complète des identifiants concernés : il faudrait comparer le paquet à une base compilée avec `backzone`.

Vingt minutes d'erreur sur l'heure, c'est environ 0,014° de mouvement solaire. C'est sans effet sur le signe solaire, sauf pour une naissance survenue dans les vingt minutes qui entourent une entrée du Soleil dans un signe. L'effet sera bien plus grand en V1 : l'Ascendant se déplace d'environ un degré toutes les quatre minutes.

## Ce que fait le moteur en attendant
- Le calcul n'est pas modifié : il utilise le décalage que rend `tzdata`.
- Tout résultat pour une date antérieure à 1970 porte la réserve `zone_history_may_be_merged_before_1970`. L'interface devra afficher le décalage utilisé, pour que la personne puisse le contrôler.
- Chaque scénario porte déjà son décalage en secondes (`utc_offset_seconds`).

## Options
- **A. Garder `tzdata` tel quel, avec la réserve affichée.** Rien à installer. Suffisant pour le signe solaire ; à revoir avant la V1.
- **B. Ajouter une base compilée avec `backzone`.** C'est une nouvelle source de données : à déclarer dans `donnees/sources.toml`, avec son empreinte, et à valider par Micky. L'histoire d'avant 1970 y est d'une fiabilité inégale, de l'aveu même de ses mainteneurs.
- **C. Avant 1970, faire confirmer le décalage par la personne.** L'interface montre le décalage proposé et permet de le corriger ; la saisie garde alors la trace d'un décalage imposé.

## Conséquences immédiates
- Aucune pour le critère de la phase 5 : les jeux d'essai sont à Paris, dont l'histoire est propre.
- À traiter avant la V1 (Ascendant et maisons), et à mentionner à l'expert avec le reste du dossier.
