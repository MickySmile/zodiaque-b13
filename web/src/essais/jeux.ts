/**
 * Jeux d'essai des tests de l'interface.
 *
 * Les 13 frontières sont lues dans `generes/frontieres.csv`, le fichier que le moteur produit :
 * aucune largeur n'est écrite ici. Les positions et les instants sont fabriqués par calcul à
 * partir de ces frontières et portent le statut « synthetic », affiché « démonstrateur
 * synthétique » : ils ne décrivent ni le ciel ni une personne.
 */
import csv from '../../../generes/frontieres.csv?raw'
import type { Api } from '../api/client.ts'
import type {
  Calendar,
  DataStatus,
  Place,
  Scenario,
  SunSignResult,
  WheelData,
  WheelSign,
} from '../api/types.ts'

export const synthetic = true

const NOMS: Record<string, [name: string, glyph: string]> = {
  Ari: ['Bélier', '\u2648'],
  Tau: ['Taureau', '\u2649'],
  Gem: ['Gémeaux', '\u264a'],
  Cnc: ['Cancer', '\u264b'],
  Leo: ['Lion', '\u264c'],
  Vir: ['Vierge', '\u264d'],
  Lib: ['Balance', '\u264e'],
  Sco: ['Scorpion', '\u264f'],
  Oph: ['Serpentaire', '\u26ce'],
  Sgr: ['Sagittaire', '\u2650'],
  Cap: ['Capricorne', '\u2651'],
  Aqr: ['Verseau', '\u2652'],
  Psc: ['Poissons', '\u2653'],
}

export function wrap(angle: number): number {
  return ((angle % 360) + 360) % 360
}

/** Les 13 signes du fichier généré, sans arrondi. */
export function signesGeneres(): WheelSign[] {
  const [, ...lignes] = csv.trim().split('\n')
  return lignes.map((ligne) => {
    const [sign_id, start, end, width] = ligne.trim().split(',')
    const [name, glyph] = NOMS[sign_id]
    return {
      sign_id,
      name,
      glyph,
      start_deg: Number(start),
      end_deg: Number(end),
      width_deg: Number(width),
    }
  })
}

const MANIFESTE = {
  calculation_engine_version: '0.0.0-essai',
  model_id: 'model_b_iau_ecliptic_j2000_v1',
  ephemeris_id_and_hash: { id: 'essai', sha256: 'empreinte-d-essai' },
  timezone_database_version: 'essai',
  chart_input_hash: 'empreinte-de-saisie-d-essai',
}

export function roue(statut: DataStatus = 'candidate'): WheelData {
  return {
    status: statut,
    data_status: statut,
    reference_frame_id: 'repère d’essai',
    boundary_model_id: MANIFESTE.model_id,
    boundary_validation_status: statut === 'verified' ? 'validated' : 'not_validated',
    interval_policy: 'start_included_end_excluded',
    orientation: { anchor: 'zero_longitude_left', direction: 'counterclockwise' },
    signs: signesGeneres(),
    houses: null,
    houses_status: 'not_computed_in_this_version',
    angles: null,
    angles_status: 'not_computed_in_this_version',
    bodies: [],
    aspects: null,
    aspects_status: 'not_computed_in_this_version',
    manifest: { ...MANIFESTE, data_status: statut },
  }
}

/** Longitude fabriquée : une fraction de la largeur d'un signe, depuis son début. */
export function longitudeDans(signId: string, fraction: number): number {
  const signe = signesGeneres().find((s) => s.sign_id === signId)!
  return wrap(signe.start_deg + fraction * signe.width_deg)
}

interface ScenarioEssai {
  signe: string
  fraction?: number
  /** Signes possibles, dans l'ordre du temps : le statut devient « possible ». */
  possibles?: [string, string]
  fold?: number
  decalage?: number
  conditionnel?: boolean
}

