/** Aluminum bar inventory — full CRUD with two finishes (clair / noir),
 *  restock min/max thresholds, status badges, color filter chips, and a
 *  one-click supplier purchase-order PDF.
 *
 *  UX choices (the "ludique" part):
 *   - Color dots prominent on every row (⚫ noir, ⚪ clair)
 *   - Top summary band: stock total + how many refs need reordering
 *   - Filter chips (Tout · Noir · Clair) with live counts
 *   - Status badge per row: 🟢 OK · 🟠 Bas · 🔴 Rupture · ⚪ —
 *   - Mini progress bar showing qty / max ratio (filled red below min)
 *   - "Modifier min/max" inline pencil
 *   - "Bon de commande PDF" button — fixed at top, downloads grouped by mfr */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
    Plus, Trash2, Minus, RefreshCw, Boxes, Scissors as ScissorsIcon,
    Download, AlertTriangle, Pencil, EyeOff, SlidersHorizontal,
} from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";
import { useAuth } from "@/context/AuthContext";

// `key` = inventory profile_key, identical to the optimizer's display key,
// so "Confirmer coupes" can match and deduct correctly.
// Format: "AT Fabrication #<AT_CODE>" — descriptions include the Hydro code (MH8xxxx)
// extracted from the official Hydro Extrusion DXF (Jun 2026).
const PRESET_KEYS = [
    // ─── AT Fabrication — séries portes AT1000 / ATi1000 ───────────────
    { key: "AT Fabrication #ATT1005",   desc: "ATT1005 / MH80477 — Tête 2¼\" — AT1000 / ATi1000",                   len: 6800 },
    { key: "AT Fabrication #ATB1000",   desc: "ATB1000 / MH80476 — Base 3⅞\" AT1000 + tête AT2000 (partagée)",      len: 6800 },
    { key: "AT Fabrication #ATV1010",   desc: "ATV1010 / MH80478 — Stile charnière 2\" — AT1000 / ATi1000",         len: 6800 },
    { key: "AT Fabrication #ATV1015",   desc: "ATV1015 / MH80479 — Stile serrure 2⅛\" — AT1000 / ATi1000",          len: 6800 },
    { key: "AT Fabrication #ATV1020",   desc: "ATV1020 / MH80480 — Side extrusion (jambage latéral cadre) — AT1000", len: 6800 },
    { key: "AT Fabrication #ATV1025",   desc: "ATV1025 / MH80481 — Jamb extrusion (jambage cadre) — AT1000",        len: 6800 },
    { key: "AT Fabrication #ATCV1030",  desc: "ATCV1030 / MH80483 — Cladding vertical — ATi1000",                   len: 6800 },
    { key: "AT Fabrication #ATCHA1035", desc: "ATCHA1035 / MH80482 — Cladding horizontal — ATi1000 / ATi2000",     len: 6800 },
    { key: "AT Fabrication #ATCHB1040", desc: "ATCHB1040 / MH80484 — Sweep (joint balai bas) — ATi1000",            len: 6800 },
    // ─── AT Fabrication — séries portes AT2000 / ATi2000 ───────────────
    { key: "AT Fabrication #ATB2000",   desc: "ATB2000 / MH80321 — Base 6⅞\" — AT2000 / ATi2000",                   len: 6800 },
    { key: "AT Fabrication #ATV2010",   desc: "ATV2010 / MH81325 — Stile charnière 3½\" — AT2000 / ATi2000",        len: 6800 },
    { key: "AT Fabrication #ATV2015",   desc: "ATV2015 / MH81326 — Stile serrure 3⅝\" — AT2000 / ATi2000",          len: 6800 },
    { key: "AT Fabrication #ATV2020",   desc: "ATV2020 / MH81327 — Side extrusion (jambage latéral cadre) — AT2000", len: 6800 },
    { key: "AT Fabrication #ATV2025",   desc: "ATV2025 / MH81320 — Jamb extrusion (jambage cadre) — AT2000",        len: 6800 },
    { key: "AT Fabrication #ATCV2030",  desc: "ATCV2030 / MH81324 — Cladding vertical — ATi2000",                   len: 6800 },
    { key: "AT Fabrication #ATCHB2040", desc: "ATCHB2040 / MH81323 — Sweep (joint balai bas) — ATi2000",            len: 6800 },
    // ─── Moulures (interchangeables sur toutes les portes AT) ──────────
    { key: "AT Fabrication #AT1045",    desc: "AT1045 / MH80485 — Moulure CARRÉE 13.48 — verre simple 6 mm",        len: 6800 },
    { key: "AT Fabrication #AT1050",    desc: "AT1050 / MH80486 — Moulure PLATE 14.3 — verre thermos 25.4 mm",      len: 6800 },
    // ─── Accessoires AT (longueurs spéciales) ──────────────────────────
    { key: "AT Fabrication #AT1065",    desc: "AT1065 — PVC bris thermique — ATi1000 / ATi2000 (barres 5000 mm)",   len: 5000 },
    { key: "AT Fabrication #AT1070",    desc: "AT1070 — Garniture à moulures (joint vitrage) — barres 10'-0\" (3048 mm)", len: 3048 },
    // ─── Trifab — Flush Glaze ──────────────────────────────────────────
    { key: "Trifab #450CG005", desc: "450CG005 — Tube à poche 1¾\" × 4½\" — Trifab VG450",                          len: 7315 },
    { key: "Trifab #450CG011", desc: "450CG011 — Tube escalier 1¾\" × 4½\" — Trifab VG450",                         len: 7315 },
    // ─── Kawneer — Mur-rideau 1620 ─────────────────────────────────────
    { key: "Kawneer #178-001", desc: "178-001 — Meneau 2\" × 3¾\" — Kawneer 1620",                                  len: 7315 },
    { key: "Kawneer #178-006", desc: "178-006 — Couvercle 2\" × ¾\" — Kawneer 1620",                                len: 7315 },
    { key: "Kawneer #178-300", desc: "178-300 — Plaque à pression 2\" — Kawneer 1620",                              len: 7315 },
];

