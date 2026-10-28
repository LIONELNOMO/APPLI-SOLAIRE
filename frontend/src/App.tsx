/**
 * Coquille de l'application.
 *
 * Deux dispositions selon la largeur : rail latéral à partir de 941 px,
 * barre d'onglets en bas en dessous. En version PC, l'interface attend
 * que le moteur de calcul réponde avant d'afficher quoi que ce soit.
 */

import { useEffect, useState } from "react";

import { attendreApi, cheminJournal } from "./api/client";
import { Demarrage } from "./components/Demarrage";
import { BarreMobile, BarreOnglets, Rail, type Onglet } from "./components/Rail";
import { PanneauVerifications } from "./components/PanneauVerifications";
import { OngletPotentiel } from "./features/potentiel/OngletPotentiel";
import { OngletBilan } from "./features/bilan/OngletBilan";
import { OngletDimensionnement } from "./features/dimensionnement/OngletDimensionnement";
import { OngletInjection } from "./features/injection/OngletInjection";
import { useProjet } from "./store/projet";
import "./App.css";

type EtatDemarrage = "attente" | "pret" | "echec";

export default function App() {
  const [demarrage, setDemarrage] = useState<EtatDemarrage>("attente");
  const [journal, setJournal] = useState<string | undefined>();
  const [onglet, setOnglet] = useState<Onglet>("potentiel");

  const { entree, resultats, erreur, initialiser } = useProjet();

  useEffect(() => {
    let annule = false;

    async function demarrer() {
      const pret = await attendreApi();
      if (annule) return;
      if (pret) {
        setDemarrage("pret");
        await initialiser();
      } else {
        setJournal(await cheminJournal());
        setDemarrage("echec");
      }
    }

    void demarrer();
    return () => {
      annule = true;
    };
  }, [initialiser]);

  function reessayer() {
    setDemarrage("attente");
    void (async () => {
      const pret = await attendreApi();
      if (pret) {
        setDemarrage("pret");
        await initialiser();
      } else {
        setDemarrage("echec");
      }
    })();
  }

  function naviguer(cible: Onglet) {
    setOnglet(cible);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (demarrage !== "pret" || !entree) {
    return (
      <Demarrage
        etat={demarrage === "echec" ? "echec" : "attente"}
        journal={journal}
        erreur={erreur}
        onReessayer={reessayer}
      />
    );
  }

  return (
    <div className="coque">
      <Rail actif={onglet} resultats={resultats} onNaviguer={naviguer} />
      <BarreMobile />

      <main className="travail">
        <div className="baie">
          {onglet === "potentiel" && <OngletPotentiel />}
          {onglet === "bilan" && <OngletBilan />}
          {onglet === "dimensionnement" && <OngletDimensionnement />}
          {onglet === "injection" && (
            <OngletInjection
              onAllerAuDimensionnement={() => naviguer("dimensionnement")}
            />
          )}
          {onglet === "verifications" && (
            <PanneauVerifications resultats={resultats} />
          )}
        </div>
      </main>

      <BarreOnglets actif={onglet} resultats={resultats} onNaviguer={naviguer} />
    </div>
  );
}
