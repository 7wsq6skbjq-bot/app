"""Profile catalog — read-only reference data for cut-list authoring.

Contains everything Portech knows about each manufacturer's profile system:
AT Fabrication doors (AT1000 / AT2000 / ATi series), Trifab VG450 flush-glaze,
Kawneer 1620 curtain wall. Used by the frontend Catalogue panel + the cut-list
optimizer.

Values verified against:
  - AT Fabrication official DXF (May 2026)
  - User-supplied BMO de la Rivière shop drawings (May 2026)
  - Hydro Extrusion DXF "Details des pieces de portes AT1000 et 2000" (Jun 2026)
    → provides the official AT ↔ Hydro code mapping below.

To add a new profile: append a dict to the relevant `profiles` list.
To add a new system entirely: add a new top-level entry to `SYSTEMS`.
"""

INCH_MM = 25.4


def _in(value: float) -> float:
    """Inches → mm rounded to 2 decimals."""
    return round(value * INCH_MM, 2)


# ===========================================================================
# Master AT ↔ Hydro mapping — single source of truth.
# Extracted from the official Hydro Extrusion DXF (Jun 2026).
# All four AT door series (AT1000 / AT2000 / ATi1000 / ATi2000) share the same
# extrusion pool — only the configuration (insulated / not) and the choice of
# moulure varies. Both parclose types can be used on ANY of the four series:
#   • AT1045 — moulure CARRÉE (large, 13.48 mm face) → pour verre simple 6 mm
#   • AT1050 — moulure PLATE  (mince, 14.3 mm face)  → pour thermos 25.4 mm
# The end client's glass spec drives which moulure is cut, not the door series.
# ===========================================================================
HYDRO_PARTS = {
    # ── AT1000 / ATi1000 family ──────────────────────────────────────────
    "ATT1005":   {"hydro": "MH80477", "internal": "40063-2",
                  "label": "Extrusion tête (head) — tube 2¼\"",
                  "dim_in": "2 1/4\" x 1 3/4\"", "dim_mm": "55.5 x 44.45"},
    "ATB1000":   {"hydro": "MH80476", "internal": "40063-1",
                  "label": "Extrusion base / seuil 3⅞\"",
                  "dim_in": "3 7/8\" x 1 3/4\"", "dim_mm": "98.43 x 44.45"},
    "ATV1010":   {"hydro": "MH80478", "internal": "40063-3",
                  "label": "Stile — strike side (montant côté gâche)",
                  "dim_in": "2\" x 1 3/4\"", "dim_mm": "50.8 x 44.45"},
    "ATV1015":   {"hydro": "MH80479", "internal": "40063-4",
                  "label": "Stile — lock side (montant côté serrure, usinage MS)",
                  "dim_in": "2 1/8\" x 1 3/4\"", "dim_mm": "53.975 x 44.45"},
    "ATV1020":   {"hydro": "MH80480", "internal": "40063-5",
                  "label": "Side extrusion (jambage latéral cadre)",
                  "dim_in": "—", "dim_mm": "—"},
    "ATV1025":   {"hydro": "MH80481", "internal": "40063-6",
                  "label": "Jamb extrusion (jambage du cadre)",
                  "dim_in": "—", "dim_mm": "—"},
    "AT1045":    {"hydro": "MH80485", "internal": "40063-10",
                  "label": "Moulure CARRÉE 13.48 mm — verre simple 6 mm",
                  "dim_in": "1/4\" carrée", "dim_mm": "13.48 face"},
    "AT1050":    {"hydro": "MH80486", "internal": "40063-11",
                  "label": "Moulure PLATE 14.3 mm — verre thermos 25.4 mm",
                  "dim_in": "—", "dim_mm": "14.3 face"},
    "ATCV1030":  {"hydro": "MH80483", "internal": "40063-8",
                  "label": "Cladding vertical — ATi1000",
                  "dim_in": "—", "dim_mm": "—"},
    "ATCHA1035": {"hydro": "MH80482", "internal": "40063-7",
                  "label": "Cladding horizontal — ATi1000",
                  "dim_in": "—", "dim_mm": "—"},
    "ATCHB1040": {"hydro": "MH80484", "internal": "40063-9",
                  "label": "Sweep extrusion (joint balai bas)",
                  "dim_in": "—", "dim_mm": "—"},
    # ── Accessoires AT1065 / AT1070 (longueurs non-standard) ─────────────
    # Codes vus dans le DXF Hydro sans description explicite — probablement
    # joints d'étanchéité ou garnitures. Longueurs spécifiques :
    "AT1065":    {"hydro": None, "internal": None,
                  "label": "Accessoire AT1065 — vendu en barres 5000 mm",
                  "dim_in": "—", "dim_mm": "—"},
    "AT1070":    {"hydro": None, "internal": None,
                  "label": "Accessoire AT1070 — vendu en barres 10'-0\" (3048 mm)",
                  "dim_in": "—", "dim_mm": "—"},
    # ── AT2000 / ATi2000 family ──────────────────────────────────────────
    "ATB2000":   {"hydro": "MH80321", "internal": "40777-2",
                  "label": "Extrusion base lourde 6⅞\"",
                  "dim_in": "6 7/8\" x 1 3/4\"", "dim_mm": "174.625 x 44.45"},
    "ATV2010":   {"hydro": "MH81325", "internal": "40777-6",
                  "label": "Stile — strike side (montant côté gâche, AT2000)",
                  "dim_in": "3 1/2\" x 1 3/4\"", "dim_mm": "88.9 x 44.45"},
    "ATV2015":   {"hydro": "MH81326", "internal": "40777-7",
                  "label": "Stile — lock side (montant côté serrure, AT2000)",
                  "dim_in": "3 5/8\" x 1 3/4\"", "dim_mm": "92.075 x 44.45"},
    "ATV2020":   {"hydro": "MH81327", "internal": "40777-8",
                  "label": "Side extrusion (jambage latéral cadre AT2000)",
                  "dim_in": "—", "dim_mm": "—"},
    "ATV2025":   {"hydro": "MH81320", "internal": "40777-1",
                  "label": "Jamb extrusion (jambage du cadre AT2000)",
                  "dim_in": "—", "dim_mm": "—"},
    "ATCV2030":  {"hydro": "MH81324", "internal": "40777-5",
                  "label": "Cladding vertical — ATi2000",
                  "dim_in": "—", "dim_mm": "—"},
    "ATCHB2040": {"hydro": "MH81323", "internal": "40777-4",
                  "label": "Sweep extrusion (joint balai bas AT2000)",
                  "dim_in": "—", "dim_mm": "—"},
}


