/**
 * Écran de démarrage.
 *
 * En version PC, le moteur de calcul met une à cinq secondes à répondre.
 * Au-delà de 30 secondes, l'interface explique l'échec et donne le chemin
 * du journal, plutôt que de rester muette.
 */

interface Props {
  etat: "attente" | "echec";
  journal?: string;
  erreur?: string | null;
  onReessayer: () => void;
}

export function Demarrage({ etat, journal, erreur, onReessayer }: Props) {
  return (
    <div className="demarrage">
      <div className="demarrage-contenu">
        <svg className="demarrage-glyphe" viewBox="0 0 28 28" aria-hidden="true">
          <circle className="disque" cx="14" cy="14" r="5" fill="#ea580c" />
          <g className="rayons-a" stroke="#ea580c" strokeWidth="1.9" strokeLinecap="round" opacity=".55">
            <path d="M14 1.5v3.8M14 22.7v3.8M1.5 14h3.8M22.7 14h3.8" />
          </g>
          <g className="rayons-b" stroke="#ea580c" strokeWidth="1.6" strokeLinecap="round" opacity=".3">
            <path d="M5.2 5.2l2.7 2.7M20.1 20.1l2.7 2.7M22.8 5.2l-2.7 2.7M7.9 20.1l-2.7 2.7" />
          </g>
        </svg>

        <h1 className="demarrage-nom">DimSolaire</h1>
        <p className="demarrage-accroche">
          Dimensionnement solaire et injection au réseau
        </p>

        {etat === "attente" ? (
          <div className="demarrage-attente" role="status">
            <span>Démarrage du moteur de calcul…</span>
            <div className="barre-progres">
              <i />
            </div>
          </div>
        ) : (
          <div className="demarrage-echec" role="alert">
            <h2>Le moteur de calcul n'a pas pu démarrer</h2>
            <p>
              {erreur ??
                "Aucune réponse du moteur après 30 secondes."}
            </p>
            {journal && (
              <p className="demarrage-journal">
                Journal : <code>{journal}</code>
              </p>
            )}
            <button type="button" className="bouton bouton-primaire" onClick={onReessayer}>
              Réessayer
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
