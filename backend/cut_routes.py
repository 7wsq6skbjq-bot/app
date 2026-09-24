"""Cut List routes — upload, OCR extraction, DXF parsing, optimization, PDF.

Endpoints (mounted under /api/admin):
- GET    /cuts                          List cut lists
- POST   /cuts                          Create
- GET    /cuts/{id}                     Read
- PUT    /cuts/{id}                     Update
- DELETE /cuts/{id}                     Delete
- POST   /cuts/extract                  Upload PDF/image, run Gemini Vision OCR
- POST   /cuts/extract-dxf              Upload DXF, parse with ezdxf
- POST   /cuts/{id}/optimize            Run the 1D optimizer on the cut list
- GET    /cuts/{id}/export.csv          CSV export
- GET    /cuts/{id}/export.pdf          PDF workshop sheet
"""
import csv
import io
import json
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from emergentintegrations.llm.chat import (
    FileContentWithMimeType,
    LlmChat,
    UserMessage,
)
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from cut_dxf import parse_dxf
from cut_door_breakdown import decompose_at_door
from cut_models import (
    DEFAULT_ALU_STOCK_LENGTHS_MM,
    DEFAULT_SAW_KERF_MM,
    CutItem,
    CutList,
    CutListIn,
    FrameSpecs,
    ITEM_TYPES,
)
from cut_optimizer import optimize_cut_list
from cut_pdf import render_cut_list_pdf
from cut_templates import build_elevation_from_template
from profile_catalog import get_catalog

logger = logging.getLogger("portech.cuts")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
OCR_MODEL = os.environ.get("EXPENSE_OCR_MODEL", "gemini-3-flash-preview")

ALLOWED_PLAN_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
ALLOWED_DXF_EXTS = {".dxf"}
MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".heic": "image/heic", ".heif": "image/heif",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

OCR_SYSTEM = (
    "Tu es un assistant expert en quincaillerie de portes commerciales "
    "(Portech, Grand Montréal). Tu analyses des plans d'atelier (AT Fabrication, "
    "Kawneer, Reynaers, etc.) pour produire une LISTE DE COUPE PRÊTE À "
    "FABRIQUER. Tu sais lire les CARTOUCHES de détails techniques où sont "
    "indiquées les épaisseurs de profilés, les lousses, le finis (couleur "
    "anodisée), la SÉRIE de porte (AT1000, AT2000), et la liste exhaustive "
    "de quincaillerie avec numéros de pièce (UH-120-DA, ADAM-MS1853S320, "
    "UNIQ-AC4-36, ILCO-..., etc.). Tu retournes UNIQUEMENT du JSON valide."
)

