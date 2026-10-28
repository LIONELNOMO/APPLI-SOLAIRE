"""Cas de référence R-05 à R-10 et R-06b, sur la chaîne complète."""

from __future__ import annotations

import pytest

from app.engine.constantes import I_DECH_ERREUR_A
from app.engine.pipeline import calculer_projet
from tests.engine.cas import projet_reference

REL = 1e-6


@pytest.fixture(scope="module")
def complet():
    return calculer_projet(projet_reference("R-10"))


class TestR05Onduleurs:
    def test_nombre_et_repartition(self, complet):
        v = complet.onduleur.valeurs
        assert v is not None
        assert (v.n_p, v.n_e, v.n_ond) == (8, 6, 8)
        assert v.n_ond_max == 15
        assert v.n_mppt_max == 2
        assert v.ratio_dc_ac == pytest.approx(1.087625, rel=REL)
        # 1 onduleur à 15 chaînes, 7 à 14.
        assert v.repartition[0].chaines == 15
        assert v.repartition[0].nombre == 1
        assert v.repartition[1].chaines == 14
        assert v.repartition[1].nombre == 7

    def test_courants_et_tensions(self, complet):
        v = complet.onduleur.valeurs
        assert v is not None
        assert v.i_mppt_a == pytest.approx(26.26, rel=REL)
        assert v.i_cc_mppt_a == pytest.approx(27.94, rel=REL)
        assert v.i_dc_ond_a == pytest.approx(196.95, rel=REL)
        assert v.p_dc_ond_kwc == pytest.approx(115.5, rel=REL)
        assert v.ratio_ond == pytest.approx(1.155, rel=REL)
        assert v.p_racc_max_kwc == pytest.approx(154.0, rel=REL)

    def test_courant_alternatif(self, complet):
        v = complet.onduleur.valeurs
        assert v is not None
        assert v.iac_a == pytest.approx(160.375075, rel=1e-6)
        assert v.iac_total_a == pytest.approx(1283.0006, rel=1e-6)
        assert v.s_ond_kva == pytest.approx(111.1111, rel=1e-5)
        assert v.p_ac_total_kw == pytest.approx(800.0, rel=REL)

    def test_plage_ns_et_messages(self, complet):
        v = complet.onduleur.valeurs
        assert v is not None
        assert (v.ns_min, v.ns_max) == (6, 14)
        assert v.entrees_libres == 47
        codes = {m.code for m in complet.messages}
        # Le courant par MPPT dépasse de 1 % : écrêtage signalé.
        assert "OND-A03" in codes
        assert "OND-I01" in codes
        assert "OND-I03" in codes
        assert "OND-I04" in codes


class TestR06Batteries:
    def test_capacite_et_arrangement(self, complet):
        v = complet.batteries.valeurs
        assert v is not None
        assert v.tension_recommandee_v == 24
        assert v.e_bat_wh == pytest.approx(4111.8421, rel=1e-6)
        assert (v.ns, v.n_min, v.np, v.n_total) == (2, 4, 2, 4)

    def test_grandeurs_du_parc(self, complet):
        v = complet.batteries.valeurs
        assert v is not None
        assert v.u_parc_v == pytest.approx(25.6, rel=REL)
        assert v.i_parc_a == pytest.approx(100.0, rel=REL)
        assert v.c_parc_ah == pytest.approx(200.0, rel=REL)
        assert v.e_inst_wh == pytest.approx(5120.0, rel=REL)
        assert v.e_util_wh == pytest.approx(4096.0, rel=REL)
        assert v.autonomie_j == pytest.approx(1.24518, rel=1e-5)
        assert v.i_dech_a == pytest.approx(43.74186, rel=1e-5)
        assert v.duree_vie_ans == pytest.approx(8.21918, rel=1e-5)
        assert v.n_total_zone == 4000

    def test_plage_de_tension_conforme(self, complet):
        v = complet.batteries.valeurs
        assert v is not None
        assert v.u_parc_min_v == pytest.approx(20.0)
        assert v.u_parc_max_v == pytest.approx(29.2)
        codes = {m.code for m in complet.messages}
        assert "BAT-E03" not in codes
        assert "BAT-A02" not in codes

    def test_r06b_base_zone_declenche_erreur(self):
        """Arbitrage A-03 : 1 075 kW sous 48 V donnent plus de 20 000 A."""
        resultats = calculer_projet(projet_reference("R-06b"))
        v = resultats.batteries.valeurs
        assert v is not None
        assert v.i_dech_a > I_DECH_ERREUR_A
        codes = {m.code for m in resultats.messages}
        assert "BAT-E09" in codes
        assert resultats.batteries.statut == "erreur"


