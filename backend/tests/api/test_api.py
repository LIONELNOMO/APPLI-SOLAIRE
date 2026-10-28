"""Tests des routes de l'API (TestClient)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import session as module_session
from app.db.init import init_db
from tests.engine.cas import projet_reference


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """API sur une base SQLite temporaire, catalogues chargés."""
    base = tmp_path_factory.mktemp("db") / "test.db"
    module_session.reinitialiser(f"sqlite:///{base}")
    init_db()

    from app.main import create_app

    with TestClient(create_app()) as essai:
        yield essai


class TestSante:
    def test_health(self, client):
        reponse = client.get("/api/v1/health")
        assert reponse.status_code == 200
        charge = reponse.json()
        assert charge["statut"] == "ok"
        assert charge["mode"] == "dev"


class TestCalcul:
    def test_calcul_complet(self, client):
        entree = projet_reference("R-10").model_dump(mode="json")
        reponse = client.post("/api/v1/calcul", json=entree)
        assert reponse.status_code == 200
        charge = reponse.json()
        assert charge["statut_global"] == "avertissement"
        assert charge["pv"]["valeurs"]["n_total"] == 1582
        assert charge["injection"]["valeurs"]["n_tr"] == 3

    def test_projet_vide_renvoie_des_messages(self, client):
        reponse = client.post("/api/v1/calcul", json={})
        assert reponse.status_code == 200
        charge = reponse.json()
        # Principe P3 : jamais d'erreur HTTP pour une valeur métier.
        assert charge["messages"]
        assert charge["bilan"]["valeurs"] is None

    def test_type_invalide_rejete(self, client):
        reponse = client.post(
            "/api/v1/calcul", json={"potentiel": {"ghi_valeur": "beaucoup"}}
        )
        assert reponse.status_code == 422


class TestCatalogue:
    def test_lister_les_quatre_catalogues(self, client):
        attendus = {
            "panneaux": 14,
            "onduleurs": 7,
            "batteries": 10,
            "equipements": 22,
        }
        for nom, nombre in attendus.items():
            reponse = client.get(f"/api/v1/catalogue/{nom}")
            assert reponse.status_code == 200
            assert len(reponse.json()) == nombre

    def test_lire_une_fiche(self, client):
        reponse = client.get("/api/v1/catalogue/panneaux/canadian-550-mono")
        assert reponse.status_code == 200
        assert reponse.json()["pmax"] == 550

    def test_fiche_introuvable(self, client):
        reponse = client.get("/api/v1/catalogue/panneaux/inexistant")
        assert reponse.status_code == 404

    def test_recherche(self, client):
        reponse = client.get("/api/v1/catalogue/panneaux", params={"recherche": "jinko"})
        assert reponse.status_code == 200
        assert len(reponse.json()) == 3

    def test_creer_une_fiche_utilisateur(self, client):
        fiche = {
            "id": "u-essai-600",
            "nom": "Essai 600 Wp",
            "fabricant": "Essai",
            "technologie": "mono",
            "pmax": 600,
            "vmp": 43.2,
            "voc": 51.5,
            "imp": 13.89,
            "isc": 14.7,
            "coef_voc": -0.27,
            "coef_vmp": -0.33,
            "coef_pmax": -0.33,
            "noct": 45,
            "vsys_max": 1500,
        }
        reponse = client.post("/api/v1/catalogue/panneaux", json=fiche)
        assert reponse.status_code == 201
        assert reponse.json()["source"] == "utilisateur"

        # Le doublon est refusé.
        assert client.post("/api/v1/catalogue/panneaux", json=fiche).status_code == 409

        # La suppression fonctionne.
        assert (
            client.delete("/api/v1/catalogue/panneaux/u-essai-600").status_code == 204
        )

    def test_fiche_incoherente_refusee(self, client):
        fiche = {
            "id": "u-incoherent",
            "nom": "Incohérent",
            "pmax": 500,
            "vmp": 40,
            "voc": 30,  # Voc inférieur à Vmp : impossible.
            "imp": 12,
            "isc": 13,
            "coef_voc": -0.3,
            "coef_vmp": -0.35,
        }
        reponse = client.post("/api/v1/catalogue/panneaux", json=fiche)
        assert reponse.status_code == 422

    def test_identifiant_non_slug_refuse(self, client):
        fiche = {
            "id": "Mon Panneau!",
            "nom": "Essai",
            "pmax": 500,
            "vmp": 41.5,
            "voc": 49.5,
            "imp": 12.05,
            "isc": 12.8,
            "coef_voc": -0.29,
            "coef_vmp": -0.34,
        }
        reponse = client.post("/api/v1/catalogue/panneaux", json=fiche)
        assert reponse.status_code == 422

    def test_fiche_systeme_en_lecture_seule(self, client):
        reponse = client.delete("/api/v1/catalogue/panneaux/canadian-550-mono")
        assert reponse.status_code == 409


class TestSelection:
    def test_liste_de_choix_des_panneaux(self, client):
        demande = {"projet": projet_reference("R-04").model_dump(mode="json")}
        reponse = client.post("/api/v1/selection/panneaux", json=demande)
        assert reponse.status_code == 200
        propositions = reponse.json()
        assert len(propositions) == 14
        # Les compatibles d'abord, puis le surplus croissant.
        assert propositions[0]["statut"] in {"ok", "avertissement"}
        assert propositions[0]["apercu"]["n_total"] > 0

    def test_filtre_compatibles_uniquement(self, client):
        demande = {
            "projet": projet_reference("R-04").model_dump(mode="json"),
            "filtres": {"compatibles_uniquement": True, "pmax_min": 500},
        }
        reponse = client.post("/api/v1/selection/panneaux", json=demande)
        assert reponse.status_code == 200
        for proposition in reponse.json():
            assert proposition["statut"] != "erreur"
            assert proposition["fiche"]["pmax"] >= 500

    def test_liste_de_choix_des_onduleurs(self, client):
        demande = {"projet": projet_reference("R-05").model_dump(mode="json")}
        reponse = client.post("/api/v1/selection/onduleurs", json=demande)
        assert reponse.status_code == 200
        propositions = reponse.json()
        assert len(propositions) == 7
        assert propositions[0]["apercu"]["n_ond"] >= 1

    def test_liste_de_choix_des_batteries(self, client):
        demande = {"projet": projet_reference("R-06").model_dump(mode="json")}
        reponse = client.post("/api/v1/selection/batteries", json=demande)
        assert reponse.status_code == 200
        assert len(reponse.json()) == 10


class TestProjets:
    def test_projet_par_defaut_contient_la_bibliotheque(self, client):
        reponse = client.get("/api/v1/projets/defaut")
        assert reponse.status_code == 200
        charge = reponse.json()
        lignes = charge["bilan"]["profils"][0]["lignes"]
        assert len(lignes) == 22
        assert any(ligne["nom"] == "Réfrigérateur" for ligne in lignes)

    def test_r11_profil_par_defaut(self, client):
        """R-11 : le Ménage type donne 3 398 Wh/j, 1 877 W et 1 374 W."""
        defaut = client.get("/api/v1/projets/defaut").json()
        defaut["bilan"]["profils"][0]["nb_abonnes"] = 1
        reponse = client.post("/api/v1/calcul", json=defaut)
        assert reponse.status_code == 200
        profil = reponse.json()["bilan"]["valeurs"]["profils"][0]
        assert profil["e_cons_wh_j"] == pytest.approx(3398, abs=0.5)
        assert profil["p_inst_w"] == pytest.approx(1877, abs=0.5)
        assert profil["p_app_w"] == pytest.approx(1374, abs=0.5)

    def test_cycle_de_vie_complet(self, client):
        entree = projet_reference("R-10").model_dump(mode="json")
        entree["meta"]["nom"] = "Projet de recette"

        creation = client.post("/api/v1/projets", json=entree)
        assert creation.status_code == 201
        identifiant = creation.json()["id"]

        lecture = client.get(f"/api/v1/projets/{identifiant}")
        assert lecture.status_code == 200
        assert lecture.json()["entree"]["meta"]["nom"] == "Projet de recette"

        liste = client.get("/api/v1/projets")
        assert liste.status_code == 200
        assert any(p["id"] == identifiant for p in liste.json())

        entree["production"]["performance_ratio"] = 0.80
        modification = client.put(f"/api/v1/projets/{identifiant}", json=entree)
        assert modification.status_code == 200
        pc = modification.json()["resultats"]["production"]["valeurs"]["pc_retenue_kwc"]
        assert pc == pytest.approx(811.16, rel=1e-3)

        copie = client.post(f"/api/v1/projets/{identifiant}/dupliquer")
        assert copie.status_code == 201
        assert copie.json()["entree"]["meta"]["nom"].endswith("(copie)")

        assert client.delete(f"/api/v1/projets/{identifiant}").status_code == 204
        assert client.get(f"/api/v1/projets/{identifiant}").status_code == 404

    def test_aller_retour_export_import(self, client):
        entree = projet_reference("R-10").model_dump(mode="json")
        entree["meta"]["nom"] = "Projet à exporter"
        identifiant = client.post("/api/v1/projets", json=entree).json()["id"]

        export = client.get(f"/api/v1/projets/{identifiant}/export")
        assert export.status_code == 200
        assert "attachment" in export.headers["content-disposition"]
        charge = export.json()
        assert charge["format"] == "dimsolaire-projet"
        assert charge["empreinte"].startswith("sha256:")

        importation = client.post("/api/v1/projets/import", json=charge)
        assert importation.status_code == 201
        resultat = importation.json()
        assert resultat["empreinte_valide"] is True
        assert resultat["avertissements"] == []
        # Le nom existe déjà : le suffixe est ajouté.
        assert resultat["entree"]["meta"]["nom"] == "Projet à exporter (importé)"
        # Les résultats sont recalculés à l'identique.
        assert resultat["resultats"]["pv"]["valeurs"]["n_total"] == 1582

    def test_import_empreinte_alteree(self, client):
        entree = projet_reference("R-01").model_dump(mode="json")
        identifiant = client.post("/api/v1/projets", json=entree).json()["id"]
        charge = client.get(f"/api/v1/projets/{identifiant}/export").json()
        charge["projet"]["production"]["performance_ratio"] = 0.65

        reponse = client.post("/api/v1/projets/import", json=charge)
        assert reponse.status_code == 201
        resultat = reponse.json()
        assert resultat["empreinte_valide"] is False
        assert resultat["avertissements"]

    def test_import_format_inconnu(self, client):
        reponse = client.post(
            "/api/v1/projets/import", json={"format": "autre-chose", "projet": {}}
        )
        assert reponse.status_code == 422
        assert "Format inattendu" in reponse.json()["detail"]

    def test_import_version_future(self, client):
        reponse = client.post(
            "/api/v1/projets/import",
            json={
                "format": "dimsolaire-projet",
                "version_format": 99,
                "projet": {},
            },
        )
        assert reponse.status_code == 422
        assert "plus récente" in reponse.json()["detail"]


class TestRapportPdf:
    def test_pdf_depuis_une_entree(self, client):
        entree = projet_reference("R-10").model_dump(mode="json")
        reponse = client.post("/api/v1/rapports/pdf", json=entree)
        assert reponse.status_code == 200
        assert reponse.headers["content-type"] == "application/pdf"
        assert reponse.content.startswith(b"%PDF")
        # Un rapport complet fait plusieurs pages.
        assert len(reponse.content) > 10_000

    def test_pdf_d_un_projet_enregistre(self, client):
        entree = projet_reference("R-10").model_dump(mode="json")
        entree["meta"]["nom"] = "Projet pour PDF"
        identifiant = client.post("/api/v1/projets", json=entree).json()["id"]
        reponse = client.get(f"/api/v1/projets/{identifiant}/rapport.pdf")
        assert reponse.status_code == 200
        assert reponse.content.startswith(b"%PDF")

    def test_pdf_projet_vide(self, client):
        """Le rapport doit se produire même sans équipement choisi."""
        reponse = client.post("/api/v1/rapports/pdf", json={})
        assert reponse.status_code == 200
        assert reponse.content.startswith(b"%PDF")


class TestJetonDesktop:
    def test_jeton_exige_en_mode_desktop(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIMSOLAIRE_MODE", "desktop")
        monkeypatch.setenv("DIMSOLAIRE_TOKEN", "jeton-de-test")
        module_session.reinitialiser(f"sqlite:///{tmp_path / 'desktop.db'}")

        from app.main import create_app

        with TestClient(create_app()) as essai:
            # /health reste accessible, pour l'attente au démarrage.
            assert essai.get("/api/v1/health").status_code == 200
            # Les autres routes exigent le jeton.
            assert essai.get("/api/v1/catalogue/panneaux").status_code == 401
            avec_jeton = essai.get(
                "/api/v1/catalogue/panneaux",
                headers={"X-App-Token": "jeton-de-test"},
            )
            assert avec_jeton.status_code == 200
            # Un jeton erroné est refusé.
            assert (
                essai.get(
                    "/api/v1/catalogue/panneaux",
                    headers={"X-App-Token": "mauvais"},
                ).status_code
                == 401
            )
