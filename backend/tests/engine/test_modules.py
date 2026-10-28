"""Cas de référence R-01 à R-04b (§9 du cahier des charges)."""

from __future__ import annotations

import pytest

from app.engine.bilan import calculer_bilan
from app.engine.champ_pv import configurer_champ, temperatures_cellule
from app.engine.potentiel import calculer_potentiel
from app.engine.production import calculer_production
from tests.engine.cas import projet_reference

REL = 1e-6


class TestR01Potentiel:
    def test_irradiation_et_potentiel(self):
        projet = projet_reference("R-01")
        valeurs, _ = calculer_potentiel(
            projet.potentiel, projet.production.performance_ratio
        )
        assert valeurs is not None
        assert valeurs.h_kwh_m2_j == pytest.approx(4.623, rel=REL)
        assert valeurs.h_an_kwh_m2_an == pytest.approx(1687.395, rel=REL)
        assert valeurs.g_moy_w_m2 == pytest.approx(192.625, rel=REL)
        assert valeurs.surface_m2 == 10_000
        assert valeurs.e_pot_j_kwh == pytest.approx(46_230, rel=REL)
        assert valeurs.e_pot_an_kwh == pytest.approx(16_873_950, rel=REL)
        assert valeurs.pc_max_surface_kwc == pytest.approx(1050, rel=REL)
        assert valeurs.e_tech_an_kwh == pytest.approx(1_328_823.5625, rel=REL)

    def test_source_a_confirmer_signalee(self):
        projet = projet_reference("R-01")
        _, messages = calculer_potentiel(projet.potentiel, 0.75)
        assert "POT-I02" in {m.code for m in messages}

    def test_surface_absente_laisse_irradiation(self):
        projet = projet_reference("R-01")
        projet.potentiel.surface_valeur = None
        valeurs, messages = calculer_potentiel(projet.potentiel, 0.75)
        assert valeurs is not None
        assert valeurs.h_kwh_m2_j == pytest.approx(4.623, rel=REL)
        assert valeurs.e_pot_an_kwh is None
        assert "POT-I03" in {m.code for m in messages}

    def test_ghi_en_kwh_an_equivalent(self):
        projet = projet_reference("R-01")
        projet.potentiel.ghi_valeur = 1687.395
        projet.potentiel.ghi_unite = "kwh_m2_an"
        valeurs, _ = calculer_potentiel(projet.potentiel, 0.75)
        assert valeurs is not None
        assert valeurs.h_kwh_m2_j == pytest.approx(4.623, rel=REL)


class TestR02Bilan:
    def test_consommation_et_puissances(self):
        projet = projet_reference("R-02")
        valeurs, _ = calculer_bilan(projet.bilan)
        assert valeurs is not None
        profil = valeurs.profils[0]
        assert profil.e_cons_wh_j == pytest.approx(3000, rel=REL)
        assert profil.p_inst_w == pytest.approx(1350, rel=REL)
        assert profil.p_app_w == pytest.approx(1075, rel=REL)
        assert valeurs.e_zone_wh_j == pytest.approx(3_000_000, rel=REL)
        assert valeurs.e_zone_an_kwh == pytest.approx(1_095_000, rel=REL)
        assert valeurs.p_inst_zone_w == pytest.approx(1_350_000, rel=REL)
        assert valeurs.p_app_zone_w == pytest.approx(1_075_000, rel=REL)

    def test_repartition_dominee_par_le_froid(self):
        projet = projet_reference("R-02")
        valeurs, _ = calculer_bilan(projet.bilan)
        assert valeurs is not None
        premiere = valeurs.repartition_categories[0]
        assert premiere.categorie == "Froid"
        assert premiere.part_pct == pytest.approx(60.0, rel=1e-9)

    def test_quantite_nulle_sans_message(self):
        projet = projet_reference("R-02")
        projet.bilan.profils[0].lignes[0].quantite = 0
        _, messages = calculer_bilan(projet.bilan)
        assert not [m for m in messages if m.code.startswith("BIL-E")]

    def test_consommation_nulle_bloque(self):
        projet = projet_reference("R-02")
        projet.bilan.profils[0].nb_abonnes = 0
        valeurs, messages = calculer_bilan(projet.bilan)
        assert valeurs is None
        assert "BIL-E06" in {m.code for m in messages}


