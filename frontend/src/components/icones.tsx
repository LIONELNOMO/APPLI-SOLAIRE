/**
 * Icônes de l'interface.
 *
 * Trait de 1,6 px, extrémités arrondies : la même main partout. Elles
 * héritent de la couleur du texte et se dimensionnent par CSS.
 */

type Props = { className?: string };

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

/** Soleil — module 1, potentiel solaire. */
export function IconeSoleil({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

/** Prise électrique — module 2, consommation. */
export function IconePrise({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M9 2v6M15 2v6" />
      <path d="M6 8h12v3a6 6 0 0 1-6 6 6 6 0 0 1-6-6V8Z" />
      <path d="M12 17v5" />
    </svg>
  );
}

/** Panneau photovoltaïque — module 3, dimensionnement. */
export function IconePanneau({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M3.5 4.5h17l1.5 11H2l1.5-11Z" />
      <path d="M8.2 4.5 7 15.5M15.8 4.5 17 15.5M2.6 10h18.8" />
      <path d="M12 15.5V21M8.5 21h7" />
    </svg>
  );
}

/** Pylône et réseau — module 4, injection. */
export function IconeReseau({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M12 2 6 21M12 2l6 19M7.6 8h8.8M6.9 14h10.2" />
      <path d="M4 21h16" />
    </svg>
  );
}

/** Liste de contrôle — vérifications. */
export function IconeControle({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M9 5h10M9 12h10M9 19h10" />
      <path d="M3.5 5 4.6 6.2 6.5 4M3.5 12l1.1 1.2L6.5 11M3.5 19l1.1 1.2L6.5 18" />
    </svg>
  );
}

/** Points de suspension — « Plus » sur mobile. */
export function IconePlus({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <circle cx="5" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="19" cy="12" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Document — rapport PDF. */
export function IconeDocument({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M14 2.5H7a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7.5l-5-5Z" />
      <path d="M14 2.5v5h5" />
      <path d="M9 13h6M9 17h4" />
    </svg>
  );
}

/** Lune et soleil — bascule de thème. */
export function IconeTheme({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9Z" />
    </svg>
  );
}

/** Flèche montante — badge « actif ». */
export function IconeFleche({ className }: Props) {
  return (
    <svg {...base} className={className} strokeWidth={2} aria-hidden="true">
      <path d="M7 17 17 7M9 7h8v8" />
    </svg>
  );
}

/** Plus — ajouter. */
export function IconeAjouter({ className }: Props) {
  return (
    <svg {...base} className={className} strokeWidth={1.8} aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

/** Éclair — puissance. */
export function IconeEclair({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M13 2 4.5 13.5H11l-1 8.5 8.5-11.5H12l1-8.5Z" />
    </svg>
  );
}

/** Batterie. */
export function IconeBatterie({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <rect x="2.5" y="7" width="16" height="10" rx="2.5" />
      <path d="M21.5 11v2" />
      <path d="M6 10.5v3M9.5 10.5v3M13 10.5v3" />
    </svg>
  );
}

/** Câble. */
export function IconeCable({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M4 4v6a4 4 0 0 0 4 4h8a4 4 0 0 1 4 4v2" />
      <path d="M2 4h4M18 20h4" />
    </svg>
  );
}

/** Thermomètre — température. */
export function IconeThermometre({ className }: Props) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M14 14.8V4.5a2 2 0 0 0-4 0v10.3a4 4 0 1 0 4 0Z" />
    </svg>
  );
}
