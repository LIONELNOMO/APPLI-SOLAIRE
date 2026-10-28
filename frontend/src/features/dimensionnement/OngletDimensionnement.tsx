/** Onglet 3 — Dimensionnement technique (étapes 1 à 21). */

import { useEffect, useState } from "react";

import { apiPost } from "../../api/client";
import type { Proposition } from "../../api/types";
import {
  Bascule,
  Diagnostic,
  EnteteOnglet,
  NumberField,
  Plaque,
  Tuile,
} from "../../components/communs";
import { messagesDuModule, useProjet } from "../../store/projet";
import { crete, entier, nombre, pourcent } from "../../utils/format";

type SousOnglet = "production" | "panneaux" | "onduleurs" | "batteries" | "cables";

const SOUS_ONGLETS: { cle: SousOnglet; libelle: string; etapes: string }[] = [
  { cle: "production", libelle: "Production", etapes: "1–3" },
  { cle: "panneaux", libelle: "Panneaux", etapes: "4–11" },
  { cle: "onduleurs", libelle: "Onduleurs", etapes: "12–14" },
  { cle: "batteries", libelle: "Batteries", etapes: "15–19" },
  { cle: "cables", libelle: "Câbles DC", etapes: "20–21" },
];

export function OngletDimensionnement() {
  const { entree, resultats, modifier } = useProjet();
  const [sousOnglet, setSousOnglet] = useState<SousOnglet>("production");
  const [propositions, setPropositions] = useState<Proposition[]>([]);
  const [chargementListe, setChargementListe] = useState(false);

  // La liste de choix est recalculée quand on ouvre le sous-onglet concerné.
  useEffect(() => {
    if (!entree) return;
    const type =
      sousOnglet === "panneaux"
        ? "panneaux"
        : sousOnglet === "onduleurs"
          ? "onduleurs"
          : sousOnglet === "batteries"
            ? "batteries"
            : null;
    if (!type) {
      setPropositions([]);
      return;
    }

    let annule = false;
    setChargementListe(true);
    void apiPost<Proposition[]>(`/selection/${type}`, {
      projet: entree,
      filtres: { compatibles_uniquement: false },
    })
      .then((liste) => {
        if (!annule) setPropositions(liste);
      })
      .catch(() => {
        if (!annule) setPropositions([]);
      })
      .finally(() => {
        if (!annule) setChargementListe(false);
      });

    return () => {
      annule = true;
    };
    // L'entrée complète changerait à chaque frappe : on ne dépend que du
    // sous-onglet et des grandeurs qui modifient réellement la liste.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    sousOnglet,
    entree?.production.tension_systeme_v,
    entree?.production.performance_ratio,
    entree?.pv.fiche?.id,
  ]);

  if (!entree) return null;

  const prod = resultats?.production.valeurs ?? null;
  const pv = resultats?.pv.valeurs ?? null;
  const ond = resultats?.onduleur.valeurs ?? null;
  const bat = resultats?.batteries.valeurs ?? null;
  const cab = resultats?.cables.valeurs ?? null;

  const messages = [
    ...messagesDuModule(resultats, "production"),
    ...messagesDuModule(resultats, "pv"),
    ...messagesDuModule(resultats, "onduleur"),
    ...messagesDuModule(resultats, "batteries"),
    ...messagesDuModule(resultats, "cables"),
  ].filter((m) => m.niveau !== "info");

  function choisir(fiche: Record<string, unknown>) {
    modifier((p) => {
      if (sousOnglet === "panneaux") p.pv.fiche = fiche as never;
      if (sousOnglet === "onduleurs") p.onduleur.fiche = fiche as never;
      if (sousOnglet === "batteries") p.batteries.fiche = fiche as never;
    });
  }

  return (
    <>
      <EnteteOnglet
        module="Module 03"
        titre="Dimensionnement"
        accent="technique"
        description="Puissance crête, configuration série/parallèle du champ, onduleurs, parc de batteries et câbles continus."
        formules="F-09 → F-25"
      />

      <div className="onglets" role="tablist" aria-label="Étapes du dimensionnement">
        {SOUS_ONGLETS.map(({ cle, libelle, etapes }) => (
          <button
            key={cle}
            role="tab"
            aria-selected={sousOnglet === cle}
            onClick={() => setSousOnglet(cle)}
          >
            {libelle} <span className="compte">{etapes}</span>
          </button>
        ))}
      </div>

      <div className="flux">
        {messages.length > 0 && (
          <div className="diagnostics">
            {messages.slice(0, 3).map((message, index) => (
              <Diagnostic key={`${message.code}-${index}`} message={message} />
            ))}
          </div>
        )}

        <div className="banc">
          <Tuile cle="Pc retenue" valeur={nombre(prod?.pc_retenue_kwc)} unite="kWc" note="F-09" />
          <Tuile
            cle="Pc installée"
            valeur={nombre(pv?.pc_installee_kwc)}
            unite="kWc"
            note={
              pv && prod
                ? `${pv.pc_installee_kwc >= prod.pc_retenue_kwc ? "+" : ""}${nombre(
                    ((pv.pc_installee_kwc - prod.pc_retenue_kwc) / prod.pc_retenue_kwc) * 100,
                    2,
                  )} %`
                : undefined
            }
            important
          />
          <Tuile
            cle="Panneaux"
            valeur={entier(pv?.n_total)}
            note={pv ? `N_min ${entier(pv.n_min)} · +${entier(pv.n_total - pv.n_min)}` : undefined}
          />
          <Tuile
            cle="U champ"
            valeur={nombre(pv?.u_dc_v, 1)}
            unite="V"
            note={pv ? `${pourcent(pv.taux_utilisation_us)} de Us` : undefined}
          />
          <Tuile
            cle="I champ"
            valeur={nombre(pv?.i_dc_a, 1)}
            unite="A"
            note={pv ? `Icc ${nombre(pv.i_cc_dc_a, 1)} A` : undefined}
          />
        </div>

        {sousOnglet === "production" && (
          <div className="duo">
            <Plaque titre="Énergie à couvrir" formule="F-09">
              <div className="flux" style={{ gap: 15 }}>
                <NumberField
                  label="Taux de couverture"
                  valeur={entree.production.taux_couverture * 100}
                  decimales={0}
                  unite="%"
                  onChange={(valeur) =>
                    modifier((p) => {
                      p.production.taux_couverture = (valeur ?? 0) / 100;
                    })
                  }
                />
                <NumberField
                  label="Performance ratio"
                  valeur={entree.production.performance_ratio}
                  onChange={(valeur) =>
                    modifier((p) => {
                      p.production.performance_ratio = valeur ?? 0;
                    })
                  }
                  aide="Valeur courante en climat chaud : 0,75 à 0,80"
                />
                <NumberField
                  label="Tension du système (Us)"
                  valeur={entree.production.tension_systeme_v}
                  decimales={0}
                  unite="V"
                  onChange={(valeur) =>
                    modifier((p) => {
                      p.production.tension_systeme_v = valeur ?? 0;
                    })
                  }
                  aide="Borne du cahier des charges : 700 V"
                />
                <div className="equation">
                  Pc = E_cible / (Ir × PR)
                  <br />
                  <i>
                    {"   "}= {nombre(prod?.e_cible_kwh_j, 0)} / ({nombre(prod?.ir_kwh_m2_j, 3)} ×{" "}
                    {nombre(entree.production.performance_ratio, 2)})
                  </i>
                  <br />
                  <b>
                    {"   "}= {crete(prod?.pc_retenue_kwc).texte}
                  </b>
                </div>
              </div>
            </Plaque>

            <Plaque titre="Production attendue" formule="F-10">
              <dl className="paires">
                <div>
                  <dt>Irradiation retenue</dt>
                  <dd>{nombre(prod?.ir_kwh_m2_j, 3)} kWh/m²/j</dd>
                </div>
                <div>
                  <dt>Production journalière</dt>
                  <dd>{nombre(prod?.prod_installee?.j_kwh ?? prod?.prod_theorique?.j_kwh, 0)} kWh</dd>
                </div>
                <div>
                  <dt>Production annuelle</dt>
                  <dd>
                    {nombre(
                      (prod?.prod_installee?.an_kwh ?? prod?.prod_theorique?.an_kwh ?? 0) / 1000,
                      0,
                    )}{" "}
                    MWh
                  </dd>
                </div>
                <div>
                  <dt>Productible spécifique</dt>
                  <dd>
                    {nombre(prod?.prod_installee?.y_kwh_kwc ?? prod?.prod_theorique?.y_kwh_kwc, 0)}{" "}
                    kWh/kWc/an
                  </dd>
                </div>
                <div>
                  <dt>Couverture effective</dt>
                  <dd>{pourcent(prod?.taux_couverture_effectif)}</dd>
                </div>
              </dl>
            </Plaque>
          </div>
        )}

        {(sousOnglet === "panneaux" ||
          sousOnglet === "onduleurs" ||
          sousOnglet === "batteries") && (
          <Plaque
            titre={`Catalogue — ${SOUS_ONGLETS.find((s) => s.cle === sousOnglet)?.libelle}`}
            sousTitre={
              chargementListe
                ? "calcul de l'aperçu…"
                : `${propositions.length} fiche${propositions.length > 1 ? "s" : ""}`
            }
          >
            <div className="defilement">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Modèle</th>
                    {sousOnglet === "panneaux" && (
                      <>
                        <th scope="col" className="num">Pmax</th>
                        <th scope="col" className="num">Ns</th>
                        <th scope="col" className="num">Np</th>
                        <th scope="col" className="num">Total</th>
                        <th scope="col" className="num">Surplus</th>
                      </>
                    )}
                    {sousOnglet === "onduleurs" && (
                      <>
                        <th scope="col" className="num">P nom.</th>
                        <th scope="col" className="num">Nombre</th>
                        <th scope="col" className="num">Ratio</th>
                        <th scope="col" className="num">Iac</th>
                      </>
                    )}
                    {sousOnglet === "batteries" && (
                      <>
                        <th scope="col" className="num">U nom.</th>
                        <th scope="col" className="num">Config.</th>
                        <th scope="col" className="num">U parc</th>
                        <th scope="col" className="num">Autonomie</th>
                      </>
                    )}
                    <th scope="col">État</th>
                    <th scope="col" />
                  </tr>
                </thead>
                <tbody>
                  {propositions.map((proposition) => {
                    const fiche = proposition.fiche as Record<string, never>;
                    const apercu = proposition.apercu;
                    const choisi =
                      (sousOnglet === "panneaux" && entree.pv.fiche?.id === fiche.id) ||
                      (sousOnglet === "onduleurs" && entree.onduleur.fiche?.id === fiche.id) ||
                      (sousOnglet === "batteries" && entree.batteries.fiche?.id === fiche.id);
                    return (
                      <tr key={String(fiche.id)} className={choisi ? "retenue" : undefined}>
                        <td>{choisi ? <b>{String(fiche.nom)}</b> : String(fiche.nom)}</td>
                        {sousOnglet === "panneaux" && (
                          <>
                            <td className="num">{nombre(Number(fiche.pmax), 0)} W</td>
                            <td className="num">{entier(apercu.ns)}</td>
                            <td className="num">{entier(apercu.np)}</td>
                            <td className="num">{entier(apercu.n_total)}</td>
                            <td className="num">{nombre(apercu.surplus_pct, 2)} %</td>
                          </>
                        )}
                        {sousOnglet === "onduleurs" && (
                          <>
                            <td className="num">{nombre(Number(fiche.pnom_ac), 0)} kW</td>
                            <td className="num">{entier(apercu.n_ond)}</td>
                            <td className="num">{nombre(apercu.ratio_dc_ac, 3)}</td>
                            <td className="num">{nombre(apercu.iac_a, 1)} A</td>
                          </>
                        )}
                        {sousOnglet === "batteries" && (
                          <>
                            <td className="num">{nombre(Number(fiche.u_nom), 1)} V</td>
                            <td className="num">
                              {entier(apercu.ns)}s × {entier(apercu.np)}p
                            </td>
                            <td className="num">{nombre(apercu.u_parc_v, 1)} V</td>
                            <td className="num">{nombre(apercu.autonomie_j, 2)} j</td>
                          </>
                        )}
                        <td>
                          <span
                            className={
                              proposition.statut === "ok"
                                ? "jeton jeton-ok"
                                : proposition.statut === "avertissement"
                                  ? "jeton jeton-avert"
                                  : "jeton jeton-erreur"
                            }
                            title={proposition.motif ?? undefined}
                          >
                            {proposition.statut === "ok"
                              ? "Compatible"
                              : (proposition.motif ?? proposition.statut)}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="bouton bouton-petit"
                            onClick={() => choisir(proposition.fiche)}
                            disabled={choisi}
                          >
                            {choisi ? "Retenu" : "Choisir"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Plaque>
        )}

        {sousOnglet === "panneaux" && pv && entree.pv.fiche && (
          <div className="duo">
            <Plaque titre="Configuration du champ" formule="F-13 · F-14">
              <div className="flux" style={{ gap: 15 }}>
                <Bascule
                  label="Mode de configuration"
                  options={[
                    { valeur: "auto", libelle: "Automatique" },
                    { valeur: "manuel", libelle: "Manuel" },
                  ]}
                  choisie={entree.pv.mode_config}
                  onChange={(mode) =>
                    modifier((p) => {
                      p.pv.mode_config = mode;
                      if (mode === "manuel") {
                        p.pv.ns_manuel ??= pv.ns;
                        p.pv.np_manuel ??= pv.np;
                      }
                    })
                  }
                />
                <Bascule
                  label="Référence de Ns"
                  options={[
                    { valeur: "vmp", libelle: "Vmp" },
                    { valeur: "voc", libelle: "Voc" },
                    { valeur: "voc_froid", libelle: "Voc froid" },
                  ]}
                  choisie={entree.pv.tension_reference_ns}
                  onChange={(reference) =>
                    modifier((p) => {
                      p.pv.tension_reference_ns = reference;
                    })
                  }
                />
                {entree.pv.mode_config === "manuel" && (
                  <div className="duo" style={{ gap: 13 }}>
                    <NumberField
                      label="Ns (en série)"
                      valeur={entree.pv.ns_manuel}
                      decimales={0}
                      onChange={(valeur) =>
                        modifier((p) => {
                          p.pv.ns_manuel = valeur ? Math.max(Math.round(valeur), 1) : null;
                        })
                      }
                    />
                    <NumberField
                      label="Np (en parallèle)"
                      valeur={entree.pv.np_manuel}
                      decimales={0}
                      onChange={(valeur) =>
                        modifier((p) => {
                          p.pv.np_manuel = valeur ? Math.max(Math.round(valeur), 1) : null;
                        })
                      }
                    />
                  </div>
                )}
                <div className="equation">
                  Ns = ⌊{nombre(entree.production.tension_systeme_v, 0)} /{" "}
                  {nombre(pv.u_ref_v, 1)}⌋ <b>= {pv.ns}</b>
                  <br />
                  Np = ⌈{entier(pv.n_min)} / {pv.ns}⌉ <b>= {pv.np}</b>
                  <br />
                  N{"  "}= {pv.ns} × {pv.np} <b>= {entier(pv.n_total)}</b>
                </div>
              </div>
            </Plaque>

            <Plaque titre="Tenue en température" formule="F-16 → F-18">
              <div className="defilement">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Condition</th>
                      <th scope="col" className="num">T cellule</th>
                      <th scope="col" className="num">Tension</th>
                      <th scope="col">État</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Voc à vide, froid</td>
                      <td className="num">{nombre(pv.t_cell_min_c, 1)} °C</td>
                      <td className="num">{nombre(pv.voc_max_v, 2)} V</td>
                      <td>
                        {pv.voc_max_v > entree.production.tension_systeme_v ? (
                          <span className="jeton jeton-avert">&gt; Us</span>
                        ) : (
                          <span className="jeton jeton-ok">OK</span>
                        )}
                      </td>
                    </tr>
                    <tr>
                      <td>Vmp, froid</td>
                      <td className="num">{nombre(pv.t_cell_min_c, 1)} °C</td>
                      <td className="num">{nombre(pv.vmp_max_v, 2)} V</td>
                      <td>
                        {pv.vmp_max_v > entree.production.tension_systeme_v ? (
                          <span className="jeton jeton-avert">&gt; Us</span>
                        ) : (
                          <span className="jeton jeton-ok">OK</span>
                        )}
                      </td>
                    </tr>
                    <tr>
                      <td>Vmp, STC</td>
                      <td className="num">25,0 °C</td>
                      <td className="num">{nombre(pv.u_dc_v, 2)} V</td>
                      <td><span className="jeton jeton-ok">OK</span></td>
                    </tr>
                    <tr>
                      <td>Vmp, forte chaleur</td>
                      <td className="num">{nombre(pv.t_cell_max_c, 2)} °C</td>
                      <td className="num">{nombre(pv.vmp_min_v, 2)} V</td>
                      <td><span className="jeton jeton-ok">OK</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="aparte" style={{ marginTop: 16 }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
                  <path d="M12 3.2 2.3 20.4h19.4L12 3.2zM12 9.4v5.1M12 17.6v.2" />
                </svg>
                <div>
                  À {nombre(pv.t_cell_min_c, 0)} °C, les cellules sont à la température de l'air :
                  au lever du soleil, l'éclairement est trop faible pour les réchauffer. C'est le
                  cas le plus contraignant pour la tension.
                </div>
              </div>
            </Plaque>
          </div>
        )}

        {sousOnglet === "onduleurs" && ond && (
          <Plaque titre="Dimensionnement des onduleurs" formule="F-19 · F-20">
            <dl className="paires">
              <div>
                <dt>Nombre retenu</dt>
                <dd>{entier(ond.n_ond)} onduleurs</dd>
              </div>
              <div>
                <dt>Répartition des chaînes</dt>
                <dd>
                  {ond.repartition
                    .map((r) => `${r.nombre} × ${r.chaines}`)
                    .join(", ")}
                </dd>
              </div>
              <div>
                <dt>Ratio DC/AC global</dt>
                <dd>{nombre(ond.ratio_dc_ac, 3)}</dd>
              </div>
              <div>
                <dt>Courant par MPPT</dt>
                <dd>{nombre(ond.i_mppt_a, 2)} A</dd>
              </div>
              <div>
                <dt>Plage de Ns compatible</dt>
                <dd>{ond.ns_min} à {ond.ns_max}</dd>
              </div>
              <div>
                <dt>Courant AC par onduleur</dt>
                <dd>{nombre(ond.iac_a, 2)} A</dd>
              </div>
              <div>
                <dt>Puissance AC totale</dt>
                <dd>{nombre(ond.p_ac_total_kw, 0)} kW / {nombre(ond.s_ac_total_kva, 0)} kVA</dd>
              </div>
              <div>
                <dt>Entrées libres</dt>
                <dd>{entier(ond.entrees_libres)}</dd>
              </div>
            </dl>
          </Plaque>
        )}

        {sousOnglet === "batteries" && (
          <div className="duo">
            <Plaque titre="Paramètres du stockage" formule="F-21">
              <div className="flux" style={{ gap: 15 }}>
                <Bascule
                  label="Base d'énergie"
                  options={[
                    { valeur: "abonne", libelle: "Un abonné" },
                    { valeur: "zone", libelle: "La zone" },
                  ]}
                  choisie={entree.batteries.base_energie === "zone" ? "zone" : "abonne"}
                  onChange={(base) =>
                    modifier((p) => {
                      p.batteries.base_energie = base;
                    })
                  }
                />
                <NumberField
                  label="Jours d'autonomie"
                  valeur={entree.batteries.jours_autonomie}
                  decimales={1}
                  onChange={(valeur) =>
                    modifier((p) => {
                      p.batteries.jours_autonomie = valeur ?? 1;
                    })
                  }
                />
                <NumberField
                  label="Part de la consommation stockée"
                  valeur={entree.batteries.part_stockee * 100}
                  decimales={0}
                  unite="%"
                  onChange={(valeur) =>
                    modifier((p) => {
                      p.batteries.part_stockee = (valeur ?? 100) / 100;
                    })
                  }
                />
              </div>
            </Plaque>

            {bat && (
              <Plaque titre="Grandeurs du parc" formule="F-22 · F-23">
                <dl className="paires">
                  <div>
                    <dt>Énergie à stocker</dt>
                    <dd>{nombre(bat.e_bat_wh / 1000, 2)} kWh</dd>
                  </div>
                  <div>
                    <dt>Configuration</dt>
                    <dd>{bat.ns} série × {bat.np} parallèle = {bat.n_total}</dd>
                  </div>
                  <div>
                    <dt>Tension du parc</dt>
                    <dd>{nombre(bat.u_parc_v, 1)} V</dd>
                  </div>
                  <div>
                    <dt>Courant du parc</dt>
                    <dd>{nombre(bat.i_parc_a, 0)} A</dd>
                  </div>
                  <div>
                    <dt>Énergie utilisable</dt>
                    <dd>{nombre(bat.e_util_wh / 1000, 2)} kWh</dd>
                  </div>
                  <div>
                    <dt>Autonomie obtenue</dt>
                    <dd>{nombre(bat.autonomie_j, 2)} jour(s)</dd>
                  </div>
                  <div>
                    <dt>Courant de décharge</dt>
                    <dd>{nombre(bat.i_dech_a, 1)} A</dd>
                  </div>
                  {bat.n_total_zone && (
                    <div>
                      <dt>Pour la zone</dt>
                      <dd>{entier(bat.n_total_zone)} batteries</dd>
                    </div>
                  )}
                </dl>
              </Plaque>
            )}
          </div>
        )}

        {sousOnglet === "cables" && cab && (
          <Plaque titre="Câbles continus" formule="F-24 · F-25">
            <div className="defilement">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Câble</th>
                    <th scope="col" className="num">Longueur</th>
                    <th scope="col" className="num">S calculée</th>
                    <th scope="col" className="num">Section</th>
                    <th scope="col">Critère</th>
                    <th scope="col" className="num">Chute</th>
                    <th scope="col" className="num">Pertes</th>
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      ["dc_principal", cab.dc_principal, entree.cables.dc_principal],
                      ["dc_chaine", cab.dc_chaine, entree.cables.dc_chaine],
                      ["dc_batteries", cab.dc_batteries, entree.cables.dc_batteries],
                    ] as const
                  ).map(([cle, valeur, parametres]) =>
                    valeur ? (
                      <tr key={cle}>
                        <td>{valeur.nom}</td>
                        <td className="num">{nombre(parametres.longueur_m, 0)} m</td>
                        <td className="num">{nombre(valeur.s_calc_mm2, 2)} mm²</td>
                        <td className="num">
                          {valeur.n_conducteurs} × {nombre(valeur.section_mm2, 1)} mm²
                        </td>
                        <td>{valeur.critere}</td>
                        <td className="num">{nombre(valeur.epsilon_reel * 100, 3)} %</td>
                        <td className="num">{nombre(valeur.p_joule_w, 1)} W</td>
                      </tr>
                    ) : null,
                  )}
                </tbody>
              </table>
            </div>
            {cab.epsilon_dc_total !== null && (
              <p style={{ marginTop: 12, fontSize: 12.5, color: "var(--encre-2)" }}>
                Chute de tension continue totale : {nombre(cab.epsilon_dc_total * 100, 3)} %.
              </p>
            )}
          </Plaque>
        )}
      </div>
    </>
  );
}
