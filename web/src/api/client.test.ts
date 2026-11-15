import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from './client.ts'
import type { BirthRequest } from './types.ts'

/** Saisie fictive : elle ne sert qu'à suivre son trajet jusqu'à la requête. */
const SAISIE: BirthRequest = {
  date_local: '2000-06-01',
  time_local: '09:05:00',
  time_status: 'known',
  time_uncertainty_seconds: 0,
  timezone: 'Europe/Paris',
  fold: null,
  latitude_deg: 10.5,
  longitude_deg: 20.25,
  altitude_m: null,
  calendar: 'proleptic_gregorian',
  source: 'user_input',
}

function reponse(corps: unknown, statut = 200) {
  return new Response(JSON.stringify(corps), { status: statut })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('client de l’API — confidentialité', () => {
  it('la saisie de naissance part dans le corps d’un POST, jamais dans l’adresse', async () => {
    const appel = vi.fn(async () => reponse({}))
    vi.stubGlobal('fetch', appel)
    await api.sunSign(SAISIE)
    const [adresse, options] = appel.mock.calls[0] as unknown as [string, RequestInit]
    expect(adresse).toBe('/api/sun-sign')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body as string)).toEqual(SAISIE)
  })

  it('la recherche de lieu et les coordonnées partent aussi dans le corps', async () => {
    const appel = vi.fn(async () => reponse({}))
    vi.stubGlobal('fetch', appel)
    await api.searchPlaces('Villefictive')
    await api.timezoneAt(10.5, 20.25)
    const adresses = appel.mock.calls.map((arguments_) => (arguments_ as unknown as [string])[0])
    expect(adresses).toEqual(['/api/places/search', '/api/places/timezone'])
  })

  it('le calendrier ne reçoit que l’année : aucun fuseau, aucun paramètre dans l’adresse', async () => {
    const appel = vi.fn(async () => reponse({}))
    vi.stubGlobal('fetch', appel)
    await api.calendar(2026)
    const [adresse, options] = appel.mock.calls[0] as unknown as [string, RequestInit]
    expect(adresse).toBe('/api/calendar/2026')
    expect(adresse).not.toContain('?')
    expect(options.method).toBeUndefined()
    // Le client n'a pas de quoi transmettre un fuseau : celui du lieu de naissance n'y passe pas.
    expect(api.calendar.length).toBe(1)
  })

  it('toutes les adresses sont relatives : aucun autre hôte que l’API locale', async () => {
    const appel = vi.fn(async () => reponse({}))
    vi.stubGlobal('fetch', appel)
    await api.boundaries()
    await api.calendar(2026)
    await api.sunSign(SAISIE)
    for (const arguments_ of appel.mock.calls) {
      expect((arguments_ as unknown as [string])[0]).toMatch(/^\/api\//)
    }
  })
})

describe('client de l’API — erreurs', () => {
  it('un refus de l’API devient une erreur avec son code et son message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        reponse({ error: { code: 'nonexistent_local_time', message: "Cette heure n'existe pas." } }, 422),
      ),
    )
    const erreur = await api.sunSign(SAISIE).catch((cause: unknown) => cause)
    expect(erreur).toBeInstanceOf(ApiError)
    expect((erreur as ApiError).code).toBe('nonexistent_local_time')
    expect((erreur as ApiError).status).toBe(422)
    // Apostrophe typographique à l'écran, comme dans le reste de l'interface.
    expect((erreur as ApiError).message).toBe('Cette heure n’existe pas.')
  })

  it('serveur injoignable ou réponse illisible : une erreur claire, jamais un résultat', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('réseau')
      }),
    )
    await expect(api.boundaries()).rejects.toMatchObject({ code: 'unreachable' })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('<html>', { status: 200 })),
    )
    await expect(api.boundaries()).rejects.toMatchObject({ code: 'unreachable' })
  })
})
