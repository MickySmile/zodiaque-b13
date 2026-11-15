import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BandeauStatut } from './BandeauStatut.tsx'

describe('FR-18 — bandeau de statut', () => {
  it.each([
    ['verified', 'réel vérifié'],
    ['candidate', 'candidat'],
    ['synthetic', 'démonstrateur synthétique'],
  ] as const)('FR-18 : le statut « %s » s’affiche « %s »', (statut, libelle) => {
    render(<BandeauStatut statut={statut} niveaux={[]} />)
    const bandeau = screen.getByRole('complementary', { name: 'Statut de ce qui est affiché' })
    expect(within(bandeau).getByText(/Statut des données/)).toBeInTheDocument()
    expect(within(bandeau).getByText(libelle)).toBeInTheDocument()
  })

  it('FR-18 : tant que le statut n’est pas lu, rien n’est affirmé à sa place', () => {
    const { rerender } = render(<BandeauStatut statut="chargement" niveaux={[]} />)
    expect(screen.getByText('lecture en cours')).toBeInTheDocument()
    expect(screen.queryByText('candidat')).toBeNull()
    rerender(<BandeauStatut statut="indisponible" niveaux={[]} />)
    expect(screen.getByText('indisponible')).toBeInTheDocument()
    expect(screen.queryByText('candidat')).toBeNull()
  })

  it('FR-18 : chaque niveau porte un numéro et un libellé, jamais la couleur seule', () => {
    render(
      <BandeauStatut
        statut="candidate"
        niveaux={[
          { niveau: 'mesure', objet: 'longitude du Soleil' },
          { niveau: 'convention', objet: 'classement dans un signe' },
          { niveau: 'interpretation', objet: 'fiche de signe' },
        ]}
      />,
    )
    const niveaux = screen.getAllByRole('listitem')
    expect(niveaux.map((niveau) => niveau.textContent)).toEqual([
      '01 Mesure / calcul : longitude du Soleil',
      '02 Convention : classement dans un signe',
      '03 Interprétation : fiche de signe — proposition symbolique',
    ])
  })
})
