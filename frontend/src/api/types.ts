/**
 * Types de l'API.
 *
 * À remplacer par la génération automatique depuis l'OpenAPI dès que
 * `openapi-typescript` sera compatible avec TypeScript 6 :
 *   npx openapi-typescript http://127.0.0.1:8000/openapi.json -o src/api/schema.d.ts
 */

export type Niveau = "erreur" | "avertissement" | "info";
export type Statut = "ok" | "avertissement" | "erreur" | "non_calcule";
export type Mode = "auto" | "manuel";

export interface Message {
  code: string;
  niveau: Niveau;
  module: string;
  titre: string;
  message: string;
  suggestion?: string | null;
  valeur?: number | null;
  limite?: number | null;
  unite?: string | null;
  champs: string[];
}

export interface Panneau {
  id: string;
  nom: string;
  fabricant: string;
  technologie: string;
  pmax: number;
  vmp: number;
  voc: number;
  imp: number;
  isc: number;
  coef_voc: number;
  coef_vmp: number;
  coef_pmax: number;
  noct: number;
  vsys_max: number;
  source: "systeme" | "utilisateur";
}

export interface Onduleur {
  id: string;
  nom: string;
  fabricant: string;
  pnom_ac: number;
  vmppt_min: number;
  vmppt_max: number;
  vabs_max: number;
  i_max_per_mppt: number;
  nb_mppt: number;
  strings_per_mppt: number;
  u_ac: number;
  phases: 1 | 3;
  isc_max_per_mppt: number | null;
  ratio_dc_ac_max_fab: number;
  source: "systeme" | "utilisateur";
}

export interface Batterie {
  id: string;
  nom: string;
  fabricant: string;
  technologie: "lithium" | "plomb";
  u_nom: number;
  capacite_ah: number;
  dod_recommandee: number;
  dod_max: number;
  cycles: number;
  i_nom: number;
  rendement: number;
  u_charge_max: number;
  u_decharge_min: number;
  ns_max: number;
  np_max: number | null;
  source: "systeme" | "utilisateur";
}

export interface LigneEquipement {
  actif: boolean;
  nom: string;
  categorie: string;
  puissance_w: number;
  quantite: number;
  heures_j: number;
  ks: number;
  ref_bibliotheque?: string | null;
}

export interface ProfilAbonnes {
  id: string;
  nom: string;
  nb_abonnes: number;
  lignes: LigneEquipement[];
}

export interface ProjetEntree {
  meta: {
    nom: string;
    zone: string;
    auteur: string;
    notes: string;
    version_schema: number;
  };
  potentiel: {
    ghi_valeur: number;
    ghi_unite: "w_m2_moy24h" | "kwh_m2_j" | "kwh_m2_an";
    profil_mensuel_kwh_m2_j: number[] | null;
    source_ghi: string;
    surface_valeur: number | null;
    surface_unite: "m2" | "ha" | "km2";
    taux_occupation: number;
    rendement_module: number;
  };
  bilan: { profils: ProfilAbonnes[] };
  production: {
    taux_couverture: number;
    performance_ratio: number;
    critere_ir: "moyenne_annuelle" | "mois_defavorable";
    mode_pc: "calculee" | "imposee";
    pc_imposee_kwc: number | null;
    tension_systeme_v: number;
  };
  pv: {
    fiche: Panneau | null;
    mode_config: Mode;
    tension_reference_ns: "vmp" | "voc" | "voc_froid";
    ns_manuel: number | null;
    np_manuel: number | null;
    t_amb_min_c: number;
    t_amb_max_c: number;
    g_ref_w_m2: number;
  };
  onduleur: {
    fiche: Onduleur | null;
    mode_nombre: Mode;
    nb_manuel: number | null;
    ratio_dc_ac_max: number;
    limiter_courant_mppt: boolean;
    cos_phi: number;
  };
  batteries: {
    actif: boolean;
    fiche: Batterie | null;
    base_energie: "abonne" | "zone" | "personnalisee";
    profil_id: string | null;
    energie_perso_kwh_j: number | null;
    puissance_perso_w: number | null;
    part_stockee: number;
    jours_autonomie: number;
    dod: number | null;
    rendement_batterie: number | null;
    rendement_onduleur: number;
    marge: number;
    mode_tension: Mode;
    tension_parc_v: number | null;
    tension_max_v: number;
    u_conv_min_v: number | null;
    u_conv_max_v: number | null;
    mode_config: Mode;
    ns_manuel: number | null;
    np_manuel: number | null;
  };
  cables: {
    rho_mode: "cahier" | "service" | "personnalise";
    rho_perso_cu: number | null;
    rho_perso_al: number | null;
    dc_principal: CableEntree;
    dc_chaine: CableEntree;
    dc_batteries: CableEntree;
  };
  injection: {
    transfo_mode: Mode;
    transfo_s_kva: number | null;
    transfo_marge: number;
    u_hta_kv: number;
    p0_w: number | null;
    pk_w: number | null;
    cable_ac: CableEntree & { formule: "cahier" | "triphasee_exacte" };
    k_disjoncteur: number;
    mode: "totale" | "surplus";
    taux_autoconsommation: number;
    pertes_ac_incluses_pr: boolean;
    tarif_fcfa_kwh: number | null;
    facteur_co2_kg_kwh: number | null;
  };
}

