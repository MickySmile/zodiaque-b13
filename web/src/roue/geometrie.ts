/**
 * Géométrie de la roue (annexe technique § H). Une seule transformation angulaire sert à tous
 * les calques : longitude 0° à gauche, longitudes croissantes dans le sens direct.
 *
 * Rien ici ne modifie une longitude : on place des points, on ne corrige aucune position.
 */

const TAILLE = 1000
export const CENTRE = TAILLE / 2
/** R : rayon extérieur de l'anneau des signes. Les repères extérieurs vont jusqu'à 1,15 R. */
export const R = 400

/**
 * Cadre du dessin. Rien n'est tracé au-delà de l'anneau des signes tant qu'aucun angle n'est
 * calculé : la zone des repères ASC, DSC, MC et IC (1,00 R à 1,15 R) n'est pas réservée, et la
 * roue occupe toute la largeur disponible.
 */
const MARGE = 40
export const CADRE = { origine: CENTRE - R - MARGE, taille: 2 * (R + MARGE) } as const

/** Anneaux, en fractions de R (annexe § H). */
export const ANNEAUX = {
  signesInterieur: 0.855,
  signesExterieur: 1,
  graduationInterieur: 0.81,
  chiffres: 0.765,
  repereExact: 0.715,
  etiquettesExterieur: 0.69,
  etiquettes: 0.6,
} as const

export interface Point {
  x: number
  y: number
}

export function wrap(angle: number): number {
  return ((angle % 360) + 360) % 360
}

/** Point de l'écran pour une longitude et un rayon (fraction de R). */
export function point(longitudeDeg: number, fraction: number): Point {
  const angle = ((180 + longitudeDeg) * Math.PI) / 180
  const rayon = fraction * R
  return { x: CENTRE + rayon * Math.cos(angle), y: CENTRE - rayon * Math.sin(angle) }
}

function nombre(valeur: number): string {
  return valeur.toFixed(3)
}

export function coordonnees(p: Point): string {
  return `${nombre(p.x)} ${nombre(p.y)}`
}

/**
 * Tracé d'un secteur d'anneau, de `debutDeg` sur `largeurDeg` degrés dans le sens direct.
 * La largeur est celle des données : elle n'est ni arrondie ni ajustée au contenu.
 */
export function secteur(
  debutDeg: number,
  largeurDeg: number,
  interieur: number,
  exterieur: number,
): string {
  const fin = debutDeg + largeurDeg
  const grandArc = largeurDeg > 180 ? 1 : 0
  const [re, ri] = [nombre(exterieur * R), nombre(interieur * R)]
  return [
    `M ${coordonnees(point(debutDeg, exterieur))}`,
    // Longitudes croissantes : sens direct à l'écran, donc drapeau de balayage à 0.
    `A ${re} ${re} 0 ${grandArc} 0 ${coordonnees(point(fin, exterieur))}`,
    `L ${coordonnees(point(fin, interieur))}`,
    `A ${ri} ${ri} 0 ${grandArc} 1 ${coordonnees(point(debutDeg, interieur))}`,
    'Z',
  ].join(' ')
}

/**
 * Longitudes d'affichage des étiquettes : écartées d'au moins `ecartMinDeg`, dans le même ordre
 * que les longitudes vraies. Seules les étiquettes bougent ; les points restent où ils sont.
 */
export function placerEtiquettes(longitudes: readonly number[], ecartMinDeg: number): number[] {
  const ordre = longitudes.map((_, rang) => rang).sort((a, b) => longitudes[a] - longitudes[b])
  const places = ordre.map((rang) => longitudes[rang])
  if (places.length > 1 && places.length * ecartMinDeg <= 360) {
    for (let tour = 0; tour < 200; tour += 1) {
      let deplace = false
      for (let rang = 0; rang < places.length; rang += 1) {
        const suivant = (rang + 1) % places.length
        const ecart = wrap(places[suivant] - places[rang])
        if (ecart < ecartMinDeg - 1e-9) {
          const moitie = (ecartMinDeg - ecart) / 2
          places[rang] -= moitie
          places[suivant] += moitie
          deplace = true
        }
      }
      if (!deplace) break
    }
  }
  const resultat = new Array<number>(longitudes.length)
  ordre.forEach((rang, position) => {
    resultat[rang] = places[position]
  })
  return resultat
}
