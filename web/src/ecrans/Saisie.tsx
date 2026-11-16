import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client.ts'
import type { Api } from '../api/client.ts'
import type { BirthRequest, Place, SunSignResult } from '../api/types.ts'
import { MOIS } from '../formats.ts'
import { BandeauStatut } from '../statut/BandeauStatut.tsx'
import type { StatutAffiche } from '../statut/BandeauStatut.tsx'
import { FORMULAIRE_VIDE, PRECISIONS, construire, decimal } from './formulaire.ts'
import type { Formulaire } from './formulaire.ts'

const CHAINE = [
  ['Date + heure + fuseau', 'Saisie locale validée dans le fuseau historique'],
  ['Instant UTC → TT', 'Un instant, ou plusieurs si l’heure est ambiguë ou incertaine'],
  ['Direction géocentrique', 'Position astrométrique, centre de la Terre'],
  ['Écliptique moyen J2000', 'Repère fixe, aucun déplacement annuel'],
  ['Extraction de λ', 'Longitude seule, latitude ignorée'],
  ['Recherche de l’intervalle', '13 intervalles inégaux, début inclus, fin exclue'],
] as const

const CONVENTIONS = [
  ['Frontières', 'UAI, réalisation Skyfield / Roman 1987 (VI/42)'],
  ['Écliptique', 'Repère moyen fixe J2000'],
  ['Observateur', 'Géocentrique'],
  ['Positions', 'Astrométriques (temps de parcours de la lumière)'],
  ['Classement', 'Longitude seule'],
  ['Bornes', 'Début inclus, fin exclue'],
] as const

type Recherche =
  | { etat: 'repos' }
  | { etat: 'en-cours' }
  | { etat: 'trouve'; lieux: Place[] }
  | { etat: 'erreur'; message: string }

interface Props {
  client: Api
  statut: StatutAffiche
  initial?: Formulaire
  onResultat: (formulaire: Formulaire, saisie: BirthRequest, resultat: SunSignResult) => void
}

/**
 * Écran de saisie (planche 6, thème clair de la planche 7). FR-01 : une heure inexistante
 * donne un message bloquant, sans résultat. Le moteur reste seul juge des valeurs.
 */
