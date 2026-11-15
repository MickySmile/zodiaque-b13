import { useEffect, useState } from 'react'
import { ApiError } from '../api/client.ts'
import type { Api } from '../api/client.ts'
import type {
  Provenance,
  SheetEntry,
  SheetSection,
  SignSheet,
  Signs,
  WheelData,
} from '../api/types.ts'
import { degres, glypheTexte } from '../formats.ts'
import { BandeauStatut } from '../statut/BandeauStatut.tsx'
import type { StatutAffiche } from '../statut/BandeauStatut.tsx'
import './fiches.css'

type Etat =
  | { etat: 'chargement' }
  | { etat: 'pret'; fiches: Signs }
  | { etat: 'erreur'; message: string }

interface Props {
  client: Api
  /** Découpage calculé : rang et bornes du signe ; `null` s'il n'a pas pu être lu. */
  roue: WheelData | null
  statut: StatutAffiche
  /** Identifiant du signe demandé dans l'adresse, ou `null`. */
  signe: string | null
  onSigne: (signId: string) => void
  glyphesDisponibles?: boolean
}

const PROVENANCES: Record<Provenance, string> = {
  H: 'héritage documenté',
  M: 'référence mythologique',
  C: 'choix contemporain',
}

/** Rubriques communes aux 13 fiches, dans l'ordre de la carte. Même liste pour tous les signes. */
const RUBRIQUES = [
  ['archetype', 'Archétype'],
  ['resources', 'Ressources'],
  ['tensions', 'Tensions'],
  ['introspection_question', 'Question d’introspection'],
  ['forbidden_inferences', 'Inférences interdites'],
] as const

const NOMS_RUBRIQUES: Record<string, string> = {
  operation: 'opération',
  archetype: 'archétype',
  resources: 'ressources',
  tensions: 'tensions',
  introspection_question: 'question d’introspection',
  forbidden_inferences: 'inférences interdites',
}

function provenance(entree: SheetEntry): string {
  return (entree.provenance ?? []).map((lettre) => `${lettre} · ${PROVENANCES[lettre]}`).join(', ')
}

