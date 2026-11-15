import { useEffect, useState } from 'react'

/**
 * Vrai tant que la police des glyphes (Noto Sans Symbols, auto-hébergée) répond. Si elle manque,
 * les 13 signes se replient sur leur identifiant (« Oph » pour le Serpentaire), de la même façon.
 */
export function useGlyphesDisponibles(): boolean {
  const [disponibles, setDisponibles] = useState(true)
  useEffect(() => {
    const polices = document.fonts
    if (polices === undefined || typeof polices.load !== 'function') return
    let actif = true
    polices.load('1em "Noto Sans Symbols"', '⛎').then(
      (chargees) => actif && setDisponibles(chargees.length > 0),
      () => actif && setDisponibles(false),
    )
    return () => {
      actif = false
    }
  }, [])
  return disponibles
}
