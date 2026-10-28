/**
 * Design tokens de DimSolaire (§10 d'ARCHITECTURE.md).
 *
 * Direction visuelle : instrument de mesure. Les grandeurs dominent,
 * les libellés s'effacent. Un seul accent, l'ambre solaire, distinct des
 * quatre couleurs sémantiques pour qu'un avertissement ne se confonde
 * jamais avec un chiffre mis en avant.
 */

export const palette = {
  clair: {
    fond: "#f7f8f7",
    surface: "#ffffff",
    surfaceCreuse: "#eceeed",
    rail: "#0e1419",
    railGrave: "#222d36",
    encre: "#0e1419",
    encreAtenuee: "#5a6670",
    encreFaible: "#8d979f",
    filet: "#dde0de",
    filetFort: "#c4c9c6",
    accent: "#c2410c",
    accentVif: "#ea580c",
    accentFond: "#fdf0e7",
    accentBord: "#f5c9a8",
    erreur: "#a81d1d",
    erreurFond: "#fbebeb",
    avertissement: "#8a5a00",
    avertissementFond: "#fbf3e4",
    info: "#0f5c6b",
    infoFond: "#e7f3f5",
    succes: "#1a5c3c",
    succesFond: "#e8f3ed",
  },
  sombre: {
    fond: "#11181e",
    surface: "#18212a",
    surfaceCreuse: "#0d1419",
    rail: "#070b0e",
    railGrave: "#1e2831",
    encre: "#e8edf0",
    encreAtenuee: "#9aa7b1",
    encreFaible: "#6b7883",
    filet: "#212c35",
    filetFort: "#2e3c47",
    accent: "#fb923c",
    accentVif: "#fdba74",
    accentFond: "#2a1608",
    accentBord: "#5c3312",
    erreur: "#fca5a5",
    erreurFond: "#2a1111",
    avertissement: "#fcd34d",
    avertissementFond: "#271d06",
    info: "#67d8e8",
    infoFond: "#07222a",
    succes: "#6ee7a8",
    succesFond: "#07231a",
  },
} as const;

export const polices = {
  /** Titres et grandes valeurs. */
  affichage: '"Chivo", "Helvetica Neue", system-ui, sans-serif',
  /** Corps de texte, libellés, boutons. */
  texte: '"Inter", system-ui, sans-serif',
  /** Formules, codes de message, colonnes de chiffres. */
  chasseFixe: '"IBM Plex Mono", ui-monospace, monospace',
} as const;

/** Grille de 4 px. */
export const espacements = [0, 4, 8, 12, 16, 20, 24, 32, 44] as const;

export const rayons = { petit: 3, moyen: 6, grand: 10 } as const;

export const durees = {
  /** Retour tactile immédiat. */
  bref: 120,
  /** Transition courante. */
  normal: 180,
  /** Entrée d'un panneau. */
  long: 320,
} as const;

export const courbes = {
  sortie: "cubic-bezier(0.16, 1, 0.3, 1)",
  ressort: "cubic-bezier(0.34, 1.56, 0.64, 1)",
  douce: "cubic-bezier(0.33, 0, 0.2, 1)",
} as const;

/** Seuils de bascule, en pixels. */
export const seuils = {
  rail: 940,
  colonnes: 820,
  compact: 420,
  minuscule: 360,
} as const;
