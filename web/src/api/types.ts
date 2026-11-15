/**
 * Contrats de l'API (annexe technique § F), tels que `api/schemas.py` les déclare.
 * Une valeur absente est `null`, accompagnée d'un statut : l'interface ne la remplace jamais.
 */

export type DataStatus = 'verified' | 'candidate' | 'synthetic'
export type Manifest = Record<string, unknown>

export interface WheelSign {
  sign_id: string
  name: string
  glyph: string
  start_deg: number
  end_deg: number
  width_deg: number
}

export interface WheelData {
  status: DataStatus
  data_status: DataStatus
  reference_frame_id: string
  boundary_model_id: string
  boundary_validation_status: string
  interval_policy: string
  orientation: { anchor: 'zero_longitude_left'; direction: 'counterclockwise' }
  signs: WheelSign[]
  houses: null
  houses_status: string
  angles: null
  angles_status: string
  bodies: unknown[]
  aspects: null
  aspects_status: string
  manifest: Manifest
}

export type TimeStatus = 'known' | 'uncertain' | 'unknown'

/** Saisie de naissance. Donnée personnelle : gardée en mémoire, jamais enregistrée. */
export interface BirthRequest {
  date_local: string
  time_local: string | null
  time_status: TimeStatus
  time_uncertainty_seconds: number
  timezone: string
  fold: number | null
  latitude_deg: number
  longitude_deg: number
  altitude_m: number | null
  calendar: 'proleptic_gregorian'
  source: string | null
}

export interface Transition {
  instant_utc: string
  from_sign: string
  to_sign: string
  boundary_deg: number
}

export interface Scenario {
  fold: number
  instant_utc: string
  utc_offset_seconds: number
  time_scale: string
  conditional: boolean
  position: {
    body: string
    body_identifier: number
    target_kind: string
    longitude_deg: number
    latitude_deg: number
  }
  classification: {
    sign_id: string | null
    degrees_in_sign: number | null
    fraction_in_sign: number | null
    status: 'certain' | 'possible'
    possible_signs: string[]
  }
  uncertainty: {
    time_interval_utc: [string, string] | null
    longitude_interval_deg: [number, number] | null
    input_probability_distribution: null
    transitions: Transition[]
  }
  interpretation: { ruleset_id: null; epistemic_status: 'symbolic_proposal'; text: null }
}

export interface SunSignResult {
  title: string | null
  time_status: TimeStatus
  local_time_kind: 'unique' | 'ambiguous' | 'unknown'
  data_status: DataStatus
  model: {
    id: string
    reference_frame: string
    boundary_source_equinox: string
    boundary_sha256: string | null
    interval_policy: string
    validation_status: string
  }
  scenarios: Scenario[]
  ascendant: null
  ascendant_status: string
  houses: null
  houses_status: string
  timezone_caveat: string | null
  manifest: Manifest
}

export interface CalendarEntry {
  sign_id: string
  boundary_deg: number
  tt_jd: number
  instant_utc: string
  instant_local: string
  time_scale: string
  conditional: boolean
  residual_deg: number
}

export interface Calendar {
  year: number
  timezone: string
  entries: CalendarEntry[]
  notice: string
  time_notice: string
  data_status: DataStatus
  timezone_caveat: string | null
  manifest: Manifest
}

export interface Place {
  geoname_id: number
  name: string
  admin1_name: string | null
  country_code: string
  latitude_deg: number
  longitude_deg: number
  timezone: string
  population: number
}

export interface PlaceSearch {
  places: Place[]
  attribution: string
  data_status: DataStatus
  manifest: Manifest
}

export interface TimezoneLookup {
  timezone: string | null
  status: 'found' | 'no_civil_timezone' | 'unknown_to_timezone_database'
  needs_confirmation: true
  data_status: DataStatus
  manifest: Manifest
}

export type Provenance = 'H' | 'M' | 'C'

/** Rubrique d'une fiche : un texte transcrit du PRD, ou `missing` si le PRD ne dit rien. */
export interface SheetEntry {
  status: 'transcribed' | 'missing'
  text: string | null
  items: string[] | null
  table: { columns: string[]; rows: string[][] } | null
  /** Réserve que le PRD place à côté du titre de la rubrique, et phrase qui la clôt. */
  caveat: string | null
  closing: string | null
  source: string | null
  provenance: Provenance[] | null
}

export interface SheetSection extends SheetEntry {
  label: string
}

export interface Sheet {
  schema_version: 1
  sign_id: string
  name: string
  operation: SheetEntry
  archetype: SheetEntry
  resources: SheetEntry
  tensions: SheetEntry
  introspection_question: SheetEntry
  forbidden_inferences: SheetEntry
  additional_sections: SheetSection[]
  /** Catégories héritées : consultables, inactives. L'interface ne s'en sert pour rien. */
  historical_correspondences: {
    active: false
    element: string | null
    modality: string | null
    domicile: string | null
    source: string
    provenance: Provenance[]
  }
}

export interface SignSheet {
  sign_id: string
  name: string
  glyph: string
  sheet: Sheet
  sheet_status: 'transcribed'
  missing: string[]
  epistemic_status: 'symbolic_proposal'
}

export interface Signs {
  data_status: DataStatus
  ruleset_version: string
  ruleset_sha256: string
  signs: SignSheet[]
  rules: {
    schema_version: 1
    common_rules: SheetEntry
    general_policy: SheetEntry
    inherited_categories_decision: SheetEntry
    historical_heritage: SheetEntry
  }
  manifest: Manifest
}

export interface ApiErrorBody {
  error: { code: string; message: string; fields?: string[] }
}