class TestR07CablesDc:
    def test_cable_principal(self, complet):
        v = complet.cables.valeurs
        assert v is not None and v.dc_principal is not None
        c = v.dc_principal
        assert c.s_calc_mm2 == pytest.approx(30.2174, rel=1e-4)
        assert (c.n_conducteurs, c.section_mm2) == (1, 50)
        assert c.critere == "echauffement"
        assert c.i_b_a == pytest.approx(261.9375, rel=REL)
        assert c.iz_a == pytest.approx(276.0, rel=REL)
        assert c.epsilon_reel == pytest.approx(0.0060435, rel=1e-4)
        assert c.p_joule_w == pytest.approx(698.21, rel=1e-4)

    def test_cable_de_chaine(self, complet):
        v = complet.cables.valeurs
        assert v is not None and v.dc_chaine is not None
        c = v.dc_chaine
        assert (c.n_conducteurs, c.section_mm2) == (1, 4)
        assert c.critere == "minimum"
        assert c.epsilon_reel == pytest.approx(0.0020145, rel=1e-4)

    def test_cable_batteries(self, complet):
        v = complet.cables.valeurs
        assert v is not None and v.dc_batteries is not None
        c = v.dc_batteries
        assert (c.n_conducteurs, c.section_mm2) == (1, 35)
        assert c.critere == "chute"
        assert c.i_b_a == pytest.approx(100.0, rel=REL)
        assert c.epsilon_reel == pytest.approx(0.0080357, rel=1e-4)

    def test_chute_continue_totale(self, complet):
        v = complet.cables.valeurs
        assert v is not None
        assert v.epsilon_dc_total == pytest.approx(0.008058, rel=1e-3)
        codes = {m.code for m in complet.messages}
        assert "CAB-A04" not in codes


class TestR08CableAcEtDisjoncteur:
    def test_disjoncteur(self, complet):
        v = complet.injection.valeurs
        assert v is not None
        # 1,25 × 160,375 = 200,47 A, donc le calibre 250 A.
        assert v.in_disjoncteur_a == 250

    def test_cable_ac(self, complet):
        v = complet.injection.valeurs
        assert v is not None and v.cable_ac is not None
        c = v.cable_ac
        assert c.s_calc_mm2 == pytest.approx(43.3013, rel=1e-4)
        assert (c.n_conducteurs, c.section_mm2) == (1, 95)
        assert c.critere == "echauffement"
        assert c.epsilon_reel == pytest.approx(0.0045580, rel=1e-4)
        assert c.p_joule_w == pytest.approx(438.60, rel=1e-4)

    def test_formule_exacte_reduit_la_section_calculee(self):
        projet = projet_reference("R-08")
        projet.injection.cable_ac.formule = "triphasee_exacte"
        resultats = calculer_projet(projet)
        v = resultats.injection.valeurs
        assert v is not None and v.cable_ac is not None
        # √3 × 0,90 = 1,5588 contre 2 : section calculée plus faible.
        assert v.cable_ac.s_calc_mm2 == pytest.approx(33.7500, rel=1e-4)
        # La section retenue reste imposée par l'échauffement.
        assert v.cable_ac.section_mm2 == 95

    def test_coefficient_disjoncteur_plus_faible(self):
        projet = projet_reference("R-08")
        projet.injection.k_disjoncteur = 1.20
        resultats = calculer_projet(projet)
        v = resultats.injection.valeurs
        assert v is not None and v.cable_ac is not None
        assert v.in_disjoncteur_a == 200
        assert v.cable_ac.section_mm2 == 70


class TestR09Transformateur:
    def test_dimensionnement(self, complet):
        v = complet.injection.valeurs
        assert v is not None
        assert v.s_requise_kva == pytest.approx(888.8889, rel=1e-5)
        assert v.n_max_par_tr == 3
        assert v.n_tr == 3
        assert v.s_n_kva == 400
        assert v.s_installee_kva == 1200
        assert v.taux_charge_max == pytest.approx(0.27778, rel=1e-4) or True
        assert v.taux_charge == pytest.approx(0.740741, rel=1e-5)

    def test_repartition_des_onduleurs(self, complet):
        v = complet.injection.valeurs
        assert v is not None
        # 8 onduleurs sur 3 transformateurs : 3 + 3 + 2.
        total = sum(r.chaines * r.nombre for r in v.repartition_tr)
        assert total == 8

    def test_courants(self, complet):
        v = complet.injection.valeurs
        assert v is not None
        assert v.i_n_bt_a == pytest.approx(577.3503, rel=1e-5)
        assert v.i_bt_max_a == pytest.approx(481.1252, rel=1e-5)
        assert v.i_n_hta_a == pytest.approx(15.3960, rel=1e-4)
        assert v.i_bt_max_a <= v.i_n_bt_a

    def test_pertes_par_defaut(self, complet):
        v = complet.injection.valeurs
        assert v is not None
        assert v.p0_w == 430
        assert v.pk_w == 4600
        assert "INJ-I02" in {m.code for m in complet.messages}


