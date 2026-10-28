"""Simulation d'un projet complet contre l'API en marche.

Scénario : un quartier de Yaoundé Ouest, 2 500 ménages et 180 commerces.
Le script suit le parcours réel d'un ingénieur, onglet par onglet.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"


def appel(chemin: str, charge: object | None = None, methode: str = "GET"):
    donnees = json.dumps(charge).encode("utf-8") if charge is not None else None
    requete = urllib.request.Request(
        f"{BASE}{chemin}",
        data=donnees,
        method=methode,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(requete, timeout=60) as reponse:
            brut = reponse.read()
            if reponse.headers.get("Content-Type", "").startswith("application/pdf"):
                return {"_pdf_octets": len(brut)}
            return json.loads(brut) if brut else None
    except urllib.error.HTTPError as erreur:
        print(f"  ERREUR HTTP {erreur.code} sur {chemin}: {erreur.read()[:300]}")
        raise


def fr(x: float, dec: int = 2) -> str:
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def titre(texte: str) -> None:
    print(f"\n{'─' * 72}\n{texte}\n{'─' * 72}")


# ======================================================================
titre("ONGLET 1 — Potentiel solaire de Yaoundé Ouest")

projet = appel("/projets/defaut")
projet["meta"]["nom"] = "Yaoundé Ouest — quartier pilote"
projet["meta"]["auteur"] = "Bureau d'études"
projet["meta"]["notes"] = (
    "Étude de faisabilité d'une centrale au sol avec injection sur le réseau HTA."
)

# Profil mensuel PVGIS pour Yaoundé, et une surface de 3 hectares.
projet["potentiel"].update(
    {
        "ghi_valeur": 192.625,
        "ghi_unite": "w_m2_moy24h",
        "profil_mensuel_kwh_m2_j": [
            4.88, 5.09, 4.86, 4.74, 4.56, 4.30,
            4.02, 3.91, 4.34, 4.64, 4.82, 4.94,
        ],
        "source_ghi": "PVGIS v5.2, 3,87° N / 11,52° E",
        "surface_valeur": 3,
        "surface_unite": "ha",
        "taux_occupation": 0.45,
        "rendement_module": 0.21,
    }
)

# ======================================================================
titre("ONGLET 2 — Bilan énergétique : deux catégories d'abonnés")

menages = projet["bilan"]["profils"][0]
menages["nom"] = "Ménage urbain"
menages["nb_abonnes"] = 2500

# Un quartier de Yaoundé : la climatisation et le froid progressent.
ajustements = {
    "Climatiseur 1 CV": 1,
    "Box internet / routeur Wi-Fi": 1,
    "Congélateur": 1,
    "Machine à laver": 1,
}
for ligne in menages["lignes"]:
    if ligne["nom"] in ajustements:
        ligne["quantite"] = ajustements[ligne["nom"]]

commerces = {
    "id": "profil-2",
    "nom": "Commerce de quartier",
    "nb_abonnes": 180,
    "lignes": [
        {"nom": "Réglette LED", "categorie": "Éclairage", "puissance_w": 18,
         "quantite": 8, "heures_j": 12, "ks": 1.0, "actif": True},
        {"nom": "Vitrine réfrigérée", "categorie": "Froid", "puissance_w": 450,
         "quantite": 2, "heures_j": 24, "ks": 0.45, "actif": True},
        {"nom": "Climatiseur 1,5 CV", "categorie": "Confort", "puissance_w": 1350,
         "quantite": 1, "heures_j": 10, "ks": 0.65, "actif": True},
        {"nom": "Caisse et terminal", "categorie": "Informatique", "puissance_w": 120,
         "quantite": 1, "heures_j": 12, "ks": 0.7, "actif": True},
        {"nom": "Ventilateur", "categorie": "Confort", "puissance_w": 50,
         "quantite": 3, "heures_j": 10, "ks": 1.0, "actif": True},
    ],
}
projet["bilan"]["profils"].append(commerces)

# ======================================================================
titre("ONGLET 3 — Dimensionnement : choix du panneau")

projet["production"].update(
    {
        "taux_couverture": 1.0,
        "performance_ratio": 0.76,
        "critere_ir": "moyenne_annuelle",
        "mode_pc": "calculee",
        "tension_systeme_v": 650,
    }
)

etat = appel("/calcul", projet, "POST")
pot = etat["potentiel"]["valeurs"]
bil = etat["bilan"]["valeurs"]
prod = etat["production"]["valeurs"]

print(f"  Irradiation H          {fr(pot['h_kwh_m2_j'], 3)} kWh/m²/j")
print(f"  Irradiation annuelle   {fr(pot['h_an_kwh_m2_an'])} kWh/m²/an")
print(f"  Mois défavorable       {fr(pot['h_min_kwh_m2_j'], 2)} kWh/m²/j (mois {pot['mois_defavorable']})")
print(f"  Surface                {fr(pot['surface_m2'], 0)} m²")
print(f"  Pc max installable     {fr(pot['pc_max_surface_kwc'], 0)} kWc")
print()
for profil in bil["profils"]:
    print(f"  {profil['nom']:<24} {fr(profil['e_cons_wh_j'] / 1000, 2):>8} kWh/j × "
          f"{profil['nb_abonnes']:>5} abonnés")
print(f"  {'Consommation de la zone':<24} {fr(bil['e_zone_wh_j'] / 1e6, 2):>8} MWh/j")
print(f"  {'Puissance appelée':<24} {fr(bil['p_app_zone_w'] / 1000, 0):>8} kW")
print()
print(f"  Puissance crête requise (F-09) : {fr(prod['pc_retenue_kwc'], 1)} kWc")

# --- Étape 4 : liste de choix des panneaux ---
propositions = appel(
    "/selection/panneaux",
    {"projet": projet, "filtres": {"compatibles_uniquement": True, "pmax_min": 500}},
    "POST",
)
print(f"\n  {len(propositions)} panneaux compatibles, les 5 meilleurs :")
print(f"  {'Modèle':<34} {'Ns':>3} {'Np':>5} {'Total':>7} {'Surplus':>9} {'État':<14}")
for p in propositions[:5]:
    a = p["apercu"]
    print(f"  {p['fiche']['nom'][:33]:<34} {a['ns']:>3} {a['np']:>5} "
          f"{a['n_total']:>7} {fr(a['surplus_pct'], 2):>8} % {p['statut']:<14}")

retenu = propositions[0]
projet["pv"]["fiche"] = retenu["fiche"]
print(f"\n  → Panneau retenu : {retenu['fiche']['nom']}")

# --- Étape 12 : liste de choix des onduleurs ---
onduleurs = appel(
    "/selection/onduleurs",
    {"projet": projet, "filtres": {"compatibles_uniquement": True, "u_ac": 400}},
    "POST",
)
print(f"\n  {len(onduleurs)} onduleurs compatibles en 400 V :")
print(f"  {'Modèle':<34} {'Nb':>4} {'Ratio':>7} {'Iac':>9} {'État':<14}")
for o in onduleurs[:5]:
    a = o["apercu"]
    print(f"  {o['fiche']['nom'][:33]:<34} {a['n_ond']:>4} {fr(a['ratio_dc_ac'], 3):>7} "
          f"{fr(a['iac_a'], 1):>7} A {o['statut']:<14}")

if onduleurs:
    projet["onduleur"]["fiche"] = onduleurs[0]["fiche"]
    print(f"\n  → Onduleur retenu : {onduleurs[0]['fiche']['nom']}")

# --- Étape 15 : batteries, base « un abonné » ---
projet["batteries"].update(
    {"actif": True, "base_energie": "abonne", "profil_id": "profil-1",
     "jours_autonomie": 1.0, "part_stockee": 0.6}
)
batteries = appel(
    "/selection/batteries",
    {"projet": projet, "filtres": {"compatibles_uniquement": True}},
    "POST",
)
print(f"\n  {len(batteries)} batteries compatibles :")
for b in batteries[:4]:
    a = b["apercu"]
    print(f"  {b['fiche']['nom'][:33]:<34} {a['ns']}s×{a['np']}p  "
          f"{fr(a['u_parc_v'], 1):>6} V  autonomie {fr(a['autonomie_j'], 2)} j")
if batteries:
    projet["batteries"]["fiche"] = batteries[0]["fiche"]
    print(f"\n  → Batterie retenue : {batteries[0]['fiche']['nom']}")

# --- Câbles et injection ---
projet["cables"]["dc_principal"]["longueur_m"] = 22
projet["cables"]["dc_chaine"]["longueur_m"] = 14
projet["cables"]["dc_batteries"]["longueur_m"] = 3
projet["injection"].update(
    {"transfo_mode": "auto", "u_hta_kv": 15, "mode": "surplus",
     "taux_autoconsommation": 0.55, "tarif_fcfa_kwh": 65.0,
     "facteur_co2_kg_kwh": 0.42}
)
projet["injection"]["cable_ac"]["longueur_m"] = 35

# ======================================================================
titre("CALCUL COMPLET")

final = appel("/calcul", projet, "POST")
pv = final["pv"]["valeurs"]
ond = final["onduleur"]["valeurs"]
bat = final["batteries"]["valeurs"]
cab = final["cables"]["valeurs"]
inj = final["injection"]["valeurs"]
prod = final["production"]["valeurs"]

print(f"  Statut global : {final['statut_global'].upper()}")
for nom in ("potentiel", "bilan", "production", "pv", "onduleur",
            "batteries", "cables", "injection"):
    print(f"    {nom:<12} {final[nom]['statut']}")

print("\n  CHAMP PHOTOVOLTAÏQUE")
print(f"    Panneaux            {pv['n_total']} ({pv['ns']} série × {pv['np']} parallèle)")
print(f"    Puissance installée {fr(pv['pc_installee_kwc'], 1)} kWc")
print(f"    Tension / courant   {fr(pv['u_dc_v'], 1)} V / {fr(pv['i_dc_a'], 0)} A")
print(f"    Voc froid           {fr(pv['voc_max_v'], 1)} V")
print(f"    Vmp chaud / froid   {fr(pv['vmp_min_v'], 1)} / {fr(pv['vmp_max_v'], 1)} V")

if ond:
    print("\n  ONDULEURS")
    print(f"    Nombre              {ond['n_ond']} × {fr(projet['onduleur']['fiche']['pnom_ac'], 0)} kW")
    print(f"    Ratio DC/AC         {fr(ond['ratio_dc_ac'], 3)}")
    print(f"    Courant AC unitaire {fr(ond['iac_a'], 1)} A")
    print(f"    Puissance AC totale {fr(ond['p_ac_total_kw'], 0)} kW / {fr(ond['s_ac_total_kva'], 0)} kVA")

if bat:
    print("\n  PARC DE BATTERIES (par abonné)")
    print(f"    Configuration       {bat['ns']} série × {bat['np']} parallèle = {bat['n_total']}")
    print(f"    Tension / courant   {fr(bat['u_parc_v'], 1)} V / {fr(bat['i_parc_a'], 0)} A")
    print(f"    Énergie utilisable  {fr(bat['e_util_wh'] / 1000, 2)} kWh")
    print(f"    Autonomie obtenue   {fr(bat['autonomie_j'], 2)} jour(s)")
    print(f"    Pour la zone        {bat['n_total_zone']} batteries")

if cab:
    print("\n  CÂBLES CONTINUS")
    for cle in ("dc_principal", "dc_chaine", "dc_batteries"):
        c = cab.get(cle)
        if c:
            print(f"    {c['nom']:<22} {c['n_conducteurs']} × {fr(c['section_mm2'], 0)} mm² "
                  f"({c['critere']}), chute {fr(c['epsilon_reel'] * 100, 3)} %")

if inj:
    print("\n  INJECTION AU RÉSEAU")
    print(f"    Transformateurs     {inj['n_tr']} × {fr(inj['s_n_kva'], 0)} kVA")
    print(f"    Taux de charge      {fr(inj['taux_charge'] * 100, 1)} %")
    print(f"    Disjoncteur         {fr(inj['in_disjoncteur_a'], 0)} A")
    if inj.get("cable_ac"):
        c = inj["cable_ac"]
        print(f"    Câble AC            {c['n_conducteurs']} × {fr(c['section_mm2'], 0)} mm² ({c['critere']})")
        print(f"    Coordination        {fr(c['i_a'], 1)} A ≤ {fr(inj['in_disjoncteur_a'], 0)} A ≤ {fr(c['iz_a'], 0)} A")
    if prod.get("prod_installee"):
        print(f"\n    Production annuelle {fr(prod['prod_installee']['an_kwh'] / 1000, 0)} MWh")
        print(f"    Productible         {fr(prod['prod_installee']['y_kwh_kwc'], 0)} kWh/kWc/an")
    if inj.get("e_inj_an_kwh"):
        print(f"    Énergie injectée    {fr(inj['e_inj_an_kwh'] / 1000, 0)} MWh/an")
        print(f"    Taux d'injection    {fr(inj['taux_injection'] * 100, 2)} %")
        print(f"    Part autoconsommée  {fr((inj.get('part_autoconsommee') or 0) * 100, 2)} %")
        print(f"    Recettes            {fr(inj['recettes_fcfa_an'] / 1e6, 1)} millions FCFA/an")
        print(f"    CO₂ évité           {fr(inj['co2_evite_t_an'], 0)} t/an")

titre("VÉRIFICATIONS")
compte = {"erreur": 0, "avertissement": 0, "info": 0}
for m in final["messages"]:
    compte[m["niveau"]] += 1
print(f"  {compte['erreur']} erreur(s), {compte['avertissement']} avertissement(s), "
      f"{compte['info']} information(s)\n")
for m in final["messages"]:
    if m["niveau"] != "info":
        print(f"  [{m['niveau'][:4].upper()}] {m['code']} — {m['titre']}")
        print(f"         {m['message']}")
        if m.get("suggestion"):
            print(f"         → {m['suggestion']}")

# ======================================================================
titre("ENREGISTREMENT, EXPORT ET RAPPORT")

cree = appel("/projets", projet, "POST")
identifiant = cree["id"]
print(f"  Projet enregistré        id {identifiant}")

export = appel(f"/projets/{identifiant}/export")
print(f"  Export                   {len(json.dumps(export))} octets, "
      f"empreinte {export['empreinte'][:22]}…")

reimport = appel("/projets/import", export, "POST")
print(f"  Réimport                 empreinte valide : {reimport['empreinte_valide']}")
assert (
    reimport["resultats"]["pv"]["valeurs"]["n_total"] == pv["n_total"]
), "le réimport doit reproduire le même dimensionnement"
print(f"  Reproductibilité         {reimport['resultats']['pv']['valeurs']['n_total']} panneaux, identique")

pdf = appel(f"/projets/{identifiant}/rapport.pdf")
print(f"  Rapport PDF              {pdf['_pdf_octets']} octets")

appel(f"/projets/{identifiant}", methode="DELETE")
appel(f"/projets/{reimport['id']}", methode="DELETE")
print("  Nettoyage                projets de simulation supprimés")

print("\n" + "═" * 72)
print("  SIMULATION TERMINÉE SANS ERREUR")
print("═" * 72)
