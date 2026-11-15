import { useId } from 'react'
import type { KeyboardEvent } from 'react'
import type { WheelData, WheelSign } from '../api/types.ts'
import { degres, glypheTexte } from '../formats.ts'
import { ANNEAUX, CADRE, CENTRE, R, coordonnees, placerEtiquettes, point, secteur } from './geometrie.ts'
import type { Point } from './geometrie.ts'
import './roue.css'

/** Astre à placer sur la roue. Sa longitude vient de l'API ; elle n'est jamais modifiée ici. */
export interface AstreRoue {
  id: string
  nom: string
  glyphe: string
  longitude_deg: number
  /** Valeur courte à écrire sous le glyphe (degrés après l'entrée dans le signe). */
  valeur?: string
  /** Précision ajoutée au nom accessible (« 12,3° après l'entrée dans le signe »). */
  detail?: string
}

interface Props {
  donnees: WheelData
  astres?: AstreRoue[]
  selection?: string | null
  /** Sans cette fonction, les secteurs sont des images nommées, pas des boutons. */
  onSelection?: (signId: string | null) => void
  /** Faux si la police des glyphes n'a pas pu être chargée : repli sur les identifiants. */
  glyphesDisponibles?: boolean
}

/** Écart minimal entre deux étiquettes d'astres, en degrés, au rayon des étiquettes. */
const ECART_ETIQUETTES = 9

/**
 * Glyphe et code d'un signe, côte à côte le long de l'anneau, texte droit. Tailles en unités du
 * dessin : elles donnent, sur une roue de 700 px, un glyphe d'environ 29 px (annexe § H : 24 à
 * 30 px). Un secteur trop étroit pour les deux ne garde que son glyphe : il n'est jamais élargi.
 */
const LARGEUR_GLYPHE = 36
const LARGEUR_CODE = 30
const ESPACE = 8
const ARC_MIN_GLYPHE_ET_CODE = LARGEUR_GLYPHE + LARGEUR_CODE + 2 * ESPACE + 2
const MILIEU_ANNEAU = (ANNEAUX.signesInterieur + ANNEAUX.signesExterieur) / 2

const GRADUATIONS = Array.from({ length: 360 }, (_, degre) => degre)
/**
 * Longitudes chiffrées sous la graduation, sur l'échelle continue. Le pas de 45° évite qu'on y
 * lise une grille de douze secteurs de 30°.
 */
const PAS_CHIFFRES = 45
const CHIFFRES = GRADUATIONS.filter((degre) => degre % PAS_CHIFFRES === 0)

interface PlacesDuNom {
  glyphe: Point
  code: Point | null
  seul: Point
}

/**
 * Où écrire le glyphe et le code d'un signe : autour du milieu du secteur, le glyphe du côté
 * par lequel on commence à lire (à gauche, ou au-dessus sur les flancs). Même règle pour les 13.
 */
function placerNom(signe: WheelSign): PlacesDuNom {
  const milieu = signe.start_deg + signe.width_deg / 2
  const seul = point(milieu, MILIEU_ANNEAU)
  const arc = (signe.width_deg * Math.PI * R * MILIEU_ANNEAU) / 180
  if (arc < ARC_MIN_GLYPHE_ET_CODE) return { glyphe: seul, code: null, seul }
  const entreCentres = LARGEUR_GLYPHE / 2 + ESPACE + LARGEUR_CODE / 2
  const total = LARGEUR_GLYPHE + ESPACE + LARGEUR_CODE
  const enDegres = (unites: number) => (unites * 180) / (Math.PI * R * MILIEU_ANNEAU)
  // Le couple est centré sur le milieu du secteur ; ses deux centres sont de part et d'autre.
  const versGlyphe = enDegres(total / 2 - LARGEUR_GLYPHE / 2)
  const versCode = enDegres(entreCentres) - versGlyphe
  const avant = { glyphe: point(milieu - versGlyphe, MILIEU_ANNEAU), code: point(milieu + versCode, MILIEU_ANNEAU) }
  const apres = { glyphe: point(milieu + versGlyphe, MILIEU_ANNEAU), code: point(milieu - versCode, MILIEU_ANNEAU) }
  const horizontal = Math.abs(avant.glyphe.x - avant.code.x) >= Math.abs(avant.glyphe.y - avant.code.y)
  const glypheDabord = horizontal ? avant.glyphe.x < avant.code.x : avant.glyphe.y < avant.code.y
  return { ...(glypheDabord ? avant : apres), seul }
}

