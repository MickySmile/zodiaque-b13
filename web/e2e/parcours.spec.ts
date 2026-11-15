import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'

/**
 * Parcours complet de la phase 6, sur l'API réelle : aucune valeur astronomique n'est écrite
 * ici. Les naissances sont fictives : jeu F5 (`"synthetic": true`), ou heures fabriquées à
 * partir des instants d'entrée que le moteur calcule lui-même pour 2026.
 */
const F5 = JSON.parse(
  readFileSync(
    fileURLToPath(new URL('../../tests/fixtures/births/f5-paris-2026.json', import.meta.url)),
    'utf-8',
  ),
) as { synthetic: boolean; cases: Record<string, { birth: { date_local: string; time_local: string } }> }

const CAPTURES = fileURLToPath(new URL('../../captures/', import.meta.url))
const VUES = [
  ['saisie', '#/', 'Entrez vos informations de naissance'],
  ['calendrier', '#/calendrier', 'Calendrier du Soleil dans les 13 signes'],
  ['roue', '#/roue', 'La roue à 13 signes'],
] as const
const LARGEURS = [360, 1280] as const
const MOIS = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
]

interface Signe {
  sign_id: string
  name: string
  start_deg: number
  width_deg: number
}
interface Entree {
  sign_id: string
  instant_local: string
}

async function signes(request: APIRequestContext): Promise<Signe[]> {
  return (await (await request.get('/api/boundaries')).json()).signs
}

async function entrees(request: APIRequestContext): Promise<Entree[]> {
  return (await (await request.get('/api/calendar/2026')).json()).entries
}

interface Saisie {
  date: string // AAAA-MM-JJ
  heure?: string // HH:MM, absente si l'heure est inconnue
  precision?: string
}

async function saisir(page: Page, saisie: Saisie) {
  const [annee, mois, jour] = saisie.date.split('-').map(Number)
  await page.goto('/#/')
  await page.getByLabel('Année').fill(String(annee))
  await page.getByLabel('Mois').selectOption({ label: MOIS[mois - 1] })
  await page.getByLabel('Jour').fill(String(jour))
  if (saisie.heure === undefined) {
    await page.getByRole('checkbox', { name: 'Heure inconnue' }).check()
  } else {
    const [heure, minute] = saisie.heure.split(':').map(Number)
    await page.getByLabel('Heure (0-23)').fill(String(heure))
    await page.getByLabel('Minute (0-59)').fill(String(minute))
    if (saisie.precision) await page.getByRole('radio', { name: saisie.precision }).check()
  }
  await page.getByLabel('Ville de naissance').fill('Paris')
  await page.getByRole('button', { name: 'Chercher ce lieu' }).click()
  await page.getByRole('button', { name: /^Paris, Île-de-France \(FR\)/ }).click()
  await page.getByRole('button', { name: 'Calculer mon signe solaire B13' }).click()
}

async function sansViolation(page: Page) {
  const resultat = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(resultat.violations).toEqual([])
}

