import { useEffect, useRef, useState } from 'react'
import { ApiError, api } from './api/client.ts'
import type { Api } from './api/client.ts'
import type { BirthRequest, SunSignResult, WheelData } from './api/types.ts'
import { Calendrier } from './ecrans/Calendrier.tsx'
import { PageRoue } from './ecrans/PageRoue.tsx'
import { Resultat } from './ecrans/Resultat.tsx'
import { Saisie } from './ecrans/Saisie.tsx'
import { FORMULAIRE_VIDE, resumer } from './ecrans/formulaire.ts'
import type { Formulaire } from './ecrans/formulaire.ts'
import { useGlyphesDisponibles } from './glyphes.ts'
import { BandeauStatut } from './statut/BandeauStatut.tsx'
import type { StatutAffiche } from './statut/BandeauStatut.tsx'

type Route = 'saisie' | 'resultat' | 'calendrier' | 'roue'

const ROUTES: Record<string, Route> = {
  '': 'saisie',
  '#/': 'saisie',
  '#/resultat': 'resultat',
  '#/calendrier': 'calendrier',
  '#/roue': 'roue',
}

const NAVIGATION: { route: Route; hash: string; libelle: string }[] = [
  { route: 'saisie', hash: '#/', libelle: 'Mon signe' },
  { route: 'calendrier', hash: '#/calendrier', libelle: 'Calendrier' },
  { route: 'roue', hash: '#/roue', libelle: 'Roue' },
]

/** Année proposée à l'ouverture du calendrier : celle de l'horloge du navigateur. */
const ANNEE_COURANTE = new Date().getFullYear()

function viserLeTitre() {
  document.querySelector<HTMLElement>('main h1')?.focus({ preventScroll: true })
}

function routeCourante(): Route {
  return ROUTES[window.location.hash] ?? 'saisie'
}

/** Session en mémoire : rien n'est écrit dans l'adresse ni dans le stockage du navigateur. */
interface Session {
  formulaire: Formulaire
  saisie: BirthRequest
  resultat: SunSignResult
}

/**
 * Coquille de l'application : navigation, thème, et le découpage lu une fois dans l'API, qui
 * alimente toutes les vues. Chaque vue affiche le statut de ce qu'elle montre (FR-18).
 */
export default function App({ client = api }: { client?: Api }) {
  const [route, setRoute] = useState<Route>(routeCourante)
  const [sombre, setSombre] = useState(false)
  const [roue, setRoue] = useState<WheelData | null>(null)
  const [statut, setStatut] = useState<StatutAffiche>('chargement')
  const [session, setSession] = useState<Session | null>(null)
  const [occupe, setOccupe] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const glyphes = useGlyphesDisponibles()

  useEffect(() => {
    const suivre = () => setRoute(routeCourante())
    window.addEventListener('hashchange', suivre)
    return () => window.removeEventListener('hashchange', suivre)
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = sombre ? 'sombre' : 'clair'
  }, [sombre])

  useEffect(() => {
    let actif = true
    client.boundaries().then(
      (donnees) => {
        if (!actif) return
        setRoue(donnees)
        setStatut(donnees.data_status)
      },
      () => actif && setStatut('indisponible'),
    )
    return () => {
      actif = false
    }
  }, [client])

  // À chaque changement de vue, on revient en haut et le titre reçoit le focus : les lecteurs
  // d'écran l'annoncent. Pas au premier affichage : le focus reste en haut du document.
  const premierAffichage = useRef(true)
  useEffect(() => {
    if (premierAffichage.current) {
      premierAffichage.current = false
      return
    }
    window.scrollTo?.(0, 0)
    viserLeTitre()
  }, [route])

  function aller(hash: string) {
    window.location.hash = hash
    setRoute(ROUTES[hash] ?? 'saisie')
  }

  async function choisirOccurrence(fold: number) {
    if (session === null) return
    setOccupe(true)
    setErreur(null)
    const saisie = { ...session.saisie, fold }
    try {
      const resultat = await client.sunSign(saisie)
      setSession({ ...session, saisie, resultat })
      // Le bouton qui vient de servir disparaît avec le second scénario : le focus revient au
      // titre plutôt que de se perdre.
      requestAnimationFrame(viserLeTitre)
    } catch (cause) {
      setErreur(
        cause instanceof ApiError ? cause.message : 'Erreur interne : aucun résultat n’est affiché.',
      )
    } finally {
      setOccupe(false)
    }
  }

  let vue
  if (route === 'calendrier') {
    vue = (
      <Calendrier
        client={client}
        roue={roue}
        statut={statut}
        anneeInitiale={ANNEE_COURANTE}
        glyphesDisponibles={glyphes}
      />
    )
  } else if (route === 'roue') {
    vue = <PageRoue roue={roue} statut={statut} glyphesDisponibles={glyphes} />
  } else if (route === 'resultat' && session !== null) {
    vue = (
      <>
        {erreur && (
          <div className="alerte" role="alert">
            <p className="alerte-titre">Calcul impossible</p>
            <p>{erreur}</p>
          </div>
        )}
        <Resultat
          resultat={session.resultat}
          roue={roue}
          resume={resumer(session.formulaire, session.saisie)}
          onOccurrence={(fold) => void choisirOccurrence(fold)}
          occupe={occupe}
          glyphesDisponibles={glyphes}
        />
      </>
    )
  } else if (route === 'resultat') {
    vue = (
      <div className="ecran">
        <h1 tabIndex={-1}>Aucun résultat à afficher</h1>
        <BandeauStatut statut={statut} niveaux={[]} />
        <p>
          Aucune saisie n’est conservée : rien n’est enregistré, ni ici ni sur le serveur.{' '}
          <a href="#/">Saisir une naissance</a>
        </p>
      </div>
    )
  } else {
    vue = (
      <Saisie
        client={client}
        statut={statut}
        initial={session?.formulaire ?? FORMULAIRE_VIDE}
        onResultat={(formulaire, saisie, resultat) => {
          setSession({ formulaire, saisie, resultat })
          setErreur(null)
          aller('#/resultat')
        }}
      />
    )
  }

  const courante: Route = route === 'resultat' ? 'saisie' : route
  return (
    <>
      <a
        className="evitement"
        href="#contenu"
        onClick={(evenement) => {
          // L'adresse sert de route (#/…) : ce lien ne la change pas, il déplace le focus.
          evenement.preventDefault()
          document.getElementById('contenu')?.focus()
        }}
      >
        Aller au contenu
      </a>
      <header className="entete">
        <p className="marque">Zodiaque B13</p>
        <nav aria-label="Vues">
          <ul>
            {NAVIGATION.map(({ route: cible, hash, libelle }) => (
              <li key={hash}>
                <a
                  href={hash}
                  aria-current={courante === cible ? 'page' : undefined}
                  onClick={(evenement) => {
                    evenement.preventDefault()
                    aller(hash)
                  }}
                >
                  {libelle}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <button
          type="button"
          className="secondaire bascule-theme"
          aria-pressed={sombre}
          onClick={() => setSombre((avant) => !avant)}
        >
          Mode sombre
        </button>
      </header>
      <main id="contenu" tabIndex={-1}>
        {vue}
      </main>
      <footer className="pied">
        <p>
          Calcul astronomique et conventions déclarées : le calcul classe des positions, il ne
          décrit pas une personne. Aucune donnée de naissance n’est conservée.
        </p>
      </footer>
    </>
  )
}