export interface CableEntree {
  materiau: "cuivre" | "aluminium";
  longueur_m: number;
  epsilon: number;
  k_correction: number;
}

export interface PotentielValeurs {
  h_kwh_m2_j: number;
  h_an_kwh_m2_an: number;
  g_moy_w_m2: number;
  h_mensuel_kwh_m2_j: number[];
  h_min_kwh_m2_j: number;
  mois_defavorable: number;
  surface_m2: number | null;
  e_pot_j_kwh: number | null;
  e_pot_mensuel_kwh: number[] | null;
  e_pot_an_kwh: number | null;
  pc_max_surface_kwc: number | null;
  e_tech_an_kwh: number | null;
}

export interface BilanValeurs {
  profils: {
    id: string;
    nom: string;
    nb_abonnes: number;
    e_cons_wh_j: number;
    p_inst_w: number;
    p_app_w: number;
    e_profil_zone_wh_j: number;
    lignes: { nom: string; categorie: string; e_wh_j: number; part_pct: number }[];
  }[];
  e_zone_wh_j: number;
  e_zone_mensuel_kwh: number[];
  e_zone_an_kwh: number;
  p_inst_zone_w: number;
  p_app_zone_w: number;
  repartition_categories: { categorie: string; e_wh_j: number; part_pct: number }[];
}

export interface ProductionSerie {
  mensuel_kwh: number[];
  an_kwh: number;
  j_kwh: number;
  y_kwh_kwc: number;
}

export interface ProductionValeurs {
  ir_kwh_m2_j: number;
  e_cible_kwh_j: number;
  pc_calculee_kwc: number | null;
  pc_retenue_kwc: number;
  prod_theorique: ProductionSerie | null;
  prod_installee: ProductionSerie | null;
  taux_couverture_effectif: number | null;
}

export interface PvValeurs {
  n_min: number;
  ns: number;
  np: number;
  n_total: number;
  pc_installee_kwc: number;
  u_dc_v: number;
  i_dc_a: number;
  i_cc_dc_a: number;
  u_co_v: number;
  t_cell_min_c: number;
  t_cell_max_c: number;
  voc_max_v: number;
  vmp_min_v: number;
  vmp_max_v: number;
  u_ref_v: number;
  taux_utilisation_us: number;
}

