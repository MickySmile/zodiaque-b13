import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.tsx'
import { ApiError } from './api/client.ts'
import { clientEssai, fiches, roue, signeSolaire } from './essais/jeux.ts'

const ROUTES = [
  ['#/', 'Entrez vos informations de naissance'],
  ['#/calendrier', 'Calendrier du Soleil dans les 13 signes'],
  ['#/roue', 'La roue à 13 signes'],
  ['#/fiches', 'Les 13 fiches de signe'],
  ['#/fiches/Oph', 'Les 13 fiches de signe'],
  ['#/resultat', 'Aucun résultat à afficher'],
] as const

beforeEach(() => {
  window.location.hash = ''
  document.documentElement.removeAttribute('data-theme')
})

afterEach(() => {
  window.location.hash = ''
})

function bandeau() {
  return within(screen.getByRole('complementary', { name: 'Statut de ce qui est affiché' }))
}

describe('FR-18 — le statut est visible sur chaque vue', () => {
  it.each(ROUTES)('FR-18 : la vue %s affiche « candidat » tant que G1 est fermée', async (hash, titre) => {
    window.location.hash = hash
    render(<App client={clientEssai({ boundaries: async () => roue('candidate') })} />)
    expect(await screen.findByRole('heading', { level: 1, name: titre })).toBeInTheDocument()
    // Le calendrier d'essai est fabriqué : son propre statut l'emporte sur cette vue.
    const attendu = hash === '#/calendrier' ? 'démonstrateur synthétique' : 'candidat'
    await waitFor(() => expect(bandeau().getByText(attendu)).toBeInTheDocument())
    expect(bandeau().getByText(/Statut des données/)).toBeInTheDocument()
  })

  it.each(ROUTES)('FR-18 : la vue %s affiche « réel vérifié » quand l’API le dit', async (hash) => {
    window.location.hash = hash
    const client = clientEssai({
      boundaries: async () => roue('verified'),
      calendar: async (annee) => ({ ...(await clientEssai().calendar(annee)), data_status: 'verified' }),
      signs: async () => fiches('verified'),
    })
    render(<App client={client} />)
    await waitFor(() => expect(bandeau().getByText('réel vérifié')).toBeInTheDocument())
  })

  it('FR-18 : API injoignable — « indisponible », jamais un statut supposé', async () => {
    const client = clientEssai({
      boundaries: async () => {
        throw new ApiError(0, 'unreachable', 'Le serveur de calcul ne répond pas.')
      },
    })
    render(<App client={client} />)
    await waitFor(() => expect(bandeau().getByText('indisponible')).toBeInTheDocument())
    expect(bandeau().queryByText('candidat')).toBeNull()
  })

  it('FR-18 : après un calcul, la vue du résultat porte le statut du résultat', async () => {
    const sunSign = vi.fn(async () => signeSolaire([{ signe: 'Leo' }], { statut: 'candidate' }))
    render(<App client={clientEssai({ sunSign })} />)
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Année'), '2000')
    await utilisateur.selectOptions(screen.getByLabelText('Mois'), 'juin')
    await utilisateur.type(screen.getByLabelText('Jour'), '1')
    await utilisateur.click(screen.getByRole('checkbox', { name: 'Heure inconnue' }))
    await utilisateur.type(screen.getByLabelText('Ville de naissance'), 'Villefictive')
    await utilisateur.click(screen.getByRole('button', { name: 'Chercher ce lieu' }))
    await utilisateur.click(await screen.findByRole('button', { name: /^Villefictive/ }))
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Votre signe solaire B13' })).toBeInTheDocument()
    expect(window.location.hash).toBe('#/resultat')
    expect(bandeau().getByText('candidat')).toBeInTheDocument()
    expect(screen.getByText(/Saisie : 1 juin 2000, heure inconnue, Villefictive/)).toBeInTheDocument()
  })
})

