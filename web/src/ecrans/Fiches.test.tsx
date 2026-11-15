import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client.ts'
import { clientEssai, fiches, roue, signesGeneres } from '../essais/jeux.ts'
import { Fiches } from './Fiches.tsx'

/**
 * FR-15 : « Étant donné le Serpentaire, quand j'ouvre sa fiche, alors s'affichent archétype,
 * ressources, tensions, question d'introspection et provenance de chaque règle (H, M ou C). »
 * Les textes des fiches d'essai sont du remplissage : le contenu réel est contrôlé côté moteur.
 */
function monter(signe: string | null = null, client = clientEssai(), choisir = vi.fn()) {
  render(
    <Fiches client={client} roue={roue()} statut="candidate" signe={signe} onSigne={choisir} />,
  )
  return choisir
}

async function carte() {
  return within(await screen.findByRole('article'))
}

describe('FR-15 — fiches de signe (piste Carte)', () => {
  it('FR-15 : la fiche du Serpentaire montre archétype, ressources, tensions, question et provenance', async () => {
    monter('Oph')
    const fiche = await carte()
    expect(fiche.getByRole('heading', { level: 2, name: 'Serpentaire' })).toBeInTheDocument()
    for (const [rubrique, texte] of [
      ['Archétype', 'Archétype d’essai de Oph'],
      ['Ressources', 'Ressources d’essai de Oph'],
      ['Tensions', 'Tensions d’essai de Oph'],
      ['Question d’introspection', '« Question d’essai de Oph ? »'],
    ]) {
      const bloc = within(fiche.getByRole('group', { name: rubrique }))
      expect(bloc.getByText(texte)).toBeInTheDocument()
      // Provenance en toutes lettres, pas par la seule lettre ni par une couleur.
      expect(bloc.getByText('C · choix contemporain')).toBeInTheDocument()
    }
  })

  it('FR-18 : statut des données, niveau « interprétation » et mention « proposition symbolique »', async () => {
    monter('Oph')
    await carte()
    expect(screen.getByText('candidat')).toBeInTheDocument()
    const niveaux = screen.getAllByRole('listitem').map((niveau) => niveau.textContent)
    expect(niveaux).toContain('03 Interprétation : fiches de signe — proposition symbolique')
    expect(
      screen.getByText(/Proposition contemporaine · clé de lecture choisie, non une description des personnes/),
    ).toBeInTheDocument()
  })

  it('les 13 signes ont la même fiche : mêmes rubriques, même gabarit, même glyphe monochrome', async () => {
    const formes = new Set<string>()
    for (const signe of signesGeneres()) {
      const { unmount } = render(
        <Fiches client={clientEssai()} roue={roue()} statut="candidate" signe={signe.sign_id} onSigne={vi.fn()} />,
      )
      const article = await screen.findByRole('article')
      expect(within(article).getByRole('heading', { level: 2 })).toHaveTextContent(signe.name)
      const glyphe = article.querySelector('.carte-glyphe')!
      expect(glyphe.textContent).toBe(`${signe.glyph}︎`)
      formes.add(
        [
          article.className,
          ...[...article.querySelectorAll('[role="group"]')].map((groupe) => groupe.getAttribute('aria-label')),
        ].join('|'),
      )
      unmount()
    }
    expect(formes.size).toBe(1)
  })

  it('une rubrique que le PRD ne remplit pas est dite manquante, jamais comblée', async () => {
    monter('Tau')
    const fiche = await carte()
    for (const rubrique of ['Archétype', 'Ressources', 'Inférences interdites']) {
      expect(within(fiche.getByRole('group', { name: rubrique })).getByText('non rédigé à ce jour')).toBeInTheDocument()
    }
    expect(within(fiche.getByRole('group', { name: 'Tensions' })).getByText('Tensions d’essai de Tau')).toBeInTheDocument()
    const avis = screen.getByText(/Rubriques à écrire pour ce signe/)
    expect(avis).toHaveTextContent('archétype, ressources, inférences interdites')
    // Une rubrique vide ne veut pas dire que tout est permis : les règles communes valent pour tous.
    expect(avis).toHaveTextContent('Les règles communes obligatoires, plus bas, valent pour les 13 signes')
  })

  it('les rubriques complémentaires sont rendues telles quelles : texte, liste, tableau', async () => {
    monter('Oph')
    await carte()
    const zone = within(screen.getByRole('region', { name: 'Rubriques complémentaires' }))
    expect(zone.getByText('Texte complémentaire de Oph')).toBeInTheDocument()
    expect(zone.getByText('élément de liste deux')).toBeInTheDocument()
    expect(zone.getByRole('columnheader', { name: 'Colonne B' })).toBeInTheDocument()
    expect(zone.getByText('H · héritage documenté, M · référence mythologique')).toBeInTheDocument()
    expect(zone.getByText(/Propositions symboliques issues du référentiel/)).toBeInTheDocument()
  })

  it('la réserve du PRD reste sur la ligne du titre ; la phrase de clôture suit le texte', async () => {
    monter('Oph')
    await carte()
    const titre = screen.getByText('Rubrique avec réserve — réserve d’essai, à lire avant le texte')
    const textes = [...titre.closest('div')!.querySelectorAll('p')].map((p) => p.textContent)
    expect(textes.slice(0, 2)).toEqual(['Texte sous réserve de Oph', 'Phrase de clôture d’essai.'])
  })

  it('une réserve n’est jamais perdue : sur la carte, sous le sous-titre, dans les règles communes', async () => {
    const jeu = fiches()
    const reserve = 'réserve d’essai portée par cette rubrique'
    const signes = jeu.signs.map((fiche) => ({
      ...fiche,
      sheet: {
        ...fiche.sheet,
        operation: { ...fiche.sheet.operation, caveat: reserve },
        tensions: { ...fiche.sheet.tensions, caveat: reserve },
      },
    }))
    const regles = { ...jeu.rules, general_policy: { ...jeu.rules.general_policy, caveat: reserve } }
    monter('Oph', clientEssai({ signs: async () => ({ ...jeu, signs: signes, rules: regles }) }))
    const fiche = await carte()
    expect(within(fiche.getByRole('group', { name: 'Opération' })).getByText(reserve)).toBeInTheDocument()
    const tensions = within(fiche.getByRole('group', { name: 'Tensions' }))
    // Sur un titre en capitales, la réserve reste en minuscules et n'est écrite qu'une fois.
    expect(tensions.getByText(`— ${reserve}`)).toHaveClass('hors-capitales')
    expect(tensions.getAllByText(reserve, { exact: false })).toHaveLength(1)
    const communes = within(screen.getByRole('region', { name: 'Règles communes obligatoires' }))
    expect(communes.getByText(reserve)).toBeInTheDocument()
  })

  it('l’héritage historique est montré à part, avec son statut, pour tout signe', async () => {
    monter('Tau')
    await carte()
    const zone = screen.getByRole('region', { name: 'Rubriques complémentaires' })
    const titre = within(zone).getByRole('heading', { level: 3, name: 'Héritage historique' })
    expect(within(zone).getByText('Statut d’essai de l’héritage')).toBeInTheDocument()
    // La rubrique de provenance H vient après ce titre ; les autres, avant.
    const position = (texte: string) =>
      titre.compareDocumentPosition(within(zone).getByText(texte)) &
      Node.DOCUMENT_POSITION_FOLLOWING
    expect(position('Rubrique en liste')).toBeTruthy()
    expect(position('Rubrique en texte')).toBeFalsy()
    expect(position('Rubrique en tableau')).toBeFalsy()
  })

  it('sans signe demandé, la première fiche du cercle est ouverte ; la liste mène aux 13', async () => {
    const choisir = monter(null)
    const fiche = await carte()
    expect(fiche.getByRole('heading', { level: 2 })).toHaveTextContent(signesGeneres()[0].name)
    const liste = within(screen.getByRole('navigation', { name: 'Les 13 signes' }))
    expect(liste.getAllByRole('link')).toHaveLength(13)
    expect(liste.getByRole('link', { name: signesGeneres()[0].name })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await userEvent.click(liste.getByRole('link', { name: 'Serpentaire' }))
    expect(choisir).toHaveBeenCalledWith('Oph')
  })

  it('la carte donne le rang et les bornes calculées du signe, avec leur statut', async () => {
    monter('Oph')
    const fiche = await carte()
    const rang = signesGeneres().findIndex((signe) => signe.sign_id === 'Oph') + 1
    expect(fiche.getByText(`${String(rang).padStart(2, '0')} / 13`)).toBeInTheDocument()
    expect(fiche.getByText(/→.*candidat/)).toBeInTheDocument()
  })

  it('héritage : une rubrique de provenance M y va comme une rubrique H ; sans contenu, pas de titre', async () => {
    const jeu = fiches()
    const signes = jeu.signs.map((fiche) => ({
      ...fiche,
      sheet: {
        ...fiche.sheet,
        additional_sections:
          fiche.sign_id === 'Leo'
            ? fiche.sheet.additional_sections.filter((s) => !s.provenance?.includes('H'))
            : fiche.sheet.additional_sections.map((s) =>
                s.label === 'Rubrique en texte' ? { ...s, provenance: ['M' as const] } : s,
              ),
      },
    }))
    const client = clientEssai({ signs: async () => ({ ...jeu, signs: signes }) })
    const { unmount } = render(
      <Fiches client={client} roue={roue()} statut="candidate" signe="Oph" onSigne={vi.fn()} />,
    )
    await carte()
    const zone = screen.getByRole('region', { name: 'Rubriques complémentaires' })
    const titre = within(zone).getByRole('heading', { level: 3, name: 'Héritage historique' })
    expect(
      titre.compareDocumentPosition(within(zone).getByText('Rubrique en texte')) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    unmount()
    // Un signe sans rubrique de cette provenance : aucun titre creux, quel que soit le signe.
    render(<Fiches client={client} roue={roue()} statut="candidate" signe="Leo" onSigne={vi.fn()} />)
    await carte()
    expect(screen.queryByRole('heading', { level: 3, name: 'Héritage historique' })).toBeNull()
  })

  it('correspondances historiques : une vue à part, les 13 signes marqués « inactif »', async () => {
    monter('Oph')
    await carte()
    const tableau = within(screen.getByRole('table', { name: /Correspondances historiques/ }))
    const lignes = tableau.getAllByRole('row').slice(1)
    expect(lignes).toHaveLength(13)
    for (const ligne of lignes) expect(ligne).toHaveTextContent('inactif')
    expect(screen.getByText(/aucun calcul ni aucune lecture ne s’en sert/)).toBeInTheDocument()
    expect(screen.getByText('Décision d’essai sur les catégories héritées')).toBeInTheDocument()
    // Une valeur absente : un tiret, par la même règle pour tout signe, sans rien affirmer.
    const sans = lignes.filter((ligne) => within(ligne).queryAllByText('non renseigné').length > 0)
    expect(sans.length).toBeGreaterThan(0)
    for (const ligne of sans) expect(within(ligne).getAllByText('non renseigné')).toHaveLength(3)
    expect(screen.getByText('— : non renseigné dans le référentiel.')).toBeInTheDocument()
  })

  it('les règles communes du référentiel sont affichées avec sa version', async () => {
    monter('Oph')
    await carte()
    const regles = within(screen.getByRole('region', { name: 'Règles communes obligatoires' }))
    expect(regles.getByRole('heading', { name: 'Politique générale pour les 12 signes' })).toBeInTheDocument()
    expect(regles.getByText('Règle commune d’essai.')).toBeInTheDocument()
    expect(regles.getByText('Politique générale d’essai.')).toBeInTheDocument()
    expect(screen.getByText(/référentiel-d-essai/)).toBeInTheDocument()
  })

  it('signe inconnu dans l’adresse : dit, sans fiche supposée', async () => {
    monter('Xyz')
    expect(await screen.findByText(/Aucune fiche pour ce signe/)).toBeInTheDocument()
    expect(screen.queryByRole('article')).toBeNull()
  })

  it('fiches indisponibles : le message de l’API, aucune fiche', async () => {
    const signs = vi.fn(async () => {
      throw new ApiError(500, 'calculation_stopped', 'Le référentiel est invalide.')
    })
    monter('Oph', clientEssai({ signs }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Le référentiel est invalide.')
    expect(screen.queryByRole('article')).toBeNull()
  })

  it('un statut « synthetic » reçu avec les fiches s’affiche « démonstrateur synthétique »', async () => {
    monter('Oph', clientEssai({ signs: async () => fiches('synthetic') }))
    await carte()
    expect(screen.getByText('démonstrateur synthétique')).toBeInTheDocument()
  })
})