class TestR03Production:
    def test_puissance_crete_et_productible(self):
        projet = projet_reference("R-03")
        pot, _ = calculer_potentiel(projet.potentiel, 0.75)
        bil, _ = calculer_bilan(projet.bilan)
        valeurs, _ = calculer_production(projet.production, pot, bil)
        assert valeurs is not None
        assert valeurs.ir_kwh_m2_j == pytest.approx(4.623, rel=REL)
        assert valeurs.e_cible_kwh_j == pytest.approx(3000, rel=REL)
        assert valeurs.pc_retenue_kwc == pytest.approx(865.2385, rel=1e-4)
        assert valeurs.prod_theorique is not None
        assert valeurs.prod_theorique.j_kwh == pytest.approx(3000, rel=REL)
        assert valeurs.prod_theorique.an_kwh == pytest.approx(1_095_000, rel=REL)
        assert valeurs.prod_theorique.y_kwh_kwc == pytest.approx(1265.54625, rel=1e-6)

    def test_mois_defavorable_augmente_la_puissance(self):
        projet = projet_reference("R-03")
        projet.potentiel.profil_mensuel_kwh_m2_j = [
            4.88, 5.09, 4.86, 4.74, 4.56, 4.30,
            4.02, 3.91, 4.34, 4.64, 4.82, 4.94,
        ]
        projet.production.critere_ir = "mois_defavorable"
        pot, _ = calculer_potentiel(projet.potentiel, 0.75)
        bil, _ = calculer_bilan(projet.bilan)
        valeurs, _ = calculer_production(projet.production, pot, bil)
        assert valeurs is not None
        assert valeurs.ir_kwh_m2_j == pytest.approx(3.91, rel=REL)
        assert valeurs.pc_retenue_kwc > 1000

    def test_puissance_imposee_insuffisante(self):
        projet = projet_reference("R-03")
        projet.production.mode_pc = "imposee"
        projet.production.pc_imposee_kwc = 500
        pot, _ = calculer_potentiel(projet.potentiel, 0.75)
        bil, _ = calculer_bilan(projet.bilan)
        valeurs, messages = calculer_production(projet.production, pot, bil)
        assert valeurs is not None
        assert valeurs.pc_retenue_kwc == 500
        assert "PROD-A01" in {m.code for m in messages}


