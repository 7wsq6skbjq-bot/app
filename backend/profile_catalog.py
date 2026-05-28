"""Profile catalog — read-only reference data for cut-list authoring.

Contains everything Portech knows about each manufacturer's profile system:
AT Fabrication doors (AT1000 / AT2000 / ATi series), Trifab VG450 flush-glaze,
Kawneer 1620 curtain wall. Used by the frontend Catalogue panel + the cut-list
optimizer.

Values verified against:
  - AT Fabrication official DXF (May 2026)
  - User-supplied BMO de la Rivière shop drawings (May 2026)
  - Portech standard parclose 1/4" carrée = 13.48 mm face width.

To add a new profile: append a dict to the relevant `profiles` list.
To add a new system entirely: add a new top-level entry to `SYSTEMS`.
"""

INCH_MM = 25.4


def _in(value: float) -> float:
    """Inches → mm rounded to 2 decimals."""
    return round(value * INCH_MM, 2)


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
                       "Verre simple 6 mm. Configuration légère pour entrées commerciales standard.",
        "insulated": False,
        "glass_thickness_default_mm": 6.0,
        "standard_opening_mm": {"width": 914.4, "height": 2133.6},
        "standard_leaf_mm": {"width": 799.30, "height": 2111.40},
        "offsets_mm": {"width": 115.10, "height": 22.20},
        "profiles": [
            {"label": "Traverse haute (tête)", "dim_in": "2 1/4\" x 4\"", "dim_mm": "55.5 x 101.6", "part_number": None,
             "usage": "Linteau de porte. Coupe = largeur du battant."},
            {"label": "Traverse basse (base)", "dim_in": "2 1/4\" x 4\"", "dim_mm": "55.5 x 101.6", "part_number": None,
             "usage": "Seuil de porte. Coupe = largeur du battant."},
            {"label": "Montant côté charnière", "dim_in": "2\" x 4\"", "dim_mm": "50.8 x 101.6", "part_number": None,
             "usage": "Montant vertical, côté gonds. Coupe = hauteur du battant."},
            {"label": "Montant côté serrure", "dim_in": "2 1/8\" x 4\"", "dim_mm": "53.975 x 101.6", "part_number": None,
             "usage": "Montant vertical, côté serrure (légèrement plus large pour usinage MS)."},
            {"label": "Parclose carrée vitrage 1/4\"", "dim_in": "1/4\" carrée", "dim_mm": "13.48 face",
             "part_number": None,
             "usage": "Moulure de retenue du verre. 4 V + 4 H par porte (coupes mitrées 45°)."},
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
                       "Idéale pour fort trafic commercial (banques, dépanneurs, magasins).",
        "insulated": False,
        "glass_thickness_default_mm": 6.0,
        "standard_opening_mm": {"width": 914.4, "height": 2133.6},
        "standard_leaf_mm": {"width": 723.10, "height": 2111.40},
        "offsets_mm": {"width": 191.30, "height": 22.20},
        "profiles": [
            {"label": "Tête 3 7/8\"", "dim_in": "3 7/8\" x 4\"", "dim_mm": "98.43 x 101.6", "part_number": None,
             "usage": "Linteau de porte AT2000. Hauteur 3⅞\"."},
            {"label": "Base 6 7/8\"", "dim_in": "6 7/8\" x 4\"", "dim_mm": "174.625 x 101.6", "part_number": None,
             "usage": "Traverse basse renforcée (caractéristique AT2000)."},
            {"label": "Jambage côté charnière 3 1/2\"", "dim_in": "3 1/2\" x 4\"", "dim_mm": "88.9 x 101.6",
             "part_number": None, "usage": "Montant vertical, côté gonds."},
            {"label": "Jambage côté serrure 3 5/8\"", "dim_in": "3 5/8\" x 4\"", "dim_mm": "92.075 x 101.6",
             "part_number": None, "usage": "Montant vertical, côté serrure."},
            {"label": "Parclose carrée vitrage 1/4\"", "dim_in": "1/4\" carrée", "dim_mm": "13.48 face",
             "part_number": None, "usage": "Moulure de retenue. 4 V + 4 H par porte (coupes mitrées 45°)."},
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
                       "Verre thermos 25.4 mm + revêtement (cladding) extérieur 5.7 mm plus court "
                       "que le battant sur chaque axe.",
        "insulated": True,
        "glass_thickness_default_mm": 25.4,
        "standard_opening_mm": {"width": 914.4, "height": 2133.6},
        "standard_leaf_mm": {"width": 799.30, "height": 2111.40},
        "offsets_mm": {"width": 115.10, "height": 22.20},
        "cladding_offset_mm": 5.7,
        "profiles": [
            {"label": "Tête isolée", "dim_in": "2 1/4\" x 4\"", "dim_mm": "55.5 x 101.6", "part_number": None,
             "usage": "Identique AT1000 + rupture thermique intégrée."},
            {"label": "Base isolée", "dim_in": "2 1/4\" x 4\"", "dim_mm": "55.5 x 101.6", "part_number": None,
             "usage": "Idem traverse haute."},
            {"label": "Cladding vertical", "dim_in": "—", "dim_mm": "leaf_height − 5.7", "part_number": None,
             "usage": "Revêtement extérieur. 2 par porte (extérieur + intérieur)."},
            {"label": "Cladding horizontal", "dim_in": "—", "dim_mm": "leaf_width − 5.7", "part_number": None,
             "usage": "Revêtement extérieur horizontal. 2 par porte."},
            {"label": "Parclose carrée vitrage 1/4\"", "dim_in": "1/4\" carrée", "dim_mm": "13.48 face",
             "part_number": None, "usage": "Idem AT1000."},
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
                       "Verre thermos 25.4 mm + cladding. Pour zones tempérées exigeantes.",
        "insulated": True,
        "glass_thickness_default_mm": 25.4,
        "standard_opening_mm": {"width": 914.4, "height": 2133.6},
        "standard_leaf_mm": {"width": 723.10, "height": 2111.40},
        "offsets_mm": {"width": 191.30, "height": 22.20},
        "cladding_offset_mm": 5.7,
        "profiles": [
            {"label": "Tête isolée 3 7/8\"", "dim_in": "3 7/8\" x 4\"", "dim_mm": "98.43 x 101.6", "part_number": None},
            {"label": "Base isolée 6 7/8\"", "dim_in": "6 7/8\" x 4\"", "dim_mm": "174.625 x 101.6",
             "part_number": None},
            {"label": "Jambage isolé 3 1/2\" (charnière)", "dim_in": "3 1/2\"", "dim_mm": "88.9 x 101.6",
             "part_number": None},
            {"label": "Jambage isolé 3 5/8\" (serrure)", "dim_in": "3 5/8\"", "dim_mm": "92.075 x 101.6",
             "part_number": None},
            {"label": "Cladding vertical", "dim_in": "—", "dim_mm": "leaf_height − 5.7", "part_number": None},
            {"label": "Cladding horizontal", "dim_in": "—", "dim_mm": "leaf_width − 5.7", "part_number": None},
            {"label": "Parclose carrée vitrage 1/4\"", "dim_in": "1/4\" carrée", "dim_mm": "13.48 face",
             "part_number": None},
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
