"""Tests du socle : arrondis, unités, messages (§9 du cahier des charges)."""

from __future__ import annotations

import pytest

from app.engine.arrondis import arrondi_demi_haut, ceil_safe, floor_safe, normaliser
from app.engine.constantes import CALIBRES_DISJONCTEURS, JOURS_MOIS, SECTIONS
from app.engine.messages import Niveau, fmt, msg, statut
from app.engine.unites import (
    ghi_vers_h_kwh_m2_j,
    lire_nombre,
    mettre_a_echelle_energie,
    surface_vers_m2,
)


class TestArrondis:
    def test_ceil_safe_tolere_le_bruit_flottant(self):
        # 79 200 / 550 vaut 144.00000000000003 en flottant.
        assert ceil_safe(79_200 / 550) == 144
        assert ceil_safe((0.1 + 0.2) / 0.1) == 3

    def test_ceil_safe_arrondit_bien_au_dessus(self):
        assert ceil_safe(1573.16) == 1574
        assert ceil_safe(112.43) == 113

    def test_floor_safe(self):
        assert floor_safe(69.3 / 23.1) == 3
        assert floor_safe(600 / 41.9) == 14
        assert floor_safe(14.32) == 14

    def test_arrondi_demi_haut_contre_round(self):
        # round() de Python arrondit 2,5 à 2 : inacceptable pour F-22.
        assert arrondi_demi_haut(2.5) == 3
        assert arrondi_demi_haut(3.5) == 4
        assert arrondi_demi_haut(1.875) == 2
        assert arrondi_demi_haut(3.75) == 4

    def test_normaliser_series(self):
        assert normaliser(30.22, SECTIONS) == 35
        assert normaliser(43.30, SECTIONS) == 50
        assert normaliser(200.47, CALIBRES_DISJONCTEURS) == 250
        # Tolérance : 63,0000000001 A doit prendre le calibre 63 A.
        assert normaliser(63.0000000001, CALIBRES_DISJONCTEURS) == 63

    def test_normaliser_sans_solution(self):
        assert normaliser(5000, SECTIONS) is None


class TestUnites:
    def test_f01_conversion_ghi(self):
        assert ghi_vers_h_kwh_m2_j(192.625, "w_m2_moy24h") == pytest.approx(4.623)
        assert ghi_vers_h_kwh_m2_j(4.623, "kwh_m2_j") == 4.623
        assert ghi_vers_h_kwh_m2_j(1687.395, "kwh_m2_an") == pytest.approx(4.623)

    def test_surfaces(self):
        assert surface_vers_m2(1, "ha") == 10_000
        assert surface_vers_m2(1, "km2") == 1_000_000
        assert surface_vers_m2(500, "m2") == 500

    def test_lire_nombre_accepte_virgule_et_point(self):
        assert lire_nombre("192,625") == 192.625
        assert lire_nombre("192.625") == 192.625
        assert lire_nombre("1 687,40") == 1687.40
        assert lire_nombre("1 687,40") == 1687.40

    def test_mise_a_echelle(self):
        assert mettre_a_echelle_energie(3_000_000) == (3.0, "MWh")
        assert mettre_a_echelle_energie(500) == (500.0, "Wh")


class TestMessages:
    def test_format_fr(self):
        assert fmt(1687.395) == "1 687,40"
        assert fmt(4.623, 3) == "4,623"

    def test_msg_remplit_le_modele(self):
        m = msg("PV-A04", voc=728.99, us=600.0)
        assert m.code == "PV-A04"
        assert m.niveau is Niveau.AVERTISSEMENT
        assert "728,99" in m.message
        assert "600,00" in m.message

    def test_code_inconnu_leve(self):
        with pytest.raises(KeyError):
            msg("XX-E99")

    def test_statut_priorite(self):
        erreur = msg("PV-E01")
        avertissement = msg("PV-A04", voc=1.0, us=1.0)
        info = msg("PV-I02", taux="50")
        assert statut([erreur, avertissement, info]) == "erreur"
        assert statut([avertissement, info]) == "avertissement"
        assert statut([info]) == "ok"
        assert statut([]) == "ok"
        assert statut([info], calcule=False) == "non_calcule"


def test_annee_de_365_jours():
    assert sum(JOURS_MOIS) == 365