class TestR04ChampPv:
    def _configurer(self, cas: str = "R-04"):
        projet = projet_reference(cas)
        pot, _ = calculer_potentiel(projet.potentiel, 0.75)
        bil, _ = calculer_bilan(projet.bilan)
        prod, _ = calculer_production(projet.production, pot, bil)
        assert prod is not None
        return configurer_champ(
            projet.pv, prod.pc_retenue_kwc, projet.production.tension_systeme_v
        )

    def test_temperatures_cellule(self):
        projet = projet_reference("R-04")
        t_min, t_max = temperatures_cellule(projet.pv, 45)
        assert t_min == pytest.approx(10.0)
        assert t_max == pytest.approx(66.25)

    def test_configuration_mode_vmp(self):
        valeurs, _ = self._configurer()
        assert valeurs is not None
        assert valeurs.n_min == 1574
        assert valeurs.ns == 14
        assert valeurs.np == 113
        assert valeurs.n_total == 1582
        assert valeurs.pc_installee_kwc == pytest.approx(870.1, rel=REL)
        assert valeurs.u_dc_v == pytest.approx(586.6, rel=REL)
        assert valeurs.i_dc_a == pytest.approx(1483.69, rel=1e-5)
        assert valeurs.i_cc_dc_a == pytest.approx(1578.61, rel=1e-5)
        assert valeurs.u_co_v == pytest.approx(698.6, rel=REL)

    def test_tensions_extremes(self):
        valeurs, _ = self._configurer()
        assert valeurs is not None
        assert valeurs.voc_max_v == pytest.approx(728.9889, rel=1e-5)
        assert valeurs.vmp_min_v == pytest.approx(504.3277, rel=1e-5)
        assert valeurs.vmp_max_v == pytest.approx(616.5166, rel=1e-5)

    def test_messages_mode_vmp(self):
        _, messages = self._configurer()
        codes = {m.code for m in messages}
        # Voc froid à 728,99 V dépasse Us = 600 V : avertissement (arbitrage A-02).
        assert "PV-A04" in codes
        assert "PV-E06" not in codes
        # Vmp froid à 616,52 V dépasse aussi Us : anomalie A-05.
        assert "PV-A05" in codes
        # 8 panneaux ajoutés pour compléter les chaînes.
        assert "PV-I01" in codes
        # Aucune erreur : la fiche autorise 1 500 V.
        assert not [c for c in codes if c.startswith("PV-E")]

    def test_configuration_mode_voc_froid(self):
        valeurs, messages = self._configurer("R-04b")
        assert valeurs is not None
        codes = {m.code for m in messages}
        assert valeurs.ns == 11
        assert valeurs.np == 144
        assert valeurs.n_total == 1584
        assert valeurs.pc_installee_kwc == pytest.approx(871.2, rel=REL)
        assert valeurs.u_dc_v == pytest.approx(460.9, rel=REL)
        assert valeurs.voc_max_v == pytest.approx(572.7769, rel=1e-5)
        # Us devient une limite absolue, et elle est respectée.
        assert "PV-A04" not in codes
        assert "PV-E06" not in codes

    @pytest.mark.parametrize(
        "mode, ns, np_, avertit",
        [("vmp", 14, 113, True), ("voc_froid", 11, 144, False)],
    )
    def test_arbitrage_a02(self, mode, ns, np_, avertit):
        projet = projet_reference("R-04")
        projet.pv.tension_reference_ns = mode
        pot, _ = calculer_potentiel(projet.potentiel, 0.75)
        bil, _ = calculer_bilan(projet.bilan)
        prod, _ = calculer_production(projet.production, pot, bil)
        assert prod is not None
        valeurs, messages = configurer_champ(
            projet.pv, prod.pc_retenue_kwc, projet.production.tension_systeme_v
        )
        assert valeurs is not None
        assert (valeurs.ns, valeurs.np) == (ns, np_)
        codes = {m.code for m in messages}
        assert ("PV-A04" in codes) is avertit
        assert "PV-E06" not in codes

    def test_coherence_puissance(self):
        valeurs, _ = self._configurer()
        assert valeurs is not None
        # U_DC × I_DC doit être très proche de la puissance installée.
        produit_kw = valeurs.u_dc_v * valeurs.i_dc_a / 1000.0
        assert produit_kw == pytest.approx(valeurs.pc_installee_kwc, rel=0.02)

    def test_mode_manuel_recalcule(self):
        projet = projet_reference("R-04")
        projet.pv.mode_config = "manuel"
        projet.pv.ns_manuel = 13
        projet.pv.np_manuel = 122
        valeurs, _ = configurer_champ(projet.pv, 865.2385, 600)
        assert valeurs is not None
        assert valeurs.n_total == 1586
        assert valeurs.u_dc_v == pytest.approx(544.7, rel=REL)

    def test_mode_manuel_invalide(self):
        projet = projet_reference("R-04")
        projet.pv.mode_config = "manuel"
        projet.pv.ns_manuel = 0
        projet.pv.np_manuel = 10
        valeurs, messages = configurer_champ(projet.pv, 865.2385, 600)
        assert valeurs is None
        assert "PV-E05" in {m.code for m in messages}

    def test_us_trop_faible(self):
        projet = projet_reference("R-04")
        valeurs, messages = configurer_champ(projet.pv, 865.2385, 30)
        assert valeurs is None
        assert "PV-E02" in {m.code for m in messages}

    def test_panneau_absent(self):
        projet = projet_reference("R-04")
        projet.pv.fiche = None
        valeurs, messages = configurer_champ(projet.pv, 865.2385, 600)
        assert valeurs is None
        assert "PV-E01" in {m.code for m in messages}
