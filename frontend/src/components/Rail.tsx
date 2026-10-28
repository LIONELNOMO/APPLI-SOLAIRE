/**
 * Navigation : rail latéral sur grand écran, barre d'onglets en bas
 * sur mobile. Les deux affichent les mêmes cibles, et le statut de
 * chaque module s'y lit d'un coup d'œil.
 */

import type { ReactNode } from "react";

import type { ResultatsProjet, Statut } from "../api/types";
import {
  IconeControle,
  IconePanneau,
  IconePrise,
  IconeReseau,
  IconeSoleil,
} from "./icones";

export type Onglet =
  | "potentiel"
  | "bilan"
  | "dimensionnement"
  | "injection"
  | "verifications";

interface Cible {
  cle: Onglet;
  libelle: string;
  libelleCourt: string;
  icone: ReactNode;
  champ?: keyof ResultatsProjet;
}

const CIBLES: Cible[] = [
  {
    cle: "potentiel",
    libelle: "Potentiel solaire",
    libelleCourt: "Soleil",
    icone: <IconeSoleil />,
    champ: "potentiel",
  },
  {
    cle: "bilan",
    libelle: "Bilan énergétique",
    libelleCourt: "Bilan",
    icone: <IconePrise />,
    champ: "bilan",
  },
  {
    cle: "dimensionnement",
    libelle: "Dimensionnement",
    libelleCourt: "Matériel",
    icone: <IconePanneau />,
    champ: "pv",
  },
  {
    cle: "injection",
    libelle: "Injection réseau",
    libelleCourt: "Réseau",
    icone: <IconeReseau />,
    champ: "injection",
  },
  {
    cle: "verifications",
    libelle: "Vérifications",
    libelleCourt: "Contrôle",
    icone: <IconeControle />,
  },
];

function statutDuModule(
  resultats: ResultatsProjet | null,
  champ: keyof ResultatsProjet | undefined,
): Statut | undefined {
  if (!champ || !resultats) return undefined;
  const module = resultats[champ] as { statut?: Statut } | undefined;
  return module?.statut;
}

function classePastille(statut: Statut | undefined): string {
  switch (statut) {
    case "ok":
      return "pastille pastille-ok";
    case "avertissement":
      return "pastille pastille-avert";
    case "erreur":
      return "pastille pastille-erreur";
    default:
      return "pastille pastille-attente";
  }
}

function libelleStatut(statut: Statut | undefined): string {
  switch (statut) {
    case "ok":
      return "Conforme";
    case "avertissement":
      return "À examiner";
    case "erreur":
      return "Erreur à corriger";
    default:
      return "Non calculé";
  }
}

function Marque({ taille = 36 }: { taille?: number }) {
  return (
    <svg
      className="signature-glyphe"
      viewBox="0 0 24 24"
      width={taille}
      height={taille}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4.2" fill="currentColor" />
      <g
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        opacity=".6"
      >
        <path d="M12 2.2v2.4M12 19.4v2.4M2.2 12h2.4M19.4 12h2.4M5.1 5.1l1.7 1.7M17.2 17.2l1.7 1.7M18.9 5.1l-1.7 1.7M6.8 17.2l-1.7 1.7" />
      </g>
    </svg>
  );
}

interface Props {
  actif: Onglet;
  resultats: ResultatsProjet | null;
  onNaviguer: (cible: Onglet) => void;
}

/** Rail latéral, visible à partir de 941 px. */
export function Rail({ actif, resultats, onNaviguer }: Props) {
  const compte = {
    erreur: resultats?.messages.filter((m) => m.niveau === "erreur").length ?? 0,
    avertissement:
      resultats?.messages.filter((m) => m.niveau === "avertissement").length ?? 0,
  };

  return (
    <nav className="rail" aria-label="Modules">
      <div className="signature">
        <div className="signature-haut">
          <span style={{ color: "var(--accent)", display: "grid" }}>
            <Marque />
          </span>
          <span className="marque-nom">DimSolaire</span>
        </div>
        <div className="signature-zone">Yaoundé Ouest</div>
      </div>

      <div className="groupe">Étude</div>
      <div className="navigation">
        {CIBLES.slice(0, 4).map(({ cle, libelle, icone, champ }, index) => {
          const statut = statutDuModule(resultats, champ);
          return (
            <button
              key={cle}
              type="button"
              aria-current={actif === cle ? "page" : undefined}
              onClick={() => onNaviguer(cle)}
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              <span className="nav-icone">{icone}</span>
              <span>{libelle}</span>
              <span className={classePastille(statut)} title={libelleStatut(statut)} />
            </button>
          );
        })}
      </div>

      <div className="groupe">Contrôle</div>
      <div className="navigation">
        <button
          type="button"
          aria-current={actif === "verifications" ? "page" : undefined}
          onClick={() => onNaviguer("verifications")}
        >
          <span className="nav-icone">
            <IconeControle />
          </span>
          <span>Vérifications</span>
          {compte.erreur > 0 ? (
            <span className="jeton jeton-erreur">{compte.erreur}</span>
          ) : compte.avertissement > 0 ? (
            <span className="jeton jeton-avert">{compte.avertissement}</span>
          ) : (
            <span />
          )}
        </button>
      </div>

      <div className="rail-fin">
        <div className="moteur-etat">
          <div>
            <span className="temoin" /> Moteur local actif
          </div>
          <div style={{ paddingLeft: 15 }}>
            Hors ligne · version {resultats?.version_moteur ?? "1.0.0"}
          </div>
        </div>
      </div>
    </nav>
  );
}

/** En-tête mobile : la marque seule, la navigation est en bas. */
export function BarreMobile() {
  return (
    <header className="barre-mobile">
      <span style={{ color: "var(--accent)", display: "grid" }}>
        <Marque taille={32} />
      </span>
      <span className="marque-nom" style={{ fontSize: 17 }}>
        DimSolaire
      </span>
      <span
        style={{
          marginLeft: "auto",
          font: "500 12px/1.3 var(--f-txt)",
          color: "var(--encre-3)",
        }}
      >
        Yaoundé Ouest
      </span>
    </header>
  );
}

/** Barre d'onglets fixée en bas, sous 941 px. */
export function BarreOnglets({ actif, resultats, onNaviguer }: Props) {
  return (
    <nav className="barre-onglets" aria-label="Navigation principale">
      {CIBLES.map(({ cle, libelleCourt, icone, champ }) => {
        const statut = statutDuModule(resultats, champ);
        const marque =
          statut === "erreur"
            ? "m-erreur"
            : statut === "avertissement"
              ? "m-avert"
              : null;
        return (
          <button
            key={cle}
            type="button"
            aria-current={actif === cle ? "page" : undefined}
            onClick={() => onNaviguer(cle)}
          >
            <span className="onglet-icone">{icone}</span>
            <span>{libelleCourt}</span>
            {marque && (
              <span
                className={`onglet-marque ${marque}`}
                title={libelleStatut(statut)}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
}