async function passerEnSombre(page: Page) {
  await page.getByRole('button', { name: 'Mode sombre' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'sombre')
}

function statut(page: Page) {
  return page.getByRole('complementary', { name: 'Statut de ce qui est affiché' })
}

test.describe('FR-18 — statut et accessibilité de chaque vue', () => {
  for (const [nom, hash, titre] of VUES) {
    for (const largeur of LARGEURS) {
      test(`${nom} à ${largeur} px : « candidat », aucune violation axe AA, clair puis sombre`, async ({
        page,
      }) => {
        await page.setViewportSize({ width: largeur, height: 900 })
        await page.goto(`/${hash}`)
        await expect(page.getByRole('heading', { level: 1, name: titre })).toBeVisible()
        await expect(statut(page).getByText('candidat', { exact: true })).toBeVisible()
        // Le tableau n'arrive qu'avec la réponse de l'API : on l'attend avant de mesurer.
        if (nom !== 'saisie') await expect(page.getByRole('table')).toBeVisible()
        await sansViolation(page)
        const deborde = () =>
          page.evaluate(
            () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
          )
        expect(await deborde()).toBe(false)
        // Le titre d'un tableau n'est jamais coupé : il est hors de la zone qui défile.
        for (const titre of await page.locator('main h2').all()) {
          const boite = await titre.boundingBox()
          expect(boite!.x + boite!.width).toBeLessThanOrEqual(largeur)
        }
        if (nom === 'roue') {
          // Le tableau des 13 signes tient dans sa carte, même à 360 px.
          const interne = await page
            .getByRole('region', { name: 'Tableau des signes' })
            .evaluate((zone) => zone.scrollWidth > zone.clientWidth)
          expect(interne).toBe(false)
        }
        await page.screenshot({ path: `${CAPTURES}${nom}-${largeur}-clair.png`, fullPage: true })
        await passerEnSombre(page)
        await sansViolation(page)
        expect(await deborde()).toBe(false)
        await page.screenshot({ path: `${CAPTURES}${nom}-${largeur}-sombre.png`, fullPage: true })
      })
    }
  }
})

test.describe('parcours « Mon signe B13 »', () => {
  test('FR-03 : une heure à ± 15 min autour d’une entrée donne deux signes possibles', async ({
    page,
    request,
  }) => {
    const tous = await signes(request)
    const entree = (await entrees(request))[6]
    const rang = tous.findIndex((signe) => signe.sign_id === entree.sign_id)
    const avant = tous[(rang + tous.length - 1) % tous.length]
    await saisir(page, {
      date: entree.instant_local.slice(0, 10),
      heure: entree.instant_local.slice(11, 16),
      precision: '± 15 min',
    })
    const carte = page.getByRole('region', { name: 'Signes possibles' })
    await expect(
      carte.getByRole('heading', { name: `${avant.name} ou ${tous[rang].name}` }),
    ).toBeVisible()
    await expect(carte.getByText(/aucune probabilité n’est calculée/)).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'Vos signes solaires possibles (B13)',
    )
    await expect(statut(page).getByText('candidat', { exact: true })).toBeVisible()
    await expect(page.getByRole('img', { name: /^Soleil, longitude/ })).toBeVisible()
    for (const largeur of LARGEURS) {
      await page.setViewportSize({ width: largeur, height: 900 })
      await sansViolation(page)
      await page.screenshot({ path: `${CAPTURES}resultat-${largeur}-clair.png`, fullPage: true })
    }
    await passerEnSombre(page)
    await sansViolation(page)
    await page.screenshot({ path: `${CAPTURES}resultat-1280-sombre.png`, fullPage: true })
    await page.setViewportSize({ width: 360, height: 900 })
    await sansViolation(page)
    await page.screenshot({ path: `${CAPTURES}resultat-360-sombre.png`, fullPage: true })
    // Confidentialité : la saisie n'est ni dans l'adresse, ni dans le stockage du navigateur.
    expect(page.url()).toMatch(/#\/resultat$/)
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0)
    expect(await page.context().cookies()).toEqual([])
  })

  test('FR-02 : dix jours après une entrée, heure exacte, un seul signe', async ({
    page,
    request,
  }) => {
    const tous = await signes(request)
    const entree = (await entrees(request))[4]
    const [annee, mois, jour] = entree.instant_local.slice(0, 10).split('-').map(Number)
    const plusTard = new Date(Date.UTC(annee, mois - 1, jour + 10)).toISOString().slice(0, 10)
    await saisir(page, { date: plusTard, heure: '12:00' })
    const nom = tous.find((signe) => signe.sign_id === entree.sign_id)!.name
    const carte = page.getByRole('region', { name: 'Signe solaire' })
    await expect(carte.getByRole('heading', { name: new RegExp(`${nom}$`) })).toBeVisible()
    await expect(carte.getByText(/position géométrique, pas une intensité/)).toBeVisible()
    await expect(statut(page).getByText('candidat', { exact: true })).toBeVisible()
    // Sur cet écran, la roue n'offre aucun bouton sans effet : ses secteurs sont des images.
    await expect(page.locator('.roue [role="button"]')).toHaveCount(0)
    await expect(page.locator('.roue [data-sign-id][role="img"]')).toHaveCount(13)
    await sansViolation(page)
    for (const largeur of LARGEURS) {
      await page.setViewportSize({ width: largeur, height: 900 })
      await page.screenshot({
        path: `${CAPTURES}resultat-certain-${largeur}-clair.png`,
        fullPage: true,
      })
    }
  })

  test('FR-01 : heure inexistante — message bloquant, aucun résultat', async ({ page }) => {
    expect(F5.synthetic).toBe(true)
    const { date_local, time_local } = F5.cases.nonexistent.birth
    await saisir(page, { date: date_local, heure: time_local.slice(0, 5) })
    const alerte = page.getByRole('alert')
    await expect(alerte.getByText('Calcul impossible')).toBeVisible()
    await expect(alerte.getByText(/n’existe pas/)).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'Entrez vos informations de naissance',
    )
    await sansViolation(page)
  })

  test('FR-04 : heure ambiguë — deux scénarios, puis un seul après le choix', async ({ page }) => {
    const { date_local, time_local } = F5.cases.ambiguous.birth
    await saisir(page, { date: date_local, heure: time_local.slice(0, 5) })
    await expect(page.getByText(/Cette heure a existé deux fois/)).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'Signe solaire B13 : deux occurrences à départager',
    )
    await expect(page.getByRole('region', { name: /occurrence/ })).toHaveCount(2)
    await sansViolation(page)
    await page.getByRole('button', { name: /Garder la seconde occurrence/ }).click()
    await expect(page.getByText(/Cette heure a existé deux fois/)).toHaveCount(0)
    await expect(page.getByRole('region', { name: /occurrence|Signe solaire/ })).toHaveCount(1)
    // Le bouton utilisé a disparu : le focus revient au titre.
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused()
  })

  test('FR-05 : heure inconnue — carte de référence à midi, ni Ascendant ni maisons', async ({
    page,
  }) => {
    await saisir(page, { date: F5.cases.ordinary.birth.date_local })
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Carte de référence à midi')
    await expect(page.getByText(/Ascendant : absent/)).toBeVisible()
    await expect(page.getByText(/Maisons : absentes/)).toBeVisible()
    await expect(statut(page).getByText('candidat', { exact: true })).toBeVisible()
    await sansViolation(page)
    await page.screenshot({ path: `${CAPTURES}resultat-inconnue-1280-clair.png`, fullPage: true })
  })

  test('lieu introuvable : aucun voisin, coordonnées et fuseau à confirmer', async ({ page }) => {
    await page.goto('/#/')
    await page.getByLabel('Ville de naissance').fill('Lieuabsentdutout')
    await page.getByRole('button', { name: 'Chercher ce lieu' }).click()
    await expect(page.getByText(/aucun lieu voisin n’est proposé/)).toBeVisible()
    await page.getByLabel('Latitude (degrés décimaux)').fill('48,8566')
    await page.getByLabel('Longitude (degrés décimaux)').fill('2,3522')
    await page.getByRole('button', { name: 'Déduire le fuseau' }).click()
    await expect(
      page.getByRole('checkbox', { name: 'Je confirme le fuseau Europe/Paris' }),
    ).toBeVisible()
    await sansViolation(page)
  })
})

