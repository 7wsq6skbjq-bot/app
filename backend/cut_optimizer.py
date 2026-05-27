"""1D linear cutting-stock optimizer (FFD with kerf).

Given a list of required cuts (length_mm × qty) all in the SAME profile/material
and a set of available stock bar lengths with a saw kerf, produce an optimal
bar-cutting plan: which stock length to use, how many bars, what cuts per bar,
total waste.

Algorithm: First Fit Decreasing (FFD) — proven heuristic that's within ~22%
of optimal for the 1D bin packing problem. For the small jobs Portech runs
(<200 cuts per project), FFD gives near-optimal results in milliseconds.

For each candidate stock length, we run FFD; we then pick the stock length
that minimizes total waste. The user can also force a specific stock length.

Returns a JSON-serializable dict that the frontend renders as a cutting layout
and the PDF generator turns into a workshop sheet.
"""
import re
from typing import List, Optional


def _parse_dim(token: str) -> float | None:
    """Parse '1.75', '1 3/4', '1-3/4', '44.5' into a float. Returns None if unparsable."""
    s = token.strip().replace("-", " ")
    # Mixed fraction: "1 3/4"
    m = re.fullmatch(r"(\d+)\s+(\d+)/(\d+)", s)
    if m:
        whole, num, denom = (int(x) for x in m.groups())
        return whole + num / denom if denom else None
    # Pure fraction: "3/4" or "13/4" — ambiguous, but we assume proper fraction
    m = re.fullmatch(r"(\d+)/(\d+)", s)
    if m:
        num, denom = int(m.group(1)), int(m.group(2))
        return num / denom if denom else None
    # Decimal: "1.75", "44.5", "4"
    try:
        return float(s)
    except ValueError:
        return None


def normalize_profile_key(profile: str | None, material: str | None) -> tuple[str, str]:
    """Collapse synonym profile names so identical extrusions end up in the
    same cutting group.

    At Portech, 'tube à ailettes 1¾" x 4"', 'tube de tête 1¾" x 4"', and
    'tube 1¾ x 4' all describe the SAME aluminum extrusion. The optimizer
    must group them together — otherwise the user gets two separate plans
    when they should share bars.

    Strategy: extract the dimensions as numeric values, format them consistently
    (e.g. "1.75x4"), and use those + material as the canonical key. Falls back
    to the raw string if no dimensions are detected.
    """
    raw_profile = (profile or "—").strip()
    raw_material = (material or "—").strip()

    p_low = raw_profile.lower()
    frac_map = {"¼": " 1/4", "½": " 1/2", "¾": " 3/4", "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8"}
    for k, v in frac_map.items():
        p_low = p_low.replace(k, v)
    p_clean = re.sub(r"[\"'']", " ", p_low)
    p_clean = re.sub(r"\s+", " ", p_clean).strip()

    # Capture dimension pair: "1 3/4 x 4", "1.75x4", "44.5 x 101.6"
    m = re.search(
        r"(\d+(?:\s+\d+/\d+)?|\d+/\d+|\d+\.\d+|\d+)\s*[x×]\s*(\d+(?:\s+\d+/\d+)?|\d+/\d+|\d+\.\d+|\d+)",
        p_clean,
    )
    if m:
        a = _parse_dim(m.group(1))
        b = _parse_dim(m.group(2))
        if a is not None and b is not None:
            # Normalize to mm for matching: if a value < 10 it's almost certainly
            # inches, so convert to mm (1 in = 25.4 mm).
            def to_mm(v):
                return v * 25.4 if v < 10 else v
            a_mm = round(to_mm(a), 1)
            b_mm = round(to_mm(b), 1)
            dim_key = f"{a_mm}x{b_mm}mm"
            return (f"tube {dim_key}", raw_material.lower())

    return (p_clean or "—", raw_material.lower())


def _ffd_pack_one(
    cuts: List[float],
    stock_length: float,
    kerf: float,
) -> List[List[float]]:
    """First Fit Decreasing — pack `cuts` into stock bars of `stock_length`.

    `kerf` is the saw blade width consumed BETWEEN two cuts on the same bar
    (no kerf is consumed on the first cut, since the bar end is square).
    Returns a list of bars; each bar is the list of cut lengths placed in it.
    """
    if stock_length <= 0:
        raise ValueError("stock_length must be > 0")
    cuts_sorted = sorted(cuts, reverse=True)
    bars: List[List[float]] = []
    bars_remaining: List[float] = []
    for c in cuts_sorted:
        if c > stock_length:
            # Single cut larger than stock — record as an "oversize" bar of its own.
            # Frontend will flag this so the user can split the piece manually.
            bars.append([c])
            bars_remaining.append(0)
            continue
        placed = False
        for i, remaining in enumerate(bars_remaining):
            # Need kerf BEFORE this cut (since at least one cut already there)
            needed = c + kerf if bars[i] else c
            if remaining >= needed:
                bars[i].append(c)
                bars_remaining[i] = remaining - needed
                placed = True
                break
        if not placed:
            # Open a new bar
            bars.append([c])
            bars_remaining.append(stock_length - c)
    return bars