const FINISH_LABELS = { clair: "Clair", noir: "Noir", mill_finish: "Mill" };

const rowStatus = (r) => {
    const qty = r.qty_available || 0;
    const min = r.restock_min;
    if (min === null || min === undefined) return { tone: "neutral", label: "—" };
    if (qty === 0) return { tone: "danger", label: "Rupture" };
    if (qty <= min) return { tone: "warn", label: "Bas" };
    return { tone: "ok", label: "OK" };
};

export const InventoryPanel = () => {
    const { http, getToken } = useAuth();
    const [bars, setBars] = useState([]);
    const [chutes, setChutes] = useState([]);
    const [counts, setCounts] = useState({ clair: 0, noir: 0 });
    const [belowMin, setBelowMin] = useState(0);
    const [loading, setLoading] = useState(false);
    const [addOpen, setAddOpen] = useState(false);
    const [filterFinish, setFilterFinish] = useState("all"); // all | clair | noir
    const [editingThresholds, setEditingThresholds] = useState(null);
    const [editingMeta, setEditingMeta] = useState(null);
    const [bulkOpen, setBulkOpen] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        let result = null;
        try {
            const { data } = await http.get("/admin/alu-inventory");
            result = data;
        } finally {
            setLoading(false);
        }
        if (result) {
            setBars(result.bars || []);
            setChutes(result.chutes || []);
            setCounts(result.finishes_count || { clair: 0, noir: 0, mill_finish: 0 });
            setBelowMin(result.below_min || 0);
        }
    }, [http]);

    useEffect(() => {
        // Initial fetch — fire-and-forget. setState inside is OK because it
        // happens AFTER the await resolves (microtask), not synchronously.
        let cancelled = false;
        (async () => {
            try {
                const { data } = await http.get("/admin/alu-inventory");
                if (cancelled) return;
                setBars(data.bars || []);
                setChutes(data.chutes || []);
                setCounts(data.finishes_count || { clair: 0, noir: 0, mill_finish: 0 });
                setBelowMin(data.below_min || 0);
            } catch {
                // silent — user can hit Rafraîchir
            }
        })();
        return () => { cancelled = true; };
    }, [http]);

    const adjust = async (row, delta) => {
        try {
            await http.patch(`/admin/alu-inventory/${row.id}`, { delta });
            await load();
        } catch (e) { alert(e?.response?.data?.detail || "Erreur"); }
    };
    const del = async (row) => {
        if (!window.confirm(`Supprimer ${row.profile_key} (${FINISH_LABELS[row.finish] || "Clair"}, ${row.bar_length_mm}mm) ?`)) return;
        try { await http.delete(`/admin/alu-inventory/${row.id}`); await load(); }
        catch (e) { alert(e?.response?.data?.detail || "Erreur"); }
    };

    const downloadPurchaseOrder = (stealth = false) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const finishQ = filterFinish !== "all" ? `&finish=${filterFinish}` : "";
        const stealthQ = stealth ? "&stealth=1" : "";
        const url = `${base}/api/admin/alu-inventory/purchase-order.pdf?token=${token}${finishQ}${stealthQ}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const visibleBars = useMemo(() =>
        bars.filter(b => filterFinish === "all" || (b.finish || "clair") === filterFinish),
        [bars, filterFinish]);

    const totalQty = useMemo(() =>
        visibleBars.reduce((s, b) => s + (b.qty_available || 0), 0),
        [visibleBars]);

    return (
        <div className="space-y-4" data-testid="inventory-panel">
            {/* ─── Header ──────────────────────────────────────── */}
            <div className="flex items-center gap-2 flex-wrap">
                <Boxes className="w-5 h-5 text-[#0c182b]" />
                <h2 className="font-display font-bold text-xl text-[#0c182b]">Inventaire aluminium</h2>
                <button onClick={load} className="ml-auto btn-secondary !py-1.5 !px-3 !text-xs">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Rafraîchir
                </button>
                <button onClick={() => setBulkOpen(true)} data-testid="inv-bulk-thresholds"
                    className="btn-secondary !py-1.5 !px-3 !text-xs"
                    title="Définir min/max sur plusieurs lignes d'un coup">
                    <SlidersHorizontal className="w-3.5 h-3.5" /> Min/Max en lot
                </button>
                <button onClick={() => downloadPurchaseOrder(false)} data-testid="inv-po-pdf"
                    className="btn-secondary !py-1.5 !px-3 !text-xs"
                    title="Télécharger un bon de commande pour les pièces sous le minimum">
                    <Download className="w-3.5 h-3.5" /> Bon de commande PDF
                </button>
                <button onClick={() => downloadPurchaseOrder(true)} data-testid="inv-po-pdf-stealth"
                    className="btn-secondary !py-1.5 !px-3 !text-xs"
                    title="PDF anonyme : aucune mention de Portech ni signature, juste le tableau de commande">
                    <EyeOff className="w-3.5 h-3.5" /> PDF anonymisé
                </button>
                <button onClick={() => setAddOpen(true)} data-testid="inv-add" className="btn-primary !py-1.5 !px-3 !text-xs">
                    <Plus className="w-3.5 h-3.5" /> Ajouter
                </button>
            </div>

            {/* ─── Summary band + filter chips ──────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-3 flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-3 mr-auto">
                    <div>
                        <div className="text-[10px] uppercase tracking-wider text-[#4b5d7a]">Total barres pleines (filtre actif)</div>
                        <div className="font-mono text-xl font-bold text-[#0c182b]">{totalQty}</div>
                    </div>
                    {belowMin > 0 && (
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#fff5e6] border border-[#f0c674] text-[#7a4a00]">
                            <AlertTriangle className="w-4 h-4" />
                            <div className="text-xs font-semibold">{belowMin} réf. à recommander</div>
                        </div>
                    )}
                </div>
                <FilterChip active={filterFinish === "all"} onClick={() => setFilterFinish("all")} testId="inv-filter-all">
                    Tout ({bars.length})
                </FilterChip>
                <FilterChip active={filterFinish === "clair"} onClick={() => setFilterFinish("clair")} testId="inv-filter-clair">
                    <FinishDot finish="clair" /> Clair ({counts.clair || 0})
                </FilterChip>
                <FilterChip active={filterFinish === "noir"} onClick={() => setFilterFinish("noir")} testId="inv-filter-noir">
                    <FinishDot finish="noir" /> Noir ({counts.noir || 0})
                </FilterChip>
                <FilterChip active={filterFinish === "mill_finish"} onClick={() => setFilterFinish("mill_finish")} testId="inv-filter-mill">
                    <FinishDot finish="mill_finish" /> Mill ({counts.mill_finish || 0})
                </FilterChip>
            </div>

            {/* ─── Bars table ───────────────────────────────────── */}
            <InventoryTable
                title="Barres pleines"
                rows={visibleBars}
                adjust={adjust}
                del={del}
                onEditThresholds={(r) => setEditingThresholds(r)}
                onEditMeta={(r) => setEditingMeta(r)}
            />

            {/* ─── Chutes ───────────────────────────────────────── */}
            <InventoryTable
                title={<><ScissorsIcon className="w-4 h-4 inline mr-1" />Chutes réutilisables (≥ 600 mm)</>}
                rows={chutes.filter(c => filterFinish === "all" || (c.finish || "clair") === filterFinish)}
                adjust={adjust} del={del} chute
            />

            {addOpen && <AddInventoryModal onClose={() => setAddOpen(false)} onAdded={load} />}
            {editingThresholds && (
                <ThresholdsModal row={editingThresholds}
                    onClose={() => setEditingThresholds(null)}
                    onSaved={load} />
            )}
            {editingMeta && (
                <EditMetaModal row={editingMeta}
                    onClose={() => setEditingMeta(null)}
                    onSaved={load} />
            )}
            {bulkOpen && (
                <BulkThresholdsModal currentFilter={filterFinish}
                    onClose={() => setBulkOpen(false)}
                    onSaved={load} />
            )}
        </div>
    );
};

// ─── Small UI primitives ───────────────────────────────────────────────
const FinishDot = ({ finish }) => {
    const colorMap = {
        noir: { bg: "#0c182b", border: "#0c182b" },
        mill_finish: { bg: "#a8aab2", border: "#7b7f8a" },  // silver/grey for raw alu
        clair: { bg: "#f3f6fb", border: "#9aaecb" },
    };
    const c = colorMap[finish] || colorMap.clair;
    return (
        <span
            aria-hidden="true"
            className="inline-block w-3 h-3 rounded-full border"
            style={{ background: c.bg, borderColor: c.border }}
        />
    );
};

const FilterChip = ({ active, onClick, children, testId }) => (
    <button
        onClick={onClick}
        data-testid={testId}
        className={`tech-stamp px-3 py-1.5 border text-xs transition-colors flex items-center gap-1.5 ${
            active
                ? "border-[#0c182b] bg-[#0c182b] text-white"
                : "border-[#dde5f0] text-[#4b5d7a] hover:bg-[#f3f6fb]"
        }`}
    >
        {children}
    </button>
);

const StatusBadge = ({ status }) => {
    const styles = {
        ok: "bg-[#e3f6ec] text-[#1e6b3d] border-[#a4d6b6]",
        warn: "bg-[#fff5e6] text-[#7a4a00] border-[#f0c674]",
        danger: "bg-[#fde7e7] text-[#a31a1a] border-[#e89a9a]",
        neutral: "bg-[#f3f6fb] text-[#4b5d7a] border-[#dde5f0]",
    };
    return (
        <span className={`inline-block px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${styles[status.tone]}`}>
            {status.label}
        </span>
    );
};

const QtyProgressBar = ({ qty, min, max }) => {
    if (max === null || max === undefined || max <= 0) return null;
    const pct = Math.min(100, Math.round((qty / max) * 100));
    const isBelow = (min !== null && min !== undefined) && qty <= min;
    return (
        <div className="w-full h-1 bg-[#eef2f7] mt-1">
            <div
                className="h-1 transition-all"
                style={{
                    width: `${pct}%`,
                    background: isBelow ? "#cc1f1f" : qty === 0 ? "#cc1f1f" : "#22a06b",
                }}
            />
        </div>
    );
};

// ─── Inventory table ───────────────────────────────────────────────────
const InventoryTable = ({ title, rows, adjust, del, chute = false, onEditThresholds, onEditMeta }) => (
    <div className="bg-white border border-[#dde5f0]">
        <div className="px-3 py-2 bg-[#f3f6fb] border-b border-[#dde5f0] tech-stamp text-[#0c182b] text-xs flex items-center">
            {title} — {rows.length}
        </div>
        {rows.length === 0 ? (
            <div className="p-3 text-sm text-[#4b5d7a] italic">Aucune entrée.</div>
        ) : (
            <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[640px]">
                    <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                        <tr>
                            <th className="text-left px-3 py-1.5">Profilé</th>
                            <th className="text-left px-3 py-1.5">Fini</th>
                            <th className="text-right px-3 py-1.5">Longueur</th>
                            <th className="text-right px-3 py-1.5">Qté</th>
                            {!chute && <th className="text-right px-3 py-1.5 hidden sm:table-cell">Min/Max</th>}
                            {!chute && <th className="text-center px-3 py-1.5 hidden sm:table-cell">Statut</th>}
                            <th className="text-right px-3 py-1.5">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r) => {
                            const status = rowStatus(r);
                            const fin = r.finish || "clair";
                            const rowBg = !chute && status.tone === "danger" ? "bg-[#fde7e7]/40"
                                : !chute && status.tone === "warn" ? "bg-[#fff5e6]/40" : "";
                            return (
                                <tr key={r.id} className={`border-b border-[#dde5f0]/50 ${rowBg}`} data-testid={`inv-row-${r.id}`}>
                                    <td className="px-3 py-1.5">
                                        <div className="flex items-start gap-1.5">
                                            <div className="flex-1 min-w-0">
                                                <div className="text-[#0c182b]">{r.profile_key}</div>
                                                {r.label && r.label !== r.profile_key && (
                                                    <div className="text-[10px] text-[#4b5d7a]">{r.label}</div>
                                                )}
                                                {!chute && <QtyProgressBar qty={r.qty_available} min={r.restock_min} max={r.restock_max} />}
                                            </div>
                                            {!chute && onEditMeta && (
                                                <button
                                                    onClick={() => onEditMeta(r)}
                                                    className="p-1 text-[#4b5d7a] hover:text-[#0c182b] hover:bg-[#f3f6fb] flex-shrink-0"
                                                    title="Modifier la description"
                                                    data-testid={`inv-edit-meta-${r.id}`}
                                                >
                                                    <Pencil className="w-3 h-3" />
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-3 py-1.5">
                                        <span className="inline-flex items-center gap-1.5">
                                            <FinishDot finish={fin} />
                                            <span className="text-xs">{FINISH_LABELS[fin] || "Clair"}</span>
                                        </span>
                                    </td>
                                    <td className="px-3 py-1.5 text-right font-mono text-xs">{r.bar_length_mm.toFixed(0)} mm</td>
                                    <td className="px-3 py-1.5 text-right">
                                        <div className="inline-flex items-center gap-1">
                                            <button onClick={() => adjust(r, -1)} className="p-1 border border-[#dde5f0] hover:bg-[#fee]" aria-label="-1">
                                                <Minus className="w-3 h-3" />
                                            </button>
                                            <span className={`w-8 text-center font-bold ${r.qty_available === 0 ? "text-red-600" : "text-[#0c182b]"}`}>
                                                {r.qty_available}
                                            </span>
                                            <button onClick={() => adjust(r, 1)} className="p-1 border border-[#dde5f0] hover:bg-[#efe]" aria-label="+1">
                                                <Plus className="w-3 h-3" />
                                            </button>
                                        </div>
                                    </td>
                                    {!chute && (
                                        <td className="px-3 py-1.5 text-right hidden sm:table-cell">
                                            <button
                                                onClick={() => onEditThresholds(r)}
                                                className="inline-flex items-center gap-1 px-2 py-0.5 text-xs border border-[#dde5f0] hover:bg-[#f3f6fb] tech-stamp"
                                                title="Modifier les seuils min/max"
                                                data-testid={`inv-thresholds-${r.id}`}
                                            >
                                                <span className="font-mono">
                                                    {r.restock_min ?? "—"} / {r.restock_max ?? "—"}
                                                </span>
                                                <Pencil className="w-3 h-3" />
                                            </button>
                                        </td>
                                    )}
                                    {!chute && (
                                        <td className="px-3 py-1.5 text-center hidden sm:table-cell">
                                            <StatusBadge status={status} />
                                        </td>
                                    )}
                                    <td className="px-3 py-1.5 text-right">
                                        <button onClick={() => del(r)} className="p-1 text-red-600 hover:bg-red-50" data-testid={`inv-del-${r.id}`}>
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        )}
    </div>
);