OCR_USER = (
    "Analyse ce plan d'atelier commercial et produis une LISTE DE COUPE EXHAUSTIVE.\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "ÉTAPE 0 — LIRE L'ENCADRÉ TECHNIQUE EN HAUT À DROITE (PRIORITÉ ABSOLUE)\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "Chaque plan contient en HAUT-À-DROITE un encadré (souvent texte rouge) qui\n"
    "décrit PRÉCISÉMENT pour chaque élévation (FG01, MR2, E1…) :\n"
    "- LE SYSTÈME exact (ex: 'ENCADREMENT À POCHE NON-ISOLÉ SÉRIE TRIFAB VG450',\n"
    "  'MUR-RIDEAU SÉRIE KAWNEER 1620', 'PORTE NON-ISOLÉE SÉRIE AT2000 DE AT FABRICATION')\n"
    "- LE FINI EXT / FINI INT (souvent différents : ex 'Champagne' / 'Clair classe II 10µ')\n"
    "- LA LISTE DES PROFILÉS avec leur NUMÉRO DE PIÈCE exact et leurs dimensions\n"
    "  Ex (Trifab VG450) : '·Tube 2 poches 1¾ × 4½ #450CG005', "
    "'·Tube escalier 1¾ × 4½ #450CG011', '·Garniture de vitrage 6mm #027074'\n"
    "  Ex (Kawneer 1620) : '·Meneau 2 × 3¾ #178-001', '·Couvercle 2 × ¾ #178-006', "
    "'·Plaque à pression 2 #178-300', '·Bris thermique #162-310', "
    "'·Garniture ext et int #027-850'\n"
    "  Ex (AT2000)       : '·tête 3⅞', '·jambage 3⅝', "
    "'·jambage côté charnière 3½', '·base 6⅞', '·épaisseur 1¾', "
    "'·parclose carrée pour vitrage simple ¼'\n"
    "\n"
    "Tu DOIS recopier ces numéros de pièce EXACTEMENT dans `part_number` et\n"
    "renseigner `manufacturer` (Trifab/Kawneer/AT Fabrication/Adams Rite/etc).\n"
    "Si un profilé est listé dans l'encadré, il DOIT apparaître dans `items`.\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "ÉTAPE 1 — IDENTIFIER LE TYPE D'ÉLÉVATION (CODE → TYPE)\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "- Code commence par 'MR'  → elevation_type = 'curtain_wall' "
    "(MR = MUR-RIDEAU, ex: Kawneer 1620 ou 1600). PAS de porte battante.\n"
    "- Code commence par 'FG'  → elevation_type = 'flush_glaze' "
    "(Trifab VG450, encadrement à poche non isolé). PAS de porte battante.\n"
    "- Code commence par 'E', 'P' ou contient une porte battante "
    "→ elevation_type = 'door' (porte AT1000/AT2000/ATi avec sidelites/transoms).\n"
    "- Élévation contenant à la fois MR/FG ET une porte intégrée → 'mixed'.\n"
    "Ne JAMAIS classer une MR en 'flush_glaze' ou inversement.\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "ÉTAPE 2 — DÉTECTER LES PORTES (symboles MD/MG/MDR/MGR + n° de porte)\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "Sur chaque porte battante, le plan indique :\n"
    "- Le SENS D'OUVERTURE : MD (main droite), MG (main gauche), "
    "MDR (main droite renversée), MGR (main gauche renversée).\n"
    "- Le NUMÉRO DE PORTE (ex: P.-101, P-202) — pas toujours présent.\n"
    "Renseigne ces 2 champs dans `door_info` : `handing` ('MD'|'MG'|'MDR'|'MGR') "
    "et `door_number` (ex 'P.-101').\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "ÉTAPE 3 — COUPES DES MENEAUX VERTICAUX (PIÈGE FRÉQUENT)\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "Quand une élévation contient une porte battante intégrée (type 'mixed' ou 'door'),\n"
    "les MENEAUX VERTICAUX ont SOUVENT 2 HAUTEURS DIFFÉRENTES :\n"
    "- 2 meneaux pleine hauteur (côté libre)  → longueur = hauteur totale de l'élévation\n"
    "- 2 meneaux côté porte → longueur plus courte (= hauteur porte + transom)\n"
    "Liste-les comme DEUX items distincts avec qty=2 chacun. Ne JAMAIS regrouper\n"
    "4 meneaux à la même longueur quand la porte coupe la hauteur.\n"
    "\n"
    "Exemple BMO: 2 meneaux verticaux de 3029 mm (côté porte) + 2 meneaux verticaux\n"
    "de 3023 mm (côté libre) = 4 meneaux TOTAL avec 2 longueurs différentes.\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "ÉTAPE 4 — TRAVERSES HORIZONTALES (TUBE À POCHE / TUBE ESCALIER)\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "Pour les FG (Trifab VG450) :\n"
    "- LINTEAU (horizontal supérieur) = TOUJOURS Tube à poche (#450CG005)\n"
    "- BAS DE CHAQUE VITRAGE = Tube escalier (#450CG011)\n"
    "  Y COMPRIS la traverse sous le verre AU-DESSUS d'une porte\n"
    "- Toute traverse INTERMÉDIAIRE entre 2 vitrages superposés = Tube à poche\n"
    "  (#450CG005) — c'est le 'haut' du vitrage inférieur ET le 'bas' du suivant.\n"
    "Compte rigoureusement : si l'élévation a N cellules superposées avec 1 porte,\n"
    "tu auras typiquement (N-1) tube à poche + N tube escalier intermédiaires.\n"
    "\n"
    "Pour les MR (Kawneer 1620) : les profilés sont les meneaux + couvercles\n"
    "(pas tube à poche/escalier).\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "ÉTAPE 5 — CALCULS DES GARNITURES ET BRIS THERMIQUE (CRUCIAL)\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "A) Pour les FG (Trifab VG450) :\n"
    "   GARNITURE DE VITRAGE 6mm (#027074) = (somme des PÉRIMÈTRES de chaque\n"
    "   vitre thermos) × 2.\n"
    "   Exemple : 4 vitres de 2000×800 mm → périmètre par vitre = 2(2000+800) = 5600 mm\n"
    "   → 4 vitres × 5600 × 2 = 44 800 mm de garniture.\n"
    "   Liste cet item : item_type='hardware', label='Garniture de vitrage 6mm',\n"
    "   part_number='#027074', length_mm = total calculé, qty=1.\n"
    "\n"
    "B) Pour les MR (Kawneer 1620) :\n"
    "   1) BRIS THERMIQUE (#162-310) = somme LINÉAIRE de TOUS les meneaux\n"
    "      verticaux ET horizontaux du MR (additionnés en mm).\n"
    "      Liste : item_type='hardware', label='Bris thermique',\n"
    "      part_number='#162-310', length_mm=total, qty=1.\n"
    "   2) GARNITURE EXT + INT (#027-850) = (somme des périmètres des thermos) × 2.\n"
    "      Idem #027074 mais sur les MR.\n"
    "      Liste : item_type='hardware', label='Garniture ext+int',\n"
    "      part_number='#027-850', length_mm=total, qty=1.\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "ÉTAPE 6 — QUINCAILLERIE COMPLÈTE DES PORTES (ne RIEN OUBLIER)\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "Pour CHAQUE porte battante, EXTRAIS du plan/encadré TOUS les éléments\n"
    "présents — ne te limite PAS à la charnière. Inclus systématiquement\n"
    "(si visibles ou listés) :\n"
    "  • Charnière continue (ex UH-120-DA, UH83-CL)\n"
    "  • Serrure MS Adams Rite (ex ADAM-MS1853S320)\n"
    "  • CYLINDRE EXTÉRIEUR (ex ILCO-7165SC229KD)\n"
    "  • Cylindre intérieur / tourniquet (ex ADAM-4066)\n"
    "  • Gâche / strike (ex ADAM-4906)\n"
    "  • POIGNÉE À TIRER extérieure / ladder pull (ex UNIQ-AC4-36)\n"
    "  • Poignée intérieure / push paddle\n"
    "  • Barre anti-panique (ex ADAM-8400)\n"
    "  • Ferme-porte / door closer (ex LCN 4040XP, NORTON 1601)\n"
    "  • ASTRAGALE (ex pour porte double — séparation entre 2 vantaux)\n"
    "  • Seuil / threshold (ex Pemko 252 série)\n"
    "  • Joint balai / bottom sweep\n"
    "  • Butoir mural\n"
    "Pour chaque : `label`, `part_number` (EXACT, recopié), `manufacturer`, "
    "`qty` (par défaut 1).\n"
    "Si l'encadré liste un item sans n° de pièce, mets quand même le label "
    "avec part_number=null. NE JAMAIS l'omettre.\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "ÉTAPE 7 — PORTE AT (renseigner door_info pour la décomposition backend)\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "Pour la porte battante elle-même (s'il y en a une) :\n"
    "- NE PAS la décomposer (le backend Portech génère les 4 pièces du cadre\n"
    "  + 8 moulures parclose + charnière).\n"
    "- Renvoie 1 SEUL item type='panel' avec dimensions du battant + "
    "renseigne `door_info` complet : series, leaf_width_mm, leaf_height_mm,\n"
    "is_insulated, glass_thickness_mm, frame_finish, door_finish, "
    "handing, door_number.\n"
    "\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "RETOUR JSON STRICT\n"
    "════════════════════════════════════════════════════════════════════════\n"
    "{\n"
    '  "elevations": [\n'
    "    {\n"
    '      "code": "FG01" | "MR2" | "E1" | ...,\n'
    '      "elevation_type": "door" | "flush_glaze" | "curtain_wall" | "mixed",\n'
    '      "system_label"?: "ENCADREMENT À POCHE NON-ISOLÉ SÉRIE TRIFAB VG450" | ...,\n'
    '      "finish_ext"?: "Anodisé champagne" | ...,\n'
    '      "finish_int"?: "Anodisé clair classe II 10µ" | ...,\n'
    '      "total_width_mm"?: number,\n'
    '      "total_height_mm"?: number,\n'
    '      "items": [ { item_type, label, profile?, material?, part_number?, '
    'manufacturer?, length_mm, width_mm?, thickness_mm?, qty, '
    'opening_length_mm?, opening_width_mm?, notes? }, ... ],\n'
    '      "door_info"?: { series?, leaf_width_mm?, leaf_height_mm?, '
    'is_insulated?, glass_thickness_mm?, frame_finish?, door_finish?, '
    'handing?, door_number? }\n'
    "    }\n"
    "  ],\n"
    '  "frame_specs": { ... },\n'
    '  "unit_detected": "mm" | "in" | "cm" | "ft" | "unknown",\n'
    '  "confidence": 0..1,\n'
    '  "warnings": ["..."]\n'
    "}\n"
    "\n"
    "Règles finales :\n"
    "- Toutes dimensions en MILLIMÈTRES (1 in = 25.4 mm, 11/16\" = 17.46 mm, "
    "3/4\" = 19.05 mm, 1¾\" = 44.45 mm).\n"
    "- Toujours recopier EXACTEMENT le format du numéro de pièce (#450CG005, "
    "#162-310, etc.) tel qu'écrit sur le plan.\n"
    "- Si tu n'es PAS SÛR d'un classement (FG vs MR), regarde l'encadré "
    "haut-à-droite : le mot 'MUR-RIDEAU' → curtain_wall, 'ENCADREMENT À POCHE' "
    "→ flush_glaze.\n"
    "- AUCUN texte hors du JSON. Pas de ```json. Pas d'explication."
)