export interface OnduleurValeurs {
  n_p: number;
  n_e: number;
  n_cap: number;
  n_ond: number;
  repartition: { chaines: number; nombre: number }[];
  n_ond_max: number;
  n_mppt_max: number;
  ratio_dc_ac: number;
  p_dc_ond_kwc: number;
  ratio_ond: number;
  p_racc_max_kwc: number;
  i_dc_ond_a: number;
  i_mppt_a: number;
  i_cc_mppt_a: number;
  ns_min: number;
  ns_max: number;
  entrees_libres: number;
  iac_a: number;
  iac_total_a: number;
  s_ond_kva: number;
  p_ac_total_kw: number;
  s_ac_total_kva: number;
}

export interface BatteriesValeurs {
  e_base_wh_j: number;
  p_base_w: number;
  tension_recommandee_v: number;
  u_parc_visee_v: number;
  e_bat_wh: number;
  c_bat_ah: number;
  ns: number;
  n_min: number;
  np: number;
  n_total: number;
  u_parc_v: number;
  i_parc_a: number;
  c_parc_ah: number;
  e_inst_wh: number;
  e_util_wh: number;
  autonomie_j: number;
  i_dech_a: number;
  u_parc_min_v: number;
  u_parc_max_v: number;
  duree_vie_ans: number;
  n_total_zone: number | null;
}

export interface CableValeurs {
  nom: string;
  i_a: number;
  u_v: number;
  s_calc_mm2: number;
  n_conducteurs: number;
  section_mm2: number;
  critere: "chute" | "echauffement" | "minimum";
  i_b_a: number;
  iz_a: number;
  epsilon_reel: number;
  delta_u_v: number;
  p_joule_w: number;
}

export interface CablesValeurs {
  dc_principal: CableValeurs | null;
  dc_chaine: CableValeurs | null;
  dc_batteries: CableValeurs | null;
  epsilon_dc_total: number | null;
  i_dc_champ_a: number | null;
}

export interface InjectionValeurs {
  s_requise_kva: number;
  n_max_par_tr: number;
  n_tr: number;
  repartition_tr: { chaines: number; nombre: number }[];
  s_n_kva: number;
  s_installee_kva: number;
  taux_charge_max: number;
  taux_charge: number;
  i_n_bt_a: number;
  i_bt_max_a: number;
  i_n_hta_a: number;
  p0_w: number;
  pk_w: number;
  cable_ac: CableValeurs | null;
  in_disjoncteur_a: number | null;
  bilan_mensuel:
    | {
        mois: number;
        e_prod: number;
        e_cable_ac: number;
        e_auto: number;
        e_tr: number;
        e_p0: number;
        e_pk: number;
        e_inj: number;
      }[]
    | null;
  e_inj_an_kwh: number | null;
  taux_injection: number | null;
  h_eq: number | null;
  facteur_charge: number | null;
  couverture_zone: number | null;
  part_autoconsommee: number | null;
  recettes_fcfa_an: number | null;
  co2_evite_t_an: number | null;
}

export interface SortieModule<T> {
  statut: Statut;
  valeurs: T | null;
}

export interface ResultatsProjet {
  version_moteur: string;
  horodatage: string;
  statut_global: Statut;
  messages: Message[];
  potentiel: SortieModule<PotentielValeurs>;
  bilan: SortieModule<BilanValeurs>;
  production: SortieModule<ProductionValeurs>;
  pv: SortieModule<PvValeurs>;
  onduleur: SortieModule<OnduleurValeurs>;
  batteries: SortieModule<BatteriesValeurs>;
  cables: SortieModule<CablesValeurs>;
  injection: SortieModule<InjectionValeurs>;
}

export interface Proposition {
  fiche: Record<string, unknown>;
  apercu: Record<string, number | null>;
  statut: "ok" | "avertissement" | "erreur";
  motif: string | null;
}

export interface ResumeProjet {
  id: string;
  nom: string;
  zone: string;
  statut_global: Statut | null;
  pc_installee_kwc: number | null;
  n_panneaux: number | null;
  cree_le: string;
  modifie_le: string;
}