test.describe('calendrier et roue', () => {
  test('FR-06 : 13 entrées en 2026, en UTC et en heure de Paris, mention « indicatif »', async ({
    page,
  }) => {
    await page.goto('/#/calendrier')
    await page.getByLabel('Année').fill('2026')
    await page.getByRole('button', { name: 'Afficher le calendrier' }).click()
    const tableau = page.getByRole('table', { name: /2026/ })
    await expect(tableau.locator('tbody tr')).toHaveCount(13)
    await expect(tableau.getByRole('columnheader', { name: 'Entrée (UTC)' })).toBeVisible()
    await expect(
      tableau.getByRole('columnheader', { name: 'Entrée (heure de Paris)' }),
    ).toBeVisible()
    await expect(
      page.getByText("indicatif : près d'une frontière, l'heure de naissance compte"),
    ).toBeVisible()
  })

  test('FR-10 : dans le navigateur, chaque secteur couvre sa largeur à 0,1° près', async ({
    page,
    request,
  }) => {
    const tous = await signes(request)
    expect(tous).toHaveLength(13)
    await page.goto('/#/roue')
    await expect(page.locator('[data-sign-id]')).toHaveCount(13)
    const traces = await page.evaluate(() => {
      const svg = document.querySelector('.roue svg')!
      const [x, y, largeur, hauteur] = svg.getAttribute('viewBox')!.split(' ').map(Number)
      return {
        centre: [x + largeur / 2, y + hauteur / 2],
        secteurs: [...svg.querySelectorAll('[data-sign-id]')].map((groupe) => ({
          id: groupe.getAttribute('data-sign-id')!,
          d: groupe.querySelector('path.secteur')!.getAttribute('d')!,
        })),
      }
    })
    const wrap = (angle: number) => ((angle % 360) + 360) % 360
    const longitude = (px: number, py: number) =>
      wrap((Math.atan2(traces.centre[1] - py, px - traces.centre[0]) * 180) / Math.PI - 180)
    let somme = 0
    for (const signe of tous) {
      const trace = traces.secteurs.find((secteur) => secteur.id === signe.sign_id)!.d
      const morceaux = trace.match(/[MLAZ][^MLAZ]*/g)!
      const nombres = (texte: string) => texte.slice(1).trim().split(/[\s,]+/).map(Number)
      const [x0, y0] = nombres(morceaux[0])
      const arc = nombres(morceaux[1])
      const debut = longitude(x0, y0)
      const largeur = wrap(longitude(arc[5], arc[6]) - debut)
      somme += largeur
      expect(Math.abs(largeur - signe.width_deg)).toBeLessThanOrEqual(0.1)
      const ecart = wrap(debut - signe.start_deg)
      expect(Math.min(ecart, 360 - ecart)).toBeLessThanOrEqual(0.1)
    }
    expect(Math.abs(somme - 360)).toBeLessThanOrEqual(0.1)
  })

  test('roue : la police des glyphes est chargée, ⛎ est monochrome, sans repli', async ({
    page,
  }) => {
    await page.goto('/#/roue')
    await page.evaluate(() => document.fonts.ready)
    const serpentaire = page.locator('[data-nom-de="Oph"] text.glyphe')
    await expect(serpentaire).toHaveText('⛎︎')
    expect(await page.evaluate(() => document.fonts.check('28px "Noto Sans Symbols"', '⛎'))).toBe(
      true,
    )
    const police = await serpentaire.evaluate((texte) => getComputedStyle(texte).fontFamily)
    expect(police.startsWith('"Noto Sans Symbols"')).toBe(true)
    // Abréviation : le code UAI du signe, « Oph », jamais « Ser » (le Serpent).
    await expect(page.locator('[data-nom-de="Oph"] text.abreviation')).toHaveText('Oph')
  })

  test('roue : tout au clavier — un secteur se sélectionne et sa ligne de tableau répond', async ({
    page,
  }) => {
    await page.goto('/#/roue')
    await expect(page.locator('[data-sign-id]')).toHaveCount(13)
    // Depuis le haut du document, à la touche Tab seulement : lien d'évitement, trois vues,
    // thème, puis le premier secteur de la roue.
    const premier = page.locator('[data-sign-id]').first()
    for (let pas = 0; pas < 12 && !(await premier.evaluate((e) => e === document.activeElement)); pas += 1) {
      await page.keyboard.press('Tab')
    }
    await expect(premier).toBeFocused()
    const secteur = page.getByRole('button', { name: /^Serpentaire : de/ })
    for (let pas = 0; pas < 13 && !(await secteur.evaluate((e) => e === document.activeElement)); pas += 1) {
      await page.keyboard.press('Tab')
    }
    await expect(secteur).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(secteur).toHaveAttribute('aria-pressed', 'true')
    const tableau = page.getByRole('table', { name: /13 signes/ })
    await expect(tableau.getByText('sélectionné')).toHaveCount(1)
    await expect(tableau.getByRole('button', { name: 'Serpentaire' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await sansViolation(page)
    // Espace désélectionne ; le secteur suivant vient à la touche Tab.
    await page.keyboard.press('Space')
    await expect(secteur).toHaveAttribute('aria-pressed', 'false')
    await expect(tableau.getByText('sélectionné')).toHaveCount(0)
    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: /^Sagittaire : de/ })).toBeFocused()
    // La ligne du tableau commande aussi la sélection.
    const ligne = tableau.getByRole('button', { name: 'Lion' })
    await ligne.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('button', { name: /^Lion : de/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  test('le lien « Aller au contenu » mène au contenu sans quitter la vue', async ({ page }) => {
    await page.goto('/#/calendrier')
    await expect(page.getByRole('table')).toBeVisible()
    await page.keyboard.press('Tab')
    const lien = page.getByRole('link', { name: 'Aller au contenu' })
    await expect(lien).toBeFocused()
    await expect(lien).toBeInViewport()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('main')).toBeFocused()
    expect(page.url()).toMatch(/#\/calendrier$/)
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'Calendrier du Soleil dans les 13 signes',
    )
  })

  test('roue : les 13 glyphes et le Soleil sont rendus par la police des symboles', async ({
    page,
  }) => {
    await page.goto('/#/roue')
    // La roue n'est dessinée qu'une fois le découpage reçu de l'API : on l'attend.
    await expect(page.locator('.roue text.glyphe')).toHaveCount(13)
    await page.evaluate(() => document.fonts.ready)
    const glyphes = await page.locator('.roue text.glyphe').allTextContents()
    expect(glyphes).toHaveLength(13)
    for (const glyphe of glyphes) {
      expect(glyphe).toMatch(/^.\ufe0e$/u)
      expect(
        await page.evaluate(
          async (caractere) =>
            (await document.fonts.load('36px "Noto Sans Symbols"', caractere)).length,
          glyphe[0],
        ),
      ).toBeGreaterThan(0)
    }
    // Le Soleil vient de la seconde police de symboles, chargée à la demande.
    expect(
      await page.evaluate(
        async () => (await document.fonts.load('34px "Noto Sans Symbols 2"', '\u2609')).length,
      ),
    ).toBeGreaterThan(0)
  })
})

test('aucune requête ne part vers un tiers pendant le parcours', async ({ page }) => {
  const externes: string[] = []
  page.on('request', (requete) => {
    const url = new URL(requete.url())
    if (!['localhost', '127.0.0.1'].includes(url.hostname) && url.protocol !== 'data:') {
      externes.push(requete.url())
    }
  })
  await saisir(page, { date: F5.cases.ordinary.birth.date_local, heure: '12:00' })
  await expect(page.getByRole('region', { name: 'Signe solaire' })).toBeVisible()
  await page.goto('/#/calendrier')
  await expect(page.getByRole('table')).toBeVisible()
  await page.goto('/#/roue')
  await page.waitForLoadState('networkidle')
  expect(externes).toEqual([])
})

test('la saisie de naissance ne part jamais dans une adresse', async ({ page }) => {
  const adresses: string[] = []
  page.on('request', (requete) => adresses.push(requete.url()))
  const { date_local } = F5.cases.ordinary.birth
  await saisir(page, { date: date_local, heure: '12:00' })
  await expect(page.getByRole('region', { name: 'Signe solaire' })).toBeVisible()
  for (const adresse of adresses) {
    expect(adresse).not.toContain(date_local)
    expect(adresse).not.toContain('Paris')
    expect(adresse).not.toContain('?')
  }
})
