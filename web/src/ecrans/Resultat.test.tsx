import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { roue, signeSolaire } from '../essais/jeux.ts'
import { Resultat } from './Resultat.tsx'

function monter(resultat = signeSolaire([{ signe: 'Leo', fraction: 0.25 }]), onOccurrence = vi.fn()) {
  render(
    <Resultat
      resultat={resultat}
      roue={roue()}
      resume="Saisie d’essai"
      onOccurrence={onOccurrence}
      occupe={false}
    />,
  )
  return onOccurrence
}

describe('écran du résultat', () => {
  it('FR-18 : le statut vient du résultat ; un jeu fabriqué s’affiche « démonstrateur synthétique »', () => {
    monter()
    expect(screen.getByText('démonstrateur synthétique')).toBeInTheDocument()
    const niveaux = screen.getAllByRole('listitem').map((niveau) => niveau.textContent)
    expect(niveaux).toContain('01 Mesure / calcul : longitude du Soleil')
    expect(niveaux).toContain('02 Convention : classement dans l’un des 13 signes')
  })

  it('FR-18 : un résultat « candidate » s’affiche « candidat »', () => {
    monter(signeSolaire([{ signe: 'Leo' }], { statut: 'candidate' }))
    expect(screen.getByText('candidat')).toBeInTheDocument()
  })

  it('FR-02 : un signe certain est nommé, avec sa longitude et sa position dans le signe', () => {
    monter()
    const carte = screen.getByRole('region', { name: 'Signe solaire' })
    expect(within(carte).getByRole('heading', { name: /Lion/ })).toBeInTheDocument()
    expect(within(carte).getByText(/Longitude écliptique du Soleil/)).toBeInTheDocument()
    expect(within(carte).getByText(/position géométrique, pas une intensité/)).toBeInTheDocument()
    expect(within(carte).getByText('25 %', { exact: false })).toBeInTheDocument()
    // Forme imposée : « x° après l'entrée », jamais une notation qui suppose 30° par signe.
    expect(within(carte).getByText(/après\s+l’entrée, sur/)).toHaveTextContent('de largeur')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Votre signe solaire B13')
    expect(screen.getByRole('img', { name: /après l’entrée dans le signe$/ })).toBeInTheDocument()
  })

  it('FR-03 : deux signes possibles, présentés ensemble, sans probabilité', () => {
    monter(
      signeSolaire([{ signe: 'Oph', fraction: 0.0005, possibles: ['Sco', 'Oph'] }], {
        time_status: 'uncertain',
      }),
    )
    const carte = screen.getByRole('region', { name: 'Signes possibles' })
    expect(within(carte).getByRole('heading', { name: 'Scorpion ou Serpentaire' })).toBeInTheDocument()
    expect(within(carte).getByText(/aucune probabilité n’est calculée/)).toBeInTheDocument()
    expect(within(carte).getByText(/frontière entre Scorpion et Serpentaire/)).toBeInTheDocument()
    // Ni le titre ni la roue ne désignent un signe plutôt que l'autre.
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Vos signes solaires possibles (B13)',
    )
    expect(screen.getByText(/Le repère montre le Soleil à l’instant retenu/)).toHaveTextContent(
      'le repère ne désigne donc pas un signe plutôt que l’autre',
    )
    expect(carte.textContent).not.toMatch(/\d\s?% de chances|probable/)
  })

  it('FR-04 : heure ambiguë — deux scénarios, jusqu’au choix de l’occurrence', async () => {
    const onOccurrence = monter(
      signeSolaire(
        [
          { signe: 'Lib', fold: 0, decalage: 7200 },
          { signe: 'Lib', fold: 1, decalage: 3600, fraction: 0.5004 },
        ],
        { local_time_kind: 'ambiguous' },
      ),
    )
    expect(screen.getByText(/Cette heure a existé deux fois/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Signe solaire B13 : deux occurrences à départager',
    )
    expect(screen.getAllByRole('region', { name: /occurrence/ })).toHaveLength(2)
    expect(screen.getByText(/Les repères montrent le Soleil aux deux instants possibles/)).toBeInTheDocument()
    // Le décalage est une valeur : il sort de l'intitulé en capitales.
    expect(screen.getByText('(UTC+02:00)')).toHaveClass('hors-capitales')
    await userEvent.click(
      screen.getByRole('button', { name: 'Garder la seconde occurrence (UTC+01:00)' }),
    )
    expect(onOccurrence).toHaveBeenCalledWith(1)
  })

  it('FR-05 : heure inconnue — « carte de référence à midi », ni Ascendant ni maisons', () => {
    monter(
      signeSolaire([{ signe: 'Leo' }], {
        title: 'carte de référence à midi',
        time_status: 'unknown',
        local_time_kind: 'unknown',
      }),
    )
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^Carte de référence à midi$/)
    expect(screen.getByText(/Ascendant : absent/)).toHaveTextContent('heure de naissance inconnue')
    expect(screen.getByText(/Maisons : absentes/)).toBeInTheDocument()
  })

  it('FR-10 : la roue montre le Soleil à sa longitude, avec un équivalent textuel', () => {
    monter()
    expect(screen.getByRole('img', { name: /^Soleil, longitude/ })).toBeInTheDocument()
    // Sur cet écran, les secteurs sont des images nommées : aucun bouton sans effet.
    expect(screen.getAllByRole('img', { name: /largeur/ })).toHaveLength(13)
    expect(screen.queryAllByRole('button', { name: /largeur/ })).toHaveLength(0)
  })

  it('le nom complet des signes reste accessible : lien vers le tableau des 13 signes', () => {
    monter()
    expect(screen.getByRole('link', { name: 'tableau des 13 signes' })).toHaveAttribute(
      'href',
      '#/roue',
    )
  })

  it('aucun texte interprétatif dans le résultat : il renvoie à la fiche, proposition symbolique', () => {
    monter()
    const phrase = screen.getByText(/il ne contient aucun texte interprétatif/)
    expect(phrase).toHaveTextContent('proposition symbolique')
    expect(screen.getByRole('link', { name: 'fiche Lion' })).toHaveAttribute('href', '#/fiches/Leo')
  })

  it('FR-03 : deux signes possibles, deux fiches proposées, dans l’ordre du temps, sans préférence', () => {
    monter(
      signeSolaire([{ signe: 'Oph', fraction: 0.0005, possibles: ['Sco', 'Oph'] }], {
        time_status: 'uncertain',
      }),
    )
    const fichesProposees = screen.getAllByRole('link', { name: /^fiche / })
    expect(fichesProposees.map((lien) => lien.getAttribute('href'))).toEqual([
      '#/fiches/Sco',
      '#/fiches/Oph',
    ])
  })

  it('réserves : résultat conditionnel et fuseau d’avant 1970', () => {
    monter(
      signeSolaire([{ signe: 'Leo', conditionnel: true }], {
        timezone_caveat: 'zone_history_may_be_merged_before_1970',
      }),
    )
    expect(screen.getByText(/Résultat conditionnel/)).toBeInTheDocument()
    expect(screen.getByText(/avant 1970/)).toBeInTheDocument()
  })

  it('le manifeste du calcul est consultable', () => {
    monter()
    const manifeste = screen.getByText('Manifeste du calcul').closest('details')!
    expect(manifeste.textContent).toMatch(/model_b_iau_ecliptic_j2000_v1/)
    expect(manifeste.textContent).toMatch(/chart_input_hash/)
  })
})