def hydro_for(part_at: str | None) -> dict | None:
    """Lookup an AT code in the Hydro mapping. Returns None if unknown."""
    if not part_at:
        return None
    return HYDRO_PARTS.get(part_at)


# ===========================================================================
# Systems
# ===========================================================================
SYSTEMS = [
    # ──────────────────────────────────────────────────────────────────────
    # AT FABRICATION — Door series
    # ──────────────────────────────────────────────────────────────────────
    {
        "id": "at1000",
        "manufacturer": "AT Fabrication",
        "system": "AT1000",
        "category": "door",
        "description": "Porte aluminium non-isolée, sections 2¼\" symétriques. "
                       "Épaisseur du battant 1¾\" (44.45 mm). "
                       "Verre simple 6 mm. Configuration légère pour entrées commerciales standard.",
        "insulated": False,
        "leaf_thickness_mm": 44.45,
        "leaf_thickness_in": "1 3/4\"",
        "glass_thickness_default_mm": 6.0,
        "standard_opening_mm": {"width": 914.4, "height": 2133.6},
        "standard_leaf_mm": {"width": 799.30, "height": 2111.40},
        "offsets_mm": {"width": 115.10, "height": 22.20},
        "default_stock_bar_length_mm": 6800,
        "profiles": [
            {"label": "Traverse haute (tête) 2¼\"", "dim_in": "2 1/4\" x 1 3/4\"", "dim_mm": "55.5 x 44.45",
             "part_number": "ATT1005", "hydro_code": "MH80477", "internal_code": "40063-2",
             "usage": "Linteau de porte AT1000. Coupe = largeur du battant."},
            {"label": "Traverse basse (base) 3⅞\"", "dim_in": "3 7/8\" x 1 3/4\"", "dim_mm": "98.43 x 44.45",
             "part_number": "ATB1000", "hydro_code": "MH80476", "internal_code": "40063-1",
             "usage": "Seuil renforcé 3⅞\" (même extrusion que la tête AT2000). Coupe = largeur du battant."},
            {"label": "Montant côté charnière (strike) 2\"", "dim_in": "2\" x 1 3/4\"", "dim_mm": "50.8 x 44.45",
             "part_number": "ATV1010", "hydro_code": "MH80478", "internal_code": "40063-3",
             "usage": "Stile côté gâche. Coupe = hauteur du battant."},
            {"label": "Montant côté serrure (lock) 2⅛\"", "dim_in": "2 1/8\" x 1 3/4\"", "dim_mm": "53.975 x 44.45",
             "part_number": "ATV1015", "hydro_code": "MH80479", "internal_code": "40063-4",
             "usage": "Stile côté serrure (usinage MS Adams Rite)."},
            {"label": "Moulure CARRÉE 13.48 — verre simple 6 mm", "dim_in": "1/4\" carrée", "dim_mm": "13.48 face",
             "part_number": "AT1045", "hydro_code": "MH80485", "internal_code": "40063-10",
             "usage": "Moulure LARGE (carrée) si le client met du verre SIMPLE 6 mm. 4 V + 4 H par porte (mitrés 45°)."},
            {"label": "Moulure PLATE 14.3 — verre thermos 25.4 mm", "dim_in": "—", "dim_mm": "14.3 face",
             "part_number": "AT1050", "hydro_code": "MH80486", "internal_code": "40063-11",
             "usage": "Moulure MINCE (plate) si le client met du THERMOS 25.4 mm. 4 V + 4 H par porte. "
                      "✱ Les deux moulures sont interchangeables sur n'importe quelle porte AT — le choix dépend du verre commandé."},
        ],
        "hardware_typical": [
            "Charnière continue UH-120-DA (AT Fabrication)",
            "Serrure MS Adams Rite — ex. ADAM-MS1853S320",
            "Cylindre extérieur ILCO Kaba",
            "Gâche / strike Adams Rite",
            "Poignée à tirer (ladder pull) — ex. UNIQ-AC4-36",
            "Push paddle intérieur",
        ],
        "notes": [
            "Verre simple 6 mm pour les modèles AT1000.",
            "Aucun cladding (revêtement) — version non isolée.",
        ],
    },
    {
        "id": "at2000",
        "manufacturer": "AT Fabrication",
        "system": "AT2000",
        "category": "door",
        "description": "Porte aluminium non-isolée, sections asymétriques heavy-duty. "
                       "Épaisseur du battant 1¾\" (44.45 mm). "
                       "Idéale pour fort trafic commercial (banques, dépanneurs, magasins).",
        "insulated": False,
        "leaf_thickness_mm": 44.45,
        "leaf_thickness_in": "1 3/4\"",
        "glass_thickness_default_mm": 6.0,
        "standard_opening_mm": {"width": 914.4, "height": 2133.6},
        "standard_leaf_mm": {"width": 723.10, "height": 2111.40},
        "offsets_mm": {"width": 191.30, "height": 22.20},
        "default_stock_bar_length_mm": 6800,
        "profiles": [
            {"label": "Tête 3⅞\"", "dim_in": "3 7/8\" x 1 3/4\"", "dim_mm": "98.43 x 44.45",
             "part_number": "ATB1000", "hydro_code": "MH80476", "internal_code": "40063-1",
             "usage": "Linteau AT2000 — réutilise l'extrusion ATB1000 (base AT1000)."},
            {"label": "Base 6⅞\"", "dim_in": "6 7/8\" x 1 3/4\"", "dim_mm": "174.625 x 44.45",
             "part_number": "ATB2000", "hydro_code": "MH80321", "internal_code": "40777-2",
             "usage": "Traverse basse renforcée (caractéristique AT2000)."},
            {"label": "Jambage côté charnière (strike) 3½\"", "dim_in": "3 1/2\" x 1 3/4\"", "dim_mm": "88.9 x 44.45",
             "part_number": "ATV2010", "hydro_code": "MH81325", "internal_code": "40777-6",
             "usage": "Stile côté gâche."},
            {"label": "Jambage côté serrure (lock) 3⅝\"", "dim_in": "3 5/8\" x 1 3/4\"", "dim_mm": "92.075 x 44.45",
             "part_number": "ATV2015", "hydro_code": "MH81326", "internal_code": "40777-7",
             "usage": "Stile côté serrure."},
            {"label": "Moulure CARRÉE 13.48 — verre simple 6 mm", "dim_in": "1/4\" carrée", "dim_mm": "13.48 face",
             "part_number": "AT1045", "hydro_code": "MH80485", "internal_code": "40063-10",
             "usage": "Moulure LARGE (carrée) si le client met du verre SIMPLE 6 mm."},
            {"label": "Moulure PLATE 14.3 — verre thermos 25.4 mm", "dim_in": "—", "dim_mm": "14.3 face",
             "part_number": "AT1050", "hydro_code": "MH80486", "internal_code": "40063-11",
             "usage": "Moulure MINCE (plate) si le client met du THERMOS 25.4 mm. "
                      "✱ Les deux moulures sont interchangeables — choisies selon le verre commandé."},
        ],
        "hardware_typical": [
            "Charnière continue UH-120-DA renforcée",
            "Serrure MS Adams Rite (souvent MS1850S ou MS1853)",
            "Cylindre EXT + INT (selon configuration)",
            "Astragale si porte double",
            "Barre anti-panique ADAM-8400 (option)",
            "Ferme-porte LCN 4040XP ou Norton 1601 (selon spec)",
        ],
        "notes": [
            "Verre simple 6 mm en standard.",
            "Existe en variante hybride AT1000-base-AT2000 : sections AT1000 + base 6⅞\".",
        ],
    },
    {
        "id": "ati1000",
        "manufacturer": "AT Fabrication",
        "system": "ATi1000",
        "category": "door",
        "description": "Porte aluminium ISOLÉE (rupture de pont thermique). Sections 2¼\". "
                       "Épaisseur du battant 2¼\" (57.15 mm) = AT1000 1¾\" + cladding extérieur. "
                       "Verre thermos 25.4 mm + revêtement (cladding) extérieur 5.7 mm plus court "
                       "que le battant sur chaque axe.",
        "insulated": True,
        "leaf_thickness_mm": 57.15,
        "leaf_thickness_in": "2 1/4\"",
        "glass_thickness_default_mm": 25.4,
        "standard_opening_mm": {"width": 914.4, "height": 2133.6},
        "standard_leaf_mm": {"width": 799.30, "height": 2111.40},
        "offsets_mm": {"width": 115.10, "height": 22.20},
        "cladding_offset_mm": 5.7,
        "default_stock_bar_length_mm": 6800,
        "profiles": [
            {"label": "Tête isolée (tube 2¼\")", "dim_in": "2 1/4\" x 2 1/4\"", "dim_mm": "55.5 x 57.15",
             "part_number": "ATT1005", "hydro_code": "MH80477", "internal_code": "40063-2",
             "usage": "Linteau ATi1000 — même extrusion qu'AT1000, isolation via cladding."},
            {"label": "Base isolée 3⅞\"", "dim_in": "3 7/8\" x 2 1/4\"", "dim_mm": "98.43 x 57.15",
             "part_number": "ATB1000", "hydro_code": "MH80476", "internal_code": "40063-1",
             "usage": "Seuil renforcé 3⅞\"."},
            {"label": "Montant côté charnière (strike) 2\"", "dim_in": "2\" x 2 1/4\"", "dim_mm": "50.8 x 57.15",
             "part_number": "ATV1010", "hydro_code": "MH80478", "internal_code": "40063-3",
             "usage": "Stile côté gâche."},
            {"label": "Montant côté serrure (lock) 2⅛\"", "dim_in": "2 1/8\" x 2 1/4\"", "dim_mm": "53.975 x 57.15",
             "part_number": "ATV1015", "hydro_code": "MH80479", "internal_code": "40063-4",
             "usage": "Stile côté serrure (usinage MS)."},
            {"label": "Cladding vertical", "dim_in": "—", "dim_mm": "leaf_height − 5.7",
             "part_number": "ATCV1030", "hydro_code": "MH80483", "internal_code": "40063-8",
             "usage": "Revêtement extérieur vertical. 2 par porte (extérieur + intérieur)."},
            {"label": "Cladding horizontal", "dim_in": "—", "dim_mm": "leaf_width − 5.7",
             "part_number": "ATCHA1035", "hydro_code": "MH80482", "internal_code": "40063-7",
             "usage": "Revêtement extérieur horizontal. 2 par porte."},
            {"label": "Sweep (joint balai bas)", "dim_in": "—", "dim_mm": "leaf_width",
             "part_number": "ATCHB1040", "hydro_code": "MH80484", "internal_code": "40063-9",
             "usage": "Joint balai inférieur (option étanchéité)."},
            {"label": "Moulure CARRÉE 13.48 — verre simple 6 mm", "dim_in": "1/4\" carrée", "dim_mm": "13.48 face",
             "part_number": "AT1045", "hydro_code": "MH80485", "internal_code": "40063-10",
             "usage": "Moulure LARGE pour verre simple (rare sur porte isolée mais possible)."},
            {"label": "Moulure PLATE 14.3 — verre thermos 25.4 mm", "dim_in": "—", "dim_mm": "14.3 face",
             "part_number": "AT1050", "hydro_code": "MH80486", "internal_code": "40063-11",
             "usage": "Moulure MINCE pour thermos (configuration standard ATi). ✱ Les 2 moulures sont interchangeables — choix selon verre commandé."},
        ],
        "hardware_typical": [
            "Charnière continue UH-120-DA",
            "Serrure MS Adams Rite",
            "Joint balai (bottom sweep) isolant — ex. Pemko 252",
            "Seuil isolé",
        ],
        "notes": [
            "Verre thermos 25.4 mm (1\") en standard.",
            "Le cladding est essentiel à l'étanchéité — toujours fournir 2V + 2H.",
        ],
    },
    {
        "id": "ati2000",
        "manufacturer": "AT Fabrication",
        "system": "ATi2000",
        "category": "door",
        "description": "Porte aluminium ISOLÉE, sections asymétriques heavy-duty. "
                       "Épaisseur du battant 2¼\" (57.15 mm) = AT2000 1¾\" + cladding extérieur. "
                       "Verre thermos 25.4 mm + cladding. Pour zones tempérées exigeantes.",
        "insulated": True,
        "leaf_thickness_mm": 57.15,
        "leaf_thickness_in": "2 1/4\"",
        "glass_thickness_default_mm": 25.4,
        "standard_opening_mm": {"width": 914.4, "height": 2133.6},
        "standard_leaf_mm": {"width": 723.10, "height": 2111.40},
        "offsets_mm": {"width": 191.30, "height": 22.20},
        "cladding_offset_mm": 5.7,
        "default_stock_bar_length_mm": 6800,
        "profiles": [
            {"label": "Tête isolée 3⅞\"", "dim_in": "3 7/8\" x 2 1/4\"", "dim_mm": "98.43 x 57.15",
             "part_number": "ATB1000", "hydro_code": "MH80476", "internal_code": "40063-1",
             "usage": "Linteau ATi2000 — réutilise ATB1000."},
            {"label": "Base isolée 6⅞\"", "dim_in": "6 7/8\" x 2 1/4\"", "dim_mm": "174.625 x 57.15",
             "part_number": "ATB2000", "hydro_code": "MH80321", "internal_code": "40777-2",
             "usage": "Traverse basse renforcée."},
            {"label": "Jambage charnière (strike) 3½\"", "dim_in": "3 1/2\" x 2 1/4\"", "dim_mm": "88.9 x 57.15",
             "part_number": "ATV2010", "hydro_code": "MH81325", "internal_code": "40777-6"},
            {"label": "Jambage serrure (lock) 3⅝\"", "dim_in": "3 5/8\" x 2 1/4\"", "dim_mm": "92.075 x 57.15",
             "part_number": "ATV2015", "hydro_code": "MH81326", "internal_code": "40777-7"},
            {"label": "Cladding vertical", "dim_in": "—", "dim_mm": "leaf_height − 5.7",
             "part_number": "ATCV2030", "hydro_code": "MH81324", "internal_code": "40777-5"},
            {"label": "Cladding horizontal", "dim_in": "—", "dim_mm": "leaf_width − 5.7",
             "part_number": "ATCHA1035", "hydro_code": "MH80482", "internal_code": "40063-7",
             "usage": "Cladding horizontal (réutilise ATCHA1035 sur ATi2000)."},
            {"label": "Sweep (joint balai bas)", "dim_in": "—", "dim_mm": "leaf_width",
             "part_number": "ATCHB2040", "hydro_code": "MH81323", "internal_code": "40777-4"},
            {"label": "Moulure CARRÉE 13.48 — verre simple 6 mm", "dim_in": "1/4\" carrée", "dim_mm": "13.48 face",
             "part_number": "AT1045", "hydro_code": "MH80485", "internal_code": "40063-10"},
            {"label": "Moulure PLATE 14.3 — verre thermos 25.4 mm", "dim_in": "—", "dim_mm": "14.3 face",
             "part_number": "AT1050", "hydro_code": "MH80486", "internal_code": "40063-11",
             "usage": "✱ Les 2 moulures sont interchangeables sur n'importe quelle porte AT — choix selon verre commandé."},
        ],
        "hardware_typical": [
            "Comme AT2000 + joints thermiques",
        ],
        "notes": [
            "Combinaison la plus performante thermiquement — usage en façade exposée.",
        ],
    },
    # ──────────────────────────────────────────────────────────────────────
    # TRIFAB VG450 — Flush Glaze
    # ──────────────────────────────────────────────────────────────────────
    {
        "id": "trifab_vg450",
        "manufacturer": "Trifab",
        "system": "VG450",
        "category": "flush_glaze",
        "description": "Encadrement à poche non-isolé. Système Flush Glaze pour vitrages "
                       "encadrés (devantures, séparations vitrées). Profilés 1¾\" × 4½\".",
        "insulated": False,
        "glass_thickness_default_mm": 6.0,
        "default_stock_bar_length_mm": 7315,
        "profiles": [
            {"label": "Tube à poche", "dim_in": "1 3/4\" x 4 1/2\"", "dim_mm": "44.45 x 114.3",
             "part_number": "450CG005",
             "usage": "Linteau supérieur (toujours) + traverses intermédiaires entre 2 vitrages superposés."},
            {"label": "Tube escalier", "dim_in": "1 3/4\" x 4 1/2\"", "dim_mm": "44.45 x 114.3",
             "part_number": "450CG011",
             "usage": "Bas de chaque vitrage (y compris bas du vitrage AU-DESSUS d'une porte)."},
            {"label": "Garniture de vitrage 6mm", "dim_in": "—", "dim_mm": "—",
             "part_number": "027074",
             "usage": "Joint d'étanchéité. Quantité = Σ(périmètre vitres) × 2 en mm linéaire."},
        ],
        "calculation_rules": [
            "GARNITURE #027074 = (somme périmètres thermos) × 2 mm linéaire.",
            "Linteau supérieur = TOUJOURS Tube à poche.",
            "Bas de chaque vitrage = TOUJOURS Tube escalier.",
            "Traverses entre 2 vitrages superposés = Tube à poche.",
        ],
        "notes": [
            "Verre simple 6 mm en standard.",
            "Pour porte intégrée (FG mixte) : utiliser le gabarit guidé + cocher 'porte intégrée'.",
        ],
    },
    # ──────────────────────────────────────────────────────────────────────
    # KAWNEER 1620 — Curtain Wall (Mur-rideau)
    # ──────────────────────────────────────────────────────────────────────
    {
        "id": "kawneer_1620",
        "manufacturer": "Kawneer",
        "system": "1620",
        "category": "curtain_wall",
        "description": "Mur-rideau isolé (rupture thermique). Système modulaire pour façades "
                       "vitrées complètes. Meneaux 2\" × 3¾\".",
        "insulated": True,
        "glass_thickness_default_mm": 25.4,
        "default_stock_bar_length_mm": 7315,
        "profiles": [
            {"label": "Meneau 2\" × 3¾\"", "dim_in": "2\" x 3 3/4\"", "dim_mm": "50.8 x 95.25",
             "part_number": "178-001",
             "usage": "Meneaux verticaux ET horizontaux du mur-rideau."},
            {"label": "Couvercle 2\" × ¾\"", "dim_in": "2\" x 3/4\"", "dim_mm": "50.8 x 19.05",
             "part_number": "178-006",
             "usage": "Couvercle décoratif extérieur. Même longueur que le meneau."},
            {"label": "Plaque à pression 2\"", "dim_in": "2\" plate", "dim_mm": "50.8 face",
             "part_number": "178-300",
             "usage": "Plaque qui maintient le verre contre le meneau. Même longueur."},
            {"label": "Bris thermique", "dim_in": "—", "dim_mm": "—",
             "part_number": "162-310",
             "usage": "Rupture thermique. Quantité = Σ linéaire de TOUS les meneaux V+H en mm."},
            {"label": "Garniture ext + int", "dim_in": "—", "dim_mm": "—",
             "part_number": "027-850",
             "usage": "Joint vitrage (ext + int). Quantité = Σ(périmètre thermos) × 2 mm linéaire."},
        ],
        "calculation_rules": [
            "Pour chaque meneau (V ou H) : 1 meneau #178-001 + 1 couvercle #178-006 + 1 plaque #178-300, "
            "tous de la même longueur.",
            "BRIS THERMIQUE #162-310 = Σ linéaire de TOUS les meneaux V+H (en mm).",
            "GARNITURE #027-850 = (somme périmètres thermos) × 2 mm linéaire.",
            "Si porte intégrée : minimum 2 meneaux verticaux côté porte (souvent hauteur différente "
            "des meneaux côté libre).",
        ],
        "finishes_typical": [
            "Fini extérieur : Anodisé Champagne (couvercles)",
            "Fini intérieur : Anodisé Clair Classe II (10 microns) sur les meneaux",
        ],
        "notes": [
            "Verre thermos 25.4 mm (1\") en standard.",
            "Le nombre de meneaux dépend de l'architecte — peut être 2, 4, 5, 13, 15… "
            "Toujours saisir manuellement la géométrie.",
        ],
    },
]


def get_catalog() -> dict:
    """Public entry point. Returns the full catalog grouped by category."""
    by_cat: dict[str, list] = {"door": [], "flush_glaze": [], "curtain_wall": []}
    for sys in SYSTEMS:
        by_cat.setdefault(sys["category"], []).append(sys)
    return {
        "categories": [
            {"id": "door", "label": "Portes battantes (AT Fabrication)",
             "count": len(by_cat["door"]), "systems": by_cat["door"]},
            {"id": "flush_glaze", "label": "Flush Glaze (Trifab)",
             "count": len(by_cat["flush_glaze"]), "systems": by_cat["flush_glaze"]},
            {"id": "curtain_wall", "label": "Mur-rideau (Kawneer)",
             "count": len(by_cat["curtain_wall"]), "systems": by_cat["curtain_wall"]},
        ],
        "total_systems": len(SYSTEMS),
        "parclose_face_mm": 13.48,
    }
