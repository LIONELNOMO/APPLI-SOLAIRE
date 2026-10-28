/**
 * État du projet courant (Zustand).
 *
 * Chaque modification déclenche un recalcul après 300 ms sans saisie.
 * Seule la dernière réponse compte : une requête plus ancienne qui
 * arriverait en retard est ignorée.
 */

import { create } from "zustand";

import { apiGet, apiPost } from "../api/client";
import type { ProjetEntree, ResultatsProjet } from "../api/types";

const DELAI_RECALCUL_MS = 300;

interface EtatProjet {
  entree: ProjetEntree | null;
  resultats: ResultatsProjet | null;
  chargement: boolean;
  calculEnCours: boolean;
  erreur: string | null;
  /** Identifiant du projet enregistré, nul tant qu'il ne l'est pas. */
  identifiant: string | null;

  initialiser: () => Promise<void>;
  modifier: (transformation: (entree: ProjetEntree) => void) => void;
  recalculer: () => Promise<void>;
  remplacer: (entree: ProjetEntree, identifiant?: string | null) => void;
}

let minuterie: ReturnType<typeof setTimeout> | null = null;
let generation = 0;

export const useProjet = create<EtatProjet>((set, get) => ({
  entree: null,
  resultats: null,
  chargement: true,
  calculEnCours: false,
  erreur: null,
  identifiant: null,

  async initialiser() {
    set({ chargement: true, erreur: null });
    try {
      const entree = await apiGet<ProjetEntree>("/projets/defaut");
      set({ entree, chargement: false });
      await get().recalculer();
    } catch (erreur) {
      set({
        chargement: false,
        erreur:
          erreur instanceof Error
            ? erreur.message
            : "Le moteur de calcul est injoignable",
      });
    }
  },

  modifier(transformation) {
    const actuelle = get().entree;
    if (!actuelle) return;

    // Copie en profondeur : l'état précédent n'est jamais muté.
    const suivante = structuredClone(actuelle);
    transformation(suivante);
    set({ entree: suivante });

    if (minuterie) clearTimeout(minuterie);
    minuterie = setTimeout(() => {
      void get().recalculer();
    }, DELAI_RECALCUL_MS);
  },

  async recalculer() {
    const entree = get().entree;
    if (!entree) return;

    const mienne = ++generation;
    set({ calculEnCours: true });
    try {
      const resultats = await apiPost<ResultatsProjet>("/calcul", entree);
      // Une réponse dépassée ne doit pas écraser une plus récente.
      if (mienne === generation) {
        set({ resultats, calculEnCours: false, erreur: null });
      }
    } catch (erreur) {
      if (mienne === generation) {
        set({
          calculEnCours: false,
          erreur: erreur instanceof Error ? erreur.message : "Calcul en échec",
        });
      }
    }
  },

  remplacer(entree, identifiant = null) {
    set({ entree, identifiant });
    void get().recalculer();
  },
}));

/** Messages d'un module donné, pour l'affichage par onglet. */
export function messagesDuModule(
  resultats: ResultatsProjet | null,
  module: string,
) {
  return resultats?.messages.filter((m) => m.module === module) ?? [];
}