/** Contenu d'une rubrique, tel qu'il est transcrit : texte, liste ou tableau. Jamais reformulé. */
function Contenu({ entree, reserveAuTitre = false }: { entree: SheetEntry; reserveAuTitre?: boolean }) {
  if (entree.status === 'missing') {
    return <p className="rubrique-manquante">non rédigé à ce jour</p>
  }
  return (
    <>
      {/* Une réserve du PRD n'est jamais perdue : si aucun titre ne la porte, elle s'écrit ici. */}
      {entree.caveat !== null && !reserveAuTitre && (
        <p className="rubrique-reserve">{entree.caveat}</p>
      )}
      {entree.text !== null && <p>{entree.text}</p>}
      {entree.items !== null && (
        <ul>
          {entree.items.map((element) => (
            <li key={element}>{element}</li>
          ))}
        </ul>
      )}
      {entree.table !== null && (
        <div className="defilement" tabIndex={0} role="region" aria-label="Tableau de la rubrique">
          <table>
            <thead>
              <tr>
                {entree.table.columns.map((colonne) => (
                  <th key={colonne} scope="col">
                    {colonne}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entree.table.rows.map((ligne) => (
                <tr key={ligne.join('|')}>
                  {ligne.map((cellule) => (
                    <td key={cellule}>{cellule}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {entree.closing !== null && <p className="rubrique-cloture">{entree.closing}</p>}
      <p className="rubrique-provenance">{provenance(entree)}</p>
    </>
  )
}

/**
 * Vrai si la rubrique vient, en tout ou partie, de l'héritage : provenance H (héritage
 * documenté) ou M (référence mythologique). Même règle pour les 13 signes.
 */
function herite(section: SheetSection): boolean {
  return (section.provenance ?? []).some((lettre) => lettre === 'H' || lettre === 'M')
}

/**
 * Titre d'une rubrique. La réserve que le PRD place à côté du titre reste sur la même ligne :
 * elle règle la lecture du texte qui suit.
 */
function titre(libelle: string, entree: SheetEntry): string {
  return entree.caveat === null ? libelle : `${libelle} — ${entree.caveat}`
}

function Rubriques({ sections }: { sections: SheetSection[] }) {
  return (
    <dl className="rubriques-complementaires">
      {sections.map((section) => (
        <div key={section.label}>
          <dt>{titre(section.label, section)}</dt>
          <dd>
            <Contenu entree={section} reserveAuTitre />
          </dd>
        </div>
      ))}
    </dl>
  )
}

function Carte({
  fiche,
  rang,
  bornes,
  statut,
  glyphesDisponibles,
}: {
  fiche: SignSheet
  rang: number
  bornes: string | null
  statut: string
  glyphesDisponibles: boolean
}) {
  const { sheet } = fiche
  return (
    <article className="carte-signe-b13" aria-labelledby="titre-fiche">
      <p className="carte-entete">
        <span>
          {String(rang).padStart(2, '0')} / 13
        </span>
        {bornes !== null && (
          <span>
            {bornes} · {statut}
          </span>
        )}
      </p>
      <p className="carte-glyphe" aria-hidden="true">
        {glyphesDisponibles ? glypheTexte(fiche.glyph) : fiche.sign_id}
      </p>
      <h2 id="titre-fiche" className="carte-titre">
        {fiche.name}
      </h2>
      {/* Sous-titre : l'opération du signe, la même rubrique pour les 13. */}
      <div className="carte-operation" role="group" aria-label="Opération">
        <Contenu entree={sheet.operation} />
      </div>
      <div className="carte-rubriques">
        {RUBRIQUES.map(([champ, libelle]) => (
          <div key={champ} className={`carte-rubrique carte-${champ}`} role="group" aria-label={libelle}>
            <h3>
              {libelle}
              {/* Une réserve est une phrase : elle ne passe pas en capitales (annexe § K). */}
              {sheet[champ].caveat !== null && (
                <span className="hors-capitales"> — {sheet[champ].caveat}</span>
              )}
            </h3>
            <Contenu entree={sheet[champ]} reserveAuTitre />
          </div>
        ))}
      </div>
      <p className="carte-pied">
        Proposition contemporaine · clé de lecture choisie, non une description des personnes.
      </p>
    </article>
  )
}

/**
 * FR-15 : les 13 fiches de signe du référentiel B13, au même gabarit (piste Carte). Les textes
 * viennent de l'API, transcrits du PRD ; l'écran n'en rédige ni n'en complète aucun.
 */
export function Fiches({ client, roue, statut, signe, onSigne, glyphesDisponibles = true }: Props) {
  const [etat, setEtat] = useState<Etat>({ etat: 'chargement' })

  useEffect(() => {
    let actif = true
    client.signs().then(
      (fiches) => actif && setEtat({ etat: 'pret', fiches }),
      (erreur: unknown) =>
        actif &&
        setEtat({
          etat: 'erreur',
          message: erreur instanceof ApiError ? erreur.message : 'Fiches indisponibles.',
        }),
    )
    return () => {
      actif = false
    }
  }, [client])

  const fiches = etat.etat === 'pret' ? etat.fiches : null
  const demande = signe ?? fiches?.signs[0]?.sign_id ?? null
  const rang = fiches ? fiches.signs.findIndex((fiche) => fiche.sign_id === demande) : -1
  const courante = fiches && rang >= 0 ? fiches.signs[rang] : null
  const secteur = roue?.signs.find((s) => s.sign_id === demande)
  const libelleStatut = { verified: 'réel vérifié', candidate: 'candidat', synthetic: 'démonstrateur synthétique' }

  return (
    <div className="ecran ecran-fiches">
      <h1 tabIndex={-1}>Les 13 fiches de signe</h1>
      <p className="chapeau">
        Chaque fiche propose une clé de lecture, sans prétendre la tirer des étoiles. Les 13 fiches
        suivent le même gabarit ; ce que le référentiel n’a pas encore écrit est dit manquant.
      </p>
      <BandeauStatut
        statut={fiches?.data_status ?? statut}
        niveaux={[
          { niveau: 'convention', objet: 'rang et bornes du signe' },
          { niveau: 'interpretation', objet: 'fiches de signe' },
        ]}
      />

      <div aria-live="polite">
        {etat.etat === 'chargement' && <p className="aide">Lecture des fiches…</p>}
      </div>
      {etat.etat === 'erreur' && (
        <div className="alerte" role="alert">
          <p className="alerte-titre">Fiches non affichées</p>
          <p>{etat.message}</p>
        </div>
      )}

      {fiches && (
        <>
          <nav className="liste-signes" aria-label="Les 13 signes">
            <ul>
              {fiches.signs.map((fiche) => (
                <li key={fiche.sign_id}>
                  <a
                    href={`#/fiches/${fiche.sign_id}`}
                    aria-current={fiche.sign_id === demande ? 'page' : undefined}
                    onClick={(evenement) => {
                      evenement.preventDefault()
                      onSigne(fiche.sign_id)
                    }}
                  >
                    <span className="glyphe" aria-hidden="true">
                      {glyphesDisponibles ? glypheTexte(fiche.glyph) : fiche.sign_id}
                    </span>{' '}
                    {fiche.name}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          {courante === null ? (
            <p className="avis">Aucune fiche pour ce signe : choisissez-en un dans la liste.</p>
          ) : (
            <>
              <Carte
                fiche={courante}
                rang={rang + 1}
                bornes={secteur ? `${degres(secteur.start_deg)} → ${degres(secteur.end_deg)}` : null}
                statut={libelleStatut[roue?.data_status ?? fiches.data_status]}
                glyphesDisponibles={glyphesDisponibles}
              />
              {courante.missing.length > 0 && (
                <p className="avis">
                  Rubriques à écrire pour ce signe :{' '}
                  {courante.missing.map((champ) => NOMS_RUBRIQUES[champ] ?? champ).join(', ')}. Le
                  référentiel ne les donne pas encore ; rien n’est écrit à leur place. Les règles
                  communes obligatoires, plus bas, valent pour les 13 signes.
                </p>
              )}

              <section className="carte" aria-labelledby="titre-complementaires">
                <h2 id="titre-complementaires">Rubriques complémentaires</h2>
                <p className="aide">
                  Propositions symboliques issues du référentiel : des clés de lecture, pas une
                  description des personnes.
                </p>
                <Rubriques sections={courante.sheet.additional_sections.filter((s) => !herite(s))} />
                {/*
                  Ce qui vient de l'héritage (H ou M) est montré à part, avec le statut que le
                  référentiel lui donne : rien n'y est actif. Le titre ne paraît que s'il a un
                  contenu, par la même règle pour tout signe.
                */}
                {courante.sheet.additional_sections.some(herite) && (
                  <>
                    <h3>Héritage historique</h3>
                    <p className="aide">{fiches.rules.historical_heritage.text}</p>
                    <Rubriques sections={courante.sheet.additional_sections.filter(herite)} />
                  </>
                )}
              </section>
            </>
          )}

          <section className="carte" aria-labelledby="titre-historiques">
            <h2 id="titre-historiques">Correspondances historiques — inactives</h2>
            <p className="aide">
              Documentées par la tradition, conservées pour mémoire : aucun calcul ni aucune lecture
              ne s’en sert, pour aucun des 13 signes.
            </p>
            <p className="aide">{fiches.rules.inherited_categories_decision.text}</p>
            <p className="aide">— : non renseigné dans le référentiel.</p>
            <div className="defilement" tabIndex={0} role="region" aria-label="Tableau des correspondances">
              <table aria-labelledby="titre-historiques">
                <thead>
                  <tr>
                    <th scope="col">Signe</th>
                    <th scope="col">Élément</th>
                    <th scope="col">Modalité</th>
                    <th scope="col">Domicile ancien</th>
                    <th scope="col">État</th>
                  </tr>
                </thead>
                <tbody>
                  {fiches.signs.map((fiche) => {
                    const historique = fiche.sheet.historical_correspondences
                    // Même règle pour toute valeur absente, quel que soit le signe : un tiret.
                    return (
                      <tr key={fiche.sign_id}>
                        <th scope="row">{fiche.name}</th>
                        {[historique.element, historique.modality, historique.domicile].map(
                          (valeur, colonne) => (
                            <td key={colonne}>
                              {valeur ?? (
                                <>
                                  <span aria-hidden="true">—</span>
                                  <span className="lecteur">non renseigné</span>
                                </>
                              )}
                            </td>
                          ),
                        )}
                        <td>inactif</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="carte" aria-labelledby="titre-regles">
            <h2 id="titre-regles">Règles communes obligatoires</h2>
            <Contenu entree={fiches.rules.common_rules} />
            <h3>Politique générale pour les 12 signes</h3>
            <Contenu entree={fiches.rules.general_policy} />
            <p className="aide">
              Référentiel <span className="valeur">{fiches.ruleset_version}</span> : textes transcrits
              du dossier de conception, sans ajout.
            </p>
          </section>
        </>
      )}
    </div>
  )
}
