import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

test.describe('socle de la phase 2', () => {
  test('la page se charge et affiche le statut des données', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1, name: 'Zodiaque B13' })).toBeVisible()
    await expect(page.getByText('Statut des données : candidat')).toBeVisible()
  })

  test('aucune violation axe-core de niveau A ou AA', async ({ page }) => {
    await page.goto('/')
    const resultat = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze()
    expect(resultat.violations).toEqual([])
  })

  test('la page tient dans 360 px de large sans défilement horizontal', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 })
    await page.goto('/')
    const deborde = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    )
    expect(deborde).toBe(false)
  })

  test('aucune requête ne part vers un tiers', async ({ page }) => {
    const externes: string[] = []
    page.on('request', (requete) => {
      const url = new URL(requete.url())
      if (!['localhost', '127.0.0.1'].includes(url.hostname) && url.protocol !== 'data:') {
        externes.push(requete.url())
      }
    })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    expect(externes).toEqual([])
  })
})
