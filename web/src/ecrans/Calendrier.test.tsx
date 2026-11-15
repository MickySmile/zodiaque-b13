import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client.ts'
import { calendrier, clientEssai, roue } from '../essais/jeux.ts'
import { Calendrier } from './Calendrier.tsx'

function monter(client = clientEssai(), annee = 2000) {
  render(<Calendrier client={client} roue={roue()} statut="candidate" anneeInitiale={annee} />)
}

describe('écran du calendrier', () => {
  it('FR-06 : 13 entrées, en UTC et en heure de Paris, avec la mention « indicatif »', async () => {
    monter()
    const tableau = await screen.findByRole('table', { name: /Entrées du Soleil.*2000/ })
    const lignes = within(tableau).getAllByRole('row').slice(1)
    expect(lignes).toHaveLength(13)
    expect(within(tableau).getByRole('columnheader', { name: 'Entrée (UTC)' })).toBeInTheDocument()
    expect(
      within(tableau).getByRole('columnheader', { name: 'Entrée (heure de Paris)' }),
    ).toBeInTheDocument()
    // Mention du PRD, montrée telle que l'API la rend.
    expect(
      screen.getByText("indicatif : près d'une frontière, l'heure de naissance compte"),
    ).toBeInTheDocument()
  })

  it('FR-06 : dit où est le Soleil avant la première entrée, et que la sortie est l’entrée suivante', async () => {
    monter()
    await screen.findByRole('table')
    expect(screen.getByText(/La sortie d’un signe est l’entrée du suivant/)).toHaveTextContent(
      'à la fin de l’année précédente (voir le calendrier de cette année-là)',
    )
  })

  it('FR-06 : l’heure locale est celle que le serveur a calculée, lue sans reconversion', async () => {
    monter()
    const tableau = await screen.findByRole('table')
    const premiere = within(tableau).getAllByRole('row')[1]
    expect(premiere).toHaveTextContent('10 janvier 2000')
    expect(premiere).toHaveTextContent('02:03:04')
    expect(premiere).toHaveTextContent('03:03:04')
    expect(premiere).toHaveTextContent('UTC+01:00')
  })

  it('FR-18 : le statut affiché est celui du calendrier reçu', async () => {
    monter()
    expect(await screen.findByText('démonstrateur synthétique')).toBeInTheDocument()
  })

  it('les 13 signes ont la même ligne ; le glyphe est suivi de U+FE0E', async () => {
    monter()
    const tableau = await screen.findByRole('table')
    const lignes = within(tableau).getAllByRole('row').slice(1)
    expect(new Set(lignes.map((ligne) => ligne.children.length)).size).toBe(1)
    expect(within(tableau).getByText('⛎︎')).toBeInTheDocument()
    expect(within(tableau).getByText('Serpentaire')).toBeInTheDocument()
  })

  it('une entrée conditionnelle est signalée en toutes lettres', async () => {
    monter()
    const tableau = await screen.findByRole('table')
    expect(within(tableau).getAllByText('conditionnel')).toHaveLength(1)
    expect(
      screen.getByText(/Conditionnel : ces instants sont postérieurs aux tables de temps/),
    ).toBeInTheDocument()
  })

  it('changer d’année relance le calcul', async () => {
    const calendar = vi.fn(async (annee: number) => calendrier(annee))
    monter(clientEssai({ calendar }))
    await screen.findByRole('table')
    const champ = screen.getByLabelText('Année')
    await userEvent.clear(champ)
    await userEvent.type(champ, '2001')
    await userEvent.click(screen.getByRole('button', { name: 'Afficher le calendrier' }))
    expect(calendar).toHaveBeenLastCalledWith(2001)
    expect(await screen.findByRole('table', { name: /2001/ })).toBeInTheDocument()
  })

  it('année impossible : refusée à l’écran, sans appel au serveur', async () => {
    const calendar = vi.fn(async (annee: number) => calendrier(annee))
    monter(clientEssai({ calendar }))
    await screen.findByRole('table')
    const champ = screen.getByLabelText('Année')
    await userEvent.clear(champ)
    await userEvent.type(champ, '9999')
    await userEvent.click(screen.getByRole('button', { name: 'Afficher le calendrier' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('l’éphéméride couvre 1849 à 2150')
    expect(calendar).toHaveBeenCalledTimes(1)
  })

  it('année hors de l’éphéméride : le message de l’API, aucun tableau', async () => {
    const calendar = vi.fn(async () => {
      throw new ApiError(422, 'out_of_ephemeris_range', 'Date hors de la période couverte.')
    })
    monter(clientEssai({ calendar }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Date hors de la période couverte.')
    expect(screen.queryByRole('table')).toBeNull()
  })
})
