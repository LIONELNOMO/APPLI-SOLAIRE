/** Composants transverses de l'interface (§10.6 d'ARCHITECTURE.md). */

import { useId, useState, type ReactNode } from "react";

import type { Message, Niveau } from "../api/types";
import { lireNombre, nombre as formaterNombre } from "../utils/format";
import { IconeFleche } from "./icones";

/* ------------------------------------------------------------------ */
/* Saisie numérique                                                    */
/* ------------------------------------------------------------------ */

interface NumberFieldProps {
  label: string;
  valeur: number | null;
  onChange: (valeur: number | null) => void;
  unite?: string;
  unites?: { valeur: string; libelle: string }[];
  uniteChoisie?: string;
  onUniteChange?: (unite: string) => void;
  aide?: string;
  decimales?: number;
  invalide?: boolean;
  placeholder?: string;
}

/**
 * Champ numérique acceptant la virgule et le point.
 *
 * La valeur est reformatée à la perte du focus seulement : reformater à
 * chaque frappe empêcherait de saisir « 4,6 » (le zéro final disparaîtrait).
 */
export function NumberField({
  label,
  valeur,
  onChange,
  unite,
  unites,
  uniteChoisie,
  onUniteChange,
  aide,
  decimales = 2,
  invalide = false,
  placeholder,
}: NumberFieldProps) {
  const identifiant = useId();
  const [saisie, setSaisie] = useState<string | null>(null);

  // La valeur affichée vient de la saisie en cours, ou de l'état du projet.
  // Dériver pendant le rendu, plutôt que resynchroniser dans un effet,
  // évite un rendu en cascade à chaque recalcul.
  const brut =
    saisie ?? (valeur === null ? "" : formaterNombre(valeur, decimales));

  return (
    <div className="champ">
      <label htmlFor={identifiant}>{label}</label>
      <div className={unites || unite ? "paire" : undefined}>
        <input
          id={identifiant}
          type="text"
          inputMode="decimal"
          className="saisie-mono"
          value={brut}
          placeholder={placeholder}
          aria-invalid={invalide || undefined}
          aria-describedby={aide ? `${identifiant}-aide` : undefined}
          onBlur={() => {
            // La saisie est relâchée : l'affichage revient au format fr-FR.
            setSaisie(null);
          }}
          onChange={(evenement) => {
            const texte = evenement.target.value;
            setSaisie(texte);
            onChange(lireNombre(texte));
          }}
        />
        {unites && onUniteChange ? (
          <select
            aria-label={`Unité de ${label.toLowerCase()}`}
            value={uniteChoisie}
            onChange={(evenement) => onUniteChange(evenement.target.value)}
          >
            {unites.map((u) => (
              <option key={u.valeur} value={u.valeur}>
                {u.libelle}
              </option>
            ))}
          </select>
        ) : unite ? (
          <select aria-label="unité" value={unite} disabled>
            <option value={unite}>{unite}</option>
          </select>
        ) : null}
      </div>
      {aide && (
        <span className="aide" id={`${identifiant}-aide`}>
          {aide}
        </span>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Bascule                                                             */
/* ------------------------------------------------------------------ */

interface BasculeProps<T extends string> {
  label: string;
  options: { valeur: T; libelle: string }[];
  choisie: T;
  onChange: (valeur: T) => void;
}

export function Bascule<T extends string>({
  label,
  options,
  choisie,
  onChange,
}: BasculeProps<T>) {
  return (
    <div className="bascule" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.valeur}
          type="button"
          aria-pressed={choisie === option.valeur}
          onClick={() => onChange(option.valeur)}
        >
          {option.libelle}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tuile de résultat                                                   */
/* ------------------------------------------------------------------ */

interface TuileProps {
  cle: string;
  valeur: string;
  unite?: string;
  note?: string;
  important?: boolean;
  icone?: ReactNode;
  badge?: { texte: string; ton?: "ok" | "avert" | "erreur" | "info" };
}

/**
 * Carte de résultat : icône en haut, grande valeur, libellé, note.
 *
 * La valeur est l'élément le plus gros de la carte, en serif : c'est
 * elle que l'œil doit trouver en premier.
 */
export function Tuile({
  cle,
  valeur,
  unite,
  note,
  important,
  icone,
  badge,
}: TuileProps) {
  const tons = {
    ok: { background: "var(--succes-fond)", color: "var(--succes)" },
    avert: { background: "var(--avert-fond)", color: "var(--avert)" },
    erreur: { background: "var(--erreur-fond)", color: "var(--erreur)" },
    info: { background: "var(--info-fond)", color: "var(--info)" },
  } as const;

  return (
    <div className={important ? "cellule cellule-cle" : "cellule"}>
      {badge && (
        <span className="cellule-badge" style={tons[badge.ton ?? "ok"]}>
          <IconeFleche />
          {badge.texte}
        </span>
      )}
      {icone && <div className="cellule-icone">{icone}</div>}
      <div className="cellule-valeur tnum">
        {valeur}
        {unite && <em>{unite}</em>}
      </div>
      <div className="cellule-cle-texte">{cle}</div>
      {note && <div className="cellule-note">{note}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Diagnostic                                                          */
/* ------------------------------------------------------------------ */

const ICONES: Record<Niveau, ReactNode> = {
  erreur: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
      <circle cx="12" cy="12" r="9.2" />
      <path d="M12 7.4v5.4M12 16.3v.2" />
    </svg>
  ),
  avertissement: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
      <path d="M12 3.2 2.3 20.4h19.4L12 3.2zM12 9.4v5.1M12 17.6v.2" />
    </svg>
  ),
  info: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
      <circle cx="12" cy="12" r="9.2" />
      <path d="M12 11v6M12 7.4v.2" />
    </svg>
  ),
};

const CLASSES: Record<Niveau, string> = {
  erreur: "diagnostic diagnostic-erreur",
  avertissement: "diagnostic diagnostic-avert",
  info: "diagnostic diagnostic-info",
};

export function Diagnostic({ message }: { message: Message }) {
  return (
    <div className={CLASSES[message.niveau]}>
      {ICONES[message.niveau]}
      <div>
        <div className="diagnostic-titre">
          {message.titre} <code>{message.code}</code>
        </div>
        <p>{message.message}</p>
        {message.suggestion && (
          <div className="diagnostic-correctif">
            <b>Correctif</b>
            <span>{message.suggestion}</span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Plaque                                                              */
/* ------------------------------------------------------------------ */

interface PlaqueProps {
  titre: string;
  formule?: string;
  sousTitre?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}

export function Plaque({ titre, formule, sousTitre, action, children }: PlaqueProps) {
  return (
    <section className="plaque">
      <header className="plaque-entete">
        <h2>{titre}</h2>
        {formule && <span className="formule-identifiant">{formule}</span>}
        {sousTitre && <span className="sous-titre">{sousTitre}</span>}
        {action && <div style={{ marginLeft: "auto" }}>{action}</div>}
      </header>
      <div className="plaque-corps">{children}</div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* En-tête d'onglet                                                    */
/* ------------------------------------------------------------------ */

interface EnteteProps {
  module: string;
  titre: string;
  accent: string;
  description: string;
  formules?: string;
  actions?: React.ReactNode;
}

export function EnteteOnglet({
  module,
  titre,
  accent,
  description,
  formules,
  actions,
}: EnteteProps) {
  return (
    <div className="entete">
      <div className="entete-rail">
        <span className="etiquette">{module}</span>
        {formules && <span className="jeton jeton-info">{formules}</span>}
      </div>
      <div className="entete-grille">
        <div>
          <h1>
            {titre} <b>{accent}</b>
          </h1>
          <p>{description}</p>
        </div>
        {actions && <div className="actions">{actions}</div>}
      </div>
    </div>
  );
}