// ─── Modals ────────────────────────────────────────────────────────────
const AddInventoryModal = ({ onClose, onAdded }) => {
    const { http } = useAuth();
    const [profileKey, setProfileKey] = useState("");
    const [label, setLabel] = useState("");
    const [finish, setFinish] = useState("clair");
    const [length, setLength] = useState(6800);
    const [qty, setQty] = useState(1);
    const [restockMin, setRestockMin] = useState("");
    const [restockMax, setRestockMax] = useState("");
    const [busy, setBusy] = useState(false);

    const submit = async () => {
        if (!profileKey.trim() || qty < 1 || length <= 0) {
            alert("Profil, longueur et quantité requis.");
            return;
        }
        setBusy(true);
        try {
            await http.post("/admin/alu-inventory", {
                profile_key: profileKey.trim(),
                label: (label.trim() || profileKey.trim()),
                bar_length_mm: length,
                qty_available: qty,
                is_chute: false,
                finish,
                restock_min: restockMin === "" ? null : parseInt(restockMin, 10),
                restock_max: restockMax === "" ? null : parseInt(restockMax, 10),
            });
            await onAdded();
            onClose();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur");
        } finally { setBusy(false); }
    };

    return (
        <Modal
            open
            onClose={onClose}
            title="Ajouter au stock"
            testId="inv-add-modal"
            footer={
                <>
                    <button onClick={onClose} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                    <button onClick={submit} disabled={busy} data-testid="inv-add-submit" className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">
                        {busy ? "Ajout…" : "Ajouter"}
                    </button>
                </>
            }
        >
            <div className="space-y-3">
                <Field label="Profil rapide">
                    <select
                        value=""
                        onChange={(e) => {
                            const p = PRESET_KEYS.find(x => x.key === e.target.value);
                            if (p) { setProfileKey(p.key); setLabel(p.desc); setLength(p.len); }
                        }}
                        className={inputClass}
                        data-testid="inv-preset-select"
                    >
                        <option value="">— Choisir un préréglage —</option>
                        <optgroup label="AT Fabrication — séries portes">
                            {PRESET_KEYS.filter(p => p.key.startsWith("AT Fabrication")).map((p) =>
                                <option key={p.key} value={p.key}>{`${p.desc} (${p.len} mm)`}</option>)}
                        </optgroup>
                        <optgroup label="Trifab — Flush Glaze">
                            {PRESET_KEYS.filter(p => p.key.startsWith("Trifab")).map((p) =>
                                <option key={p.key} value={p.key}>{`${p.desc} (${p.len} mm)`}</option>)}
                        </optgroup>
                        <optgroup label="Kawneer — Mur-rideau 1620">
                            {PRESET_KEYS.filter(p => p.key.startsWith("Kawneer")).map((p) =>
                                <option key={p.key} value={p.key}>{`${p.desc} (${p.len} mm)`}</option>)}
                        </optgroup>
                    </select>
                </Field>
                <Field label="Clé inventaire" required>
                    <input value={profileKey} onChange={(e) => setProfileKey(e.target.value)} className={inputClass}
                        placeholder="ex. AT Fabrication #ATT1005" />
                </Field>
                <Field label="Description (libre)">
                    <input value={label} onChange={(e) => setLabel(e.target.value)} className={inputClass}
                        placeholder="ex. ATT1005 — Tête 2¼ AT1000" />
                </Field>
                <Field label="Fini / Couleur" required>
                    <div className="flex gap-2">
                        {["clair", "noir", "mill_finish"].map((f) => (
                            <button
                                key={f}
                                type="button"
                                onClick={() => setFinish(f)}
                                data-testid={`inv-finish-${f === "mill_finish" ? "mill" : f}`}
                                className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 border tech-stamp text-xs transition-colors ${
                                    finish === f
                                        ? "border-[#0c182b] bg-[#0c182b] text-white"
                                        : "border-[#dde5f0] text-[#4b5d7a] hover:bg-[#f3f6fb]"
                                }`}
                            >
                                <FinishDot finish={f} />
                                {FINISH_LABELS[f]}
                            </button>
                        ))}
                    </div>
                </Field>
                <div className="grid grid-cols-2 gap-3">
                    <Field label="Longueur (mm)" required>
                        <input type="number" step="1" value={length}
                            onChange={(e) => setLength(parseFloat(e.target.value) || 0)}
                            className={inputClass} />
                    </Field>
                    <Field label="Quantité" required>
                        <input type="number" min="1" value={qty}
                            onChange={(e) => setQty(parseInt(e.target.value, 10) || 1)}
                            className={inputClass} />
                    </Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                    <Field label="Min (seuil alerte)">
                        <input type="number" min="0" value={restockMin}
                            onChange={(e) => setRestockMin(e.target.value)}
                            className={inputClass} placeholder="ex. 3" />
                    </Field>
                    <Field label="Max (cible à recommander)">
                        <input type="number" min="0" value={restockMax}
                            onChange={(e) => setRestockMax(e.target.value)}
                            className={inputClass} placeholder="ex. 10" />
                    </Field>
                </div>
                <div className="text-[11px] text-[#4b5d7a]">
                    Standard Portech : portes AT en barres de <b>6800 mm</b> · Flush Glaze / Mur-rideau en barres de <b>7315 mm</b>.
                    L&apos;extrusion <code>AT1000</code> sert à la fois pour la base AT1000 (3⅞&quot;) et la tête AT2000 (3⅞&quot;).
                    Si une ligne identique existe (même clé + longueur + fini), la quantité est cumulée.
                </div>
            </div>
        </Modal>
    );
};

const ThresholdsModal = ({ row, onClose, onSaved }) => {
    const { http } = useAuth();
    const [rmin, setRmin] = useState(row.restock_min ?? "");
    const [rmax, setRmax] = useState(row.restock_max ?? "");
    const [busy, setBusy] = useState(false);

    const save = async () => {
        setBusy(true);
        try {
            await http.patch(`/admin/alu-inventory/${row.id}/thresholds`, {
                restock_min: rmin === "" ? null : parseInt(rmin, 10),
                restock_max: rmax === "" ? null : parseInt(rmax, 10),
            });
            await onSaved();
            onClose();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur");
        } finally { setBusy(false); }
    };

    return (
        <Modal
            open
            onClose={onClose}
            title="Seuils min / max"
            testId="inv-thresholds-modal"
            footer={
                <>
                    <button onClick={onClose} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                    <button onClick={save} disabled={busy} data-testid="inv-thresholds-save" className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">
                        {busy ? "Sauvegarde…" : "Enregistrer"}
                    </button>
                </>
            }
        >
            <div className="space-y-3">
                <div className="text-sm">
                    <div className="font-bold text-[#0c182b]">{row.profile_key}</div>
                    <div className="text-xs text-[#4b5d7a] flex items-center gap-1.5">
                        <FinishDot finish={row.finish || "clair"} /> {FINISH_LABELS[row.finish || "clair"]} · {row.bar_length_mm.toFixed(0)} mm
                    </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                    <Field label="Min (alerte si qté ≤)">
                        <input type="number" min="0" value={rmin}
                            onChange={(e) => setRmin(e.target.value)}
                            className={inputClass} placeholder="ex. 3" />
                    </Field>
                    <Field label="Max (cible à recommander)">
                        <input type="number" min="0" value={rmax}
                            onChange={(e) => setRmax(e.target.value)}
                            className={inputClass} placeholder="ex. 10" />
                    </Field>
                </div>
                <div className="text-[11px] text-[#4b5d7a]">
                    Laisser vide pour désactiver l&apos;alerte. Le bon de commande PDF calcule
                    automatiquement <code>(max − qté actuelle)</code> pour chaque pièce sous le min.
                </div>
            </div>
        </Modal>
    );
};

export default InventoryPanel;

const EditMetaModal = ({ row, onClose, onSaved }) => {
    const { http } = useAuth();
    const [label, setLabel] = useState(row.label || row.profile_key || "");
    const [profileKey, setProfileKey] = useState(row.profile_key || "");
    const [busy, setBusy] = useState(false);

    const save = async () => {
        if (!profileKey.trim()) {
            alert("La clé inventaire ne peut pas être vide.");
            return;
        }
        setBusy(true);
        try {
            await http.patch(`/admin/alu-inventory/${row.id}/meta`, {
                label: label.trim() || null,
                profile_key: profileKey.trim(),
            });
            await onSaved();
            onClose();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur");
        } finally { setBusy(false); }
    };

    return (
        <Modal
            open
            onClose={onClose}
            title="Modifier la description"
            testId="inv-edit-meta-modal"
            footer={
                <>
                    <button onClick={onClose} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                    <button onClick={save} disabled={busy} data-testid="inv-edit-meta-save" className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">
                        {busy ? "Sauvegarde…" : "Enregistrer"}
                    </button>
                </>
            }
        >
            <div className="space-y-3">
                <div className="text-xs text-[#4b5d7a] flex items-center gap-1.5">
                    <FinishDot finish={row.finish || "clair"} /> {FINISH_LABELS[row.finish || "clair"]} · {row.bar_length_mm.toFixed(0)} mm · Qté {row.qty_available}
                </div>
                <Field label="Clé inventaire (utilisée par l'optimiseur)" required>
                    <input value={profileKey} onChange={(e) => setProfileKey(e.target.value)}
                        className={inputClass} data-testid="inv-edit-meta-key"
                        placeholder="ex. AT Fabrication #ATT1005" />
                </Field>
                <Field label="Description (libre)">
                    <input value={label} onChange={(e) => setLabel(e.target.value)}
                        className={inputClass} data-testid="inv-edit-meta-label"
                        placeholder="ex. ATT1005 — Tête 2¼ AT1000" />
                </Field>
                <div className="text-[11px] text-[#4b5d7a]">
                    ⚠ Modifier la clé peut casser la déduction automatique au &quot;Confirmer coupes&quot;
                    si une liste de coupe est en cours et référence l&apos;ancienne clé. La description
                    libre est sans risque — change-la pour corriger une coquille.
                </div>
            </div>
        </Modal>
    );
};


const BulkThresholdsModal = ({ currentFilter, onClose, onSaved }) => {
    const { http } = useAuth();
    const [scope, setScope] = useState(currentFilter === "all" ? "all" : currentFilter);
    const [prefix, setPrefix] = useState("");
    const [rmin, setRmin] = useState("");
    const [rmax, setRmax] = useState("");
    const [busy, setBusy] = useState(false);

    const apply = async () => {
        if (rmin === "" && rmax === "") {
            alert("Renseigne au moins Min ou Max.");
            return;
        }
        const payload = {
            is_chute: false,
            restock_min: rmin === "" ? null : parseInt(rmin, 10),
            restock_max: rmax === "" ? null : parseInt(rmax, 10),
            finish: scope === "all" ? null : scope,
            profile_key_prefix: prefix.trim() || null,
        };
        setBusy(true);
        try {
            const { data } = await http.patch("/admin/alu-inventory-bulk-thresholds", payload);
            await onSaved();
            alert(`${data.modified} ligne(s) mise(s) à jour sur ${data.matched} correspondance(s).`);
            onClose();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur");
        } finally { setBusy(false); }
    };

    return (
        <Modal
            open
            onClose={onClose}
            title="Min / Max en lot"
            testId="inv-bulk-modal"
            footer={
                <>
                    <button onClick={onClose} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                    <button onClick={apply} disabled={busy} data-testid="inv-bulk-apply" className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">
                        {busy ? "Application…" : "Appliquer"}
                    </button>
                </>
            }
        >
            <div className="space-y-3">
                <Field label="Sur quelles lignes appliquer ?">
                    <div className="flex gap-2 flex-wrap">
                        {[
                            { v: "all", label: "Tout" },
                            { v: "clair", label: "Clair seulement" },
                            { v: "noir", label: "Noir seulement" },
                            { v: "mill_finish", label: "Mill seulement" },
                        ].map((opt) => (
                            <button
                                key={opt.v}
                                type="button"
                                onClick={() => setScope(opt.v)}
                                data-testid={`inv-bulk-scope-${opt.v}`}
                                className={`px-3 py-1.5 border tech-stamp text-xs transition-colors ${
                                    scope === opt.v
                                        ? "border-[#0c182b] bg-[#0c182b] text-white"
                                        : "border-[#dde5f0] text-[#4b5d7a] hover:bg-[#f3f6fb]"
                                }`}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </Field>
                <Field label="Filtrer par fournisseur (optionnel)">
                    <select value={prefix} onChange={(e) => setPrefix(e.target.value)} className={inputClass}
                        data-testid="inv-bulk-prefix">
                        <option value="">— Tous les fournisseurs —</option>
                        <option value="AT Fabrication">AT Fabrication seulement</option>
                        <option value="Trifab">Trifab seulement</option>
                        <option value="Kawneer">Kawneer seulement</option>
                    </select>
                </Field>
                <div className="grid grid-cols-2 gap-3">
                    <Field label="Nouveau Min (laisse vide pour ne pas toucher)">
                        <input type="number" min="0" value={rmin}
                            onChange={(e) => setRmin(e.target.value)}
                            data-testid="inv-bulk-min"
                            className={inputClass} placeholder="ex. 2" />
                    </Field>
                    <Field label="Nouveau Max (laisse vide pour ne pas toucher)">
                        <input type="number" min="0" value={rmax}
                            onChange={(e) => setRmax(e.target.value)}
                            data-testid="inv-bulk-max"
                            className={inputClass} placeholder="ex. 8" />
                    </Field>
                </div>
                <div className="text-[11px] text-[#4b5d7a] bg-[#f3f6fb] border border-[#dde5f0] p-2">
                    🛈 Cette action écrase les seuils existants sur toutes les lignes sélectionnées.
                    Tu pourras toujours les ajuster ligne par ligne après avec le crayon dans le tableau.
                </div>
            </div>
        </Modal>
    );
};
