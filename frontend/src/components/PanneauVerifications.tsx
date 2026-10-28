/** Tous les messages du moteur, groupés par niveau puis par module. */

import type { ResultatsProjet } from "../api/types";
import { Diagnostic, EnteteOnglet, Plaque } from "./communs";

const LIBELLES_MODULE: Record<string, string> = {
  potentiel: "Potentiel solaire",
  bilan: "Bilan énergétique",
  production: "Production et puissance crête",
  pv: "Champ photovoltaïque",
  onduleur: "Onduleurs",
  batteries: "Batteries",
  cables: "Câbles",
  injection: "Injection au réseau",
};

const ORDRE_NIVEAU = { erreur: 0, avertissement: 1, info: 2 } as const;

export function PanneauVerifications({
  resultats,
}: {
  resultats: ResultatsProjet | null;
}) {
  const messages = resultats?.messages ?? [];
  const compte = {
    erreur: messages.filter((m) => m.niveau === "erreur").length,
    avertissement: messages.filter((m) => m.niveau === "avertissement").length,
    info: messages.filter((m) => m.niveau === "info").length,
  };

  const parModule = new Map<string, typeof messages>();
  for (const message of messages) {
    const existants = parModule.get(message.module) ?? [];
    existants.push(message);
    parModule.set(message.module, existants);
  }

  return (
    <>
      <EnteteOnglet
        module="Contrôle"
        titre="Vérifications du"
        accent="projet"
        description="Tous les contrôles du moteur, groupés par module. Les erreurs doivent être corrigées avant la mise en œuvre."
      />

      <div className="flux">
        <div className="banc">
          <div className={compte.erreur > 0 ? "cellule cellule-cle" : "cellule"}>
            <div className="cellule-cle-texte">Erreurs</div>
            <div className="cellule-valeur tnum">{compte.erreur}</div>
            <div className="cellule-note">bloquantes</div>
          </div>
          <div className="cellule">
            <div className="cellule-cle-texte">Avertissements</div>
            <div className="cellule-valeur tnum">{compte.avertissement}</div>
            <div className="cellule-note">à examiner</div>
          </div>
          <div className="cellule">
            <div className="cellule-cle-texte">Informations</div>
            <div className="cellule-valeur tnum">{compte.info}</div>
            <div className="cellule-note">pour mémoire</div>
          </div>
          <div className="cellule">
            <div className="cellule-cle-texte">Statut global</div>
            <div className="cellule-valeur" style={{ fontSize: 22 }}>
              {resultats?.statut_global ?? "—"}
            </div>
          </div>
        </div>

        {messages.length === 0 ? (
          <Plaque titre="Aucun message">
            <p style={{ color: "var(--encre-2)", margin: 0 }}>
              Le moteur n'a signalé aucun point d'attention.
            </p>
          </Plaque>
        ) : (
          [...parModule.entries()].map(([module, liste]) => (
            <Plaque
              key={module}
              titre={LIBELLES_MODULE[module] ?? module}
              sousTitre={`${liste.length} message${liste.length > 1 ? "s" : ""}`}
            >
              <div className="diagnostics">
                {[...liste]
                  .sort(
                    (a, b) => ORDRE_NIVEAU[a.niveau] - ORDRE_NIVEAU[b.niveau],
                  )
                  .map((message) => (
                    <Diagnostic key={message.code + message.message} message={message} />
                  ))}
              </div>
            </Plaque>
          ))
        )}
      </div>
    </>
  );
}