def _bar_breakdown(bar: List[float], stock_length: float, kerf: float) -> dict:
    """Per-bar summary used by the frontend layout view."""
    if not bar:
        return {"cuts": [], "used_mm": 0, "waste_mm": stock_length, "kerf_total_mm": 0}
    n = len(bar)
    used = sum(bar) + kerf * max(0, n - 1)
    return {
        "cuts": [round(c, 1) for c in bar],
        "used_mm": round(used, 1),
        "waste_mm": round(max(0, stock_length - used), 1),
        "kerf_total_mm": kerf * max(0, n - 1),
    }


def optimize_group(
    cuts: List[float],
    candidate_stocks: List[float],
    kerf: float,
    forced_stock: Optional[float] = None,
) -> dict:
    """Run FFD against each candidate stock length, return the best plan.

    Best = lowest total waste (in mm). Ties broken by fewer bars used.
    """
    if not cuts:
        return {"bars": [], "stock_length_mm": None, "total_waste_mm": 0,
                "total_cuts": 0, "bars_count": 0}
    candidates = [forced_stock] if forced_stock else candidate_stocks
    best = None
    for stock in candidates:
        bars = _ffd_pack_one(cuts, stock, kerf)
        breakdowns = [_bar_breakdown(b, stock, kerf) for b in bars]
        total_waste = sum(b["waste_mm"] for b in breakdowns)
        score = (total_waste, len(bars))
        if best is None or score < best["score"]:
            best = {
                "score": score,
                "stock_length_mm": stock,
                "bars": breakdowns,
                "total_waste_mm": round(total_waste, 1),
                "total_cuts": len(cuts),
                "bars_count": len(bars),
                "kerf_mm": kerf,
            }
    # Drop the internal "score" tuple before returning
    best.pop("score", None)
    return best


def optimize_cut_list(
    items: list,
    stock_lengths_mm: List[int],
    kerf_mm: int,
) -> dict:
    """Group `frame` items by (profile, material) and run optimize_group on each.

    Returns:
        {
          "groups": [
            {"profile": ..., "material": ..., "plan": {bars, total_waste, ...}},
            ...
          ],
          "glass_summary": {"count", "total_area_m2", "panels": [...]},
          "hardware_count": int,
          "total_bars": int,
          "total_waste_mm": float,
          "efficiency_pct": float,    # 100 - waste/total_stock_used * 100
        }
    """
    # Expand qty into individual cuts per group.
    # The key is a NORMALIZED tuple so synonym profile names ('tube à ailettes',
    # 'tube de tête', 'tube 1¾x4') all land in the same group. We remember the
    # first human-readable profile/material seen for display purposes.
    groups_map: dict[tuple, dict] = {}
    glass_panels: list[dict] = []
    hardware_count = 0
    for it in items:
        t = it.get("item_type", "frame")
        qty = max(1, int(it.get("qty", 1) or 1))
        if t == "frame":
            key = normalize_profile_key(it.get("profile"), it.get("material"))
            bucket = groups_map.setdefault(key, {
                "cuts": [],
                "display_profile": it.get("profile") or "—",
                "display_material": it.get("material") or "—",
            })
            for _ in range(qty):
                length = float(it.get("length_mm") or 0)
                if length > 0:
                    bucket["cuts"].append(length)
        elif t in ("glass", "panel"):
            length = float(it.get("length_mm") or 0)
            width = float(it.get("width_mm") or 0)
            if length > 0 and width > 0:
                glass_panels.append({
                    "label": it.get("label") or "Verre",
                    "length_mm": length,
                    "width_mm": width,
                    "thickness_mm": it.get("thickness_mm"),
                    "qty": qty,
                    "area_m2": round((length * width * qty) / 1_000_000, 3),
                })
        elif t in ("hardware", "hole"):
            hardware_count += qty

    groups_out = []
    total_bars = 0
    total_waste = 0
    total_stock = 0
    for key, bucket in groups_map.items():
        plan = optimize_group(bucket["cuts"], [float(s) for s in stock_lengths_mm], float(kerf_mm))
        groups_out.append({
            "profile": bucket["display_profile"],
            "material": bucket["display_material"],
            "plan": plan,
        })
        total_bars += plan.get("bars_count", 0) or 0
        total_waste += plan.get("total_waste_mm", 0) or 0
        if plan.get("stock_length_mm"):
            total_stock += plan["stock_length_mm"] * plan["bars_count"]

    efficiency = round(100 * (1 - total_waste / total_stock), 1) if total_stock > 0 else 0.0

    glass_summary = {
        "count": sum(p["qty"] for p in glass_panels),
        "total_area_m2": round(sum(p["area_m2"] for p in glass_panels), 3),
        "panels": glass_panels,
    }

    return {
        "groups": groups_out,
        "glass_summary": glass_summary,
        "hardware_count": hardware_count,
        "total_bars": total_bars,
        "total_waste_mm": round(total_waste, 1),
        "total_stock_used_mm": round(total_stock, 1),
        "efficiency_pct": efficiency,
    }
