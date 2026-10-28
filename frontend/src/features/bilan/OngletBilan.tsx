/** Onglet 2 — Bilan énergétique (F-05 à F-08). */

import { useState } from "react";

import { Diagnostic, EnteteOnglet, NumberField, Plaque, Tuile } from "../../components/communs";
import { messagesDuModule, useProjet } from "../../store/projet";
import { energie, entier, nombre, puissance } from "../../utils/format";

export function OngletBilan() {
  const { entree, resultats, modifier } = useProjet();
  const [profilActif, setProfilActif] = useState(0);
  if (!entree) return null;

  const profils = entree.bilan.profils;
  const valeurs = resultats?.bilan.valeurs ?? null;
  const messages = messagesDuModule(resultats, "bilan");
  const profil = profils[profilActif];
  const profilCalcule = valeurs?.profils[profilActif] ?? null;

  function ajouterCategorie() {
    // L'index du nouveau profil est connu avant la modification : le
    // tableau en compte un de plus après l'ajout.
    const indexNouveau = profils.length;
    modifier((p) => {
      const numero = p.bilan.profils.length + 1;
      p.bilan.profils.push({
        id: `profil-${numero}`,
        nom: `Catégorie ${numero}`,
        nb_abonnes: 0,
        lignes: structuredClone(p.bilan.profils[0]?.lignes ?? []),
      });
    });
    setProfilActif(indexNouveau);
  }

  return (
    <>
      <EnteteOnglet
        module="Module 02"
        titre="Bilan"
        accent="énergétique"
        description="Consommation d'un abonné type, puis mise à l'échelle sur la zone. Le tableau s'ouvre pré-rempli depuis la bibliothèque."
        formules="F-05 → F-08"
        actions={
          <button type="button" className="bouton" onClick={ajouterCategorie}>
            Ajouter une catégorie
          </button>
        }
      />

      {entree.bilan.profils.length > 1 && (
        <div className="onglets" role="tablist" aria-label="Catégories d'abonnés">
          {entree.bilan.profils.map((p, index) => (
            <button
              key={p.id}
              role="tab"
              aria-selected={index === profilActif}
              onClick={() => setProfilActif(index)}
            >
              {p.nom} <span className="compte">{entier(p.nb_abonnes)} ab.</span>
            </button>
          ))}
        </div>
      )}

      <div className="flux">
        <div className="banc">
          <Tuile
            cle="Par abonné"
            valeur={nombre((profilCalcule?.e_cons_wh_j ?? 0) / 1000)}
            unite="kWh/j"
            note="F-06"
          />
          <Tuile
            cle="Zone entière"
            valeur={valeurs ? energie(valeurs.e_zone_wh_j).texte.split(" ")[0] : "—"}
            unite={valeurs ? `${energie(valeurs.e_zone_wh_j).unite}/j` : undefined}
            note={valeurs ? `${nombre(valeurs.e_zone_an_kwh / 1000, 0)} MWh/an` : undefined}
            important
          />
          <Tuile
            cle="P installée"
            valeur={valeurs ? puissance(valeurs.p_inst_zone_w).texte.split(" ")[0] : "—"}
            unite={valeurs ? puissance(valeurs.p_inst_zone_w).unite : undefined}
            note="zone"
          />
          <Tuile
            cle="P appelée"
            valeur={valeurs ? puissance(valeurs.p_app_zone_w).texte.split(" ")[0] : "—"}
            unite={valeurs ? puissance(valeurs.p_app_zone_w).unite : undefined}
            note="pondérée Ks"
          />
        </div>

        <Plaque
          titre={`Inventaire — ${profil?.nom ?? ""}`}
          formule="F-05"
          sousTitre="Cellules modifiables"
        >
          <div className="defilement">
            <table>
              <caption className="sr">
                Consommation journalière par appareil
              </caption>
              <thead>
                <tr>
                  <th scope="col">Appareil</th>
                  <th scope="col">Usage</th>
                  <th scope="col" className="num">P (W)</th>
                  <th scope="col" className="num">Qté</th>
                  <th scope="col" className="num">t (h/j)</th>
                  <th scope="col" className="num">Ks</th>
                  <th scope="col" className="num">E (Wh/j)</th>
                  <th scope="col" className="num">Part</th>
                </tr>
              </thead>
              <tbody>
                {profil?.lignes.map((ligne, index) => {
                  const calcul = profilCalcule?.lignes.find((l) => l.nom === ligne.nom);
                  const inactive = ligne.quantite === 0;
                  return (
                    <tr key={ligne.ref_bibliotheque ?? ligne.nom} className={inactive ? "eteinte" : undefined}>
                      <td>{ligne.nom}</td>
                      <td>{ligne.categorie}</td>
                      <td className="num">{nombre(ligne.puissance_w, 0)}</td>
                      <td className="num cellule-modifiable">
                        <input
                          type="text"
                          inputMode="numeric"
                          className="saisie-cellule tnum"
                          aria-label={`Quantité de ${ligne.nom}`}
                          value={ligne.quantite}
                          onChange={(evenement) => {
                            const valeur = Number.parseInt(evenement.target.value, 10);
                            modifier((p) => {
                              p.bilan.profils[profilActif].lignes[index].quantite =
                                Number.isFinite(valeur) ? Math.max(valeur, 0) : 0;
                            });
                          }}
                        />
                      </td>
                      <td className="num">{nombre(ligne.heures_j, 1)}</td>
                      <td className="num">{nombre(ligne.ks, 2)}</td>
                      <td className="num">{calcul ? nombre(calcul.e_wh_j, 0) : "0"}</td>
                      <td className="num">
                        {calcul && calcul.e_wh_j > 0 ? `${nombre(calcul.part_pct, 1)} %` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={6}>Total par abonné</td>
                  <td className="num">{nombre(profilCalcule?.e_cons_wh_j, 0)}</td>
                  <td className="num">100 %</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </Plaque>

        <div className="duo">
          <Plaque titre="Mise à l'échelle" formule="F-07">
            <div className="flux" style={{ gap: 15 }}>
              <NumberField
                label="Nombre d'abonnés dans la zone"
                valeur={profil?.nb_abonnes ?? 0}
                decimales={0}
                onChange={(valeur) =>
                  modifier((p) => {
                    p.bilan.profils[profilActif].nb_abonnes = Math.max(
                      Math.round(valeur ?? 0),
                      0,
                    );
                  })
                }
              />
              <div className="equation">
                E<i>_zone</i> = {nombre(profilCalcule?.e_cons_wh_j, 0)} Wh/j ×{" "}
                {entier(profil?.nb_abonnes)}
                <br />
                <b>
                  {"       "}= {valeurs ? energie(valeurs.e_zone_wh_j).texte : "—"}/j
                </b>
              </div>
              <dl className="paires">
                <div>
                  <dt>Journalier</dt>
                  <dd>{valeurs ? energie(valeurs.e_zone_wh_j).texte : "—"}</dd>
                </div>
                <div>
                  <dt>Janvier (31 j)</dt>
                  <dd>
                    {valeurs ? energie(valeurs.e_zone_mensuel_kwh[0] * 1000).texte : "—"}
                  </dd>
                </div>
                <div>
                  <dt>Annuel</dt>
                  <dd>{valeurs ? energie(valeurs.e_zone_an_kwh * 1000).texte : "—"}</dd>
                </div>
              </dl>
            </div>
          </Plaque>

          <Plaque titre="Répartition par usage">
            <div className="barres">
              {valeurs?.repartition_categories.slice(0, 6).map((categorie) => (
                <div key={categorie.categorie}>
                  <div className="barre-entete">
                    <span>{categorie.categorie}</span>
                    <b className="tnum">{nombre(categorie.part_pct, 1)} %</b>
                  </div>
                  <div className="barre-piste">
                    <i style={{ width: `${categorie.part_pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Plaque>
        </div>

        {messages.length > 0 && (
          <Plaque titre="Diagnostics">
            <div className="diagnostics">
              {messages.map((message, index) => (
                <Diagnostic key={`${message.code}-${index}`} message={message} />
              ))}
            </div>
          </Plaque>
        )}
      </div>
    </>
  );
}
