import type { Scenario, SunSignResult, WheelData, WheelSign } from '../api/types.ts'
import { decalageUtc, degres, degresPresDesBornes, glypheTexte, lireInstant, pourcentage } from '../formats.ts'
import { RoueB13 } from '../roue/RoueB13.tsx'
import type { AstreRoue } from '../roue/RoueB13.tsx'
import { BandeauStatut } from '../statut/BandeauStatut.tsx'

interface Props {
  resultat: SunSignResult
  /** Découpage, pour nommer les signes et dessiner la roue ; `null` s'il n'a pas pu être lu. */
  roue: WheelData | null
  /** Rappel de la saisie, pour contrôle. */
  resume: string
  onOccurrence: (fold: number) => void
  occupe: boolean
  glyphesDisponibles?: boolean
}

const SOLEIL = '☉'
const RANGS = ['première', 'seconde'] as const

function majuscule(texte: string): string {
  return texte.charAt(0).toUpperCase() + texte.slice(1)
}

function instantLisible(iso: string): string {
  const lu = lireInstant(iso)
  return lu === null ? iso : `${lu.date} à ${lu.heure} ${lu.decalage}`
}

function enumerer(noms: string[]): string {
  if (noms.length <= 1) return noms.join('')
  return `${noms.slice(0, -1).join(', ')} ou ${noms[noms.length - 1]}`
}

/**
 * Écran du résultat : signe solaire B13, ou signes possibles quand l'heure chevauche une
 * frontière (FR-03), scénarios d'une heure ambiguë (FR-04), carte de référence à midi (FR-05).
 */
