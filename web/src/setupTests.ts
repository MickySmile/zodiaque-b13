import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// jsdom n'a pas de défilement : l'application remonte en haut de page à chaque changement de vue.
window.scrollTo = () => {}

afterEach(() => {
  cleanup()
})
