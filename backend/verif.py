"""Relevé des cas de référence, pour comparaison manuelle avec le cahier."""

from app.engine.pipeline import calculer_projet
from tests.engine.cas import projet_reference


def ligne(libelle: str, obtenu: float, attendu: float, unite: str = "") -> None:
    ecart = abs(obtenu - attendu) / attendu * 100 if attendu else 0.0
    marque = "OK " if ecart < 0.01 else "ECART"
    print(f"  {marque} {libelle:<26} {obtenu:>14.4f}  attendu {attendu:>13.4f} {unite}")


resultats = calculer_projet(projet_reference("R-10"))

print(f"\nStatut global : {resultats.statut_global}")
for nom in ("potentiel", "bilan", "production", "pv", "onduleur", "batteries", "cables", "injection"):
    print(f"  {nom:<12} {getattr(resultats, nom).statut}")

ond = resultats.onduleur.valeurs
if ond:
    print("\n=== R-05 onduleurs ===")
    ligne("N_P", ond.n_p, 8)
    ligne("N_E", ond.n_e, 6)
    ligne("N_ond", ond.n_ond, 8)
    ligne("ratio global", ond.ratio_dc_ac, 1.0876, "")
    ligne("n_ond_max", ond.n_ond_max, 15)
    ligne("n_mppt_max", ond.n_mppt_max, 2)
    ligne("I_mppt", ond.i_mppt_a, 26.26, "A")
    ligne("I_cc_mppt", ond.i_cc_mppt_a, 27.94, "A")
    ligne("P_DC_ond", ond.p_dc_ond_kwc, 115.5, "kWc")
    ligne("ratio_ond", ond.ratio_ond, 1.155)
    ligne("I_DC_ond", ond.i_dc_ond_a, 196.95, "A")
    ligne("P_racc_max", ond.p_racc_max_kwc, 154.0, "kWc")
    ligne("Iac", ond.iac_a, 160.375075, "A")
    ligne("Iac_total", ond.iac_total_a, 1283.0006, "A")
    ligne("entrees_libres", ond.entrees_libres, 47)
    ligne("ns_min", ond.ns_min, 6)
    ligne("ns_max", ond.ns_max, 14)

bat = resultats.batteries.valeurs
if bat:
    print("\n=== R-06 batteries ===")
    ligne("tension recommandee", bat.tension_recommandee_v, 24, "V")
    ligne("E_bat", bat.e_bat_wh, 4111.8421, "Wh")
    ligne("Ns", bat.ns, 2)
    ligne("N_min", bat.n_min, 4)
    ligne("Np", bat.np, 2)
    ligne("N_total", bat.n_total, 4)
    ligne("U_parc", bat.u_parc_v, 25.6, "V")
    ligne("I_parc", bat.i_parc_a, 100.0, "A")
    ligne("C_parc", bat.c_parc_ah, 200.0, "Ah")
    ligne("E_inst", bat.e_inst_wh, 5120.0, "Wh")
    ligne("E_util", bat.e_util_wh, 4096.0, "Wh")
    ligne("autonomie", bat.autonomie_j, 1.2452, "j")
    ligne("I_dech", bat.i_dech_a, 43.7418, "A")
    ligne("duree_vie", bat.duree_vie_ans, 8.2192, "ans")
    ligne("N_zone", bat.n_total_zone or 0, 4000)

cab = resultats.cables.valeurs
if cab:
    print("\n=== R-07 cables DC ===")
    for nom, attendu_s, attendu_eps, attendu_pj in (
        ("dc_principal", 50, 0.006043, 698.2),
        ("dc_chaine", 4, 0.002015, 15.5),
        ("dc_batteries", 35, 0.008036, 20.6),
    ):
        c = getattr(cab, nom)
        if c is None:
            print(f"  ABSENT {nom}")
            continue
        print(f"  {nom}: {c.n_conducteurs} x {c.section_mm2:g} mm2 ({c.critere})"
              f"  attendu {attendu_s:g} mm2")
        ligne(f"  {nom} S_calc", c.s_calc_mm2, c.s_calc_mm2)
        ligne(f"  {nom} eps", c.epsilon_reel, attendu_eps)
        ligne(f"  {nom} I_B", c.i_b_a, c.i_b_a, "A")
        ligne(f"  {nom} P_J", c.p_joule_w, attendu_pj, "W")
    if cab.epsilon_dc_total:
        ligne("eps DC total", cab.epsilon_dc_total, 0.008058)

inj = resultats.injection.valeurs
if inj:
    print("\n=== R-08/09/10 injection ===")
    ligne("S_ond", ond.s_ond_kva if ond else 0, 111.1111, "kVA")
    ligne("S_requise", inj.s_requise_kva, 888.8889, "kVA")
    ligne("n_max_par_tr", inj.n_max_par_tr, 3)
    ligne("n_tr", inj.n_tr, 3)
    ligne("S_n", inj.s_n_kva, 400.0, "kVA")
    ligne("S_installee", inj.s_installee_kva, 1200.0, "kVA")
    ligne("taux_charge_max", inj.taux_charge_max, 0.8333)
    ligne("taux_charge", inj.taux_charge, 0.7407)
    ligne("I_n_BT", inj.i_n_bt_a, 577.3503, "A")
    ligne("I_BT_max", inj.i_bt_max_a, 481.1252, "A")
    ligne("I_n_HTA", inj.i_n_hta_a, 15.3960, "A")
    ligne("P0", inj.p0_w, 430.0, "W")
    ligne("Pk", inj.pk_w, 4600.0, "W")
    ligne("In disjoncteur", inj.in_disjoncteur_a or 0, 250.0, "A")
    if inj.cable_ac:
        c = inj.cable_ac
        print(f"  cable AC: {c.n_conducteurs} x {c.section_mm2:g} mm2 ({c.critere})"
              f"  attendu 95 mm2")
        ligne("  AC S_calc", c.s_calc_mm2, 43.3013)
        ligne("  AC eps", c.epsilon_reel, 0.004558)
        ligne("  AC P_J", c.p_joule_w, 438.60, "W")
    if inj.e_inj_an_kwh:
        prod = resultats.production.valeurs
        if prod and prod.prod_installee:
            ligne("E_prod an", prod.prod_installee.an_kwh, 1101151.79, "kWh")
        ligne("E_inj an", inj.e_inj_an_kwh, 1074645.06, "kWh")
        ligne("taux injection", inj.taux_injection or 0, 0.97593)
        ligne("h_eq", inj.h_eq or 0, 1343.3063, "h")
        ligne("facteur charge", inj.facteur_charge or 0, 0.153346)
        ligne("couverture zone", inj.couverture_zone or 0, 0.981411)

print("\n=== Messages ===")
for m in resultats.messages:
    print(f"  [{m.niveau.value[:4]}] {m.code}: {m.message[:92]}")
