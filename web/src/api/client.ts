/**
 * Client de l'API locale. Aucun appel à un tiers : toutes les adresses sont relatives.
 * Les données de naissance partent dans le corps d'une requête POST, jamais dans une adresse.
 */
import type {
  ApiErrorBody,
  BirthRequest,
  Calendar,
  PlaceSearch,
  SunSignResult,
  TimezoneLookup,
  WheelData,
} from './types.ts'

/** Refus ou panne rendus par l'API : un code stable et un message en français. */
export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

const UNREACHABLE = new ApiError(
  0,
  'unreachable',
  'Le serveur de calcul ne répond pas : aucun résultat n’est affiché.',
)

async function call<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(
      path,
      body === undefined
        ? { headers: { Accept: 'application/json' } }
        : {
            method: 'POST',
            headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          },
    )
  } catch {
    throw UNREACHABLE
  }
  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw UNREACHABLE
  }
  if (!response.ok) {
    const error = (payload as Partial<ApiErrorBody>).error
    throw new ApiError(
      response.status,
      error?.code ?? 'internal_error',
      // Le serveur écrit des apostrophes droites ; l'écran les montre typographiques.
      (error?.message ?? 'Erreur interne : aucun résultat n’est affiché.').replaceAll("'", '’'),
    )
  }
  return payload as T
}

export const api = {
  boundaries: () => call<WheelData>('/api/boundaries'),
  sunSign: (birth: BirthRequest) => call<SunSignResult>('/api/sun-sign', birth),
  /** L'année consultée n'est pas une donnée de naissance : elle peut figurer dans l'adresse. */
  calendar: (year: number) => call<Calendar>(`/api/calendar/${year}`),
  searchPlaces: (query: string) => call<PlaceSearch>('/api/places/search', { query }),
  timezoneAt: (latitude_deg: number, longitude_deg: number) =>
    call<TimezoneLookup>('/api/places/timezone', { latitude_deg, longitude_deg }),
}

export type Api = typeof api
