import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client.ts'
import type { Api } from '../api/client.ts'
import { LIEU_FICTIF, clientEssai, signeSolaire } from '../essais/jeux.ts'
import { Saisie } from './Saisie.tsx'

/** Saisie fictive : une date et une heure quelconques, dans un lieu inventé. */
async function remplir(options: { heure?: boolean } = {}) {
  const utilisateur = userEvent.setup()
  await utilisateur.type(screen.getByLabelText('Année'), '2000')
  await utilisateur.selectOptions(screen.getByLabelText('Mois'), 'juin')
  await utilisateur.type(screen.getByLabelText('Jour'), '1')
  if (options.heure !== false) {
    await utilisateur.type(screen.getByLabelText('Heure (0-23)'), '9')
    await utilisateur.type(screen.getByLabelText('Minute (0-59)'), '5')
  }
  await utilisateur.type(screen.getByLabelText('Ville de naissance'), 'Villefictive')
  await utilisateur.click(screen.getByRole('button', { name: 'Chercher ce lieu' }))
  await utilisateur.click(await screen.findByRole('button', { name: /^Villefictive/ }))
  return utilisateur
}

function monter(client = clientEssai(), onResultat = vi.fn()) {
  render(<Saisie client={client} statut="candidate" onResultat={onResultat} />)
  return onResultat
}