function scenario(essai: ScenarioEssai): Scenario {
  const fraction = essai.fraction ?? 0.5
  const signe = signesGeneres().find((s) => s.sign_id === essai.signe)!
  const longitude = longitudeDans(essai.signe, fraction)
  const certain = essai.possibles === undefined
  return {
    fold: essai.fold ?? 0,
    instant_utc: '2000-01-01T11:00:00+00:00',
    utc_offset_seconds: essai.decalage ?? 3600,
    time_scale: 'utc',
    conditional: essai.conditionnel ?? false,
    position: {
      body: 'Sun',
      body_identifier: 10,
      target_kind: 'center',
      longitude_deg: longitude,
      latitude_deg: 0,
    },
    classification: {
      sign_id: certain ? essai.signe : null,
      degrees_in_sign: certain ? fraction * signe.width_deg : null,
      fraction_in_sign: certain ? fraction : null,
      status: certain ? 'certain' : 'possible',
      possible_signs: essai.possibles ?? [essai.signe],
    },
    uncertainty: {
      time_interval_utc: certain ? null : ['2000-01-01T10:50:00+00:00', '2000-01-01T11:10:00+00:00'],
      longitude_interval_deg: certain ? null : [wrap(longitude - 0.01), wrap(longitude + 0.01)],
      input_probability_distribution: null,
      transitions: certain
        ? []
        : [
            {
              instant_utc: '2000-01-01T11:02:03+00:00',
              from_sign: essai.possibles![0],
              to_sign: essai.possibles![1],
              boundary_deg: signesGeneres().find((s) => s.sign_id === essai.possibles![1])!
                .start_deg,
            },
          ],
    },
    interpretation: { ruleset_id: null, epistemic_status: 'symbolic_proposal', text: null },
  }
}

export function signeSolaire(
  scenarios: ScenarioEssai[],
  options: Partial<
    Pick<SunSignResult, 'title' | 'time_status' | 'local_time_kind' | 'timezone_caveat'>
  > & { statut?: DataStatus } = {},
): SunSignResult {
  const statut = options.statut ?? 'synthetic'
  const inconnue = options.time_status === 'unknown'
  return {
    title: options.title ?? null,
    time_status: options.time_status ?? 'known',
    local_time_kind: options.local_time_kind ?? 'unique',
    data_status: statut,
    model: {
      id: MANIFESTE.model_id,
      reference_frame: 'repère d’essai',
      boundary_source_equinox: 'B1875',
      boundary_sha256: null,
      interval_policy: 'start_included_end_excluded',
      validation_status: 'not_validated',
    },
    scenarios: scenarios.map(scenario),
    ascendant: null,
    ascendant_status: inconnue ? 'undefined_without_birth_time' : 'not_computed_in_this_version',
    houses: null,
    houses_status: inconnue ? 'undefined_without_birth_time' : 'not_computed_in_this_version',
    timezone_caveat: options.timezone_caveat ?? null,
    manifest: { ...MANIFESTE, data_status: statut },
  }
}

/** Calendrier d'essai : 13 entrées espacées de 28 jours, sans rapport avec le ciel. */
export function calendrier(annee = 2000, statut: DataStatus = 'synthetic'): Calendar {
  const depart = Date.UTC(annee, 0, 10, 2, 3, 4)
  return {
    year: annee,
    timezone: 'Europe/Paris',
    entries: signesGeneres().map((signe, rang) => {
      const utc = new Date(depart + rang * 28 * 86_400_000).toISOString().slice(0, 19)
      const local = new Date(depart + rang * 28 * 86_400_000 + 3_600_000).toISOString().slice(0, 19)
      return {
        sign_id: signe.sign_id,
        boundary_deg: signe.start_deg,
        tt_jd: 0,
        instant_utc: `${utc}+00:00`,
        instant_local: `${local}+01:00`,
        time_scale: 'utc',
        conditional: rang === 12,
        residual_deg: 0,
      }
    }),
    // Mention du PRD, telle que l'API la rend (apostrophes droites comprises).
    notice: "indicatif : près d'une frontière, l'heure de naissance compte",
    time_notice: 'Mention d’essai sur les échelles de temps.',
    data_status: statut,
    timezone_caveat: null,
    manifest: { ...MANIFESTE, data_status: statut, chart_input_hash: null },
  }
}

export const LIEU_FICTIF: Place = {
  geoname_id: 1,
  name: 'Villefictive',
  admin1_name: 'Région d’essai',
  country_code: 'ZZ',
  latitude_deg: 10.5,
  longitude_deg: 20.25,
  timezone: 'Europe/Paris',
  population: 50_000,
}

/** Client d'essai : chaque appel rend un jeu fabriqué ; rien ne part sur le réseau. */
export function clientEssai(remplacements: Partial<Api> = {}): Api {
  return {
    boundaries: async () => roue(),
    sunSign: async () => signeSolaire([{ signe: 'Leo' }]),
    calendar: async (annee) => calendrier(annee),
    searchPlaces: async () => ({
      places: [LIEU_FICTIF],
      attribution: 'Lieux : GeoNames (geonames.org), licence CC BY 4.0',
      data_status: 'candidate',
      manifest: {},
    }),
    timezoneAt: async () => ({
      timezone: 'Europe/Paris',
      status: 'found',
      needs_confirmation: true,
      data_status: 'candidate',
      manifest: {},
    }),
    ...remplacements,
  }
}