export function Saisie({ client, statut, initial = FORMULAIRE_VIDE, onResultat }: Props) {
  const [f, setF] = useState<Formulaire>(initial)
  const [recherche, setRecherche] = useState<Recherche>({ etat: 'repos' })
  // « repos », « en-cours », « absent », « inconnu », ou le message d'une erreur à afficher.
  const [fuseau, setFuseau] = useState<string>('repos')
  const [blocage, setBlocage] = useState<{ titre: string; lignes: string[] } | null>(null)
  const [occupe, setOccupe] = useState(false)
  const alerte = useRef<HTMLDivElement>(null)

  const changer = (partiel: Partial<Formulaire>) => setF((avant) => ({ ...avant, ...partiel }))
  const bloquer = (titre: string, lignes: string[]) => {
    setBlocage({ titre, lignes })
    requestAnimationFrame(() => alerte.current?.focus())
  }

  async function chercher() {
    if (f.recherche.trim().length < 2) {
      setRecherche({ etat: 'erreur', message: 'Indiquez au moins deux lettres.' })
      return
    }
    setRecherche({ etat: 'en-cours' })
    try {
      const reponse = await client.searchPlaces(f.recherche)
      setRecherche({ etat: 'trouve', lieux: reponse.places })
    } catch (erreur) {
      const message = erreur instanceof ApiError ? erreur.message : 'Recherche impossible.'
      setRecherche({ etat: 'erreur', message })
    }
  }

  /** Choisir une ville remplit ses coordonnées et son fuseau, tels que GeoNames les donne. */
  function choisirVille(lieu: Place) {
    setFuseau('repos')
    changer({
      lieu,
      latitude: String(lieu.latitude_deg),
      longitude: String(lieu.longitude_deg),
      fuseauDeduit: null,
      fuseauConfirme: false,
    })
  }

  /** Retoucher une coordonnée : la ville n'est plus la source, le fuseau est à redéduire. */
  function saisirCoordonnee(champ: 'latitude' | 'longitude', valeur: string) {
    setFuseau('repos')
    changer({ [champ]: valeur, lieu: null, fuseauDeduit: null, fuseauConfirme: false })
  }

  async function deduireFuseau() {
    const latitude = decimal(f.latitude)
    const longitude = decimal(f.longitude)
    changer({ fuseauDeduit: null, fuseauConfirme: false })
    if (latitude === null || longitude === null) {
      setFuseau('Indiquez la latitude et la longitude en degrés décimaux.')
      return
    }
    setFuseau('en-cours')
    try {
      const reponse = await client.timezoneAt(latitude, longitude)
      if (reponse.timezone === null) {
        setFuseau(reponse.status === 'unknown_to_timezone_database' ? 'inconnu' : 'absent')
      } else {
        setFuseau('repos')
        changer({ fuseauDeduit: reponse.timezone, fuseauConfirme: false })
      }
    } catch (erreur) {
      setFuseau(erreur instanceof ApiError ? erreur.message : 'Fuseau indisponible.')
    }
  }

  async function envoyer(evenement: FormEvent) {
    evenement.preventDefault()
    const construit = construire(f)
    if ('manques' in construit) {
      bloquer('Il manque :', construit.manques)
      return
    }
    setBlocage(null)
    setOccupe(true)
    try {
      const resultat = await client.sunSign(construit.saisie)
      onResultat(f, construit.saisie, resultat)
    } catch (erreur) {
      const message =
        erreur instanceof ApiError ? erreur.message : 'Erreur interne : aucun résultat n’est affiché.'
      bloquer('Calcul impossible', [message])
    } finally {
      setOccupe(false)
    }
  }

  const saisies = f.latitude.trim() !== '' || f.longitude.trim() !== ''
  const origine = f.lieu
    ? `GeoNames, ${f.lieu.name}${f.lieu.admin1_name ? `, ${f.lieu.admin1_name}` : ''} (${f.lieu.country_code})`
    : saisies
      ? 'saisies à la main'
      : 'choisissez une ville, ou saisissez-les'

  return (
    <div className="ecran ecran-saisie">
      <div className="colonne-principale">
        <p className="etiquette-modele">Modèle B · 13 signes · J2000</p>
        <h1 tabIndex={-1}>Entrez vos informations de naissance</h1>
        <p className="chapeau">
          Le calcul classe le Soleil selon sa seule longitude, dans 13 intervalles inégaux issus
          des frontières des constellations.
        </p>
        <BandeauStatut
          statut={statut}
          niveaux={[
            { niveau: 'mesure', objet: 'position du Soleil' },
            { niveau: 'convention', objet: 'découpage en 13 signes' },
          ]}
        />

        <form className="carte" onSubmit={envoyer} noValidate>
          <fieldset>
            <legend>Date de naissance</legend>
            <div className="rangee rangee-3">
              <label>
                <span>Année</span>
                <input
                  type="number"
                  inputMode="numeric"
                  autoComplete="off"
                  value={f.annee}
                  onChange={(e) => changer({ annee: e.target.value })}
                />
              </label>
              <label>
                <span>Mois</span>
                <select value={f.mois} onChange={(e) => changer({ mois: e.target.value })}>
                  <option value="">Choisir</option>
                  {MOIS.map((nom, rang) => (
                    <option key={nom} value={String(rang + 1)}>
                      {nom}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Jour</span>
                <input
                  type="number"
                  inputMode="numeric"
                  autoComplete="off"
                  value={f.jour}
                  onChange={(e) => changer({ jour: e.target.value })}
                />
              </label>
            </div>
            <p className="aide">Calendrier grégorien proleptique.</p>
          </fieldset>

          <fieldset>
            <legend>Heure de naissance (heure légale, 24 h)</legend>
            <label className="case">
              <input
                type="checkbox"
                checked={f.heureInconnue}
                onChange={(e) => changer({ heureInconnue: e.target.checked })}
              />
              <span>Heure inconnue</span>
            </label>
            <div className="rangee rangee-2">
              <label>
                <span>Heure (0-23)</span>
                <input
                  type="number"
                  inputMode="numeric"
                  autoComplete="off"
                  disabled={f.heureInconnue}
                  value={f.heure}
                  onChange={(e) => changer({ heure: e.target.value })}
                />
              </label>
              <label>
                <span>Minute (0-59)</span>
                <input
                  type="number"
                  inputMode="numeric"
                  autoComplete="off"
                  disabled={f.heureInconnue}
                  value={f.minute}
                  onChange={(e) => changer({ minute: e.target.value })}
                />
              </label>
            </div>
            <div className="precision" role="radiogroup" aria-label="Précision de l’heure">
              <span className="precision-titre" aria-hidden="true">
                Précision de l’heure
              </span>
              {PRECISIONS.map(({ secondes, libelle }) => (
                <label key={secondes} className="pastille">
                  <input
                    type="radio"
                    name="precision"
                    disabled={f.heureInconnue}
                    checked={f.precision === secondes}
                    onChange={() => changer({ precision: secondes })}
                  />
                  <span>{libelle}</span>
                </label>
              ))}
            </div>
            <p className="aide">
              Heure ambiguë au changement d’heure : deux scénarios. Heure inexistante : erreur,
              aucune correction silencieuse. Heure inconnue : carte de référence à midi.
            </p>
          </fieldset>

          <fieldset>
            <legend>Lieu de naissance</legend>
            <div className="rangee rangee-recherche">
              <label>
                <span>Ville de naissance</span>
                <input
                  type="text"
                  autoComplete="off"
                  value={f.recherche}
                  onChange={(e) => changer({ recherche: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      void chercher()
                    }
                  }}
                />
              </label>
              <button type="button" className="secondaire" onClick={() => void chercher()}>
                Chercher ce lieu
              </button>
            </div>

            <div aria-live="polite">
              {recherche.etat === 'en-cours' && <p className="aide">Recherche en cours…</p>}
              {recherche.etat === 'erreur' && <p className="avis">{recherche.message}</p>}
              {recherche.etat === 'trouve' && recherche.lieux.length === 0 && (
                <p className="avis">
                  Aucune localité de plus de 15 000 habitants ne correspond. Saisissez la latitude
                  et la longitude ci-dessous : aucun lieu voisin n’est proposé à la place.
                </p>
              )}
            </div>
            {recherche.etat === 'trouve' && recherche.lieux.length > 0 && (
              <ul className="lieux">
                {recherche.lieux.map((lieu) => (
                  <li key={lieu.geoname_id}>
                    <button
                      type="button"
                      className="secondaire"
                      aria-pressed={f.lieu?.geoname_id === lieu.geoname_id}
                      onClick={() => choisirVille(lieu)}
                    >
                      {lieu.name}
                      {lieu.admin1_name ? `, ${lieu.admin1_name}` : ''} ({lieu.country_code}) ·{' '}
                      {lieu.timezone}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {/*
              Coordonnées : toujours visibles. Remplies par la ville choisie, ou saisies à la main
              pour un lieu absent de la liste ; dans ce cas, le fuseau est déduit et confirmé.
            */}
            <div className="rangee rangee-2">
              <label>
                <span>Latitude (degrés décimaux)</span>
                <input
                  type="text"
                  inputMode="decimal"
                  autoComplete="off"
                  value={f.latitude}
                  onChange={(e) => saisirCoordonnee('latitude', e.target.value)}
                />
              </label>
              <label>
                <span>Longitude (degrés décimaux)</span>
                <input
                  type="text"
                  inputMode="decimal"
                  autoComplete="off"
                  value={f.longitude}
                  onChange={(e) => saisirCoordonnee('longitude', e.target.value)}
                />
              </label>
            </div>
            <p className="aide">
              Remplies par la ville choisie. Pour un lieu absent de la liste, saisissez-les (nord et
              est positifs ; sud et ouest négatifs), puis déduisez le fuseau.
            </p>
            {f.lieu === null && saisies && (
              <>
                <div className="rangee-boutons">
                  <button type="button" className="secondaire" onClick={() => void deduireFuseau()}>
                    Déduire le fuseau
                  </button>
                </div>
                <div aria-live="polite">
                  {fuseau === 'en-cours' && <p className="aide">Recherche du fuseau…</p>}
                  {fuseau === 'absent' && (
                    <p className="avis">
                      Aucun fuseau civil à ces coordonnées (pleine mer, par exemple). Vérifiez-les :
                      aucun fuseau n’est supposé.
                    </p>
                  )}
                  {fuseau === 'inconnu' && (
                    <p className="avis">
                      Le fuseau de ces coordonnées n’est pas connu de la base des fuseaux utilisée :
                      aucun fuseau n’est supposé à sa place. Le calcul ne peut pas se faire avec ces
                      coordonnées dans cette version.
                    </p>
                  )}
                  {!['repos', 'en-cours', 'absent', 'inconnu'].includes(fuseau) && (
                    <p className="avis">{fuseau}</p>
                  )}
                </div>
                {f.fuseauDeduit !== null && (
                  <label className="case">
                    <input
                      type="checkbox"
                      checked={f.fuseauConfirme}
                      onChange={(e) => changer({ fuseauConfirme: e.target.checked })}
                    />
                    <span>Je confirme le fuseau {f.fuseauDeduit}</span>
                  </label>
                )}
              </>
            )}

            <div className="encart">
              <p>
                Fuseau historique :{' '}
                <span className="valeur">
                  {(f.lieu ? f.lieu.timezone : f.fuseauDeduit) ?? 'déduit du lieu'}
                </span>
              </p>
              <p>
                Coordonnées :{' '}
                <span className="valeur">{origine}</span>
              </p>
              <p className="aide">
                Le lieu sert à trouver le fuseau, donc l’instant. Pour un même instant, la position
                du Soleil est la même partout : elle est géocentrique. L’Ascendant et les maisons,
                qui dépendent du lieu, ne sont pas calculés dans cette version.
              </p>
            </div>
            <p className="attribution">Lieux : GeoNames (geonames.org), licence CC BY 4.0</p>
          </fieldset>

          {blocage && (
            <div className="alerte" role="alert" tabIndex={-1} ref={alerte}>
              <p className="alerte-titre">{blocage.titre}</p>
              {blocage.lignes.length === 1 ? (
                <p>{blocage.lignes[0]}</p>
              ) : (
                <ul>
                  {blocage.lignes.map((ligne) => (
                    <li key={ligne}>{ligne}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <button type="submit" className="principal" disabled={occupe}>
            Calculer mon signe solaire B13
          </button>
          <p className="pied-carte">
            Le calcul classe des positions. Sa précision ne valide aucune interprétation.
          </p>
        </form>
      </div>

      <div className="colonne-laterale">
        <section className="carte" aria-labelledby="titre-chaine">
          <h2 id="titre-chaine" className="surtitre">
            Chaîne de calcul
          </h2>
          <ol className="chaine">
            {CHAINE.map(([titre, detail]) => (
              <li key={titre}>
                <strong>{titre}</strong>
                <span>{detail}</span>
              </li>
            ))}
          </ol>
        </section>
        <section className="carte" aria-labelledby="titre-conventions">
          <h2 id="titre-conventions" className="surtitre">
            Conventions
          </h2>
          <dl className="conventions">
            {CONVENTIONS.map(([terme, valeur]) => (
              <div key={terme}>
                <dt>{terme}</dt>
                <dd>{valeur}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  )
}