export function Resultat({
  resultat,
  roue,
  resume,
  onOccurrence,
  occupe,
  glyphesDisponibles = true,
}: Props) {
  const signes = new Map<string, WheelSign>((roue?.signs ?? []).map((signe) => [signe.sign_id, signe]))
  const nom = (id: string) => signes.get(id)?.name ?? id
  const bornes = (roue?.signs ?? []).map((signe) => signe.start_deg)
  const ambigu = resultat.local_time_kind === 'ambiguous' && resultat.scenarios.length > 1
  const inconnue = resultat.time_status === 'unknown'

  const astres: AstreRoue[] = resultat.scenarios.map((scenario, rang) => ({
    id: `soleil-${scenario.fold}`,
    nom: ambigu ? `Soleil, ${RANGS[rang] ?? `${rang + 1}e`} occurrence` : 'Soleil',
    glyphe: SOLEIL,
    longitude_deg: scenario.position.longitude_deg,
    valeur:
      scenario.classification.degrees_in_sign === null
        ? undefined
        : degres(scenario.classification.degrees_in_sign, 1),
    detail:
      scenario.classification.degrees_in_sign === null
        ? undefined
        : `${degres(scenario.classification.degrees_in_sign, 1)} après l’entrée dans le signe`,
  }))
  const possible = resultat.scenarios.some((scenario) => scenario.classification.status === 'possible')
  // Signes cités par le résultat, dans l'ordre du temps, sans en préférer un.
  const signesCites = [
    ...new Set(resultat.scenarios.flatMap((scenario) => scenario.classification.possible_signs)),
  ]
  // Le titre ne promet pas un signe unique quand il y en a plusieurs à départager.
  const titrePage = resultat.title
    ? majuscule(resultat.title)
    : possible
      ? 'Vos signes solaires possibles (B13)'
      : ambigu
        ? 'Signe solaire B13 : deux occurrences à départager'
        : 'Votre signe solaire B13'

  const carte = (scenario: Scenario, rang: number) => {
    const { classification, position, uncertainty } = scenario
    const certain = classification.status === 'certain' && classification.sign_id !== null
    const signe = certain ? signes.get(classification.sign_id!) : undefined
    const titre = ambigu
      ? `${majuscule(RANGS[rang] ?? `${rang + 1}e`)} occurrence`
      : certain
        ? 'Signe solaire'
        : 'Signes possibles'
    const identifiant = `scenario-${scenario.fold}`
    return (
      <section key={scenario.fold} className="carte carte-signe" aria-labelledby={identifiant}>
        <p id={identifiant} className="surtitre">
          {titre}
          {ambigu && (
            <span className="valeur hors-capitales">
              {' '}
              ({decalageUtc(scenario.utc_offset_seconds)})
            </span>
          )}
        </p>
        {certain ? (
          <h2 className="signe-nom">
            {signe && (
              <span className="glyphe" aria-hidden="true">
                {glyphesDisponibles ? glypheTexte(signe.glyph) : signe.sign_id}
              </span>
            )}{' '}
            {nom(classification.sign_id!)}
          </h2>
        ) : (
          <>
            <h2 className="signe-nom">{enumerer(classification.possible_signs.map(nom))}</h2>
            <p>
              L’incertitude sur l’heure chevauche une frontière : les signes sont présentés
              ensemble, aucun n’est avancé à la place des autres, et aucune probabilité n’est
              calculée.
            </p>
            <ul className="transitions">
              {uncertainty.transitions.map((transition) => (
                <li key={transition.instant_utc}>
                  Le Soleil franchit la frontière entre {nom(transition.from_sign)} et{' '}
                  {nom(transition.to_sign)} le{' '}
                  <span className="valeur">{instantLisible(transition.instant_utc)}</span>{' '}
                  (longitude <span className="valeur">{degres(transition.boundary_deg, 4)}</span>
                  ).
                </li>
              ))}
            </ul>
          </>
        )}
        <dl className="mesures">
          <div>
            <dt>Longitude écliptique du Soleil (repère B, J2000)</dt>
            <dd className="valeur">{degresPresDesBornes(position.longitude_deg, bornes)}</dd>
          </div>
          {certain && classification.degrees_in_sign !== null && signe && (
            <div>
              <dt>Position dans le signe</dt>
              <dd>
                <span className="valeur">{degres(classification.degrees_in_sign)}</span> après
                l’entrée, sur <span className="valeur">{degres(signe.width_deg)}</span> de largeur
                {classification.fraction_in_sign !== null && (
                  <>
                    {' '}
                    — {pourcentage(classification.fraction_in_sign)} de la largeur : position
                    géométrique, pas une intensité.
                  </>
                )}
              </dd>
            </div>
          )}
          <div>
            <dt>{inconnue ? 'Instant de référence (midi, heure locale)' : 'Instant retenu'}</dt>
            <dd>
              <span className="valeur">{instantLisible(scenario.instant_utc)}</span> — décalage du
              fuseau utilisé : <span className="valeur">{decalageUtc(scenario.utc_offset_seconds)}</span>
            </dd>
          </div>
          {uncertainty.time_interval_utc && (
            <div>
              <dt>{inconnue ? 'Journée locale étudiée' : 'Intervalle étudié'}</dt>
              <dd className="valeur">
                {instantLisible(uncertainty.time_interval_utc[0])} →{' '}
                {instantLisible(uncertainty.time_interval_utc[1])}
              </dd>
            </div>
          )}
        </dl>
        {scenario.conditional && (
          <p className="avis">
            Résultat conditionnel : cet instant est postérieur aux tables de temps disponibles ; il
            suppose qu’aucune seconde intercalaire ni règle d’heure légale nouvelle
            n’interviendra d’ici là.
          </p>
        )}
        {scenario.time_scale !== 'utc' && (
          <p className="aide">Avant 1972, l’heure civile est lue comme du temps universel (UT1).</p>
        )}
        {ambigu && (
          <button
            type="button"
            className="secondaire"
            disabled={occupe}
            onClick={() => onOccurrence(scenario.fold)}
          >
            Garder la {RANGS[rang] ?? `${rang + 1}e`} occurrence (
            {decalageUtc(scenario.utc_offset_seconds)})
          </button>
        )}
      </section>
    )
  }

  return (
    <div className="ecran ecran-resultat">
      <h1 tabIndex={-1}>{titrePage}</h1>
      <p className="chapeau">Saisie : {resume}</p>
      <BandeauStatut
        statut={resultat.data_status}
        niveaux={[
          { niveau: 'mesure', objet: 'longitude du Soleil' },
          { niveau: 'convention', objet: 'classement dans l’un des 13 signes' },
        ]}
      />

      {inconnue && (
        <p className="avis">
          Heure inconnue : le Soleil est placé à midi, heure locale, et le signe est cherché sur
          toute la journée de naissance.
        </p>
      )}
      {ambigu && (
        <p className="avis">
          Cette heure a existé deux fois ce jour-là (recul des horloges). Les deux scénarios sont
          montrés tant que vous n’avez pas précisé l’occurrence.
        </p>
      )}
      {resultat.timezone_caveat && (
        <p className="avis">
          Réserve : avant 1970, l’histoire de ce fuseau peut être confondue avec celle d’un fuseau
          voisin dans la base utilisée. Contrôlez le décalage affiché.
        </p>
      )}

      <div className="grille-resultat">
        <div className="cartes-signes">{resultat.scenarios.map(carte)}</div>
        <section className="carte" aria-label="Roue">
          {roue ? (
            <>
              <RoueB13 donnees={roue} astres={astres} glyphesDisponibles={glyphesDisponibles} />
              <p className="aide">
                {ambigu
                  ? 'Les repères montrent le Soleil aux deux instants possibles'
                  : `Le repère montre le Soleil à l’instant retenu${
                      inconnue ? ' (midi, heure locale)' : ''
                    }`}
                .
                {possible &&
                  ' Pendant l’intervalle étudié, il franchit la frontière indiquée : le repère ne désigne donc pas un signe plutôt que l’autre.'}
              </p>
              <p className="aide">
                Le nom complet de chaque signe de la roue est dans le{' '}
                <a href="#/roue">tableau des 13 signes</a>.
              </p>
            </>
          ) : (
            <p className="avis">La roue n’est pas affichée : le découpage n’a pas pu être lu.</p>
          )}
        </section>
      </div>

      <section className="carte" aria-label="Ce qui n’est pas calculé">
        {inconnue ? (
          <>
            <p>
              Ascendant : absent — heure de naissance inconnue (et non calculé dans cette version).
            </p>
            <p>
              Maisons : absentes — heure de naissance inconnue (et non calculées dans cette
              version).
            </p>
          </>
        ) : (
          <p>Ascendant et maisons : non calculés dans cette version.</p>
        )}
        <p>
          Ce résultat est un calcul : il ne contient aucun texte interprétatif. La lecture proposée
          pour un signe est dans sa fiche, à lire comme une proposition symbolique :{' '}
          {signesCites.map((id, rang) => (
            <span key={id}>
              {rang > 0 && ', '}
              <a href={`#/fiches/${id}`}>fiche {nom(id)}</a>
            </span>
          ))}
          .
        </p>
      </section>

      <details className="carte manifeste">
        <summary>Manifeste du calcul</summary>
        <p className="aide">Ce qu’il faut pour régénérer ce résultat à l’identique.</p>
        <pre>{JSON.stringify(resultat.manifest, null, 2)}</pre>
      </details>

      <p>
        <a href="#/">Modifier la saisie</a>
      </p>
    </div>
  )
}
