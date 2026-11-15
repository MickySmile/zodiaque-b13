import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App.tsx'

describe('socle de la phase 2', () => {
  it('affiche le titre de la page', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: 'Zodiaque B13' })).toBeInTheDocument()
  })

  it('affiche le statut des données « candidat »', () => {
    render(<App />)
    expect(screen.getByText('Statut des données : candidat')).toBeInTheDocument()
  })
})