describe('coquille de l’application', () => {
  it('la navigation mène aux trois vues et marque la vue courante', async () => {
    render(<App client={clientEssai()} />)
    const navigation = screen.getByRole('navigation', { name: 'Vues' })
    const liens = within(navigation).getAllByRole('link')
    expect(liens.map((lien) => lien.textContent)).toEqual(['Mon signe', 'Calendrier', 'Roue', 'Fiches'])
    expect(within(navigation).getByRole('link', { name: 'Mon signe' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await userEvent.click(within(navigation).getByRole('link', { name: 'Roue' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'La roue à 13 signes' })).toBeInTheDocument()
    expect(within(navigation).getByRole('link', { name: 'Roue' })).toHaveAttribute('aria-current', 'page')
  })

  it('le lien « Aller au contenu » mène au contenu de la vue courante, sans changer de vue', async () => {
    window.location.hash = '#/roue'
    render(<App client={clientEssai()} />)
    await screen.findByRole('heading', { level: 1, name: 'La roue à 13 signes' })
    await userEvent.click(screen.getByRole('link', { name: 'Aller au contenu' }))
    expect(screen.getByRole('main')).toHaveFocus()
    expect(window.location.hash).toBe('#/roue')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('La roue à 13 signes')
  })

  it('au premier affichage, le focus reste en haut du document ; il va au titre en changeant de vue', async () => {
    render(<App client={clientEssai()} />)
    expect(screen.getByRole('heading', { level: 1 })).not.toHaveFocus()
    await userEvent.tab()
    expect(screen.getByRole('link', { name: 'Aller au contenu' })).toHaveFocus()
    await userEvent.click(screen.getByRole('link', { name: 'Calendrier' }))
    const titre = await screen.findByRole('heading', {
      level: 1,
      name: 'Calendrier du Soleil dans les 13 signes',
    })
    expect(titre).toHaveFocus()
  })

  it('FR-15 : l’adresse d’une fiche ouvre ce signe ; la liste change de fiche sans quitter la vue', async () => {
    window.location.hash = '#/fiches/Oph'
    render(<App client={clientEssai()} />)
    const article = await screen.findByRole('article')
    expect(within(article).getByRole('heading', { level: 2 })).toHaveTextContent('Serpentaire')
    expect(screen.getByRole('link', { name: 'Fiches' })).toHaveAttribute('aria-current', 'page')
    await userEvent.click(
      within(screen.getByRole('navigation', { name: 'Les 13 signes' })).getByRole('link', {
        name: 'Lion',
      }),
    )
    expect(window.location.hash).toBe('#/fiches/Leo')
    expect(within(screen.getByRole('article')).getByRole('heading', { level: 2 })).toHaveTextContent(
      'Lion',
    )
  })

  it('FR-18 : toute vue qui montre une fiche porte « proposition symbolique »', async () => {
    window.location.hash = '#/fiches'
    render(<App client={clientEssai()} />)
    await screen.findByRole('article')
    expect(bandeau().getByText(/proposition symbolique/)).toBeInTheDocument()
  })

  it('mode sombre : un bouton bascule le thème, clair par défaut', async () => {
    render(<App client={clientEssai()} />)
    expect(document.documentElement).toHaveAttribute('data-theme', 'clair')
    const bouton = screen.getByRole('button', { name: 'Mode sombre' })
    expect(bouton).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(bouton)
    expect(document.documentElement).toHaveAttribute('data-theme', 'sombre')
    expect(screen.getByRole('button', { name: 'Mode sombre' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('confidentialité : la saisie ne passe ni dans l’adresse ni dans le stockage du navigateur', async () => {
    const poser = vi.spyOn(Storage.prototype, 'setItem')
    render(<App client={clientEssai()} />)
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Année'), '2000')
    await utilisateur.selectOptions(screen.getByLabelText('Mois'), 'juin')
    await utilisateur.type(screen.getByLabelText('Jour'), '1')
    await utilisateur.click(screen.getByRole('checkbox', { name: 'Heure inconnue' }))
    await utilisateur.type(screen.getByLabelText('Ville de naissance'), 'Villefictive')
    await utilisateur.click(screen.getByRole('button', { name: 'Chercher ce lieu' }))
    await utilisateur.click(await screen.findByRole('button', { name: /^Villefictive/ }))
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    await screen.findByRole('heading', { level: 1, name: 'Votre signe solaire B13' })
    expect(window.location.href).not.toMatch(/2000|Villefictive/)
    expect(poser).not.toHaveBeenCalled()
    expect(document.cookie).toBe('')
    poser.mockRestore()
  })

  it('confidentialité : le calendrier part de l’année de l’horloge, jamais de l’année saisie', async () => {
    const calendar = vi.fn(async (annee: number) => clientEssai().calendar(annee))
    render(<App client={clientEssai({ calendar })} />)
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Année'), '2000')
    await utilisateur.selectOptions(screen.getByLabelText('Mois'), 'juin')
    await utilisateur.type(screen.getByLabelText('Jour'), '1')
    await utilisateur.click(screen.getByRole('checkbox', { name: 'Heure inconnue' }))
    await utilisateur.type(screen.getByLabelText('Ville de naissance'), 'Villefictive')
    await utilisateur.click(screen.getByRole('button', { name: 'Chercher ce lieu' }))
    await utilisateur.click(await screen.findByRole('button', { name: /^Villefictive/ }))
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    await screen.findByRole('heading', { level: 1, name: 'Votre signe solaire B13' })
    await utilisateur.click(screen.getByRole('link', { name: 'Calendrier' }))
    await screen.findByRole('table')
    const courante = new Date().getFullYear()
    expect(courante).not.toBe(2000)
    expect(screen.getByLabelText('Année')).toHaveValue(courante)
    expect(calendar).toHaveBeenCalledTimes(1)
    expect(calendar).toHaveBeenCalledWith(courante)
  })

  it('FR-04 : choisir l’occurrence relance le calcul avec `fold`', async () => {
    const sunSign = vi
      .fn()
      .mockResolvedValueOnce(
        signeSolaire(
          [
            { signe: 'Lib', fold: 0, decalage: 7200 },
            { signe: 'Lib', fold: 1, decalage: 3600, fraction: 0.5004 },
          ],
          { local_time_kind: 'ambiguous' },
        ),
      )
      .mockResolvedValueOnce(signeSolaire([{ signe: 'Lib', fold: 1 }], { local_time_kind: 'ambiguous' }))
    render(<App client={clientEssai({ sunSign })} />)
    const utilisateur = userEvent.setup()
    await utilisateur.type(screen.getByLabelText('Année'), '2000')
    await utilisateur.selectOptions(screen.getByLabelText('Mois'), 'octobre')
    await utilisateur.type(screen.getByLabelText('Jour'), '29')
    await utilisateur.type(screen.getByLabelText('Heure (0-23)'), '2')
    await utilisateur.type(screen.getByLabelText('Minute (0-59)'), '30')
    await utilisateur.type(screen.getByLabelText('Ville de naissance'), 'Villefictive')
    await utilisateur.click(screen.getByRole('button', { name: 'Chercher ce lieu' }))
    await utilisateur.click(await screen.findByRole('button', { name: /^Villefictive/ }))
    await utilisateur.click(screen.getByRole('button', { name: 'Calculer mon signe solaire B13' }))
    await utilisateur.click(await screen.findByRole('button', { name: /Garder la seconde occurrence/ }))
    await waitFor(() => expect(sunSign).toHaveBeenCalledTimes(2))
    expect(sunSign.mock.calls[1][0]).toMatchObject({ fold: 1, time_local: '02:30:00' })
    await waitFor(() => expect(screen.queryByText(/Cette heure a existé deux fois/)).toBeNull())
    // Le bouton utilisé a disparu : le focus revient au titre, il ne se perd pas.
    await waitFor(() => expect(screen.getByRole('heading', { level: 1 })).toHaveFocus())
  })
})
