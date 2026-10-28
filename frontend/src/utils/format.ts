/**
 * Formatage et lecture des nombres en français (§2.3 du cahier des charges).
 *
 * Le moteur formate déjà les nombres contenus dans ses messages ; ces
 * fonctions servent à l'affichage des valeurs calculées.
 */

const FR = "fr-FR";

/** Formate un nombre : 1 687,40. */
export function nombre(valeur: number | null | undefined, decimales = 2): string {
  if (valeur === null || valeur === undefined || !Number.isFinite(valeur)) {
    return "—";
  }
  return valeur.toLocaleString(FR, {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  });
}

/** Formate un comptage, sans décimale : 1 582. */
export function entier(valeur: number | null | undefined): string {
  return nombre(valeur, 0);
}

/** Formate un ratio sans unité en pourcentage : 0,978 → « 97,8 % ». */
export function pourcent(
  ratio: number | null | undefined,
  decimales = 1,
): string {
  if (ratio === null || ratio === undefined || !Number.isFinite(ratio)) {
    return "—";
  }
  return `${nombre(ratio * 100, decimales)} %`;
}

export interface ValeurEchelle {
  valeur: number;
  unite: string;
  texte: string;
}

/** Met une énergie en Wh à l'échelle : Wh, kWh, MWh ou GWh. */
export function energie(wh: number | null | undefined, decimales = 2): ValeurEchelle {
  if (wh === null || wh === undefined || !Number.isFinite(wh)) {
    return { valeur: 0, unite: "Wh", texte: "—" };
  }
  const paliers: [number, number, string][] = [
    [1e9, 1e9, "GWh"],
    [1e6, 1e6, "MWh"],
    [1e3, 1e3, "kWh"],
  ];
  for (const [seuil, facteur, unite] of paliers) {
    if (Math.abs(wh) >= seuil) {
      const valeur = wh / facteur;
      return { valeur, unite, texte: `${nombre(valeur, decimales)} ${unite}` };
    }
  }
  return { valeur: wh, unite: "Wh", texte: `${nombre(wh, decimales)} Wh` };
}

/** Met une puissance en W à l'échelle : W, kW ou MW. */
export function puissance(w: number | null | undefined, decimales = 2): ValeurEchelle {
  if (w === null || w === undefined || !Number.isFinite(w)) {
    return { valeur: 0, unite: "W", texte: "—" };
  }
  if (Math.abs(w) >= 1e6) {
    const valeur = w / 1e6;
    return { valeur, unite: "MW", texte: `${nombre(valeur, decimales)} MW` };
  }
  if (Math.abs(w) >= 1e3) {
    const valeur = w / 1e3;
    return { valeur, unite: "kW", texte: `${nombre(valeur, decimales)} kW` };
  }
  return { valeur: w, unite: "W", texte: `${nombre(w, decimales)} W` };
}

/** Met une puissance crête à l'échelle : kWc ou MWc (seuil 1 000 kWc). */
export function crete(kwc: number | null | undefined, decimales = 2): ValeurEchelle {
  if (kwc === null || kwc === undefined || !Number.isFinite(kwc)) {
    return { valeur: 0, unite: "kWc", texte: "—" };
  }
  if (Math.abs(kwc) >= 1000) {
    const valeur = kwc / 1000;
    return { valeur, unite: "MWc", texte: `${nombre(valeur, decimales)} MWc` };
  }
  return { valeur: kwc, unite: "kWc", texte: `${nombre(kwc, decimales)} kWc` };
}

/**
 * Lit un nombre saisi avec la virgule ou le point.
 *
 * Accepte « 192,625 », « 192.625 », « 1 687,40 » et l'espace insécable
 * fine que produit `toLocaleString`.
 */
export function lireNombre(texte: string): number | null {
  const nettoye = texte
    .trim()
    .replace(/ /g, "")
    .replace(/ /g, "")
    .replace(/\s/g, "")
    .replace(",", ".");
  if (nettoye === "") return null;
  const valeur = Number(nettoye);
  return Number.isFinite(valeur) ? valeur : null;
}

export const MOIS_COURTS = [
  "JAN", "FÉV", "MAR", "AVR", "MAI", "JUN",
  "JUL", "AOÛ", "SEP", "OCT", "NOV", "DÉC",
] as const;

export const MOIS_LONGS = [
  "janvier", "février", "mars", "avril", "mai", "juin",
  "juillet", "août", "septembre", "octobre", "novembre", "décembre",
] as const;
