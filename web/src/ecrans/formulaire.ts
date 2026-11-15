/**
 * Formulaire de naissance : son état, et sa conversion vers la saisie de l'annexe F.
 * Le moteur reste seul juge des valeurs ; ici on ne vérifie que ce qui manque.
 */
import type { BirthRequest, Place } from '../api/types.ts'
import { MOIS, degres } from '../formats.ts'

/** État du formulaire. Donnée personnelle : gardée en mémoire, jamais enregistrée. */
export interface Formulaire {
  annee: string
  mois: string
  jour: string
  heure: string
  minute: string
  heureInconnue: boolean
  precision: number
  recherche: string
  lieu: Place | null
  manuel: boolean
  latitude: string
  longitude: string
  fuseauDeduit: string | null
  fuseauConfirme: boolean
}

export const FORMULAIRE_VIDE: Formulaire = {
  annee: '',
  mois: '',
  jour: '',
  heure: '',
  minute: '',
  heureInconnue: false,
  precision: 0,
  recherche: '',
  lieu: null,
  manuel: false,
  latitude: '',
  longitude: '',
  fuseauDeduit: null,
  fuseauConfirme: false,
}

export const PRECISIONS = [
  { secondes: 0, libelle: 'Exacte' },
  { secondes: 300, libelle: '± 5 min' },
  { secondes: 900, libelle: '± 15 min' },
  { secondes: 3600, libelle: '± 1 h' },
] as const

function entier(texte: string, min: number, max: number): number | null {
  if (!/^\d+$/.test(texte.trim())) return null
  const valeur = Number(texte)
  return valeur >= min && valeur <= max ? valeur : null
}

export function decimal(texte: string): number | null {
  const propre = texte.trim().replace(',', '.').replace('−', '-')
  if (!/^-?\d+(\.\d+)?$/.test(propre)) return null
  return Number(propre)
}

function deuxChiffres(valeur: number): string {
  return String(valeur).padStart(2, '0')
}

/** Construit la saisie de l'annexe F, ou la liste de ce qui manque. */
export function construire(f: Formulaire): { saisie: BirthRequest } | { manques: string[] } {
  const manques: string[] = []
  const annee = entier(f.annee, 1, 9999)
  const mois = entier(f.mois, 1, 12)
  const jour = entier(f.jour, 1, 31)
  if (annee === null || mois === null || jour === null) manques.push('la date de naissance')
  const heure = entier(f.heure, 0, 23)
  const minute = entier(f.minute, 0, 59)
  if (!f.heureInconnue && (heure === null || minute === null)) {
    manques.push('l’heure de naissance, ou la case « Heure inconnue »')
  }
  let lieu: { timezone: string; latitude_deg: number; longitude_deg: number } | null = null
  if (f.manuel) {
    const latitude = decimal(f.latitude)
    const longitude = decimal(f.longitude)
    if (latitude === null || longitude === null) manques.push('la latitude et la longitude')
    else if (f.fuseauDeduit === null) manques.push('le fuseau, à déduire des coordonnées')
    else if (!f.fuseauConfirme) manques.push('la confirmation du fuseau')
    else lieu = { timezone: f.fuseauDeduit, latitude_deg: latitude, longitude_deg: longitude }
  } else if (f.lieu === null) {
    manques.push('le lieu de naissance')
  } else {
    lieu = {
      timezone: f.lieu.timezone,
      latitude_deg: f.lieu.latitude_deg,
      longitude_deg: f.lieu.longitude_deg,
    }
  }
  if (manques.length > 0 || lieu === null) return { manques }
  const statut = f.heureInconnue ? 'unknown' : f.precision === 0 ? 'known' : 'uncertain'
  return {
    saisie: {
      date_local: `${String(annee).padStart(4, '0')}-${deuxChiffres(mois!)}-${deuxChiffres(jour!)}`,
      time_local: f.heureInconnue ? null : `${deuxChiffres(heure!)}:${deuxChiffres(minute!)}:00`,
      time_status: statut,
      time_uncertainty_seconds: statut === 'uncertain' ? f.precision : 0,
      ...lieu,
      fold: null,
      altitude_m: null,
      calendar: 'proleptic_gregorian',
      source: 'user_input',
    },
  }
}

/** Résumé de la saisie, à montrer au-dessus du résultat pour contrôle. */
export function resumer(f: Formulaire, saisie: BirthRequest): string {
  const [annee, mois, jour] = saisie.date_local.split('-')
  const precision = PRECISIONS.find((p) => p.secondes === saisie.time_uncertainty_seconds)
  const heure =
    saisie.time_local === null
      ? 'heure inconnue'
      : `${saisie.time_local.slice(0, 5)}${
          saisie.time_status === 'uncertain' && precision ? ` (${precision.libelle})` : ''
        }`
  const lieu = f.manuel
    ? `${degres(saisie.latitude_deg, 4)}, ${degres(saisie.longitude_deg, 4)}`
    : (f.lieu?.name ?? '')
  return `${Number(jour)} ${MOIS[Number(mois) - 1]} ${annee}, ${heure}, ${lieu} (${saisie.timezone})`
}
