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
from typing import List, Optional


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
    # Expand qty into individual cuts per group
    groups_map: dict[tuple, List[float]] = {}
    glass_panels: list[dict] = []
    hardware_count = 0
    for it in items:
        t = it.get("item_type", "frame")
        qty = max(1, int(it.get("qty", 1) or 1))
        if t == "frame":
            key = (it.get("profile") or "—", it.get("material") or "—")
            for _ in range(qty):
                length = float(it.get("length_mm") or 0)
                if length > 0:
                    groups_map.setdefault(key, []).append(length)
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
    for (profile, material), cuts in groups_map.items():
        plan = optimize_group(cuts, [float(s) for s in stock_lengths_mm], float(kerf_mm))
        groups_out.append({
            "profile": profile, "material": material,
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
