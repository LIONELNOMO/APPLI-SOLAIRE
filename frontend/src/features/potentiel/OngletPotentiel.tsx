/** Onglet 1 — Potentiel solaire (F-01 à F-04). */

import { apiBlob } from "../../api/client";
import { Diagnostic, EnteteOnglet, NumberField, Plaque, Tuile } from "../../components/communs";
import {
  IconeDocument,
  IconeEclair,
  IconePanneau,
  IconeSoleil,
  IconeTheme,
} from "../../components/icones";
import { messagesDuModule, useProjet } from "../../store/projet";
import { MOIS_COURTS, crete, energie, nombre } from "../../utils/format";

const UNITES_GHI = [
  { valeur: "w_m2_moy24h", libelle: "W/m² moy. 24 h" },
  { valeur: "kwh_m2_j", libelle: "kWh/m²/j" },
  { valeur: "kwh_m2_an", libelle: "kWh/m²/an" },
];

const UNITES_SURFACE = [
  { valeur: "m2", libelle: "m²" },
  { valeur: "ha", libelle: "ha" },
  { valeur: "km2", libelle: "km²" },
];

export function OngletPotentiel() {
  const { entree, resultats, modifier } = useProjet();
  if (!entree) return null;

  const valeurs = resultats?.potentiel.valeurs ?? null;
  const messages = [
    ...messagesDuModule(resultats, "potentiel"),
    ...messagesDuModule(resultats, "production").filter((m) =>
      m.code.startsWith("PROD-A02"),
    ),
  ];

  async function telechargerRapport() {
    const { blob, nomFichier } = await apiBlob("/rapports/pdf", entree);
    const url = URL.createObjectURL(blob);
    const lien = document.createElement("a");
    lien.href = url;
    lien.download = nomFichier;
    lien.click();
    URL.revokeObjectURL(url);
  }

  const mensuel = valeurs?.h_mensuel_kwh_m2_j ?? [];
  const maximum = mensuel.length ? Math.max(...mensuel) : 1;
  const minimum = mensuel.length ? Math.min(...mensuel) : 0;

  return (
    <>
      <EnteteOnglet
        module="Module 01"
        titre="Potentiel"
        accent="solaire"
        description="Irradiation disponible sur la zone et énergie théoriquement récupérable sur la surface d'étude."
        formules="F-01 → F-04"
        actions={
          <>
            <button
              type="button"
              className="bouton"
              onClick={() => {
                const racine = document.documentElement;
                const sombre = window.matchMedia("(prefers-color-scheme: dark)").matches;
                const actuel = racine.getAttribute("data-theme") ?? (sombre ? "dark" : "light");
                racine.setAttribute("data-theme", actuel === "dark" ? "light" : "dark");
              }}
            >
              <IconeTheme />
              Thème
            </button>
            <button
              type="button"
              className="bouton bouton-primaire"
              onClick={() => void telechargerRapport()}
            >
              <IconeDocument />
              Rapport PDF
            </button>
          </>
        }
      />

      <div className="flux">
        <div className="banc">
          <Tuile
            cle="Irradiation journalière"
            valeur={nombre(valeurs?.h_kwh_m2_j, 3)}
            unite="kWh/m²/j"
            note={
              valeurs
                ? `Soit ${nombre(valeurs.h_kwh_m2_j, 2)} h de plein soleil`
                : undefined
            }
            icone={<IconeSoleil />}
            badge={valeurs ? { texte: "calculé", ton: "ok" } : undefined}
            important
          />
          <Tuile
            cle="Cumul annuel"
            valeur={nombre(valeurs?.h_an_kwh_m2_an, 0)}
            unite="kWh/m²"
            note="Sur 365 jours"
            icone={<IconeSoleil />}
          />
          <Tuile
            cle="Potentiel brut du terrain"
            valeur={
              valeurs?.e_pot_an_kwh
                ? energie(valeurs.e_pot_an_kwh * 1000).texte.split(" ")[0]
                : "—"
            }
            unite={
              valeurs?.e_pot_an_kwh
                ? `${energie(valeurs.e_pot_an_kwh * 1000).unite}/an`
                : undefined
            }
            note={
              valeurs?.e_pot_j_kwh
                ? `${nombre(valeurs.e_pot_j_kwh, 0)} kWh par jour`
                : "Renseignez la surface"
            }
            icone={<IconeEclair />}
          />
          <Tuile
            cle="Puissance installable"
            valeur={
              valeurs?.pc_max_surface_kwc
                ? crete(valeurs.pc_max_surface_kwc).texte.split(" ")[0]
                : "—"
            }
            unite={
              valeurs?.pc_max_surface_kwc
                ? crete(valeurs.pc_max_surface_kwc).unite
                : undefined
            }
            note={
              valeurs?.e_tech_an_kwh
                ? `${nombre(valeurs.e_tech_an_kwh / 1000, 0)} MWh/an récupérables`
                : "Renseignez la surface"
            }
            icone={<IconePanneau />}
          />
        </div>

        <div className="duo">
          <Plaque titre="Irradiance mesurée" formule="F-01">
            <div className="flux" style={{ gap: 15 }}>
              <NumberField
                label="GHI"
                valeur={entree.potentiel.ghi_valeur}
                decimales={3}
                unites={UNITES_GHI}
                uniteChoisie={entree.potentiel.ghi_unite}
                onUniteChange={(unite) =>
                  modifier((p) => {
                    p.potentiel.ghi_unite = unite as typeof p.potentiel.ghi_unite;
                  })
                }
                onChange={(valeur) =>
                  modifier((p) => {
                    p.potentiel.ghi_valeur = valeur ?? 0;
                  })
                }
                aide="La virgule et le point sont acceptés."
              />
              <div className="equation">
                H = G × 24 / 1 000
                <br />
                <i> = {nombre(entree.potentiel.ghi_valeur, 3)} × 0,024</i>
                <br />
                <b> = {nombre(valeurs?.h_kwh_m2_j, 3)} kWh/m²/j</b>
              </div>
              <div className="champ">
                <label htmlFor="source-ghi">Source de la donnée</label>
                <input
                  id="source-ghi"
                  type="text"
                  value={entree.potentiel.source_ghi}
                  onChange={(evenement) =>
                    modifier((p) => {
                      p.potentiel.source_ghi = evenement.target.value;
                    })
                  }
                />
              </div>
            </div>
          </Plaque>

          <Plaque titre="Surface d'étude" formule="F-02 · F-03">
            <div className="flux" style={{ gap: 15 }}>
              <NumberField
                label="Surface de la zone"
                valeur={entree.potentiel.surface_valeur}
                placeholder="Non renseignée"
                unites={UNITES_SURFACE}
                uniteChoisie={entree.potentiel.surface_unite}
                onUniteChange={(unite) =>
                  modifier((p) => {
                    p.potentiel.surface_unite = unite as typeof p.potentiel.surface_unite;
                  })
                }
                onChange={(valeur) =>
                  modifier((p) => {
                    p.potentiel.surface_valeur = valeur;
                  })
                }
                aide={
                  valeurs?.surface_m2
                    ? `${nombre(valeurs.surface_m2, 0)} m² retenus`
                    : "Question ouverte Q-02"
                }
              />
              <div className="duo" style={{ gap: 13 }}>
                <NumberField
                  label="Taux d'occupation"
                  valeur={entree.potentiel.taux_occupation * 100}
                  decimales={0}
                  unite="%"
                  onChange={(valeur) =>
                    modifier((p) => {
                      p.potentiel.taux_occupation = (valeur ?? 0) / 100;
                    })
                  }
                />
                <NumberField
                  label="Rendement module"
                  valeur={entree.potentiel.rendement_module * 100}
                  decimales={0}
                  unite="%"
                  onChange={(valeur) =>
                    modifier((p) => {
                      p.potentiel.rendement_module = (valeur ?? 0) / 100;
                    })
                  }
                />
              </div>
              <dl className="paires">
                <div>
                  <dt>Pc max = A × τ × η</dt>
                  <dd>{crete(valeurs?.pc_max_surface_kwc).texte}</dd>
                </div>
                <div>
                  <dt>Potentiel brut annuel</dt>
                  <dd>{valeurs?.e_pot_an_kwh ? energie(valeurs.e_pot_an_kwh * 1000).texte : "—"}</dd>
                </div>
                <div>
                  <dt>Potentiel technique</dt>
                  <dd>{valeurs?.e_tech_an_kwh ? energie(valeurs.e_tech_an_kwh * 1000).texte : "—"}</dd>
                </div>
              </dl>
            </div>
          </Plaque>
        </div>

        {mensuel.length === 12 && (
          <Plaque
            titre="Profil mensuel"
            sousTitre="12 valeurs · kWh/m²/j"
            action={
              <span className="jeton jeton-avert">
                Minimum {MOIS_COURTS[(valeurs?.mois_defavorable ?? 1) - 1]} — {nombre(minimum, 2)}
              </span>
            }
          >
            <div className="histogramme" role="img"
              aria-label={`Irradiation mensuelle, de ${nombre(minimum, 2)} à ${nombre(maximum, 2)} kWh/m²/j.`}>
              {mensuel.map((valeur, index) => (
                <div key={index} className="histogramme-colonne">
                  <div className="histogramme-piste">
                    <div
                      className={valeur === minimum ? "histogramme-barre barre-min" : "histogramme-barre"}
                      style={{ height: `${(valeur / maximum) * 100}%` }}
                    />
                  </div>
                  <div className="histogramme-mois">{MOIS_COURTS[index]}</div>
                  <div className="histogramme-valeur tnum">{nombre(valeur, 2)}</div>
                </div>
              ))}
            </div>
          </Plaque>
        )}

        {messages.length > 0 && (
          <Plaque
            titre="Diagnostics"
            action={
              <span className="jeton jeton-info">
                {messages.length} message{messages.length > 1 ? "s" : ""}
              </span>
            }
          >
            <div className="diagnostics">
              {messages.map((message) => (
                <Diagnostic key={message.code} message={message} />
              ))}
            </div>
          </Plaque>
        )}
      </div>
    </>
  );
}
