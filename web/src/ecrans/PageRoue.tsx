import { useState } from 'react'
import type { WheelData } from '../api/types.ts'
import { degres, glypheTexte } from '../formats.ts'
import { RoueB13 } from '../roue/RoueB13.tsx'
import { BandeauStatut } from '../statut/BandeauStatut.tsx'
import type { StatutAffiche } from '../statut/BandeauStatut.tsx'

interface Props {
  roue: WheelData | null
  statut: StatutAffiche
  glyphesDisponibles?: boolean
}

/** FR-10 : la roue proportionnelle et son équivalent en tableau, reliés par la sélection. */
export function PageRoue({ roue, statut, glyphesDisponibles = true }: Props) {
  const [selection, setSelection] = useState<string | null>(null)
  return (
    <div className="ecran ecran-roue">
      <h1 tabIndex={-1}>La roue à 13 signes</h1>
      <p className="chapeau">
        Chaque secteur a la largeur de son signe sur l’écliptique : les 13 signes sont inégaux,
        et dessinés comme tels. Un signe est un intervalle de longitude défini par convention ; il
        ne se confond pas avec la constellation du même nom.
      </p>
      <BandeauStatut
        statut={statut}
        niveaux={[
          { niveau: 'mesure', objet: 'largeurs calculées' },
          { niveau: 'convention', objet: 'frontières des 13 signes (modèle B)' },
        ]}
      />
      {roue === null ? (
        <p className="avis">La roue n’est pas affichée : le découpage n’a pas pu être lu.</p>
      ) : (
        <div className="grille-roue">
          <section className="carte" aria-label="Roue">
            <RoueB13
              donnees={roue}
              selection={selection}
              onSelection={setSelection}
              glyphesDisponibles={glyphesDisponibles}
            />
          </section>
          <section className="carte">
            <h2 id="titre-tableau-signes">Les 13 signes du modèle B, par longitude croissante</h2>
            <div className="defilement" tabIndex={0} role="region" aria-label="Tableau des signes">
              <table aria-labelledby="titre-tableau-signes">
                <thead>
                  <tr>
                    <th scope="col">Signe</th>
                    <th scope="col">Début</th>
                    <th scope="col">Fin</th>
                    <th scope="col">Largeur</th>
                  </tr>
                </thead>
                <tbody>
                  {roue.signs.map((signe) => {
                    const choisi = selection === signe.sign_id
                    return (
                      <tr key={signe.sign_id} className={choisi ? 'ligne-choisie' : undefined}>
                        <th scope="row">
                          <span className="glyphe" aria-hidden="true">
                            {glyphesDisponibles ? glypheTexte(signe.glyph) : signe.sign_id}
                          </span>{' '}
                          <button
                            type="button"
                            className="lien"
                            aria-pressed={choisi}
                            onClick={() => setSelection(choisi ? null : signe.sign_id)}
                          >
                            {signe.name}
                          </button>
                          {choisi && <span className="etat-ligne"> sélectionné</span>}
                        </th>
                        <td className="valeur">{degres(signe.start_deg)}</td>
                        <td className="valeur">{degres(signe.end_deg)}</td>
                        <td className="valeur">{degres(signe.width_deg)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p className="aide">
              Début inclus, fin exclue. Longitudes dans l’écliptique moyen J2000 ; frontières UAI,
              réalisation Skyfield / Roman 1987 (VI/42).
            </p>
          </section>
        </div>
      )}
    </div>
  )
}
