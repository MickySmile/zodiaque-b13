import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { longitudeDans, roue, signesGeneres, wrap } from '../essais/jeux.ts'
import { RoueB13 } from './RoueB13.tsx'
import type { AstreRoue } from './RoueB13.tsx'

/**
 * FR-10 : « chaque secteur couvre sa largeur à 0,1° près, chaque point est à sa longitude, et une
 * étiquette déplacée est reliée à son point par un trait ».
 *
 * Les mesures sont refaites ici à partir du SVG rendu, par une projection inverse écrite dans ce
 * fichier : centre lu dans le viewBox, longitude 0° à gauche, sens direct (annexe § H et § J).
 * Les largeurs attendues viennent de `generes/frontieres.csv`.
 */
const TOLERANCE = 0.1

function centre(svg: SVGSVGElement): [number, number] {
  const [x, y, largeur, hauteur] = svg.getAttribute('viewBox')!.split(' ').map(Number)
  return [x + largeur / 2, y + hauteur / 2]
}

function longitudeDe(svg: SVGSVGElement, x: number, y: number): number {
  const [cx, cy] = centre(svg)
  return wrap((Math.atan2(cy - y, x - cx) * 180) / Math.PI - 180)
}

function rayonDe(svg: SVGSVGElement, x: number, y: number): number {
  const [cx, cy] = centre(svg)
  return Math.hypot(x - cx, y - cy)
}

function ecart(a: number, b: number): number {
  const d = wrap(a - b)
  return Math.min(d, 360 - d)
}

interface ArcMesure {
  debut: number
  largeur: number
  rayonExterieur: number
  rayonInterieur: number
}

/** Lit le tracé d'un secteur : M départ, A … arrivée (arc extérieur), L …, A … (arc intérieur). */
function mesurer(svg: SVGSVGElement, signId: string): ArcMesure {
  const trace = svg.querySelector(`[data-sign-id="${signId}"] path.secteur`)!.getAttribute('d')!
  const morceaux = trace.match(/[MLAZ][^MLAZ]*/g)!
  const nombres = (texte: string) => texte.slice(1).trim().split(/[\s,]+/).map(Number)
  const [x0, y0] = nombres(morceaux[0])
  const arc = nombres(morceaux[1])
  const [grandArc, x1, y1] = [arc[3], arc[5], arc[6]]
  const [xi, yi] = nombres(morceaux[2])
  const debut = longitudeDe(svg, x0, y0)
  const largeur = wrap(longitudeDe(svg, x1, y1) - debut)
  expect(grandArc).toBe(largeur > 180 ? 1 : 0)
  return {
    debut,
    largeur,
    rayonExterieur: rayonDe(svg, x0, y0),
    rayonInterieur: rayonDe(svg, xi, yi),
  }
}

function rendre(astres: AstreRoue[] = []) {
  const { container } = render(<RoueB13 donnees={roue()} astres={astres} />)
  return container.querySelector('svg') as SVGSVGElement
}