def _strip_json_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


async def _ocr_plan(file_path: Path, mime: str) -> dict:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "EMERGENT_LLM_KEY non configurée — OCR indisponible.")
    chat = (
        LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-plan-{uuid.uuid4().hex[:8]}",
            system_message=OCR_SYSTEM,
        )
        .with_model("gemini", OCR_MODEL)
    )
    msg = UserMessage(
        text=OCR_USER,
        file_contents=[FileContentWithMimeType(file_path=str(file_path), mime_type=mime)],
    )
    raw = await chat.send_message(msg)
    raw_text = raw if isinstance(raw, str) else str(raw)
    try:
        data = json.loads(_strip_json_fence(raw_text))
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw_text)
        if not m:
            raise HTTPException(502, "Réponse OCR invalide")
        data = json.loads(m.group(0))

    def _coerce_item_type(raw_type: str, label: str, profile: str) -> str:
        if raw_type in ITEM_TYPES:
            return raw_type
        # Heuristic remap from Gemini's free-text type values.
        text = f"{raw_type} {label} {profile}".lower()
        if any(k in text for k in ("verre", "vitrage", "thermos", "glass")):
            return "glass"
        if any(k in text for k in ("perçage", "percage", "trou", "hole", "machinage")):
            return "hole"
        if any(k in text for k in ("gasket", "joint", "weatherseal", "weather seal",
                                    "boudin", "calfeutrage", "garniture vitrage",
                                    "garniture de vitrage", "garniture ext", "garniture int")):
            return "gasket"
        if any(k in text for k in ("charnière", "charniere", "serrure", "cylindre",
                                    "gâche", "gache", "poignée", "poignee", "ferme-porte",
                                    "barre", "panique", "bris thermique",
                                    "astragale", "seuil", "butoir", "quincaillerie")):
            return "hardware"
        if any(k in text for k in ("porte", "panneau", "panel")):
            return "panel"
        # Default: any tube/meneau/couvercle/horizontal/vertical/linteau/parclose/moulure → frame
        return "frame"

    def _sanitize_items(raw_items: list) -> list:
        out = []
        for it in raw_items or []:
            raw_type = (it.get("item_type") or "").strip().lower()
            label = str(it.get("label") or "")
            profile = str(it.get("profile") or "")
            item_type = _coerce_item_type(raw_type, label, profile)
            # Strip leading '#' from part_number so we don't double-hash on display
            pn = (it.get("part_number") or None) or None
            if isinstance(pn, str):
                pn = pn.lstrip("#").strip() or None
            out.append({
                "id": str(uuid.uuid4()),
                "item_type": item_type,
                "label": label[:140],
                "profile": (it.get("profile") or None) or None,
                "material": (it.get("material") or None) or None,
                "part_number": pn,
                "manufacturer": (it.get("manufacturer") or None) or None,
                "length_mm": float(it.get("length_mm") or 0),
                "width_mm": float(it.get("width_mm")) if it.get("width_mm") not in (None, "") else None,
                "thickness_mm": float(it.get("thickness_mm")) if it.get("thickness_mm") not in (None, "") else None,
                "qty": int(it.get("qty") or 1) if str(it.get("qty") or "").replace(".", "").isdigit() else 1,
                "opening_length_mm": float(it.get("opening_length_mm")) if it.get("opening_length_mm") not in (None, "") else None,
                "opening_width_mm": float(it.get("opening_width_mm")) if it.get("opening_width_mm") not in (None, "") else None,
                "notes": (it.get("notes") or None) or None,
                "source": "ocr",
            })
        return out

    # New format: data has "elevations": [...]
    # Backward-compat: data has "items": [...] at top-level → wrap into 1 elevation.
    raw_elevations = data.get("elevations")
    if not raw_elevations:
        raw_elevations = [{
            "code": "E1",
            "elevation_type": "door" if data.get("door_info") else "flush_glaze",
            "items": data.get("items") or [],
            "door_info": data.get("door_info") or {},
        }]

    elevations = []
    for idx, ev in enumerate(raw_elevations):
        code = str(ev.get("code") or f"E{idx + 1}")[:32]
        code_upper = code.upper().strip()

        # ---- DETERMINISTIC classification by code prefix (overrides LLM guess) ----
        # FG* = Flush Glaze always (no door even if LLM thought there was one).
        # MR* = Mur-rideau (curtain wall). If the elevation has a door integrated,
        #       classify as 'mixed' (door inside curtain wall). Else 'curtain_wall'.
        # E*, P* = porte (door elevation).
        di = ev.get("door_info") or {}
        has_door = bool(di.get("series") or di.get("leaf_width_mm") or di.get("leaf_height_mm")) \
            or any((it.get("item_type") == "panel"
                    and re.search(r"AT[I]?[12]000", ((it.get("profile") or "") + " " + (it.get("label") or "")).upper()))
                   for it in (ev.get("items") or []))
        if code_upper.startswith("FG"):
            # FG = Flush Glaze (Trifab). With door integrated → mixed (FG mixte).
            # Without door → pure flush_glaze.
            ev_type = "mixed" if has_door else "flush_glaze"
        elif code_upper.startswith("MR"):
            # MR = Mur-rideau (Kawneer). With door integrated → mixed.
            # Without door → pure curtain_wall.
            ev_type = "mixed" if has_door else "curtain_wall"
        elif code_upper.startswith(("E", "P")):
            ev_type = "door" if has_door else "flush_glaze"
        else:
            # Fallback to LLM-provided type if no code prefix matched
            ev_type = ev.get("elevation_type")
            if ev_type not in ("door", "flush_glaze", "curtain_wall", "mixed"):
                ev_type = "door" if has_door else "flush_glaze"

        # ---- AUTO-CONVERT opening → leaf dims if LLM returned the opening by mistake ----
        # AT series standard 36"×84" opening = 914.4 × 2133.6 mm → leaf = various per series.
        # If leaf_w/h match the OPENING within 5mm tolerance, the LLM almost certainly returned
        # the opening instead of the leaf. Convert using known AT offsets.
        if di:
            lw = di.get("leaf_width_mm")
            lh = di.get("leaf_height_mm")
            series_norm = str(di.get("series") or "").upper().replace(" ", "").replace("-", "")
            if isinstance(lw, (int, float)) and isinstance(lh, (int, float)):
                # Standard rough openings AT uses
                opening_w = round(float(lw))
                opening_h = round(float(lh))
                # Detect known openings; convert to leaf
                width_off = None
                if "AT2000" in series_norm or "ATI2000" in series_norm:
                    width_off = 191.30
                elif "AT1000" in series_norm or "ATI1000" in series_norm:
                    width_off = 115.10
                height_off = 22.20 if "ATI" not in series_norm else 22.20  # both =22.20 now
                # Heuristic: if width is suspiciously close to 914 (=36"), 1219 (=48"), 1828 (=72") -- common openings
                common_openings_w = {914, 1219, 1524, 1828, 2438}
                common_openings_h = {2032, 2134, 2438, 2540}  # 80", 84", 96", 100"
                if width_off and opening_w in common_openings_w and opening_h in common_openings_h:
                    di = dict(di)
                    di["leaf_width_mm"] = round(float(lw) - width_off, 2)
                    di["leaf_height_mm"] = round(float(lh) - height_off, 2)
                    di["_converted_from_opening"] = {"width": float(lw), "height": float(lh)}

        # Normalize handing & door_number (free-text, kept short)
        if di.get("handing"):
            h = str(di["handing"]).upper().strip()
            di["handing"] = h if h in ("MD", "MG", "MDR", "MGR") else None
        if di.get("door_number"):
            di["door_number"] = str(di["door_number"])[:24]
        elevations.append({
            "id": str(uuid.uuid4()),
            "code": code,
            "elevation_type": ev_type,
            "system_label": (ev.get("system_label") or None) or None,
            "finish_ext": (ev.get("finish_ext") or None) or None,
            "finish_int": (ev.get("finish_int") or None) or None,
            "total_width_mm": float(ev["total_width_mm"]) if ev.get("total_width_mm") not in (None, "") else None,
            "total_height_mm": float(ev["total_height_mm"]) if ev.get("total_height_mm") not in (None, "") else None,
            "items": _sanitize_items(ev.get("items") or []),
            "door_info": di,
        })

    return {
        "elevations": elevations,
        "frame_specs": data.get("frame_specs") or {},
        "unit_detected": data.get("unit_detected", "unknown"),
        "confidence": float(data.get("confidence") or 0),
        "warnings": data.get("warnings", []) or [],
    }


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.post("/cuts/decompose-door")
    async def decompose_door(payload: dict, _: dict = Depends(auth_dep)):
        """Take a 'panel'-type door spec and return the 4 frame pieces + 8 parcloses
        + hardware positions. Frontend calls this after the user fills in or
        confirms the door dimensions / series. No persistence.

        Input semantics: door_width_mm / door_height_mm are the LEAF dimensions
        (battant fini) — what AT shop drawings list (ex 723.1 × 2114.5).
        """
        try:
            door_w = float(payload.get("door_width_mm") or 0)
            door_h = float(payload.get("door_height_mm") or 0)
        except (TypeError, ValueError):
            raise HTTPException(400, "door_width_mm et door_height_mm requis (mm).")
        if door_w <= 0 or door_h <= 0:
            raise HTTPException(400, "door_width_mm et door_height_mm doivent être > 0.")
        result = decompose_at_door(
            leaf_width_mm=door_w,
            leaf_height_mm=door_h,
            series=str(payload.get("series") or "AT1000"),
            glass_thickness_mm=float(payload.get("glass_thickness_mm") or 6.0),
            material=str(payload.get("material") or "Aluminium anodisé bronze"),
            label_prefix=str(payload.get("label_prefix") or "Porte"),
            qty=int(payload.get("qty") or 1),
            hardware_rules=payload.get("hardware_rules") or None,
        )
        return {
            "items": result.items + result.hardware,
            "notes": result.notes,
        }

    @router.post("/cuts/template-build")
    async def template_build(payload: dict, _: dict = Depends(auth_dep)):
        """Build a DETERMINISTIC elevation from a user-filled template form.

        Bypasses Gemini OCR. The user supplies geometry (verticals, horizontals,
        glasses, optional integrated door) and we compute every cut item with
        the correct profile names + manufacturer part numbers (Trifab VG450,
        Kawneer 1620, AT Fabrication) and the auto-calculated garniture /
        bris-thermique totals.

        Payload shape: see cut_templates.build_elevation_from_template.
        """
        try:
            result = build_elevation_from_template(payload)
        except KeyError as exc:
            raise HTTPException(400, f"Champ requis manquant : {exc}")
        except (ValueError, TypeError) as exc:
            raise HTTPException(400, str(exc))
        return result

    @router.get("/profile-catalog")
    async def profile_catalog(_: dict = Depends(auth_dep)):
        """Read-only catalog of all profile systems Portech tracks.

        Used by the ERP Catalog panel + the cut-list authoring UI to look up
        part numbers, manufacturer dimensions, and calculation rules.
        Static data — no DB query, no LLM, no rate limit concerns.
        """
        return get_catalog()

    @router.get("/cuts/meta")
    async def cuts_meta(_: dict = Depends(auth_dep)):
        return {
            "item_types": ITEM_TYPES,
            "default_stock_lengths_mm": DEFAULT_ALU_STOCK_LENGTHS_MM,
            "default_saw_kerf_mm": DEFAULT_SAW_KERF_MM,
        }

    @router.get("/cuts")
    async def list_cuts(_: dict = Depends(auth_dep)):
        cur = db.erp_cut_lists.find({}, {"_id": 0}).sort("updated_at", -1).limit(200)
        rows = [d async for d in cur]
        # Drop heavy "items" from list view to keep payload light
        return [{k: v for k, v in r.items() if k not in ("items", "last_optimization")} | {"items_count": len(r.get("items", []))} for r in rows]

    @router.post("/cuts", status_code=201, response_model=CutList)
    async def create_cut(data: CutListIn, _: dict = Depends(auth_dep)):
        cut = CutList(**data.model_dump())
        await db.erp_cut_lists.insert_one(cut.model_dump())
        return cut

    @router.get("/cuts/{cut_id}", response_model=CutList)
    async def get_cut(cut_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Liste de coupe introuvable")
        return CutList(**doc)

    @router.put("/cuts/{cut_id}", response_model=CutList)
    async def update_cut(cut_id: str, data: CutListIn, _: dict = Depends(auth_dep)):
        update = data.model_dump()
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = await db.erp_cut_lists.update_one({"id": cut_id}, {"$set": update})
        if res.matched_count == 0:
            raise HTTPException(404, "Liste de coupe introuvable")
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        return CutList(**doc)

    @router.delete("/cuts/{cut_id}")
    async def delete_cut(cut_id: str, _: dict = Depends(auth_dep)):
        res = await db.erp_cut_lists.delete_one({"id": cut_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Liste de coupe introuvable")
        return {"deleted": cut_id}

    @router.post("/cuts/extract")
    async def extract_from_plan(
        file: UploadFile = File(...),
        _: dict = Depends(auth_dep),
    ):
        """Upload a PDF/image plan, run Gemini Vision OCR, return items."""
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_PLAN_EXTS:
            raise HTTPException(400, f"Format non supporté. Acceptés : {', '.join(sorted(ALLOWED_PLAN_EXTS))}")
        contents = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"Fichier trop volumineux (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB)")
        fname = f"plan_{uuid.uuid4().hex}{ext}"
        tf = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tf.write(contents)
        tf.close()
        out_path = Path(tf.name)
        mime = MIME_BY_EXT.get(ext, "application/octet-stream")
        try:
            result = await _ocr_plan(out_path, mime)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("OCR plan failed: %s", exc)
            raise HTTPException(502, f"Échec de l'extraction OCR : {exc}")
        finally:
            # Remove the transient temp file after parsing — we keep only the structured items
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass

        # AUTO-DECOMPOSE any AT door panel the OCR detected per elevation.
        # Previously this was a manual click; users want it automatic on import.
        elevations_in = result.get("elevations") or []
        out_elevations = []
        all_warnings = list(result.get("warnings") or [])

        for ev in elevations_in:
            items = list(ev.get("items") or [])
            door_info = ev.get("door_info") or {}
            ev_notes: list[str] = []

            # FALLBACK: if door_info is missing key dims but a 'panel' item with
            # an AT* profile is in items, harvest the dims from it. This avoids
            # silently dropping the AT door's frame pieces + parcloses + glass
            # when the OCR failed to fill door_info correctly.
            series = (door_info.get("series") or "").strip()
            leaf_w = door_info.get("leaf_width_mm")
            leaf_h = door_info.get("leaf_height_mm")
            if not (series and leaf_w and leaf_h):
                for it in items:
                    if it.get("item_type") != "panel":
                        continue
                    text = ((it.get("profile") or "") + " " + (it.get("label") or "")).upper().replace(" ", "")
                    if not re.search(r"AT[I]?[12]000", text):
                        continue
                    # Build canonical series from the panel item itself
                    if not series:
                        if "ATI2000" in text:
                            series = "ATI2000"
                        elif "ATI1000" in text:
                            series = "ATI1000"
                        elif "AT1000" in text and "AT2000" in text and "BASE" in text:
                            series = "AT1000-base-AT2000"
                        elif "AT2000" in text:
                            series = "AT2000"
                        else:
                            series = "AT1000"
                    # length_mm = leaf height, width_mm = leaf width (per OCR_USER step 7)
                    leaf_h = leaf_h or it.get("length_mm")
                    leaf_w = leaf_w or it.get("width_mm")
                    door_info = dict(door_info)
                    door_info["series"] = series
                    door_info["leaf_width_mm"] = leaf_w
                    door_info["leaf_height_mm"] = leaf_h
                    door_info["glass_thickness_mm"] = door_info.get("glass_thickness_mm") or it.get("thickness_mm") or 6.0
                    break

            if series and leaf_w and leaf_h:
                glass_t = door_info.get("glass_thickness_mm") or 6.0
                finish = door_info.get("door_finish") or door_info.get("frame_finish") \
                    or "Aluminium anodisé bronze"
                br = decompose_at_door(
                    leaf_width_mm=float(leaf_w),
                    leaf_height_mm=float(leaf_h),
                    series=str(series),
                    glass_thickness_mm=float(glass_t),
                    material=str(finish),
                    label_prefix=f"Porte {ev.get('code') or ''}".strip(),
                    qty=1,
                )
                # Remove any panel item the OCR added for the door
                items = [
                    it for it in items
                    if not (it.get("item_type") == "panel"
                            and re.search(r"AT\s*1?2?000", (it.get("profile") or "") + (it.get("label") or ""), re.I))
                ]
                items.extend(br.items + br.hardware)
                ev_notes.extend(br.notes)
                handing = door_info.get("handing")
                door_number = door_info.get("door_number")
                tag = " — ".join(filter(None, [series, door_number, handing]))
                ev_notes.append(f"Porte AT décomposée automatiquement ({tag}).")
            out_elevations.append({
                **ev,
                "items": items,
                "notes": ev_notes,
            })
            if ev_notes:
                all_warnings.extend([f"[{ev.get('code')}] {n}" for n in ev_notes])

        return {
            "source_filename": fname,
            "source_type": "pdf" if ext == ".pdf" else "image",
            "elevations": out_elevations,
            "frame_specs": result.get("frame_specs") or {},
            "unit_detected": result.get("unit_detected", "unknown"),
            "confidence": result.get("confidence", 0),
            "warnings": all_warnings,
        }

    @router.post("/cuts/extract-dxf")
    async def extract_from_dxf(
        file: UploadFile = File(...),
        _: dict = Depends(auth_dep),
    ):
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_DXF_EXTS:
            raise HTTPException(400, "Format non supporté. Utilisez un fichier .dxf")
        contents = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"Fichier trop volumineux (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB)")
        fname = f"plan_{uuid.uuid4().hex}{ext}"
        tf = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tf.write(contents)
        tf.close()
        out_path = Path(tf.name)
        try:
            result = parse_dxf(str(out_path))
        finally:
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
        # Attach UUIDs to items
        for it in result.get("items", []):
            it["id"] = str(uuid.uuid4())
        return {
            "source_filename": fname,
            "source_type": "dxf",
            **result,
        }

    @router.post("/cuts/{cut_id}/optimize")
    async def optimize(cut_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Liste de coupe introuvable")
        opt = optimize_cut_list(
            items=doc.get("items", []),
            stock_lengths_mm=doc.get("stock_lengths_mm") or DEFAULT_ALU_STOCK_LENGTHS_MM,
            kerf_mm=int(doc.get("saw_kerf_mm") or DEFAULT_SAW_KERF_MM),
        )
        await db.erp_cut_lists.update_one(
            {"id": cut_id},
            {"$set": {
                "last_optimization": opt,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return opt

    @router.post("/cuts/optimize-preview")
    async def optimize_preview(payload: CutListIn, _: dict = Depends(auth_dep)):
        """Run the optimizer on the inline payload without persisting."""
        items = [it.model_dump() if hasattr(it, "model_dump") else it for it in payload.items]
        return optimize_cut_list(
            items=items,
            stock_lengths_mm=payload.stock_lengths_mm or DEFAULT_ALU_STOCK_LENGTHS_MM,
            kerf_mm=int(payload.saw_kerf_mm or DEFAULT_SAW_KERF_MM),
        )

    @router.get("/cuts/{cut_id}/export.csv")
    async def export_csv(cut_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Liste de coupe introuvable")
        buf = io.StringIO()
        buf.write("\ufeff")
        w = csv.writer(buf)
        w.writerow(["Type", "Label", "Profilé", "Matériau",
                    "N° pièce", "Fabricant",
                    "Long. (mm)", "Larg. (mm)", "Épais. (mm)", "Qté",
                    "Pos. X", "Pos. Y", "Notes"])
        for it in doc.get("items", []):
            w.writerow([
                it.get("item_type", ""),
                it.get("label", ""),
                it.get("profile") or "",
                it.get("material") or "",
                it.get("part_number") or "",
                it.get("manufacturer") or "",
                f"{float(it.get('length_mm', 0) or 0):.1f}",
                f"{float(it.get('width_mm') or 0):.1f}" if it.get("width_mm") else "",
                f"{float(it.get('thickness_mm') or 0):.1f}" if it.get("thickness_mm") else "",
                str(it.get("qty", 1) or 1),
                str(it.get("position_x") or ""),
                str(it.get("position_y") or ""),
                (it.get("notes") or "").replace("\n", " "),
            ])
        buf.seek(0)
        safe_name = re.sub(r"[^a-zA-Z0-9-]+", "-", (doc.get("name") or "liste-coupe"))
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="coupes-{safe_name}.csv"'},
        )

    @router.get("/cuts/{cut_id}/export.pdf")
    async def export_pdf(cut_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Liste de coupe introuvable")
        # Always recompute optimization for the latest items
        opt = optimize_cut_list(
            items=doc.get("items", []),
            stock_lengths_mm=doc.get("stock_lengths_mm") or DEFAULT_ALU_STOCK_LENGTHS_MM,
            kerf_mm=int(doc.get("saw_kerf_mm") or DEFAULT_SAW_KERF_MM),
        )
        pdf_bytes = render_cut_list_pdf(doc, opt)
        safe_name = re.sub(r"[^a-zA-Z0-9-]+", "-", (doc.get("name") or "liste-coupe"))
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="coupes-{safe_name}.pdf"'},
        )
