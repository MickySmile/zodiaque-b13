import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { roue, signesGeneres } from '../essais/jeux.ts'
import { PageRoue } from './PageRoue.tsx'

describe('écran de la roue', () => {
  it('FR-18 : statut des données et niveau « convention »', () => {
    render(<PageRoue roue={roue()} statut="candidate" />)
    expect(screen.getByText('candidat')).toBeInTheDocument()
    expect(screen.getByText('Convention')).toBeInTheDocument()
  })

  it('FR-10 : le tableau donne les mêmes largeurs que la roue, pour les 13 signes', () => {
    render(<PageRoue roue={roue()} statut="candidate" />)
    const tableau = screen.getByRole('table', { name: /13 signes/ })
    const lignes = within(tableau).getAllByRole('row').slice(1)
    expect(lignes).toHaveLength(13)
    signesGeneres().forEach((signe, rang) => {
      expect(lignes[rang]).toHaveTextContent(signe.name)
      expect(lignes[rang]).toHaveTextContent(
        signe.width_deg.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
      )
    })
  })

  it('sélection : le secteur et sa ligne de tableau se répondent, au clavier comme à la souris', async () => {
    render(<PageRoue roue={roue()} statut="candidate" />)
    const tableau = screen.getByRole('table', { name: /13 signes/ })
    await userEvent.click(within(tableau).getByRole('button', { name: 'Serpentaire' }))
    expect(within(tableau).getByRole('button', { name: 'Serpentaire' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: /^Serpentaire : de/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(within(tableau).getByText('sélectionné')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /^Lion : de/ }))
    expect(within(tableau).getByRole('button', { name: 'Lion' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(within(tableau).getAllByText('sélectionné')).toHaveLength(1)
  })

  it('sans données, rien n’est dessiné à la place', () => {
    render(<PageRoue roue={null} statut="indisponible" />)
    expect(screen.queryByRole('table')).toBeNull()
    expect(screen.getByText(/La roue n’est pas affichée/)).toBeInTheDocument()
  })
})
