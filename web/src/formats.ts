/**
 * Mise en forme des valeurs affichées. Rien n'est arrondi avant le classement : ces fonctions
 * ne servent qu'à l'écran. Chiffres à la française, virgule décimale.
 */

const SELECTEUR_TEXTE = '︎'

/** Glyphe en présentation texte : U+FE0E interdit la forme emoji (annexe § H). */
export function glypheTexte(glyphe: string): string {
  return `${glyphe}${SELECTEUR_TEXTE}`
}

export function degres(valeur: number, decimales = 2): string {
  return `${valeur.toLocaleString('fr-FR', {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  })}°`
}

/**
 * Longitude affichée avec assez de décimales pour ne pas se confondre avec une frontière :
 * si la valeur arrondie semble égale à une borne alors qu'elle en diffère, la précision
 * augmente (annexe § G).
 */
export function degresPresDesBornes(
  valeur: number,
  bornes: readonly number[],
  decimales = 4,
): string {
  let precision = decimales
  while (
    precision < 12 &&
    bornes.some((borne) => borne !== valeur && borne.toFixed(precision) === valeur.toFixed(precision))
  ) {
    precision += 1
  }
  return degres(valeur, precision)
}

export function pourcentage(fraction: number): string {
  return `${(fraction * 100).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`
}

const MOIS = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
] as const

export { MOIS }

const INSTANT = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?([+-]\d{2}:\d{2})$/

export interface InstantAffiche {
  date: string
  heure: string
  decalage: string
}

/**
 * Lit un instant ISO tel que l'API le rend, sans le reconvertir : l'heure locale affichée est
 * celle que le serveur a calculée avec sa base de fuseaux, pas celle du navigateur.
 */
export function lireInstant(iso: string): InstantAffiche | null {
  const trouve = INSTANT.exec(iso)
  if (trouve === null) return null
  const [, annee, mois, jour, heure, minute, seconde, decalage] = trouve
  return {
    date: `${Number(jour)} ${MOIS[Number(mois) - 1]} ${annee}`,
    heure: `${heure}:${minute}:${seconde}`,
    decalage: decalage === '+00:00' ? 'UTC' : `UTC${decalage.replace('-', '−')}`,
  }
}

export function decalageUtc(secondes: number): string {
  const signe = secondes < 0 ? '−' : '+'
  const absolu = Math.abs(secondes)
  const heures = String(Math.floor(absolu / 3600)).padStart(2, '0')
  const minutes = String(Math.floor((absolu % 3600) / 60)).padStart(2, '0')
  return `UTC${signe}${heures}:${minutes}`
}