/**
 * Roue du modèle B : 13 secteurs proportionnels aux largeurs reçues (FR-10).
 * Construite à partir des données, jamais une illustration : une étiquette peut bouger, une
 * frontière ou une position jamais. Les 13 signes passent par le même tracé.
 */
export function RoueB13({
  donnees,
  astres = [],
  selection = null,
  onSelection,
  glyphesDisponibles = true,
}: Props) {
  const titre = useId()
  const { signesInterieur, signesExterieur, graduationInterieur, repereExact } = ANNEAUX
  const places = placerEtiquettes(
    astres.map((astre) => astre.longitude_deg),
    ECART_ETIQUETTES,
  )

  const basculer = (signId: string) => onSelection?.(selection === signId ? null : signId)
  const auClavier = (evenement: KeyboardEvent<SVGGElement>, signId: string) => {
    if (evenement.key === 'Enter' || evenement.key === ' ') {
      evenement.preventDefault()
      basculer(signId)
    }
  }

  return (
    <figure className="roue">
      <svg
        viewBox={`${CADRE.origine} ${CADRE.origine} ${CADRE.taille} ${CADRE.taille}`}
        role="group"
        aria-labelledby={titre}
      >
        <title id={titre}>
          Roue du modèle B : 13 secteurs, chacun de la largeur calculée de son signe
        </title>

        <circle className="guide" cx={CENTRE} cy={CENTRE} r={repereExact * R} />

        <g className="graduation" aria-hidden="true">
          {GRADUATIONS.map((degre) => {
            const longueur = degre % 10 === 0 ? 1 : degre % 5 === 0 ? 0.6 : 0.35
            const debut = signesInterieur - longueur * (signesInterieur - graduationInterieur)
            const a = point(degre, debut)
            const b = point(degre, signesInterieur)
            return (
              <line
                key={degre}
                className={degre % 5 === 0 ? 'repere' : 'repere fin'}
                x1={a.x.toFixed(3)}
                y1={a.y.toFixed(3)}
                x2={b.x.toFixed(3)}
                y2={b.y.toFixed(3)}
              />
            )
          })}
          {CHIFFRES.map((degre) => {
            const place = point(degre, ANNEAUX.chiffres)
            return (
              <text key={degre} className="chiffre" x={place.x.toFixed(3)} y={place.y.toFixed(3)}>
                {degre}°
              </text>
            )
          })}
        </g>

        {donnees.signs.map((signe) => {
          const nom = `${signe.name} : de ${degres(signe.start_deg)} à ${degres(
            signe.end_deg,
          )}, largeur ${degres(signe.width_deg)}`
          // Avec une sélection à offrir, le secteur est un bouton ; sinon une image nommée, hors
          // de l'ordre de tabulation : un bouton qui ne fait rien serait un leurre.
          const role = onSelection
            ? {
                role: 'button',
                tabIndex: 0,
                'aria-pressed': selection === signe.sign_id,
                onClick: () => basculer(signe.sign_id),
                onKeyDown: (evenement: KeyboardEvent<SVGGElement>) =>
                  auClavier(evenement, signe.sign_id),
              }
            : { role: 'img' }
          return (
            <g
              key={signe.sign_id}
              className="signe"
              data-sign-id={signe.sign_id}
              aria-label={nom}
              {...role}
            >
              <title className="nom-complet">{signe.name}</title>
              <path
                className="secteur"
                d={secteur(signe.start_deg, signe.width_deg, signesInterieur, signesExterieur)}
                style={{ fill: `var(--secteur-${signe.sign_id.toLowerCase()})` }}
              />
              <path
                className="focus"
                d={secteur(signe.start_deg, signe.width_deg, signesInterieur, signesExterieur)}
              />
            </g>
          )
        })}

        {/*
          Glyphes et codes : un calque à part, hors des boutons. Le nom accessible d'un secteur
          est son nom complet et ses bornes ; ce calque n'est qu'un repère visuel.
        */}
        <g className="noms" aria-hidden="true">
          {donnees.signs.map((signe) => {
            const place = placerNom(signe)
            const glyphe = glyphesDisponibles ? glypheTexte(signe.glyph) : signe.sign_id
            return (
              <g
                key={signe.sign_id}
                className="nom"
                data-nom-de={signe.sign_id}
                data-choisi={selection === signe.sign_id}
              >
                <text className="glyphe" x={place.glyphe.x.toFixed(3)} y={place.glyphe.y.toFixed(3)}>
                  {glyphe}
                </text>
                <text
                  className="abreviation"
                  x={(place.code ?? place.seul).x.toFixed(3)}
                  y={(place.code ?? place.seul).y.toFixed(3)}
                >
                  {place.code === null || !glyphesDisponibles ? '' : signe.sign_id}
                </text>
                {/* Petit écran : le code est masqué, le glyphe revient au milieu du secteur. */}
                <text className="glyphe-seul" x={place.seul.x.toFixed(3)} y={place.seul.y.toFixed(3)}>
                  {glyphe}
                </text>
              </g>
            )
          })}
        </g>

        <g className="frontieres" aria-hidden="true">
          {donnees.signs.map((signe) => {
            const a = point(signe.start_deg, signesInterieur)
            const b = point(signe.start_deg, signesExterieur)
            return (
              <line
                key={signe.sign_id}
                className="frontiere"
                x1={a.x.toFixed(3)}
                y1={a.y.toFixed(3)}
                x2={b.x.toFixed(3)}
                y2={b.y.toFixed(3)}
              />
            )
          })}
        </g>
        <circle className="bord" cx={CENTRE} cy={CENTRE} r={signesExterieur * R} />
        <circle className="bord" cx={CENTRE} cy={CENTRE} r={signesInterieur * R} />

        {astres.map((astre, rang) => {
          const exact = point(astre.longitude_deg, repereExact)
          const tige = point(astre.longitude_deg, repereExact + 0.03)
          const deplacee = Math.abs(places[rang] - astre.longitude_deg) > 1e-9
          const ancre = point(places[rang], ANNEAUX.etiquettesExterieur)
          const glyphe = point(places[rang], ANNEAUX.etiquettes + 0.03)
          const valeur = point(places[rang], ANNEAUX.etiquettes - 0.05)
          return (
            <g
              key={astre.id}
              className="astre"
              data-astre-id={astre.id}
              role="img"
              tabIndex={0}
              aria-label={`${astre.nom}, longitude ${degres(astre.longitude_deg, 4)}${
                astre.detail ? `, ${astre.detail}` : ''
              }`}
            >
              {deplacee && (
                <line
                  className="rappel"
                  x1={exact.x.toFixed(3)}
                  y1={exact.y.toFixed(3)}
                  x2={ancre.x.toFixed(3)}
                  y2={ancre.y.toFixed(3)}
                />
              )}
              <path className="tige" d={`M ${coordonnees(exact)} L ${coordonnees(tige)}`} />
              <circle
                className="repere-exact"
                cx={exact.x.toFixed(3)}
                cy={exact.y.toFixed(3)}
                r={6}
              />
              {/* Anneau de focus : visible seulement quand le repère a le focus du clavier. */}
              <circle className="halo" cx={glyphe.x.toFixed(3)} cy={glyphe.y.toFixed(3)} r={30} />
              <text className="etiquette-glyphe" x={glyphe.x.toFixed(3)} y={glyphe.y.toFixed(3)}>
                {glyphesDisponibles ? glypheTexte(astre.glyphe) : astre.nom}
              </text>
              {astre.valeur !== undefined && (
                <text className="etiquette-valeur" x={valeur.x.toFixed(3)} y={valeur.y.toFixed(3)}>
                  {astre.valeur}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      <figcaption>
        <span>Treize secteurs, chacun de la largeur calculée de son signe.</span>{' '}
        <span>
          Longitude 0° à gauche, longitudes croissantes dans le sens inverse des aiguilles d’une
          montre.
        </span>{' '}
        <span>
          Aucun Ascendant n’est calculé dans cette version : la roue n’est pas orientée sur lui.
        </span>
      </figcaption>
    </figure>
  )
}