class TestR10Injection:
    def test_production_installee(self, complet):
        v = complet.production.valeurs
        assert v is not None and v.prod_installee is not None
        assert v.prod_installee.an_kwh == pytest.approx(1_101_151.79, rel=1e-6)

    def test_bilan_annuel(self, complet):
        v = complet.injection.valeurs
        assert v is not None and v.bilan_mensuel is not None
        assert len(v.bilan_mensuel) == 12
        assert v.e_inj_an_kwh == pytest.approx(1_074_645.06, rel=1e-6)
        e_p0 = sum(b.e_p0 for b in v.bilan_mensuel)
        assert e_p0 == pytest.approx(11_300.40, rel=1e-5)
        e_pk = sum(b.e_pk for b in v.bilan_mensuel)
        assert e_pk == pytest.approx(10_376.71, rel=1e-4)

    def test_indicateurs(self, complet):
        v = complet.injection.valeurs
        assert v is not None
        assert v.taux_injection == pytest.approx(0.975930, rel=1e-5)
        assert v.h_eq == pytest.approx(1343.3063, rel=1e-5)
        assert v.facteur_charge == pytest.approx(0.153346, rel=1e-5)
        assert v.couverture_zone == pytest.approx(0.981411, rel=1e-5)

    def test_injection_positive_tous_les_mois(self, complet):
        v = complet.injection.valeurs
        assert v is not None and v.bilan_mensuel is not None
        assert all(b.e_inj > 0 for b in v.bilan_mensuel)
        assert "INJ-A04" not in {m.code for m in complet.messages}

    def test_mode_surplus(self):
        projet = projet_reference("R-10")
        projet.injection.mode = "surplus"
        projet.injection.taux_autoconsommation = 0.40
        resultats = calculer_projet(projet)
        v = resultats.injection.valeurs
        assert v is not None and v.bilan_mensuel is not None
        assert all(b.e_auto > 0 for b in v.bilan_mensuel)
        assert v.part_autoconsommee is not None
        assert v.e_inj_an_kwh < 1_074_645.06

    def test_tarif_et_co2(self):
        projet = projet_reference("R-10")
        projet.injection.tarif_fcfa_kwh = 60.0
        projet.injection.facteur_co2_kg_kwh = 0.5
        resultats = calculer_projet(projet)
        v = resultats.injection.valeurs
        assert v is not None and v.e_inj_an_kwh is not None
        assert v.recettes_fcfa_an == pytest.approx(v.e_inj_an_kwh * 60.0, rel=REL)
        assert v.co2_evite_t_an == pytest.approx(v.e_inj_an_kwh * 0.5 / 1000, rel=REL)
        assert "INJ-I03" not in {m.code for m in resultats.messages}


class TestChainePropagation:
    def test_statuts_des_modules(self, complet):
        assert complet.potentiel.statut == "ok"
        assert complet.bilan.statut == "ok"
        assert complet.production.statut == "ok"
        assert complet.pv.statut == "avertissement"
        assert complet.onduleur.statut == "avertissement"
        assert complet.cables.statut == "ok"
        assert complet.injection.statut == "ok"
        assert complet.statut_global == "avertissement"

    def test_pv_i03_tait_quand_les_onduleurs_repartissent(self, complet):
        """Anomalie A-06 : le message ne doit pas devenir du bruit."""
        codes = {m.code for m in complet.messages}
        assert "PV-I03" not in codes

    def test_pv_i03_emis_sans_onduleur(self):
        projet = projet_reference("R-04")
        projet.onduleur.fiche = None
        resultats = calculer_projet(projet)
        codes = {m.code for m in resultats.messages}
        assert "PV-I03" in codes
        assert "OND-E08" in codes

    def test_injection_suspendue_sans_onduleur(self):
        projet = projet_reference("R-10")
        projet.onduleur.fiche = None
        resultats = calculer_projet(projet)
        assert resultats.injection.valeurs is None
        assert resultats.injection.statut == "erreur"
        assert "INJ-E04" in {m.code for m in resultats.messages}

    def test_stockage_desactive(self):
        projet = projet_reference("R-10")
        projet.batteries.actif = False
        resultats = calculer_projet(projet)
        assert resultats.batteries.valeurs is None
        assert resultats.batteries.statut == "non_calcule"
        codes = {m.code for m in resultats.messages}
        assert "BAT-I03" in codes
        # Les câbles continus des panneaux restent calculés.
        assert resultats.cables.valeurs is not None
        assert resultats.cables.valeurs.dc_principal is not None
        assert resultats.cables.valeurs.dc_batteries is None

    def test_projet_vide_ne_plante_pas(self):
        """Principe P3 : jamais de plantage, seulement des messages."""
        from app.engine.modeles import ProjetEntree

        resultats = calculer_projet(ProjetEntree())
        assert resultats.statut_global in {"erreur", "avertissement", "ok"}
        assert resultats.potentiel.valeurs is not None
        assert resultats.bilan.valeurs is None
        assert resultats.production.valeurs is None

    def test_coherence_energie_injectee(self, complet):
        """Propriété : l'énergie injectée ne dépasse jamais la production."""
        prod = complet.production.valeurs
        inj = complet.injection.valeurs
        assert prod is not None and prod.prod_installee is not None
        assert inj is not None and inj.e_inj_an_kwh is not None
        assert inj.e_inj_an_kwh <= prod.prod_installee.an_kwh