describe('FR-10 — roue à 13 secteurs proportionnels', () => {
  it('FR-10 : chaque secteur couvre sa largeur calculée à 0,1° près, mesurée sur le SVG', () => {
    const svg = rendre()
    for (const signe of signesGeneres()) {
      const mesure = mesurer(svg, signe.sign_id)
      expect(Math.abs(mesure.largeur - signe.width_deg)).toBeLessThanOrEqual(TOLERANCE)
      expect(ecart(mesure.debut, signe.start_deg)).toBeLessThanOrEqual(TOLERANCE)
    }
  })

  it('FR-10 : les 13 secteurs pavent le cercle, sans lacune ni chevauchement', () => {
    const svg = rendre()
    const mesures = signesGeneres().map((signe) => mesurer(svg, signe.sign_id))
    expect(mesures).toHaveLength(13)
    const somme = mesures.reduce((total, mesure) => total + mesure.largeur, 0)
    expect(Math.abs(somme - 360)).toBeLessThanOrEqual(TOLERANCE)
    mesures.forEach((mesure, rang) => {
      const suivant = mesures[(rang + 1) % mesures.length]
      expect(ecart(mesure.debut + mesure.largeur, suivant.debut)).toBeLessThanOrEqual(TOLERANCE)
    })
  })

  it('FR-10 : les secteurs ne sont pas égaux, le plus étroit n’est pas élargi', () => {
    const svg = rendre()
    const signes = signesGeneres()
    const largeurs = signes.map((signe) => mesurer(svg, signe.sign_id).largeur)
    expect(Math.max(...largeurs) - Math.min(...largeurs)).toBeGreaterThan(10)
    const etroit = signes.reduce((a, b) => (a.width_deg < b.width_deg ? a : b))
    expect(Math.abs(mesurer(svg, etroit.sign_id).largeur - etroit.width_deg)).toBeLessThanOrEqual(
      TOLERANCE,
    )
  })

  it('une frontière de signe s’arrête à son anneau (0,855 R à 1,00 R)', () => {
    const svg = rendre()
    const exterieur = mesurer(svg, 'Ari').rayonExterieur
    for (const signe of signesGeneres()) {
      const mesure = mesurer(svg, signe.sign_id)
      expect(mesure.rayonExterieur).toBeCloseTo(exterieur, 2)
      expect(mesure.rayonInterieur / exterieur).toBeCloseTo(0.855, 3)
    }
    const frontieres = [...svg.querySelectorAll('line.frontiere')]
    expect(frontieres).toHaveLength(13)
    const debuts = signesGeneres().map((signe) => signe.start_deg)
    for (const trait of frontieres) {
      const [x1, y1, x2, y2] = ['x1', 'y1', 'x2', 'y2'].map((nom) =>
        Number(trait.getAttribute(nom)),
      )
      const rayons = [rayonDe(svg, x1, y1), rayonDe(svg, x2, y2)].sort((a, b) => a - b)
      expect(rayons[0] / exterieur).toBeCloseTo(0.855, 3)
      expect(rayons[1] / exterieur).toBeCloseTo(1, 3)
      const longitude = longitudeDe(svg, x2, y2)
      expect(debuts.some((debut) => ecart(debut, longitude) <= TOLERANCE)).toBe(true)
    }
  })

  it('FR-10 : chaque point est à sa longitude', () => {
    const longitude = longitudeDans('Vir', 0.25)
    const svg = rendre([{ id: 'soleil', nom: 'Soleil', glyphe: '☉', longitude_deg: longitude }])
    const point = svg.querySelector('[data-astre-id="soleil"] circle.repere-exact')!
    const mesuree = longitudeDe(
      svg,
      Number(point.getAttribute('cx')),
      Number(point.getAttribute('cy')),
    )
    expect(ecart(mesuree, longitude)).toBeLessThanOrEqual(TOLERANCE)
    const exterieur = mesurer(svg, 'Ari').rayonExterieur
    const rayon = rayonDe(svg, Number(point.getAttribute('cx')), Number(point.getAttribute('cy')))
    expect(rayon / exterieur).toBeCloseTo(0.715, 3)
  })

  it('FR-10 : une étiquette déplacée est reliée à son point par un trait, le point ne bouge pas', () => {
    const premiere = longitudeDans('Gem', 0.5)
    const seconde = wrap(premiere + 0.04)
    const svg = rendre([
      { id: 'a', nom: 'Soleil, première occurrence', glyphe: '☉', longitude_deg: premiere },
      { id: 'b', nom: 'Soleil, seconde occurrence', glyphe: '☉', longitude_deg: seconde },
    ])
    const positions: number[] = []
    for (const [id, longitude] of [
      ['a', premiere],
      ['b', seconde],
    ] as const) {
      const groupe = svg.querySelector(`[data-astre-id="${id}"]`)!
      const point = groupe.querySelector('circle.repere-exact')!
      const [px, py] = [Number(point.getAttribute('cx')), Number(point.getAttribute('cy'))]
      // Le point reste à sa longitude vraie : l'anti-collision ne déplace que l'étiquette.
      expect(ecart(longitudeDe(svg, px, py), longitude)).toBeLessThanOrEqual(0.001)
      const etiquette = groupe.querySelector('text.etiquette-glyphe')!
      const [ex, ey] = [Number(etiquette.getAttribute('x')), Number(etiquette.getAttribute('y'))]
      positions.push(longitudeDe(svg, ex, ey))
      const rappel = groupe.querySelector('line.rappel')!
      expect(Number(rappel.getAttribute('x1'))).toBeCloseTo(px, 2)
      expect(Number(rappel.getAttribute('y1'))).toBeCloseTo(py, 2)
      const bout = longitudeDe(
        svg,
        Number(rappel.getAttribute('x2')),
        Number(rappel.getAttribute('y2')),
      )
      expect(ecart(bout, positions.at(-1)!)).toBeLessThanOrEqual(0.001)
    }
    // Les deux étiquettes sont écartées, dans l'ordre des longitudes.
    expect(wrap(positions[1] - positions[0])).toBeGreaterThan(5)
    expect(wrap(positions[1] - positions[0])).toBeLessThan(180)
  })

  it('FR-10 : une étiquette à sa place n’a pas de trait de rappel', () => {
    const svg = rendre([
      { id: 'seul', nom: 'Soleil', glyphe: '☉', longitude_deg: longitudeDans('Cap', 0.5) },
    ])
    expect(svg.querySelector('[data-astre-id="seul"] line.rappel')).toBeNull()
  })

  it('la graduation est continue : 360 traits, sans remise à zéro aux frontières', () => {
    const svg = rendre()
    expect(svg.querySelectorAll('.graduation line')).toHaveLength(360)
    // Chiffrée tous les 45° : huit repères, qu'on ne peut pas lire comme douze secteurs de 30°.
    const chiffres = [...svg.querySelectorAll('.graduation text.chiffre')].map((t) => t.textContent)
    expect(chiffres).toHaveLength(8)
    expect(chiffres).not.toContain('30°')
  })

  it('l’abréviation d’un signe est son code UAI : « Oph » pour le Serpentaire, jamais « Ser »', () => {
    const svg = rendre()
    const codes = signesGeneres().map(
      (signe) => svg.querySelector(`[data-nom-de="${signe.sign_id}"] text.abreviation`)!.textContent,
    )
    signesGeneres().forEach((signe, rang) => {
      // Le code est celui du signe, ou rien quand le secteur est trop étroit pour le loger.
      expect(['', signe.sign_id]).toContain(codes[rang])
    })
    expect(codes).toContain('Oph')
    expect(codes).not.toContain('Ser')
    expect(codes.filter((code) => code === '').length).toBeLessThan(13)
  })

  it('glyphe et code tiennent dans leur secteur et dans l’anneau : rien n’est élargi pour eux', () => {
    const svg = rendre()
    const exterieur = mesurer(svg, 'Ari').rayonExterieur
    for (const signe of signesGeneres()) {
      const nom = svg.querySelector(`[data-nom-de="${signe.sign_id}"]`)!
      const textes = [...nom.querySelectorAll('text')].filter((texte) => texte.textContent !== '')
      for (const texte of textes) {
        const [x, y] = [Number(texte.getAttribute('x')), Number(texte.getAttribute('y'))]
        const depuisLeDebut = wrap(longitudeDe(svg, x, y) - signe.start_deg)
        expect(depuisLeDebut).toBeGreaterThan(0)
        expect(depuisLeDebut).toBeLessThan(signe.width_deg)
        const fraction = rayonDe(svg, x, y) / exterieur
        expect(fraction).toBeGreaterThan(0.855)
        expect(fraction).toBeLessThan(1)
      }
    }
  })

  it('petit secteur : le glyphe seul, au milieu, sans code (annexe § H)', () => {
    const svg = rendre()
    const etroit = signesGeneres().reduce((a, b) => (a.width_deg < b.width_deg ? a : b))
    const nom = svg.querySelector(`[data-nom-de="${etroit.sign_id}"]`)!
    expect(nom.querySelector('text.abreviation')!.textContent).toBe('')
    const glyphe = nom.querySelector('text.glyphe')!
    const milieu = longitudeDe(svg, Number(glyphe.getAttribute('x')), Number(glyphe.getAttribute('y')))
    expect(ecart(milieu, etroit.start_deg + etroit.width_deg / 2)).toBeLessThanOrEqual(0.01)
  })
})

