import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client.ts'
import type { Api } from '../api/client.ts'
import type { Calendar, WheelData } from '../api/types.ts'
import { degres, glypheTexte, lireInstant } from '../formats.ts'
import { BandeauStatut } from '../statut/BandeauStatut.tsx'
import type { StatutAffiche } from '../statut/BandeauStatut.tsx'

type Etat =
  | { etat: 'chargement' }
  | { etat: 'pret'; calendrier: Calendar }
  | { etat: 'erreur'; message: string }

interface Props {
  client: Api
  roue: WheelData | null
  /** Statut lu avec le découpage, affiché tant que le calendrier n'est pas reçu. */
  statut: StatutAffiche
  anneeInitiale: number
  glyphesDisponibles?: boolean
}

function Instant({ iso }: { iso: string }) {
  const lu = lireInstant(iso)
  if (lu === null) return <span className="valeur">{iso}</span>
  // Deux lignes : la date, puis l'heure et son décalage. Le tableau reste étroit sur petit écran.
  return (
    <span className="valeur instant">
      <span className="instant-date">{lu.date}</span>{' '}
      <span className="instant-heure">
        {lu.heure} <span className="decalage">{lu.decalage}</span>
      </span>
    </span>
  )
}

/** FR-06 : entrées du Soleil dans les 13 signes pour une année, en UTC et en heure de Paris. */
export function Calendrier({
  client,
  roue,
  statut,
  anneeInitiale,
  glyphesDisponibles = true,
}: Props) {
  const [annee, setAnnee] = useState(anneeInitiale)
  const [champ, setChamp] = useState(String(anneeInitiale))
  const [etat, setEtat] = useState<Etat>({ etat: 'chargement' })

  useEffect(() => {
    let actif = true
    client.calendar(annee).then(
      (calendrier) => actif && setEtat({ etat: 'pret', calendrier }),
      (erreur: unknown) =>
        actif &&
        setEtat({
          etat: 'erreur',
          message: erreur instanceof ApiError ? erreur.message : 'Calendrier indisponible.',
        }),
    )
    return () => {
      actif = false
    }
  }, [client, annee])

  function afficher(evenement: FormEvent) {
    evenement.preventDefault()
    if (!/^\d{1,4}$/.test(champ.trim()) || Number(champ) < 1 || Number(champ) > 9998) {
      setEtat({
        etat: 'erreur',
        message: 'Indiquez une année en chiffres ; l’éphéméride couvre 1849 à 2150.',
      })
      return
    }
    if (Number(champ) !== annee) {
      setEtat({ etat: 'chargement' })
      setAnnee(Number(champ))
    }
  }

  const signes = new Map((roue?.signs ?? []).map((signe) => [signe.sign_id, signe]))
  const calendrier = etat.etat === 'pret' ? etat.calendrier : null
  const fuseau =
    calendrier === null || calendrier.timezone === 'Europe/Paris'
      ? 'heure de Paris'
      : `heure locale, ${calendrier.timezone}`

  return (
    <div className="ecran ecran-calendrier">
      <h1 tabIndex={-1}>Calendrier du Soleil dans les 13 signes</h1>
      <p className="chapeau">
        Les dates d’entrée changent d’une année à l’autre : elles sont calculées, jamais prises
        dans une liste fixe.
      </p>
      <BandeauStatut
        statut={calendrier?.data_status ?? statut}
        niveaux={[
          { niveau: 'mesure', objet: 'instants de passage du Soleil' },
          { niveau: 'convention', objet: 'frontières des 13 signes' },
        ]}
      />

      <form className="carte formulaire-annee" onSubmit={afficher} noValidate>
        <label>
          <span>Année</span>
          <input
            type="number"
            inputMode="numeric"
            value={champ}
            onChange={(e) => setChamp(e.target.value)}
          />
        </label>
        <button type="submit" className="secondaire">
          Afficher le calendrier
        </button>
      </form>

      <div aria-live="polite">
        {etat.etat === 'chargement' && <p className="aide">Calcul en cours…</p>}
      </div>
      {etat.etat === 'erreur' && (
        <div className="alerte" role="alert">
          <p className="alerte-titre">Calendrier non affiché</p>
          <p>{etat.message}</p>
        </div>
      )}

      {calendrier && (
        <section className="carte">
          <h2 id="titre-calendrier">Entrées du Soleil dans les 13 signes en {calendrier.year}</h2>
          <div className="defilement" tabIndex={0} role="region" aria-label="Tableau du calendrier">
            <table aria-labelledby="titre-calendrier">
              <thead>
                <tr>
                  <th scope="col">Signe</th>
                  <th scope="col">Entrée (UTC)</th>
                  <th scope="col">Entrée ({fuseau})</th>
                  <th scope="col">Frontière</th>
                </tr>
              </thead>
              <tbody>
                {calendrier.entries.map((entree) => {
                  const signe = signes.get(entree.sign_id)
                  return (
                    <tr key={entree.sign_id}>
                      <th scope="row">
                        <span className="glyphe" aria-hidden="true">
                          {signe && glyphesDisponibles ? glypheTexte(signe.glyph) : entree.sign_id}
                        </span>{' '}
                        <span>{signe?.name ?? entree.sign_id}</span>
                        {entree.conditional && <span className="etat-ligne"> conditionnel</span>}
                      </th>
                      <td>
                        <Instant iso={entree.instant_utc} />
                      </td>
                      <td>
                        <Instant iso={entree.instant_local} />
                      </td>
                      <td className="valeur">{degres(entree.boundary_deg, 4)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="mention">{calendrier.notice}</p>
          <p className="aide">
            La sortie d’un signe est l’entrée du suivant. Avant la première entrée de l’année, le
            Soleil est encore dans le signe où il est entré à la fin de l’année précédente (voir le
            calendrier de cette année-là).
          </p>
          <p className="aide">{calendrier.time_notice}</p>
          {calendrier.entries.some((entree) => entree.conditional) && (
            <p className="aide">
              Conditionnel : ces instants sont postérieurs aux tables de temps disponibles ; ils
              supposent qu’aucune seconde intercalaire ni règle d’heure légale nouvelle
              n’interviendra d’ici là.
            </p>
          )}
          {calendrier.timezone_caveat && (
            <p className="avis">
              Réserve : avant 1970, l’histoire de ce fuseau peut être confondue avec celle d’un
              fuseau voisin dans la base utilisée.
            </p>
          )}
        </section>
      )}
    </div>
  )
}
