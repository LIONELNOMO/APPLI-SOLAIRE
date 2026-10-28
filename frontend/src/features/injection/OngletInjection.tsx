/** Onglet 4 — Injection au réseau (F-26 à F-30). */

import {
  Bascule,
  Diagnostic,
  EnteteOnglet,
  NumberField,
  Plaque,
  Tuile,
} from "../../components/communs";
import { messagesDuModule, useProjet } from "../../store/projet";
import { MOIS_COURTS, entier, nombre, pourcent } from "../../utils/format";

export function OngletInjection({
  onAllerAuDimensionnement,
}: {
  onAllerAuDimensionnement: () => void;
}) {
  const { entree, resultats, modifier } = useProjet();
  if (!entree) return null;

  const inj = resultats?.injection.valeurs ?? null;
  const messages = messagesDuModule(resultats, "injection");
  const bloquant = messages.find((m) => m.code === "INJ-E04");

  if (!inj) {
    return (
      <>
        <EnteteOnglet
          module="Module 04"
          titre="Injection"
          accent="réseau"
          description="Transformateur BT/HTA, câble alternatif, disjoncteur de raccordement et bilan de l'énergie injectée."
          formules="F-26 → F-30"
        />
        <section className="plaque">
          <div className="plaque-corps vide">
            <svg className="vide-glyphe" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
              <path d="M6 42h36M12 42V19l12-11 12 11v23M20 42V30h8v12" />
            </svg>
            <h3>Calcul suspendu</h3>
            <p>
              {bloquant?.message ??
                "L'étude d'injection a besoin des onduleurs des étapes 12 à 14."}
            </p>
            <div style={{ marginTop: 20 }}>
              <button
                type="button"
                className="bouton bouton-primaire"
                onClick={onAllerAuDimensionnement}
              >
                Aller au module 03
              </button>
            </div>
            <p className="vide-note">
              Le moteur calcule tout ce qui peut l'être — principe P3
            </p>
          </div>
        </section>
      </>
    );
  }

  const bilan = inj.bilan_mensuel ?? [];
  const maximum = bilan.length ? Math.max(...bilan.map((b) => b.e_prod)) : 1;

  return (
    <>
      <EnteteOnglet
        module="Module 04"
        titre="Injection"
        accent="réseau"
        description="Transformateur BT/HTA, câble alternatif, disjoncteur de raccordement et bilan de l'énergie injectée."
        formules="F-26 → F-30"
      />

      <div className="flux">
        <div className="banc">
          <Tuile
            cle="Transformateurs"
            valeur={entier(inj.n_tr)}
            unite={`× ${nombre(inj.s_n_kva, 0)} kVA`}
            note={`${nombre(inj.s_installee_kva, 0)} kVA installés`}
          />
          <Tuile
            cle="Énergie injectée"
            valeur={nombre((inj.e_inj_an_kwh ?? 0) / 1000, 0)}
            unite="MWh/an"
            note={inj.taux_injection ? `taux ${pourcent(inj.taux_injection, 2)}` : undefined}
            important
          />
          <Tuile
            cle="Taux de charge"
            valeur={nombre(inj.taux_charge * 100, 1)}
            unite="%"
            note={`max ${nombre(inj.taux_charge_max * 100, 1)} %`}
          />
          <Tuile
            cle="Disjoncteur"
            valeur={nombre(inj.in_disjoncteur_a, 0)}
            unite="A"
            note={inj.cable_ac ? `Iz ${nombre(inj.cable_ac.iz_a, 0)} A` : undefined}
          />
          <Tuile
            cle="Heures équivalentes"
            valeur={nombre(inj.h_eq, 0)}
            unite="h"
            note={inj.facteur_charge ? `FC ${pourcent(inj.facteur_charge, 2)}` : undefined}
          />
        </div>

        <div className="duo">
          <Plaque titre="Transformateur BT/HTA" formule="F-26">
            <div className="flux" style={{ gap: 15 }}>
              <NumberField
                label="Tension HTA du réseau"
                valeur={entree.injection.u_hta_kv}
                decimales={0}
                unite="kV"
                onChange={(valeur) =>
                  modifier((p) => {
                    p.injection.u_hta_kv = valeur ?? 15;
                  })
                }
                aide="Question ouverte Q-06"
              />
              <dl className="paires">
                <div>
                  <dt>Puissance requise</dt>
                  <dd>{nombre(inj.s_requise_kva)} kVA</dd>
                </div>
                <div>
                  <dt>Onduleurs par transformateur</dt>
                  <dd>{inj.n_max_par_tr} au maximum</dd>
                </div>
                <div>
                  <dt>Courant nominal BT</dt>
                  <dd>{nombre(inj.i_n_bt_a, 1)} A</dd>
                </div>
                <div>
                  <dt>Courant BT maximal</dt>
                  <dd>{nombre(inj.i_bt_max_a, 1)} A</dd>
                </div>
                <div>
                  <dt>Courant nominal HTA</dt>
                  <dd>{nombre(inj.i_n_hta_a, 2)} A</dd>
                </div>
                <div>
                  <dt>Pertes P0 / Pk</dt>
                  <dd>{nombre(inj.p0_w, 0)} W / {nombre(inj.pk_w, 0)} W</dd>
                </div>
              </dl>
            </div>
          </Plaque>

          <Plaque titre="Câble AC et disjoncteur" formule="F-27 · F-28">
            <div className="flux" style={{ gap: 15 }}>
              <NumberField
                label="Longueur du câble (aller simple)"
                valeur={entree.injection.cable_ac.longueur_m}
                decimales={0}
                unite="m"
                onChange={(valeur) =>
                  modifier((p) => {
                    p.injection.cable_ac.longueur_m = valeur ?? 20;
                  })
                }
                aide="Plage du cahier des charges : 5 à 50 m"
              />
              <Bascule
                label="Formule de chute de tension"
                options={[
                  { valeur: "cahier", libelle: "Cahier (facteur 2)" },
                  { valeur: "triphasee_exacte", libelle: "Triphasée exacte" },
                ]}
                choisie={entree.injection.cable_ac.formule}
                onChange={(formule) =>
                  modifier((p) => {
                    p.injection.cable_ac.formule = formule;
                  })
                }
              />
              {inj.cable_ac && (
                <dl className="paires">
                  <div>
                    <dt>Section calculée</dt>
                    <dd>{nombre(inj.cable_ac.s_calc_mm2, 2)} mm²</dd>
                  </div>
                  <div>
                    <dt>Section retenue</dt>
                    <dd>
                      {inj.cable_ac.n_conducteurs} × {nombre(inj.cable_ac.section_mm2, 1)} mm² (
                      {inj.cable_ac.critere})
                    </dd>
                  </div>
                  <div>
                    <dt>Coordination</dt>
                    <dd>
                      {nombre(inj.cable_ac.i_a, 1)} ≤ {nombre(inj.in_disjoncteur_a, 0)} ≤{" "}
                      {nombre(inj.cable_ac.iz_a, 0)} A
                    </dd>
                  </div>
                  <div>
                    <dt>Chute réelle</dt>
                    <dd>{nombre(inj.cable_ac.epsilon_reel * 100, 3)} %</dd>
                  </div>
                  <div>
                    <dt>Pertes Joule</dt>
                    <dd>{nombre(inj.cable_ac.p_joule_w, 1)} W</dd>
                  </div>
                </dl>
              )}
            </div>
          </Plaque>
        </div>

        {bilan.length === 12 && (
          <Plaque
            titre="Bilan mensuel de l'injection"
            formule="F-29"
            action={
              <Bascule
                label="Mode d'injection"
                options={[
                  { valeur: "totale", libelle: "Totale" },
                  { valeur: "surplus", libelle: "Surplus" },
                ]}
                choisie={entree.injection.mode}
                onChange={(mode) =>
                  modifier((p) => {
                    p.injection.mode = mode;
                  })
                }
              />
            }
          >
            <div className="histogramme" role="img"
              aria-label={`Énergie injectée mensuelle, de ${nombre(
                Math.min(...bilan.map((b) => b.e_inj)) / 1000,
                0,
              )} à ${nombre(Math.max(...bilan.map((b) => b.e_inj)) / 1000, 0)} MWh.`}>
              {bilan.map((mois) => (
                <div key={mois.mois} className="histogramme-colonne">
                  <div className="histogramme-piste">
                    <div
                      className="histogramme-barre barre-production"
                      style={{ height: `${(mois.e_prod / maximum) * 100}%` }}
                    />
                    <div
                      className="histogramme-barre barre-injectee"
                      style={{ height: `${(mois.e_inj / maximum) * 100}%` }}
                    />
                  </div>
                  <div className="histogramme-mois">{MOIS_COURTS[mois.mois - 1]}</div>
                  <div className="histogramme-valeur tnum">
                    {nombre(mois.e_inj / 1000, 0)}
                  </div>
                </div>
              ))}
            </div>
            <div className="legende">
              <span>
                <i className="pastille-legende production" /> Production
              </span>
              <span>
                <i className="pastille-legende injectee" /> Injectée
              </span>
              <span>Valeurs en MWh</span>
            </div>
          </Plaque>
        )}

        <div className="duo">
          <Plaque titre="Indicateurs" formule="F-30">
            <dl className="paires">
              <div>
                <dt>Énergie injectée annuelle</dt>
                <dd>{nombre((inj.e_inj_an_kwh ?? 0) / 1000, 0)} MWh</dd>
              </div>
              <div>
                <dt>Taux d'injection</dt>
                <dd>{pourcent(inj.taux_injection, 2)}</dd>
              </div>
              <div>
                <dt>Heures équivalentes</dt>
                <dd>{nombre(inj.h_eq, 1)} h</dd>
              </div>
              <div>
                <dt>Facteur de charge</dt>
                <dd>{pourcent(inj.facteur_charge, 2)}</dd>
              </div>
              {inj.couverture_zone !== null && (
                <div>
                  <dt>Couverture équivalente</dt>
                  <dd>{pourcent(inj.couverture_zone, 2)}</dd>
                </div>
              )}
              {inj.part_autoconsommee !== null && (
                <div>
                  <dt>Part autoconsommée</dt>
                  <dd>{pourcent(inj.part_autoconsommee, 2)}</dd>
                </div>
              )}
            </dl>
          </Plaque>

          <Plaque titre="Indicateurs complémentaires">
            <div className="flux" style={{ gap: 15 }}>
              <NumberField
                label="Tarif d'achat"
                valeur={entree.injection.tarif_fcfa_kwh}
                decimales={0}
                unite="FCFA/kWh"
                placeholder="Non renseigné"
                onChange={(valeur) =>
                  modifier((p) => {
                    p.injection.tarif_fcfa_kwh = valeur;
                  })
                }
                aide="Question ouverte Q-09"
              />
              <NumberField
                label="Facteur d'émission du réseau"
                valeur={entree.injection.facteur_co2_kg_kwh}
                unite="kg/kWh"
                placeholder="Non renseigné"
                onChange={(valeur) =>
                  modifier((p) => {
                    p.injection.facteur_co2_kg_kwh = valeur;
                  })
                }
              />
              {(inj.recettes_fcfa_an !== null || inj.co2_evite_t_an !== null) && (
                <dl className="paires">
                  {inj.recettes_fcfa_an !== null && (
                    <div>
                      <dt>Recettes annuelles</dt>
                      <dd>{nombre(inj.recettes_fcfa_an / 1e6, 1)} M FCFA</dd>
                    </div>
                  )}
                  {inj.co2_evite_t_an !== null && (
                    <div>
                      <dt>CO₂ évité</dt>
                      <dd>{nombre(inj.co2_evite_t_an, 0)} t/an</dd>
                    </div>
                  )}
                </dl>
              )}
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