describe('écran de saisie (planche 6)', () => {
  it('FR-18 : affiche le statut des données', () => {
    monter()
    expect(screen.getByText('candidat')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Entrez vos informations de naissance',
    )
  })

  it('aucune date n’est préremplie : rien ne peut être calculé par mégarde', () => {
    monter()
    expect(screen.getByLabelText('Année')).toHaveValue(null)
    expect(screen.getByLabelText('Jour')).toHaveValue(null)
    expect(screen.getByLabelText('Mois')).toHaveValue('')
  })

  it('FR-01 : envoie la saisie telle que l’annexe la décrit, dans le corps de la requête', async () => {
    const sunSign = vi.fn<Api['sunSign']>(async () => signeSolaire([{ signe: 'Leo' }]))
    const onResultat = monter(clientEssai({ sunSign }))
    const utilisateur = await remplir()
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    expect(sunSign).toHaveBeenCalledWith({
      date_local: '2000-06-01',
      time_local: '09:05:00',
      time_status: 'known',
      time_uncertainty_seconds: 0,
      timezone: LIEU_FICTIF.timezone,
      fold: null,
      latitude_deg: LIEU_FICTIF.latitude_deg,
      longitude_deg: LIEU_FICTIF.longitude_deg,
      altitude_m: null,
      calendar: 'proleptic_gregorian',
      source: 'user_input',
    })
    expect(onResultat).toHaveBeenCalledTimes(1)
  })

  it('FR-01 : heure inexistante — message bloquant, aucun résultat', async () => {
    const message = 'Cette heure locale n’existe pas : ce jour-là, les horloges ont été avancées.'
    const sunSign = vi.fn(async () => {
      throw new ApiError(422, 'nonexistent_local_time', message)
    })
    const onResultat = monter(clientEssai({ sunSign }))
    const utilisateur = await remplir()
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    const alerte = await screen.findByRole('alert')
    expect(within(alerte).getByText('Calcul impossible')).toBeInTheDocument()
    expect(within(alerte).getByText(message)).toBeInTheDocument()
    expect(onResultat).not.toHaveBeenCalled()
  })

  it('FR-03 : la précision de l’heure part en secondes, avec le statut « uncertain »', async () => {
    const sunSign = vi.fn<Api['sunSign']>(async () => signeSolaire([{ signe: 'Leo' }]))
    monter(clientEssai({ sunSign }))
    const utilisateur = await remplir()
    await utilisateur.click(screen.getByRole('radio', { name: '± 15 min' }))
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    expect(sunSign.mock.calls[0][0]).toMatchObject({
      time_status: 'uncertain',
      time_uncertainty_seconds: 900,
    })
  })

  it('FR-05 : « heure inconnue » retire l’heure de la saisie', async () => {
    const sunSign = vi.fn<Api['sunSign']>(async () => signeSolaire([{ signe: 'Leo' }]))
    monter(clientEssai({ sunSign }))
    const utilisateur = await remplir({ heure: false })
    await utilisateur.click(screen.getByRole('checkbox', { name: 'Heure inconnue' }))
    expect(screen.getByLabelText('Heure (0-23)')).toBeDisabled()
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    expect(sunSign.mock.calls[0][0]).toMatchObject({
      time_status: 'unknown',
      time_local: null,
      time_uncertainty_seconds: 0,
    })
  })

  it('champs manquants : la demande ne part pas, la liste des manques est annoncée', async () => {
    const sunSign = vi.fn()
    monter(clientEssai({ sunSign }))
    await userEvent.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    const alerte = await screen.findByRole('alert')
    expect(within(alerte).getByText(/la date de naissance/)).toBeInTheDocument()
    expect(within(alerte).getByText(/le lieu de naissance/)).toBeInTheDocument()
    expect(sunSign).not.toHaveBeenCalled()
  })

  it('FR-01 : choisir une ville remplit la latitude, la longitude et le fuseau', async () => {
    monter()
    await remplir()
    const lieu = screen.getByRole('group', { name: 'Lieu de naissance' })
    expect(within(lieu).getByText(/^Lieux : GeoNames/)).toHaveTextContent('CC BY 4.0')
    expect(within(lieu).getByLabelText('Latitude (degrés décimaux)')).toHaveValue('10.5')
    expect(within(lieu).getByLabelText('Longitude (degrés décimaux)')).toHaveValue('20.25')
    expect(within(lieu).getByText(/Fuseau historique/)).toHaveTextContent('Europe/Paris')
    expect(within(lieu).getByText(/Coordonnées/)).toHaveTextContent('GeoNames, Villefictive')
    // Le fuseau vient du registre des lieux : aucune confirmation n'est demandée.
    expect(within(lieu).queryByRole('checkbox', { name: /Je confirme le fuseau/ })).toBeNull()
  })

  it('les champs de coordonnées sont toujours là, même avant toute recherche', () => {
    monter()
    expect(screen.getByLabelText('Latitude (degrés décimaux)')).toHaveValue('')
    expect(screen.getByLabelText('Longitude (degrés décimaux)')).toHaveValue('')
    expect(screen.getByLabelText('Ville de naissance')).toBeInTheDocument()
  })

  it('retoucher les coordonnées d’une ville : la ville est oubliée, le fuseau est à déduire', async () => {
    const sunSign = vi.fn<Api['sunSign']>(async () => signeSolaire([{ signe: 'Leo' }]))
    monter(clientEssai({ sunSign }))
    const utilisateur = await remplir()
    const latitude = screen.getByLabelText('Latitude (degrés décimaux)')
    await utilisateur.clear(latitude)
    await utilisateur.type(latitude, '11')
    expect(screen.getByText(/Coordonnées/)).toHaveTextContent('saisies à la main')
    expect(screen.getByRole('button', { name: /^Villefictive/ })).toHaveAttribute('aria-pressed', 'false')
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    expect(sunSign).not.toHaveBeenCalled()
    expect(await screen.findByRole('alert')).toHaveTextContent('le fuseau, à déduire des coordonnées')
  })

  it('choisir une autre ville remplace les coordonnées saisies à la main', async () => {
    monter()
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Latitude (degrés décimaux)'), '1')
    await utilisateur.type(screen.getByLabelText('Longitude (degrés décimaux)'), '2')
    await utilisateur.type(screen.getByLabelText('Ville de naissance'), 'Villefictive')
    await utilisateur.click(screen.getByRole('button', { name: 'Chercher ce lieu' }))
    await utilisateur.click(await screen.findByRole('button', { name: /^Villefictive/ }))
    expect(screen.getByLabelText('Latitude (degrés décimaux)')).toHaveValue('10.5')
    expect(screen.getByLabelText('Longitude (degrés décimaux)')).toHaveValue('20.25')
  })

  it('lieu introuvable : aucun voisin proposé, la saisie des coordonnées est offerte', async () => {
    const searchPlaces = vi.fn(async () => ({
      places: [],
      attribution: '',
      data_status: 'candidate' as const,
      manifest: {},
    }))
    monter(clientEssai({ searchPlaces }))
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Ville de naissance'), 'Lieuabsent')
    await utilisateur.click(screen.getByRole('button', { name: 'Chercher ce lieu' }))
    expect(await screen.findByText(/Aucune localité de plus de 15 000 habitants/)).toBeInTheDocument()
    expect(screen.getByText(/aucun lieu voisin n’est proposé/)).toBeInTheDocument()
    expect(screen.getByLabelText('Latitude (degrés décimaux)')).toBeInTheDocument()
  })

  it('coordonnées saisies : le fuseau déduit doit être confirmé avant le calcul', async () => {
    const sunSign = vi.fn<Api['sunSign']>(async () => signeSolaire([{ signe: 'Leo' }]))
    const timezoneAt = vi.fn(async () => ({
      timezone: 'Europe/Paris',
      status: 'found' as const,
      needs_confirmation: true as const,
      data_status: 'candidate' as const,
      manifest: {},
    }))
    monter(clientEssai({ sunSign, timezoneAt }))
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Année'), '2000')
    await utilisateur.selectOptions(screen.getByLabelText('Mois'), 'juin')
    await utilisateur.type(screen.getByLabelText('Jour'), '1')
    await utilisateur.click(screen.getByRole('checkbox', { name: 'Heure inconnue' }))
    await utilisateur.type(screen.getByLabelText('Latitude (degrés décimaux)'), '10,5')
    await utilisateur.type(screen.getByLabelText('Longitude (degrés décimaux)'), '20.25')
    await utilisateur.click(screen.getByRole('button', { name: 'Déduire le fuseau' }))
    expect(timezoneAt).toHaveBeenCalledWith(10.5, 20.25)
    const confirmation = await screen.findByRole('checkbox', {
      name: 'Je confirme le fuseau Europe/Paris',
    })
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    expect(sunSign).not.toHaveBeenCalled()
    expect(await screen.findByRole('alert')).toHaveTextContent('la confirmation du fuseau')
    await utilisateur.click(confirmation)
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    expect(sunSign.mock.calls[0][0]).toMatchObject({
      timezone: 'Europe/Paris',
      latitude_deg: 10.5,
      longitude_deg: 20.25,
    })
  })

  it('coordonnées sans fuseau civil : rien n’est déduit, rien n’est calculé', async () => {
    const timezoneAt = vi.fn(async () => ({
      timezone: null,
      status: 'no_civil_timezone' as const,
      needs_confirmation: true as const,
      data_status: 'candidate' as const,
      manifest: {},
    }))
    monter(clientEssai({ timezoneAt }))
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Latitude (degrés décimaux)'), '0')
    await utilisateur.type(screen.getByLabelText('Longitude (degrés décimaux)'), '-30')
    await utilisateur.click(screen.getByRole('button', { name: 'Déduire le fuseau' }))
    expect(await screen.findByText(/Aucun fuseau civil à ces coordonnées/)).toBeInTheDocument()
    expect(screen.queryByRole('checkbox', { name: /Je confirme le fuseau/ })).toBeNull()
  })

  it('fuseau inconnu de la base : dit comme tel, pas comme une pleine mer', async () => {
    const timezoneAt = vi.fn(async () => ({
      timezone: null,
      status: 'unknown_to_timezone_database' as const,
      needs_confirmation: true as const,
      data_status: 'candidate' as const,
      manifest: {},
    }))
    monter(clientEssai({ timezoneAt }))
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Latitude (degrés décimaux)'), '10')
    await utilisateur.type(screen.getByLabelText('Longitude (degrés décimaux)'), '10')
    await utilisateur.click(screen.getByRole('button', { name: 'Déduire le fuseau' }))
    expect(await screen.findByText(/n’est pas connu de la base des fuseaux/)).toBeInTheDocument()
    expect(screen.queryByText(/pleine mer/)).toBeNull()
    expect(screen.queryByRole('checkbox', { name: /Je confirme le fuseau/ })).toBeNull()
  })

  it('le rôle du lieu est dit exactement : il fixe le fuseau, donc l’instant', () => {
    monter()
    expect(screen.getByText(/Le lieu sert à trouver le fuseau, donc l’instant/)).toHaveTextContent(
      'Pour un même instant, la position du Soleil est la même partout',
    )
  })

  it('les conventions annoncent la réalisation Skyfield / Roman, jamais une reproduction exacte', () => {
    monter()
    const conventions = screen.getByRole('region', { name: 'Conventions' })
    expect(within(conventions).getByText(/réalisation Skyfield \/ Roman/)).toBeInTheDocument()
    expect(conventions.textContent).not.toMatch(/Delporte/)
  })
})