describe('roue — treize signes, un seul traitement', () => {
  it('les 13 secteurs ont la même structure et la même règle de couleur', () => {
    const svg = rendre()
    const groupes = [...svg.querySelectorAll('[data-sign-id]')]
    expect(groupes).toHaveLength(13)
    const forme = (groupe: Element) =>
      [...groupe.children].map((enfant) => `${enfant.tagName}.${enfant.getAttribute('class')}`).join('|')
    expect(new Set(groupes.map(forme)).size).toBe(1)
    const noms = [...svg.querySelectorAll('[data-nom-de]')]
    expect(noms.map((nom) => nom.getAttribute('data-nom-de'))).toEqual(
      groupes.map((groupe) => groupe.getAttribute('data-sign-id')),
    )
    expect(new Set(noms.map(forme)).size).toBe(1)
    expect(new Set(noms.map((nom) => nom.getAttribute('class')))).toEqual(new Set(['nom']))
    for (const groupe of groupes) {
      const id = groupe.getAttribute('data-sign-id')!
      expect(groupe.getAttribute('class')).toBe('signe')
      expect(groupe.querySelector('path.secteur')!.getAttribute('style')).toContain(
        `var(--secteur-${id.toLowerCase()})`,
      )
    }
  })

  it('le glyphe du Serpentaire est U+26CE suivi de U+FE0E, sans présentation emoji', () => {
    const svg = rendre()
    const glyphe = svg.querySelector('[data-nom-de="Oph"] text.glyphe')!
    expect(glyphe.textContent).toBe('⛎︎')
    for (const texte of svg.querySelectorAll('text.glyphe')) {
      expect(texte.textContent).toMatch(/^.︎$/u)
    }
  })

  it('repli : sans la police des glyphes, chaque signe montre son identifiant (« Oph »)', () => {
    const { container } = render(<RoueB13 donnees={roue()} glyphesDisponibles={false} />)
    const textes = [...container.querySelectorAll('text.glyphe')].map((t) => t.textContent)
    expect(textes).toEqual(signesGeneres().map((signe) => signe.sign_id))
    expect(textes).toContain('Oph')
  })
})

