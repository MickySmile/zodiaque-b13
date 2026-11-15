import type { DataStatus } from '../api/types.ts'
import './statut.css'

/** Statut lu dans une réponse de l'API, ou état de cette lecture. */
export type StatutAffiche = DataStatus | 'chargement' | 'indisponible'

export type Niveau = 'mesure' | 'convention' | 'interpretation'

export interface NiveauAffiche {
  niveau: Niveau
  /** Ce qui, dans la vue, relève de ce niveau. */
  objet: string
}

const STATUTS: Record<StatutAffiche, { libelle: string; explication: string }> = {
  verified: {
    libelle: 'réel vérifié',
    explication: 'frontières vérifiées par une seconde source indépendante.',
  },
  candidate: {
    libelle: 'candidat',
    explication: 'frontières calculées, pas encore vérifiées par une seconde source indépendante.',
  },
  synthetic: {
    libelle: 'démonstrateur synthétique',
    explication: 'données fabriquées pour la démonstration : elles ne décrivent ni le ciel ni une personne.',
  },
  chargement: { libelle: 'lecture en cours', explication: 'le serveur de calcul est interrogé.' },
  indisponible: {
    libelle: 'indisponible',
    explication: 'le serveur de calcul ne répond pas : aucune donnée n’est affichée.',
  },
}

const NIVEAUX: Record<Niveau, { numero: string; libelle: string }> = {
  mesure: { numero: '01', libelle: 'Mesure / calcul' },
  convention: { numero: '02', libelle: 'Convention' },
  interpretation: { numero: '03', libelle: 'Interprétation' },
}

/**
 * FR-18 : statut des données et niveau de ce que la vue montre (piste Pédagogique).
 * Chaque badge porte un numéro et un libellé ; la couleur ne porte jamais l'information seule.
 */
export function BandeauStatut({
  statut,
  niveaux,
}: {
  statut: StatutAffiche
  niveaux: NiveauAffiche[]
}) {
  const { libelle, explication } = STATUTS[statut]
  return (
    <aside className="bandeau-statut" aria-label="Statut de ce qui est affiché">
      <p className="statut-donnees" data-statut={statut}>
        <span>Statut des données : </span>
        <strong>{libelle}</strong>
        <span className="statut-explication"> — {explication}</span>
      </p>
      {niveaux.length > 0 && (
        <ul className="niveaux">
          {niveaux.map(({ niveau, objet }) => (
            <li key={niveau} className={`badge badge-${NIVEAUX[niveau].numero}`}>
              <span className="badge-numero">{NIVEAUX[niveau].numero}</span>{' '}
              <span className="badge-libelle">{NIVEAUX[niveau].libelle}</span>
              <span className="badge-objet">
                {' : '}
                {objet}
                {niveau === 'interpretation' && ' — proposition symbolique'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
