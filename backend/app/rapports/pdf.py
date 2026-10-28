"""Rapport PDF de dimensionnement (§12 d'ARCHITECTURE.md).

ReportLab seul, sans matplotlib : l'exécutable de la version PC resterait
sinon beaucoup plus lourd.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..engine.constantes import MOIS_NOMS
from ..engine.messages import Niveau, fmt, fmt_entier, fmt_pct
from ..engine.modeles import ProjetEntree, ResultatsProjet

ENCRE = colors.HexColor("#0E1419")
ACCENT = colors.HexColor("#C2410C")
GRIS = colors.HexColor("#5A6670")
FILET = colors.HexColor("#DDE0DE")
FOND = colors.HexColor("#F7F8F7")

COULEURS_NIVEAU = {
    Niveau.ERREUR: colors.HexColor("#A81D1D"),
    Niveau.AVERTISSEMENT: colors.HexColor("#8A5A00"),
    Niveau.INFO: colors.HexColor("#0F5C6B"),
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titre": ParagraphStyle(
            "titre", parent=base["Title"], fontSize=26, leading=30,
            textColor=ENCRE, spaceAfter=4,
        ),
        "sous_titre": ParagraphStyle(
            "sous_titre", parent=base["Normal"], fontSize=12, leading=16,
            textColor=GRIS, spaceAfter=18,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontSize=15, leading=19,
            textColor=ENCRE, spaceBefore=16, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=11.5, leading=15,
            textColor=ACCENT, spaceBefore=12, spaceAfter=6,
        ),
        "corps": ParagraphStyle(
            "corps", parent=base["Normal"], fontSize=9.5, leading=13.5,
            textColor=ENCRE, alignment=TA_LEFT,
        ),
        "petit": ParagraphStyle(
            "petit", parent=base["Normal"], fontSize=8.5, leading=11.5,
            textColor=GRIS,
        ),
        "mono": ParagraphStyle(
            "mono", parent=base["Code"], fontSize=8.5, leading=12,
            textColor=ENCRE,
        ),
    }


def _pied_de_page(canevas, document) -> None:
    canevas.saveState()
    canevas.setFont("Helvetica", 7.5)
    canevas.setFillColor(GRIS)
    canevas.drawString(
        20 * mm, 12 * mm, "DimSolaire — rapport de dimensionnement"
    )
    canevas.drawRightString(190 * mm, 12 * mm, f"page {document.page}")
    canevas.setStrokeColor(FILET)
    canevas.setLineWidth(0.4)
    canevas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canevas.restoreState()


def _tableau(donnees: list[list[str]], largeurs: list[float], entete: bool = True) -> Table:
    table = Table(donnees, colWidths=largeurs, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), ENCRE),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, FILET),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]
    if entete:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), FOND),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("TEXTCOLOR", (0, 0), (-1, 0), GRIS),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, FILET),
        ]
    table.setStyle(TableStyle(style))
    return table


def _graphique_mensuel(
    valeurs: list[float], unite: str, largeur: float = 165 * mm, hauteur: float = 42 * mm
) -> Table:
    """Barres mensuelles dessinées en tableau : pas de dépendance graphique."""
    maximum = max(valeurs) if valeurs and max(valeurs) > 0 else 1.0
    cellules_hautes: list[str] = []
    for valeur in valeurs:
        proportion = max(valeur / maximum, 0.0)
        # Huit niveaux de blocs, lisibles sans police spéciale.
        niveau = round(proportion * 8)
        cellules_hautes.append("█" * max(niveau, 1))

    donnees = [
        cellules_hautes,
        [m[:3].upper() for m in MOIS_NOMS],
        [fmt(v / 1000.0, 1) if abs(v) >= 1000 else fmt(v, 1) for v in valeurs],
    ]
    colonne = largeur / 12.0
    table = Table(donnees, colWidths=[colonne] * 12, rowHeights=[hauteur, 10, 10])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, 0), 5.5),
                ("TEXTCOLOR", (0, 0), (-1, 0), ACCENT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
                ("FONTSIZE", (0, 1), (-1, 1), 6.5),
                ("TEXTCOLOR", (0, 1), (-1, 1), GRIS),
                ("FONTSIZE", (0, 2), (-1, 2), 6.5),
                ("LINEABOVE", (0, 1), (-1, 1), 0.5, ENCRE),
            ]
        )
    )
    note = Paragraph(
        f"Valeurs en {unite}. Chaque bloc représente un huitième du mois le plus fort.",
        _styles()["petit"],
    )
    enveloppe = Table([[table], [note]], colWidths=[largeur], hAlign="LEFT")
    enveloppe.setStyle(TableStyle([("TOPPADDING", (0, 1), (0, 1), 4)]))
    return enveloppe


def construire_rapport(entree: ProjetEntree, resultats: ResultatsProjet) -> bytes:
    """Rapport complet, en mémoire."""
    tampon = io.BytesIO()
    document = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=f"DimSolaire — {entree.meta.nom}",
        author=entree.meta.auteur or "DimSolaire",
    )
    s = _styles()
    flux: list[object] = []
    largeur = 170 * mm

    # --- 1. Page de garde ---
    flux.append(Paragraph("DimSolaire", s["titre"]))
    flux.append(
        Paragraph("Rapport de dimensionnement photovoltaïque", s["sous_titre"])
    )
    flux.append(
        _tableau(
            [
                ["Projet", entree.meta.nom],
                ["Zone d'étude", entree.meta.zone],
                ["Auteur", entree.meta.auteur or "—"],
                ["Date", datetime.now().strftime("%d/%m/%Y à %H:%M")],
                ["Version du moteur", resultats.version_moteur],
                ["Statut global", resultats.statut_global],
            ],
            [45 * mm, largeur - 45 * mm],
            entete=False,
        )
    )
    if entree.meta.notes:
        flux.append(Spacer(1, 8))
        flux.append(Paragraph(entree.meta.notes, s["corps"]))

    # --- 2. Synthèse ---
    flux.append(Paragraph("Synthèse", s["h1"]))
    pv = resultats.pv.valeurs
    ond = resultats.onduleur.valeurs
    bat = resultats.batteries.valeurs
    inj = resultats.injection.valeurs
    prod = resultats.production.valeurs

    synthese: list[list[str]] = []
    if prod:
        synthese.append(
            ["Puissance crête retenue", f"{fmt(prod.pc_retenue_kwc)} kWc"]
        )
    if pv:
        synthese.append(
            ["Puissance crête installée", f"{fmt(pv.pc_installee_kwc)} kWc"]
        )
        synthese.append(
            [
                "Panneaux",
                f"{fmt_entier(pv.n_total)} ({pv.ns} en série × {pv.np} en parallèle)",
            ]
        )
    if ond:
        synthese.append(
            [
                "Onduleurs",
                f"{fmt_entier(ond.n_ond)} × {fmt(entree.onduleur.fiche.pnom_ac, 0)} kW"
                if entree.onduleur.fiche
                else fmt_entier(ond.n_ond),
            ]
        )
    if bat:
        synthese.append(
            [
                "Batteries",
                f"{fmt_entier(bat.n_total)} par abonné, parc {fmt(bat.u_parc_v, 1)} V",
            ]
        )
    if inj:
        synthese.append(
            [
                "Transformateurs",
                f"{fmt_entier(inj.n_tr)} × {fmt(inj.s_n_kva, 0)} kVA",
            ]
        )
        if inj.e_inj_an_kwh is not None:
            synthese.append(
                ["Énergie injectée", f"{fmt(inj.e_inj_an_kwh / 1000.0)} MWh/an"]
            )
    if synthese:
        flux.append(_tableau(synthese, [60 * mm, largeur - 60 * mm], entete=False))

    # --- 3. Hypothèses ---
    flux.append(Paragraph("Hypothèses et données d'entrée", s["h1"]))
    flux.append(
        _tableau(
            [
                ["Donnée", "Valeur", "Source ou référence"],
                [
                    "GHI",
                    f"{fmt(entree.potentiel.ghi_valeur, 3)} ({entree.potentiel.ghi_unite})",
                    entree.potentiel.source_ghi,
                ],
                [
                    "Surface",
                    f"{fmt(entree.potentiel.surface_valeur or 0)} "
                    f"{entree.potentiel.surface_unite}",
                    "Question ouverte Q-02",
                ],
                [
                    "Performance ratio",
                    fmt(entree.production.performance_ratio),
                    "Défaut 0,75",
                ],
                [
                    "Tension du système",
                    f"{fmt(entree.production.tension_systeme_v, 0)} V",
                    "Borne du cahier : 700 V",
                ],
                [
                    "Températures de conception",
                    f"{fmt(entree.pv.t_amb_min_c, 0)} à {fmt(entree.pv.t_amb_max_c, 0)} °C",
                    "Question ouverte Q-04",
                ],
                [
                    "Référence de Ns",
                    entree.pv.tension_reference_ns,
                    "Arbitrage A-02",
                ],
                [
                    "Facteur de puissance",
                    fmt(entree.onduleur.cos_phi),
                    "Question ouverte Q-05",
                ],
            ],
            [45 * mm, 45 * mm, largeur - 90 * mm],
        )
    )
    flux.append(Spacer(1, 6))
    flux.append(
        Paragraph(
            "<b>H-01</b> — L'irradiation retenue est celle d'un plan horizontal. "
            "Acceptable à 3,9° de latitude avec des modules inclinés de 5 à 10°.<br/>"
            "<b>H-02</b> — La production est l'énergie alternative en sortie d'onduleur.<br/>"
            "<b>H-03</b> — L'écrêtage des onduleurs n'est pas déduit.<br/>"
            "<b>H-04</b> — Les pertes en charge des transformateurs sont majorées.",
            s["petit"],
        )
    )

    flux.append(PageBreak())

    # --- 4. Potentiel solaire ---
    pot = resultats.potentiel.valeurs
    flux.append(Paragraph("1. Potentiel solaire", s["h1"]))
    if pot:
        flux.append(Paragraph("F-01 — Irradiation", s["h2"]))
        flux.append(
            _tableau(
                [
                    ["Grandeur", "Valeur"],
                    ["Irradiation journalière moyenne H", f"{fmt(pot.h_kwh_m2_j, 3)} kWh/m²/j"],
                    ["Irradiation annuelle", f"{fmt(pot.h_an_kwh_m2_an)} kWh/m²/an"],
                    ["Irradiance moyenne sur 24 h", f"{fmt(pot.g_moy_w_m2, 3)} W/m²"],
                    [
                        "Mois le plus défavorable",
                        f"{MOIS_NOMS[pot.mois_defavorable - 1]} — "
                        f"{fmt(pot.h_min_kwh_m2_j, 3)} kWh/m²/j",
                    ],
                ],
                [80 * mm, largeur - 80 * mm],
            )
        )
        flux.append(Spacer(1, 8))
        flux.append(_graphique_mensuel(pot.h_mensuel_kwh_m2_j, "kWh/m²/j"))

        if pot.e_pot_an_kwh is not None:
            flux.append(Paragraph("F-02 à F-04 — Potentiel de la zone", s["h2"]))
            flux.append(
                _tableau(
                    [
                        ["Grandeur", "Valeur"],
                        ["Surface retenue", f"{fmt(pot.surface_m2 or 0, 0)} m²"],
                        ["Potentiel brut journalier", f"{fmt(pot.e_pot_j_kwh or 0)} kWh/j"],
                        [
                            "Potentiel brut annuel",
                            f"{fmt((pot.e_pot_an_kwh or 0) / 1000.0)} MWh/an",
                        ],
                        [
                            "Puissance crête installable",
                            f"{fmt(pot.pc_max_surface_kwc or 0)} kWc",
                        ],
                        [
                            "Potentiel technique annuel",
                            f"{fmt((pot.e_tech_an_kwh or 0) / 1000.0)} MWh/an",
                        ],
                    ],
                    [80 * mm, largeur - 80 * mm],
                )
            )
    else:
        flux.append(Paragraph("Module non calculé.", s["corps"]))

    # --- 5. Bilan énergétique ---
    bil = resultats.bilan.valeurs
    flux.append(Paragraph("2. Bilan énergétique", s["h1"]))
    if bil:
        for profil in bil.profils:
            flux.append(Paragraph(f"Catégorie « {profil.nom} »", s["h2"]))
            lignes = [["Appareil", "E (Wh/j)", "Part"]]
            lignes += [
                [ligne.nom, fmt(ligne.e_wh_j, 0), f"{fmt(ligne.part_pct, 1)} %"]
                for ligne in profil.lignes
                if ligne.e_wh_j > 0
            ]
            lignes.append(["Total par abonné", fmt(profil.e_cons_wh_j, 0), "100,0 %"])
            flux.append(_tableau(lignes, [95 * mm, 40 * mm, largeur - 135 * mm]))
            flux.append(Spacer(1, 4))
            flux.append(
                Paragraph(
                    f"Puissance installée {fmt(profil.p_inst_w, 0)} W, "
                    f"puissance appelée {fmt(profil.p_app_w, 0)} W, "
                    f"{fmt_entier(profil.nb_abonnes)} abonnés.",
                    s["petit"],
                )
            )

        flux.append(Paragraph("F-07 — Consommation de la zone", s["h2"]))
        flux.append(
            _tableau(
                [
                    ["Grandeur", "Valeur"],
                    ["Journalière", f"{fmt(bil.e_zone_wh_j / 1000.0)} kWh/j"],
                    ["Annuelle", f"{fmt(bil.e_zone_an_kwh / 1000.0)} MWh/an"],
                    ["Puissance installée", f"{fmt(bil.p_inst_zone_w / 1000.0)} kW"],
                    ["Puissance appelée", f"{fmt(bil.p_app_zone_w / 1000.0)} kW"],
                ],
                [80 * mm, largeur - 80 * mm],
            )
        )
    else:
        flux.append(Paragraph("Module non calculé.", s["corps"]))

    flux.append(PageBreak())

    # --- 6. Dimensionnement ---
    flux.append(Paragraph("3. Dimensionnement technique", s["h1"]))
    if prod and prod.prod_installee:
        flux.append(Paragraph("F-09 et F-10 — Production", s["h2"]))
        flux.append(
            _tableau(
                [
                    ["Grandeur", "Valeur"],
                    ["Irradiation retenue", f"{fmt(prod.ir_kwh_m2_j, 3)} kWh/m²/j"],
                    ["Énergie à couvrir", f"{fmt(prod.e_cible_kwh_j)} kWh/j"],
                    [
                        "Puissance crête calculée",
                        f"{fmt(prod.pc_calculee_kwc or 0)} kWc",
                    ],
                    ["Puissance crête retenue", f"{fmt(prod.pc_retenue_kwc)} kWc"],
                    [
                        "Production annuelle installée",
                        f"{fmt(prod.prod_installee.an_kwh / 1000.0)} MWh/an",
                    ],
                    [
                        "Productible spécifique",
                        f"{fmt(prod.prod_installee.y_kwh_kwc)} kWh/kWc/an",
                    ],
                    [
                        "Taux de couverture effectif",
                        f"{fmt_pct(prod.taux_couverture_effectif or 0, 1)} %",
                    ],
                ],
                [80 * mm, largeur - 80 * mm],
            )
        )
        flux.append(Spacer(1, 8))
        flux.append(_graphique_mensuel(prod.prod_installee.mensuel_kwh, "kWh"))

    if pv and entree.pv.fiche:
        p = entree.pv.fiche
        flux.append(Paragraph("F-11 à F-18 — Champ photovoltaïque", s["h2"]))
        flux.append(
            _tableau(
                [
                    ["Grandeur", "Valeur"],
                    ["Panneau retenu", p.nom],
                    ["Puissance unitaire", f"{fmt(p.pmax, 0)} Wc"],
                    ["Nombre minimal (F-11)", fmt_entier(pv.n_min)],
                    [
                        "Configuration (F-13, F-14)",
                        f"{pv.ns} en série × {pv.np} en parallèle = {fmt_entier(pv.n_total)}",
                    ],
                    ["Puissance installée (F-12)", f"{fmt(pv.pc_installee_kwc)} kWc"],
                    ["Tension du champ", f"{fmt(pv.u_dc_v, 1)} V"],
                    ["Courant du champ", f"{fmt(pv.i_dc_a, 1)} A"],
                    ["Courant de court-circuit", f"{fmt(pv.i_cc_dc_a, 1)} A"],
                    [
                        "Température de cellule",
                        f"{fmt(pv.t_cell_min_c, 1)} à {fmt(pv.t_cell_max_c, 1)} °C",
                    ],
                    ["Voc par temps froid (F-16)", f"{fmt(pv.voc_max_v, 1)} V"],
                    [
                        "Vmp aux extrêmes (F-17)",
                        f"{fmt(pv.vmp_min_v, 1)} à {fmt(pv.vmp_max_v, 1)} V",
                    ],
                ],
                [80 * mm, largeur - 80 * mm],
            )
        )

    if ond and entree.onduleur.fiche:
        o = entree.onduleur.fiche
        flux.append(Paragraph("F-19 et F-20 — Onduleurs", s["h2"]))
        repartition = ", ".join(
            f"{r.nombre} × {r.chaines} chaînes" for r in ond.repartition
        )
        flux.append(
            _tableau(
                [
                    ["Grandeur", "Valeur"],
                    ["Onduleur retenu", o.nom],
                    ["Nombre", f"{fmt_entier(ond.n_ond)} × {fmt(o.pnom_ac, 0)} kW"],
                    ["Répartition des chaînes", repartition],
                    ["Ratio DC/AC global", fmt(ond.ratio_dc_ac)],
                    ["Courant par MPPT", f"{fmt(ond.i_mppt_a, 2)} A"],
                    ["Plage de Ns compatible", f"{ond.ns_min} à {ond.ns_max}"],
                    ["Courant alternatif par onduleur", f"{fmt(ond.iac_a, 2)} A"],
                    ["Puissance alternative totale", f"{fmt(ond.p_ac_total_kw, 0)} kW"],
                    ["Puissance apparente totale", f"{fmt(ond.s_ac_total_kva)} kVA"],
                ],
                [80 * mm, largeur - 80 * mm],
            )
        )

    if bat and entree.batteries.fiche:
        flux.append(Paragraph("F-21 à F-23 — Parc de batteries", s["h2"]))
        flux.append(
            _tableau(
                [
                    ["Grandeur", "Valeur"],
                    ["Batterie retenue", entree.batteries.fiche.nom],
                    ["Base d'énergie", entree.batteries.base_energie],
                    ["Énergie à stocker (F-21)", f"{fmt(bat.e_bat_wh, 0)} Wh"],
                    [
                        "Configuration (F-22)",
                        f"{bat.ns} en série × {bat.np} en parallèle "
                        f"= {fmt_entier(bat.n_total)}",
                    ],
                    ["Tension du parc", f"{fmt(bat.u_parc_v, 1)} V"],
                    ["Courant du parc", f"{fmt(bat.i_parc_a, 1)} A"],
                    ["Capacité", f"{fmt(bat.c_parc_ah, 0)} Ah"],
                    ["Énergie utilisable", f"{fmt(bat.e_util_wh, 0)} Wh"],
                    ["Autonomie obtenue", f"{fmt(bat.autonomie_j, 2)} jour(s)"],
                    ["Courant de décharge", f"{fmt(bat.i_dech_a, 1)} A"],
                    ["Durée de vie estimée", f"{fmt(bat.duree_vie_ans, 1)} ans"],
                ],
                [80 * mm, largeur - 80 * mm],
            )
        )

    cab = resultats.cables.valeurs
    if cab:
        flux.append(Paragraph("F-24 et F-25 — Câbles continus", s["h2"]))
        lignes = [["Câble", "Section", "Critère", "Chute réelle", "Pertes"]]
        for valeurs in (cab.dc_principal, cab.dc_chaine, cab.dc_batteries):
            if valeurs is None:
                continue
            lignes.append(
                [
                    valeurs.nom,
                    f"{valeurs.n_conducteurs} × {fmt(valeurs.section_mm2, 1)} mm²",
                    valeurs.critere,
                    f"{fmt_pct(valeurs.epsilon_reel, 2)} %",
                    f"{fmt(valeurs.p_joule_w, 1)} W",
                ]
            )
        flux.append(
            _tableau(lignes, [50 * mm, 32 * mm, 30 * mm, 28 * mm, largeur - 140 * mm])
        )
        if cab.epsilon_dc_total is not None:
            flux.append(Spacer(1, 4))
            flux.append(
                Paragraph(
                    f"Chute de tension continue totale : {fmt_pct(cab.epsilon_dc_total, 2)} %.",
                    s["petit"],
                )
            )

    flux.append(PageBreak())

    # --- 7. Injection ---
    flux.append(Paragraph("4. Injection au réseau", s["h1"]))
    if inj:
        flux.append(Paragraph("F-26 — Transformateurs", s["h2"]))
        flux.append(
            _tableau(
                [
                    ["Grandeur", "Valeur"],
                    ["Puissance apparente requise", f"{fmt(inj.s_requise_kva)} kVA"],
                    [
                        "Transformateurs",
                        f"{fmt_entier(inj.n_tr)} × {fmt(inj.s_n_kva, 0)} kVA",
                    ],
                    ["Puissance installée", f"{fmt(inj.s_installee_kva, 0)} kVA"],
                    ["Taux de charge global", f"{fmt_pct(inj.taux_charge, 1)} %"],
                    ["Courant nominal BT", f"{fmt(inj.i_n_bt_a, 1)} A"],
                    ["Courant BT maximal", f"{fmt(inj.i_bt_max_a, 1)} A"],
                    ["Courant nominal HTA", f"{fmt(inj.i_n_hta_a, 2)} A"],
                    ["Pertes à vide P0", f"{fmt(inj.p0_w, 0)} W"],
                    ["Pertes en charge Pk", f"{fmt(inj.pk_w, 0)} W"],
                ],
                [80 * mm, largeur - 80 * mm],
            )
        )

        if inj.cable_ac and inj.in_disjoncteur_a:
            c = inj.cable_ac
            flux.append(Paragraph("F-27 et F-28 — Câble AC et disjoncteur", s["h2"]))
            flux.append(
                _tableau(
                    [
                        ["Grandeur", "Valeur"],
                        [
                            "Section retenue",
                            f"{c.n_conducteurs} × {fmt(c.section_mm2, 1)} mm² ({c.critere})",
                        ],
                        ["Calibre du disjoncteur", f"{fmt(inj.in_disjoncteur_a, 0)} A"],
                        [
                            "Coordination",
                            f"{fmt(c.i_a, 1)} A ≤ {fmt(inj.in_disjoncteur_a, 0)} A "
                            f"≤ {fmt(c.iz_a, 0)} A",
                        ],
                        ["Chute de tension réelle", f"{fmt_pct(c.epsilon_reel, 3)} %"],
                        ["Pertes Joule", f"{fmt(c.p_joule_w, 1)} W"],
                    ],
                    [80 * mm, largeur - 80 * mm],
                )
            )

        if inj.bilan_mensuel:
            flux.append(Paragraph("F-29 — Bilan mensuel de l'injection", s["h2"]))
            lignes = [["Mois", "Production", "Pertes AC", "Pertes transfo.", "Injecté"]]
            for mensuel in inj.bilan_mensuel:
                lignes.append(
                    [
                        MOIS_NOMS[mensuel.mois - 1][:4],
                        fmt(mensuel.e_prod / 1000.0, 1),
                        fmt(mensuel.e_cable_ac / 1000.0, 2),
                        fmt((mensuel.e_p0 + mensuel.e_pk) / 1000.0, 2),
                        fmt(mensuel.e_inj / 1000.0, 1),
                    ]
                )
            flux.append(
                _tableau(
                    lignes, [26 * mm, 36 * mm, 32 * mm, 38 * mm, largeur - 132 * mm]
                )
            )
            flux.append(Spacer(1, 3))
            flux.append(Paragraph("Valeurs en MWh.", s["petit"]))

            flux.append(Paragraph("F-30 — Indicateurs", s["h2"]))
            indicateurs = [
                ["Indicateur", "Valeur"],
                [
                    "Énergie injectée annuelle",
                    f"{fmt((inj.e_inj_an_kwh or 0) / 1000.0)} MWh/an",
                ],
                ["Taux d'injection", f"{fmt_pct(inj.taux_injection or 0, 2)} %"],
                ["Heures équivalentes", f"{fmt(inj.h_eq or 0, 1)} h"],
                ["Facteur de charge", f"{fmt_pct(inj.facteur_charge or 0, 2)} %"],
            ]
            if inj.couverture_zone is not None:
                indicateurs.append(
                    ["Couverture équivalente", f"{fmt_pct(inj.couverture_zone, 2)} %"]
                )
            if inj.part_autoconsommee is not None:
                indicateurs.append(
                    ["Part autoconsommée", f"{fmt_pct(inj.part_autoconsommee, 2)} %"]
                )
            if inj.recettes_fcfa_an is not None:
                indicateurs.append(
                    ["Recettes annuelles", f"{fmt(inj.recettes_fcfa_an, 0)} FCFA"]
                )
            if inj.co2_evite_t_an is not None:
                indicateurs.append(
                    ["CO₂ évité", f"{fmt(inj.co2_evite_t_an, 1)} t/an"]
                )
            flux.append(_tableau(indicateurs, [80 * mm, largeur - 80 * mm]))
    else:
        flux.append(
            Paragraph(
                "Module non calculé : les onduleurs doivent être dimensionnés "
                "au préalable.",
                s["corps"],
            )
        )

    # --- 8. Vérifications ---
    flux.append(PageBreak())
    flux.append(Paragraph("Vérifications", s["h1"]))
    ordre = {Niveau.ERREUR: 0, Niveau.AVERTISSEMENT: 1, Niveau.INFO: 2}
    for message in sorted(resultats.messages, key=lambda m: ordre[m.niveau]):
        couleur = COULEURS_NIVEAU[message.niveau]
        bloc = [
            Paragraph(
                f'<font color="{couleur.hexval()}"><b>{message.code}</b></font> '
                f"— {message.titre}",
                s["corps"],
            ),
            Paragraph(message.message, s["petit"]),
        ]
        if message.suggestion:
            bloc.append(
                Paragraph(f"<i>Correctif : {message.suggestion}</i>", s["petit"])
            )
        bloc.append(Spacer(1, 6))
        flux.append(KeepTogether(bloc))

    # --- 9. Annexe : formules ---
    flux.append(PageBreak())
    flux.append(Paragraph("Annexe — Formules appliquées", s["h1"]))
    formules = [
        ["F-01", "H = G × 24 / 1 000 (GHI en W/m² moyennés sur 24 h)"],
        ["F-02", "E_pot = H × A"],
        ["F-03", "Pc_max = A × τ_occ × η_mod × 1 kW/m²"],
        ["F-04", "E_tech = Pc_max × H_an × PR"],
        ["F-05", "Eᵢ = Pᵢ × Nᵢ × tᵢ × Ksᵢ"],
        ["F-06", "E_cons = Σ Eᵢ"],
        ["F-07", "E_zone = Σ (E_cons,k × N_ab,k)"],
        ["F-08", "P_inst = Σ Pᵢ × Nᵢ ; P_app = Σ Pᵢ × Nᵢ × Ksᵢ"],
        ["F-09", "Pc = E_cible / (Ir × PR)"],
        ["F-10", "E_m = Pc × Hₘ × PR × dₘ"],
        ["F-11", "N_min = ⌈Pc × 1 000 / Pmax⌉"],
        ["F-12", "Pc_installée = N_total × Pmax / 1 000"],
        ["F-13", "Ns = ⌊Us / U_ref⌋"],
        ["F-14", "Np = ⌈N_min / Ns⌉ ; N_total = Ns × Np"],
        ["F-15", "I_DC = Np × Imp ; U_DC = Ns × Vmp"],
        ["F-16", "Voc,max = Ns × Voc × [1 + coef_voc/100 × (T_cell,min − 25)]"],
        ["F-17", "Vmp = Ns × Vmp × [1 + coef_vmp/100 × (T_cell − 25)]"],
        ["F-18", "T_cell = T_amb + (NOCT − 20) / 800 × G"],
        ["F-19", "N_ond = max(N_P ; N_E)"],
        ["F-20", "Iac = Pac / (√3 × U × cos φ) en triphasé"],
        ["F-21", "E_bat = E_base × part × N_aut × k_m / (DoD × η_bat × η_ond)"],
        ["F-22", "Ns_bat = arrondi(U_parc / u_nom) ; Np_bat = ⌈N_min / Ns_bat⌉"],
        ["F-23", "U_parc = Ns × u_nom ; I_parc = Np × i_nom"],
        ["F-24", "S = 2 × ρ × L × I / (ε × U), L en aller simple"],
        ["F-25", "S retenue = max(S_chute ; S_échauffement ; S_min)"],
        ["F-26", "S_requise = N_ond × S_ond × (1 + marge)"],
        ["F-27", "In = plus petit calibre ≥ k × Iac, avec Iac ≤ In ≤ Iz"],
        ["F-28", "S = √3 × ρ × L × I × cos φ / (ε × U) en triphasé exact"],
        ["F-29", "E_inj = E_tr − E_P0 − E_Pk"],
        ["F-30", "τ_inj = E_inj / E_prod ; h_eq = E_inj / P_ac"],
    ]
    flux.append(
        _tableau(
            [["Code", "Formule"], *formules], [18 * mm, largeur - 18 * mm]
        )
    )

    document.build(flux, onFirstPage=_pied_de_page, onLaterPages=_pied_de_page)
    return tampon.getvalue()