describe('roue — accessibilité et sélection', () => {
  it('le texte dessiné dans l’anneau reste hors des boutons (WCAG 2.5.3)', () => {
    const { container } = render(<RoueB13 donnees={roue()} onSelection={vi.fn()} />)
    const svg = container.querySelector('svg')!
    expect(svg.querySelectorAll('[role="button"]')).toHaveLength(13)
    for (const bouton of svg.querySelectorAll('[role="button"]')) {
      expect(bouton.querySelector('text')).toBeNull()
    }
    expect(svg.querySelector('g.noms')).toHaveAttribute('aria-hidden', 'true')
  })

  it('sans sélection à offrir, un secteur est une image nommée, pas un bouton qui ne fait rien', () => {
    const svg = rendre()
    expect(screen.queryAllByRole('button')).toHaveLength(0)
    const images = [...svg.querySelectorAll('[data-sign-id]')]
    expect(images).toHaveLength(13)
    for (const image of images) {
      expect(image).toHaveAttribute('role', 'img')
      expect(image).not.toHaveAttribute('tabindex')
      expect(image).not.toHaveAttribute('aria-pressed')
      expect(image.getAttribute('aria-label')).toMatch(/largeur \d+,\d+°/)
    }
  })

  it('chaque secteur est atteignable au clavier et porte un nom accessible complet', () => {
    render(<RoueB13 donnees={roue()} onSelection={vi.fn()} />)
    const boutons = screen.getAllByRole('button')
    expect(boutons).toHaveLength(13)
    for (const bouton of boutons) {
      expect(bouton).toHaveAttribute('tabindex', '0')
      expect(bouton).toHaveAttribute('aria-pressed', 'false')
    }
    const serpentaire = screen.getByRole('button', { name: /^Serpentaire/ })
    expect(serpentaire.getAttribute('aria-label')).toMatch(/largeur \d+,\d+°/)
  })

  it('la sélection passe par le clavier et se voit sans la couleur (aria-pressed)', async () => {
    const choisir = vi.fn()
    const { rerender } = render(<RoueB13 donnees={roue()} onSelection={choisir} />)
    const lion = screen.getByRole('button', { name: /^Lion/ })
    lion.focus()
    await userEvent.keyboard('{Enter}')
    expect(choisir).toHaveBeenLastCalledWith('Leo')
    rerender(<RoueB13 donnees={roue()} selection="Leo" onSelection={choisir} />)
    expect(screen.getByRole('button', { name: /^Lion/ })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.keyboard(' ')
    expect(choisir).toHaveBeenLastCalledWith(null)
  })

  it('la légende dit l’orientation et l’absence d’Ascendant', () => {
    const { container } = render(<RoueB13 donnees={roue()} />)
    const legende = within(container.querySelector('figcaption')!)
    expect(legende.getByText(/longitude 0° à gauche/i)).toBeInTheDocument()
    expect(legende.getByText(/aucun Ascendant/i)).toBeInTheDocument()
  })

  it('focus et sélection ont chacun leur tracé : on ne les confond pas', () => {
    const { container } = render(<RoueB13 donnees={roue()} selection="Leo" onSelection={vi.fn()} />)
    const lion = container.querySelector('[data-sign-id="Leo"]')!
    expect(lion.querySelector('path.secteur')).not.toBeNull()
    expect(lion.querySelector('path.focus')).not.toBeNull()
    expect(container.querySelector('[data-nom-de="Leo"]')).toHaveAttribute('data-choisi', 'true')
    expect(container.querySelector('[data-nom-de="Vir"]')).toHaveAttribute('data-choisi', 'false')
  })

  it('un astre porte un nom accessible avec sa longitude', () => {
    const longitude = longitudeDans('Leo', 0.5)
    rendre([{ id: 'soleil', nom: 'Soleil', glyphe: '☉', longitude_deg: longitude }])
    expect(screen.getByRole('img', { name: /^Soleil, longitude \d+,\d+°/ })).toBeInTheDocument()
  })
})
