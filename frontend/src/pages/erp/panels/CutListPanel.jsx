/* eslint-disable react-hooks/exhaustive-deps */
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";import {
    Plus, Pencil, Trash2, RefreshCw, Download, FileText, Scissors,
    Upload, Sparkles, Layers, FileDown, X as XIcon,
} from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";
import { DataCard } from "../../../components/mobile/DataCard";
import { FAB } from "../../../components/mobile/FAB";
import { formatDate } from "../utils";

const TYPE_LABELS = {
    frame: "Cadre",
    glass: "Verre",
    panel: "Panneau",
    hardware: "Quincaillerie",
    hole: "Perçage",
    other: "Autre",
};

const TYPE_BADGE = {
    frame:    "bg-[#eaf1fb] text-[#1d3557] border-[#9bb6d8]",
    glass:    "bg-[#e0f7f5] text-[#0a6b6b] border-[#7bd1cf]",
    panel:    "bg-[#f4f4f5] text-[#52525b] border-[#c5c5cc]",
    hardware: "bg-[#fdf2e0] text-[#8a4f1f] border-[#e8b87b]",
    hole:     "bg-[#fbe8e8] text-[#8a1f1f] border-[#e8a5a5]",
    other:    "bg-[#f4f4f5] text-[#52525b] border-[#c5c5cc]",
};

const emptyCut = () => ({
    name: "",
    project_ref: "",
    customer_name: "",
    items: [],
    stock_lengths_mm: [6800, 7000, 7315],
    saw_kerf_mm: 10,
    notes: "",
});

const emptyItem = () => ({
    item_type: "frame",
    label: "",
    profile: "",
    material: "",
    length_mm: 0,
    width_mm: null,
    thickness_mm: null,
    qty: 1,
    notes: "",
});

export const CutListPanel = () => {
    const { http, getToken } = useAuth();
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editOpen, setEditOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [optimization, setOptimization] = useState(null);
    const [extractBusy, setExtractBusy] = useState(false);
    const [extractMsg, setExtractMsg] = useState("");
    const planInputRef = useRef(null);
    const dxfInputRef = useRef(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await http.get("/admin/cuts");
            setRows(data || []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const openNew = () => {
        setEditing(emptyCut());
        setOptimization(null);
        setExtractMsg("");
        setEditOpen(true);
    };

    const openEdit = async (cut) => {
        try {
            const { data } = await http.get(`/admin/cuts/${cut.id}`);
            setEditing(data);
            setOptimization(data.last_optimization || null);
            setExtractMsg("");
            setEditOpen(true);
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur de chargement");
        }
    };

    const closeEdit = () => {
        setEditOpen(false);
        setExtractMsg("");
    };

    const save = async () => {
        if (!editing.name?.trim()) {
            alert("Donnez un nom au projet de coupe.");
            return null;
        }
        try {
            const payload = { ...editing };
            ["project_ref", "customer_name", "notes"].forEach((k) => {
                if (payload[k] === "") payload[k] = null;
            });
            let cutId = editing.id;
            if (cutId) {
                await http.put(`/admin/cuts/${cutId}`, payload);
            } else {
                const { data: created } = await http.post("/admin/cuts", payload);
                cutId = created.id;
                setEditing((prev) => ({ ...prev, id: cutId }));
            }
            await load();
            return cutId;
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur de sauvegarde");
            return null;
        }
    };

    const remove = async (cut) => {
        if (!window.confirm(`Supprimer le projet "${cut.name}" ?`)) return;
        await http.delete(`/admin/cuts/${cut.id}`);
        await load();
    };

    const handleExtractPlan = async (file) => {
        if (!file) return;
        if (file.size > 20 * 1024 * 1024) {
            alert("Fichier trop volumineux (max 20 MB).");
            return;
        }
        setExtractBusy(true);
        setExtractMsg("");
        try {
            const fd = new FormData();
            fd.append("file", file);
            const { data } = await http.post("/admin/cuts/extract", fd, {
                headers: { "Content-Type": "multipart/form-data" },
                timeout: 120000,
            });
            setEditing((prev) => ({
                ...prev,
                source_filename: data.source_filename,
                source_type: data.source_type,
                frame_specs: data.frame_specs || prev.frame_specs || null,
                items: [...(prev.items || []), ...(data.items || [])],
            }));
            const warn = (data.warnings || []).length ? ` — ${data.warnings.join(" / ")}` : "";
            const specsParts = [];
            if (data.frame_specs?.mullion_thickness_mm) specsParts.push(`meneau ${data.frame_specs.mullion_thickness_mm}mm`);
            if (data.frame_specs?.side_clearance_mm) specsParts.push(`lousse ${data.frame_specs.side_clearance_mm}mm`);
            if (data.frame_specs?.undercut_clearance_mm) specsParts.push(`sous-porte ${data.frame_specs.undercut_clearance_mm}mm`);
            const specsStr = specsParts.length ? ` · ${specsParts.join(" / ")}` : "";
            setExtractMsg(
                `🪄 ${data.items.length} élément(s) extrait(s) du plan via IA · confiance ${Math.round((data.confidence || 0) * 100)}%${specsStr}${warn}`,
            );
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur OCR du plan");
        } finally {
            setExtractBusy(false);
        }
    };

    const handleExtractDxf = async (file) => {
        if (!file) return;
        setExtractBusy(true);
        setExtractMsg("");
        try {
            const fd = new FormData();
            fd.append("file", file);
            const { data } = await http.post("/admin/cuts/extract-dxf", fd, {
                headers: { "Content-Type": "multipart/form-data" },
                timeout: 60000,
            });
            setEditing((prev) => ({
                ...prev,
                source_filename: data.source_filename,
                source_type: data.source_type,
                items: [...(prev.items || []), ...(data.items || [])],
            }));
            const warn = (data.warnings || []).length ? ` — ${data.warnings.join(" / ")}` : "";
            setExtractMsg(`📐 ${data.items.length} entité(s) extraite(s) du DXF${warn}`);
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur lecture DXF");
        } finally {
            setExtractBusy(false);
        }
    };

    const addItem = () => {
        setEditing((prev) => ({
            ...prev,
            items: [...(prev.items || []), { ...emptyItem(), id: `tmp_${Date.now()}` }],
        }));
    };

    const updateItem = (idx, patch) => {
        setEditing((prev) => {
            const items = [...(prev.items || [])];
            items[idx] = { ...items[idx], ...patch };
            return { ...prev, items };
        });
    };

    const removeItem = (idx) => {
        setEditing((prev) => {
            const items = [...(prev.items || [])];
            items.splice(idx, 1);
            return { ...prev, items };
        });
    };

    /** Find the first panel item that looks like an AT door and ask the backend
     *  to break it down into 4 frame pieces + 8 mouldings + hardware positions. */
    const decomposeATDoor = async () => {
        const items = editing.items || [];
        const door = items.find(it =>
            it.item_type === "panel" &&
            it.length_mm > 0 && it.width_mm > 0 &&
            (((it.profile || "") + (it.label || "")).match(/AT\s*1?2?000/i)),
        );
        if (!door) {
            alert(
                "Pour décomposer une porte AT, ajoutez d'abord une ligne 'Panneau' avec :\n" +
                "  • profilé = 'AT1000' ou 'AT2000'\n" +
                "  • longueur (mm) = hauteur de la porte\n" +
                "  • largeur (mm) = largeur de la porte\n",
            );
            return;
        }
        // Detect series — 4 production models from AT spec
        const text = ((door.profile || "") + " " + (door.label || "")).toUpperCase().replace(/[\s-_]/g, "");
        let series = "AT1000";
        if (text.includes("ATI2000")) series = "ATi2000";
        else if (text.includes("ATI1000")) series = "ATi1000";
        else if (text.includes("AT2000")) series = "AT2000";
        const customSeries = window.prompt(
            "Série détectée : " + series + "\n\nValidez ou modifiez (AT1000, AT2000, ATi1000, ATi2000) :",
            series,
        );
        if (!customSeries) return;
        try {
            const fs = editing.frame_specs || {};
            const { data } = await http.post("/admin/cuts/decompose-door", {
                door_width_mm: door.width_mm,
                door_height_mm: door.length_mm,
                series: customSeries,
                glass_thickness_mm: door.thickness_mm || 6.0,
                material: door.material || "Aluminium anodisé bronze",
                label_prefix: door.label || "Porte",
                qty: door.qty || 1,
                hardware_rules: {
                    cylinder_height_mm: fs.cylinder_height_mm ?? 1016,
                    strike_offset_mm: fs.strike_offset_mm ?? 19.05,
                    handle_height_mm: fs.handle_height_mm ?? 876.3,
                },
            });
            // Replace the panel door with its breakdown
            const others = items.filter(it => it !== door);
            setEditing((prev) => ({ ...prev, items: [...others, ...(data.items || [])] }));
            const notes = (data.notes || []).join(" · ");
            alert(`✅ Porte décomposée en ${data.items.length} pièces.\n\n${notes}`);
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur de décomposition");
        }
    };

    const optimize = async () => {
        const hasValidFrame = (editing.items || []).some(
            (it) => it.item_type === "frame" && Number(it.length_mm) > 0,
        );
        if (!hasValidFrame) {
            alert("Ajoutez au moins un élément 'Cadre' avec une longueur > 0 mm avant d'optimiser.");
            return;
        }
        try {
            // Ensure saved before optimizing (so we have an id + persisted items)
            if (!editing.id) {
                await save();
                // refetch the saved doc into editing.id
                const { data: list } = await http.get("/admin/cuts");
                const last = list[0];
                if (last) setEditing((prev) => ({ ...prev, id: last.id }));
            }
            const payload = { ...editing };
            const { data } = await http.post("/admin/cuts/optimize-preview", payload);
            setOptimization(data);
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur d'optimisation");
        }
    };

    /** Build the absolute export URL with auth token in the query string.
     *  This lets the browser handle the download natively (no blob/popup
     *  acrobatics, no popup blocker, no iOS WebKit quirks). The backend
     *  accepts ?token= as an alternative to the Bearer header. */
    const buildExportUrl = (cutId, format) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        return `${base}/api/admin/cuts/${cutId}/export.${format}?token=${token}`;
    };

    const exportCsv = async () => {
        const cutId = editing.id || (await save());
        if (!cutId) return;
        // Direct URL navigation — browser triggers a native download because the
        // backend sets Content-Disposition: attachment.
        const url = buildExportUrl(cutId, "csv");
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) {
            // Same-tab navigation works reliably on iOS Safari for downloads.
            window.location.href = url;
        } else {
            window.open(url, "_blank");
        }
    };

    const exportPdf = async () => {
        const cutId = editing.id || (await save());
        if (!cutId) return;
        const url = buildExportUrl(cutId, "pdf");
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) {
            window.location.href = url;
        } else {
            window.open(url, "_blank");
        }
    };

    return (
        <div data-testid="cuts-panel" className="space-y-6">
            <div className="hidden md:block">
                <div className="tech-stamp mb-1">Atelier · Production</div>
                <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Listes de coupe</h1>
                <p className="text-sm text-[#4b5d7a] mt-1">
                    Importez un plan (PDF/photo), un fichier DXF, ou créez une liste manuellement.
                    L'optimiseur calcule le plan de coupe sur barres standards avec saignée et génère un PDF atelier.
                </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
                <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Rafraîchir
                </button>
                <button onClick={openNew} data-testid="cuts-new" className="hidden md:inline-flex btn-primary !py-2 !px-4 !text-xs ml-auto">
                    <Plus className="w-3.5 h-3.5" /> Nouvelle liste
                </button>
            </div>

            {/* MOBILE cards */}
            <div className="md:hidden space-y-3">
                {!loading && rows.length === 0 && (
                    <div className="p-8 text-center text-[#4b5d7a] text-sm border border-[#dde5f0] bg-white">
                        Aucune liste de coupe. Appuyez sur + pour créer.
                    </div>
                )}
                {rows.map((c) => (
                    <DataCard
                        key={c.id}
                        testid={`cuts-card-${c.id}`}
                        stamp={c.source_type ? c.source_type.toUpperCase() : "MANUEL"}
                        title={c.name}
                        subtitle={c.customer_name || c.project_ref || "—"}
                        primary={`${c.items_count || 0} él.`}
                        secondary={`Modifié ${formatDate(c.updated_at)}`}
                        onTap={() => openEdit(c)}
                        actions={[
                            {
                                icon: Trash2,
                                onClick: () => remove(c),
                                label: "Supprimer",
                                testid: `cuts-delete-${c.id}`,
                                color: "border-red-300 text-red-600 active:bg-red-50",
                            },
                        ]}
                    />
                ))}
            </div>

            {/* DESKTOP table */}
            <div className="hidden md:block border border-[#dde5f0] bg-white">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                    <div className="col-span-3">Projet</div>
                    <div className="col-span-2">Réf.</div>
                    <div className="col-span-3">Client</div>
                    <div className="col-span-1 text-center">Éléments</div>
                    <div className="col-span-1 text-center">Source</div>
                    <div className="col-span-1">Modifié</div>
                    <div className="col-span-1 text-right">Actions</div>
                </div>
                {!loading && rows.length === 0 && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">Aucune liste — créez la première !</div>
                )}
                <ul>
                    {rows.map((c) => (
                        <li key={c.id} className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb]">
                            <div className="grid grid-cols-12 gap-4 px-6 py-3 items-center">
                                <div className="col-span-3 text-sm font-medium text-[#0c182b]">
                                    <button onClick={() => openEdit(c)} className="hover:underline text-left">
                                        {c.name}
                                    </button>
                                </div>
                                <div className="col-span-2 text-sm text-[#4b5d7a]">{c.project_ref || "—"}</div>
                                <div className="col-span-3 text-sm">{c.customer_name || "—"}</div>
                                <div className="col-span-1 text-center font-display font-bold">{c.items_count || 0}</div>
                                <div className="col-span-1 text-center">
                                    <span className="tech-stamp px-2 py-0.5 border border-[#dde5f0] text-[10px]">
                                        {(c.source_type || "manuel").toUpperCase()}
                                    </span>
                                </div>
                                <div className="col-span-1 text-xs text-[#4b5d7a]">{formatDate(c.updated_at)}</div>
                                <div className="col-span-1 flex justify-end gap-1">
                                    <button onClick={() => openEdit(c)} className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]" aria-label="Modifier">
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => remove(c)} className="p-2 border border-[#dde5f0] hover:bg-red-50 text-red-600" aria-label="Supprimer">
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>

            <FAB onClick={openNew} label="Nouvelle liste" testid="cuts-fab-new" />

            {editing && (
                <Modal
                    open={editOpen}
                    onClose={closeEdit}
                    title={editing.id ? `Liste : ${editing.name || "Sans titre"}` : "Nouvelle liste de coupe"}
                    testId="cuts-modal"
                    wide
                    footer={
                        <>
                            {editing.id && (
                                <button
                                    onClick={async () => {
                                        if (!window.confirm(`Supprimer la liste "${editing.name}" ? Cette action est définitive.`)) return;
                                        try {
                                            await http.delete(`/admin/cuts/${editing.id}`);
                                            await load();
                                            closeEdit();
                                        } catch (e) {
                                            alert(e?.response?.data?.detail || "Erreur de suppression");
                                        }
                                    }}
                                    data-testid="cuts-modal-delete"
                                    className="px-4 py-2 border border-red-300 text-red-700 tech-stamp hover:bg-red-50 flex items-center gap-1"
                                >
                                    <Trash2 className="w-3.5 h-3.5" /> Supprimer
                                </button>
                            )}
                            <button onClick={closeEdit} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Fermer</button>
                            <button data-testid="cuts-save" onClick={save} className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">
                                Enregistrer
                            </button>
                        </>
                    }
                >
                    <div className="space-y-5">
                        {/* Header fields */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <Field label="Nom du projet" required>
                                <input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className={inputClass} data-testid="cuts-name" />
                            </Field>
                            <Field label="Réf. projet">
                                <input value={editing.project_ref || ""} onChange={(e) => setEditing({ ...editing, project_ref: e.target.value })} className={inputClass} />
                            </Field>
                            <Field label="Client">
                                <input value={editing.customer_name || ""} onChange={(e) => setEditing({ ...editing, customer_name: e.target.value })} className={inputClass} />
                            </Field>
                        </div>

                        {/* Import zone */}
                        <div className="border-2 border-dashed border-[#c5d4e7] bg-[#f9fbfd] p-4">
                            <div className="tech-stamp text-[#4b5d7a] mb-3 flex items-center gap-2">
                                <Upload className="w-3.5 h-3.5" /> Importer un plan
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                <button
                                    type="button"
                                    data-testid="cuts-import-plan"
                                    onClick={() => planInputRef.current?.click()}
                                    disabled={extractBusy}
                                    className="w-full px-4 py-3 border-2 border-[#0c182b] bg-[#0c182b] text-white tech-stamp hover:bg-[#1d3557] flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    <Sparkles className={`w-4 h-4 ${extractBusy ? "animate-pulse" : ""}`} />
                                    {extractBusy ? "Analyse IA…" : "PDF / Photo de plan (IA)"}
                                </button>
                                <button
                                    type="button"
                                    data-testid="cuts-import-dxf"
                                    onClick={() => dxfInputRef.current?.click()}
                                    disabled={extractBusy}
                                    className="w-full px-4 py-3 border border-[#0c182b] text-[#0c182b] tech-stamp hover:bg-[#f3f6fb] flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    <Layers className="w-4 h-4" />
                                    Fichier DXF (exact)
                                </button>
                            </div>
                            {extractMsg && (
                                <div className="mt-3 p-2 border border-[#8ec79d] bg-[#e6f4ea] text-[#0b6b2f] text-xs" data-testid="cuts-extract-result">
                                    {extractMsg}
                                </div>
                            )}
                            <input ref={planInputRef} type="file" accept="application/pdf,image/*" className="hidden"
                                onChange={(e) => { handleExtractPlan(e.target.files?.[0]); e.target.value = ""; }} />
                            <input ref={dxfInputRef} type="file" accept=".dxf" className="hidden"
                                onChange={(e) => { handleExtractDxf(e.target.files?.[0]); e.target.value = ""; }} />
                        </div>

                        {/* Stock + kerf config */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 bg-[#f3f6fb] border border-[#dde5f0]">
                            <Field label="Longueurs barres (mm)" className="col-span-3">
                                <input
                                    value={(editing.stock_lengths_mm || []).join(", ")}
                                    onChange={(e) => {
                                        const arr = e.target.value.split(",").map(s => parseInt(s.trim(), 10)).filter(Boolean);
                                        setEditing({ ...editing, stock_lengths_mm: arr });
                                    }}
                                    className={inputClass}
                                    data-testid="cuts-stock"
                                />
                            </Field>
                            <Field label="Saignée (mm)">
                                <input type="number" min="0" max="20" value={editing.saw_kerf_mm}
                                    onChange={(e) => setEditing({ ...editing, saw_kerf_mm: parseInt(e.target.value, 10) || 0 })}
                                    className={inputClass} data-testid="cuts-kerf" />
                            </Field>
                        </div>

                        {/* Frame specs (editable, with Portech defaults) */}
                        <details className="border border-[#dde5f0]" data-testid="cuts-frame-specs">
                            <summary className="px-3 py-2 bg-[#f3f6fb] tech-stamp text-xs cursor-pointer flex items-center justify-between">
                                <span>⚙️ Paramètres de fabrication (lousses, profilés, positions)</span>
                                <span className="text-[#4b5d7a] text-[10px]">cliquez pour ouvrir</span>
                            </summary>
                            <div className="p-3 space-y-3 bg-white">
                                <div className="tech-stamp text-[#4b5d7a] text-[11px] mb-1">Lousses (clearances) entre la porte et le cadre</div>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <Field label="Lousse haut (mm)">
                                        <input type="number" step="0.01" value={editing.frame_specs?.head_clearance_mm ?? 4.84}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), head_clearance_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} data-testid="cuts-spec-head" />
                                    </Field>
                                    <Field label="Lousse sous-porte (mm)">
                                        <input type="number" step="0.01" value={editing.frame_specs?.undercut_clearance_mm ?? 17.46}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), undercut_clearance_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} data-testid="cuts-spec-undercut" />
                                    </Field>
                                    <Field label="Lousse latérale (mm)">
                                        <input type="number" step="0.01" value={editing.frame_specs?.side_clearance_mm ?? 3.0}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), side_clearance_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} />
                                    </Field>
                                    <Field label="Épais. seuil (mm)">
                                        <input type="number" step="0.01" value={editing.frame_specs?.threshold_thickness_mm ?? 12.7}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), threshold_thickness_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} data-testid="cuts-spec-threshold" />
                                    </Field>
                                </div>
                                <div className="tech-stamp text-[#4b5d7a] text-[11px] mt-3 mb-1">Profilés du cadre (tube à ailettes)</div>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <Field label="Largeur montant (mm)">
                                        <input type="number" step="0.1" value={editing.frame_specs?.jamb_thickness_mm ?? 44.5}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), jamb_thickness_mm: parseFloat(e.target.value) || 0, mullion_thickness_mm: parseFloat(e.target.value) || 0, head_thickness_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} data-testid="cuts-spec-jamb" />
                                    </Field>
                                    <Field label="Profondeur profilé (mm)">
                                        <input type="number" step="0.1" value={editing.frame_specs?.profile_depth_mm ?? 101.6}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), profile_depth_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} />
                                    </Field>
                                </div>
                                <div className="tech-stamp text-[#4b5d7a] text-[11px] mt-3 mb-1">Positions de quincaillerie (depuis le bas de la porte)</div>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <Field label="Cylindre (mm)">
                                        <input type="number" step="0.1" value={editing.frame_specs?.cylinder_height_mm ?? 1016}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), cylinder_height_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} />
                                    </Field>
                                    <Field label="Gâche (offset)">
                                        <input type="number" step="0.1" value={editing.frame_specs?.strike_offset_mm ?? 19.05}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), strike_offset_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} />
                                    </Field>
                                    <Field label="Poignée (mm)">
                                        <input type="number" step="0.1" value={editing.frame_specs?.handle_height_mm ?? 876.3}
                                            onChange={(e) => setEditing({ ...editing, frame_specs: { ...(editing.frame_specs || {}), handle_height_mm: parseFloat(e.target.value) || 0 } })}
                                            className={inputClass} />
                                    </Field>
                                </div>
                            </div>
                        </details>

                        {/* Items table */}
                        <div>
                            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                                <div className="tech-stamp text-[#4b5d7a]">Éléments ({(editing.items || []).length})</div>
                                <div className="flex flex-wrap gap-1">
                                    <button onClick={decomposeATDoor} data-testid="cuts-decompose-door" className="px-3 py-1.5 border border-[#8a4f1f] text-[#8a4f1f] tech-stamp text-xs hover:bg-[#fdf2e0] flex items-center gap-1">
                                        <Layers className="w-3 h-3" /> Décomposer porte AT
                                    </button>
                                    <button onClick={addItem} data-testid="cuts-add-item" className="px-3 py-1.5 border border-[#0c182b] text-[#0c182b] tech-stamp text-xs hover:bg-[#f3f6fb] flex items-center gap-1">
                                        <Plus className="w-3 h-3" /> Ajouter une ligne
                                    </button>
                                </div>
                            </div>
                            {(editing.items || []).length === 0 ? (
                                <div className="p-6 text-center text-[#4b5d7a] text-sm border border-dashed border-[#dde5f0]">
                                    Aucun élément. Importez un plan ou ajoutez une ligne manuellement.
                                </div>
                            ) : (
                                <div className="overflow-x-auto border border-[#dde5f0]">
                                    <table className="w-full text-xs">
                                        <thead className="bg-[#0c182b] text-white">
                                            <tr>
                                                <th className="p-2 text-left">Type</th>
                                                <th className="p-2 text-left">Label</th>
                                                <th className="p-2 text-left">Profilé</th>
                                                <th className="p-2 text-left">N° pièce</th>
                                                <th className="p-2 text-right">L (mm)</th>
                                                <th className="p-2 text-right">l (mm)</th>
                                                <th className="p-2 text-right">Ép. (mm)</th>
                                                <th className="p-2 text-center">Qté</th>
                                                <th className="p-2"></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {(editing.items || []).map((it, idx) => (
                                                <tr key={it.id || idx} className="border-t border-[#dde5f0]">
                                                    <td className="p-1">
                                                        <select value={it.item_type} onChange={(e) => updateItem(idx, { item_type: e.target.value })} className="w-full px-1 py-1 border border-[#dde5f0]">
                                                            {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                                                        </select>
                                                    </td>
                                                    <td className="p-1"><input value={it.label || ""} onChange={(e) => updateItem(idx, { label: e.target.value })} className="w-full px-1 py-1 border border-[#dde5f0]" /></td>
                                                    <td className="p-1"><input value={it.profile || ""} onChange={(e) => updateItem(idx, { profile: e.target.value })} className="w-full px-1 py-1 border border-[#dde5f0]" placeholder="ex. CS68" /></td>
                                                    <td className="p-1"><input value={it.part_number || ""} onChange={(e) => updateItem(idx, { part_number: e.target.value })} className="w-full px-1 py-1 border border-[#dde5f0] font-mono" placeholder="ex. UH-120-DA" /></td>
                                                    <td className="p-1"><input type="number" step="0.1" value={it.length_mm || 0} onChange={(e) => updateItem(idx, { length_mm: parseFloat(e.target.value) || 0 })} className="w-20 px-1 py-1 border border-[#dde5f0] text-right" /></td>
                                                    <td className="p-1"><input type="number" step="0.1" value={it.width_mm || ""} onChange={(e) => updateItem(idx, { width_mm: e.target.value === "" ? null : parseFloat(e.target.value) })} className="w-20 px-1 py-1 border border-[#dde5f0] text-right" disabled={!["glass","panel"].includes(it.item_type)} /></td>
                                                    <td className="p-1"><input type="number" step="0.1" value={it.thickness_mm || ""} onChange={(e) => updateItem(idx, { thickness_mm: e.target.value === "" ? null : parseFloat(e.target.value) })} className="w-16 px-1 py-1 border border-[#dde5f0] text-right" disabled={it.item_type !== "glass"} /></td>
                                                    <td className="p-1"><input type="number" min="1" value={it.qty || 1} onChange={(e) => updateItem(idx, { qty: parseInt(e.target.value, 10) || 1 })} className="w-14 px-1 py-1 border border-[#dde5f0] text-center" /></td>
                                                    <td className="p-1 text-right">
                                                        <button onClick={() => removeItem(idx)} className="p-1 text-red-600 hover:bg-red-50" aria-label="Supprimer ligne">
                                                            <XIcon className="w-3.5 h-3.5" />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                        {/* Action bar : optimize + exports */}
                        <div className="flex flex-wrap gap-2 items-center">
                            <button onClick={optimize} data-testid="cuts-optimize" className="px-4 py-2 bg-[#0b6b2f] text-white tech-stamp flex items-center gap-2 hover:bg-[#0a5a28]">
                                <Scissors className="w-4 h-4" /> Optimiser les coupes
                            </button>
                            <button onClick={exportCsv} className="px-4 py-2 border border-[#0c182b] text-[#0c182b] tech-stamp flex items-center gap-2 hover:bg-[#f3f6fb]">
                                <Download className="w-4 h-4" /> CSV
                            </button>
                            <button onClick={exportPdf} data-testid="cuts-export-pdf" className="px-4 py-2 border border-[#0c182b] text-[#0c182b] tech-stamp flex items-center gap-2 hover:bg-[#f3f6fb]">
                                <FileDown className="w-4 h-4" /> PDF atelier
                            </button>
                        </div>

                        {/* Optimization result */}
                        {optimization && (
                            <div data-testid="cuts-optimization" className="space-y-3 border border-[#dde5f0] bg-white p-4">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                                    <Tile label="Barres" value={optimization.total_bars} />
                                    <Tile label="Chute" value={`${(optimization.total_waste_mm || 0).toFixed(0)} mm`} />
                                    <Tile label="Efficacité" value={`${(optimization.efficiency_pct || 0).toFixed(1)}%`} accent={(optimization.efficiency_pct || 0) >= 85 ? "text-[#0b6b2f]" : "text-[#8a4f1f]"} />
                                    <Tile label="Verres" value={`${optimization.glass_summary?.count || 0} (${(optimization.glass_summary?.total_area_m2 || 0).toFixed(2)} m²)`} />
                                </div>
                                {(optimization.groups || []).map((g, gi) => (
                                    <div key={gi} className="border border-[#dde5f0]">
                                        <div className="px-3 py-2 bg-[#f3f6fb] tech-stamp text-xs">
                                            Profilé : <b>{g.profile}</b> · {g.material} · barre {g.plan.stock_length_mm} mm · {g.plan.bars_count} barre(s) · chute {g.plan.total_waste_mm.toFixed(0)} mm
                                        </div>
                                        <ul>
                                            {(g.plan.bars || []).map((b, bi) => (
                                                <li key={bi} className="border-t border-[#dde5f0] px-3 py-2 text-xs flex items-center gap-3">
                                                    <span className="font-display font-bold text-[#0c182b] w-6">#{bi + 1}</span>
                                                    <span className="flex-1 font-mono">{(b.cuts || []).map(c => c.toFixed(0)).join(" + ")} mm</span>
                                                    <span className="text-[#4b5d7a]">utilisé {b.used_mm.toFixed(0)} mm</span>
                                                    <span className={`${b.waste_mm > 500 ? "text-red-700" : "text-[#0b6b2f]"} font-medium`}>chute {b.waste_mm.toFixed(0)} mm</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        )}

                        <Field label="Notes">
                            <textarea rows={2} value={editing.notes || ""} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} className={inputClass} />
                        </Field>

                        <div className="p-3 bg-[#f3f6fb] border border-[#dde5f0] text-xs text-[#4b5d7a]">
                            💡 Astuce : importez un plan PDF avec cotes — l'IA extrait automatiquement linteau, montants, vitrages avec leurs dimensions exactes. Vérifiez le tableau et cliquez « Optimiser » pour obtenir le plan de coupe sur barres standards avec saignée {editing.saw_kerf_mm} mm.
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
};

const Tile = ({ label, value, accent }) => (
    <div className="bg-white p-3 md:p-4">
        <div className="tech-stamp text-[#4b5d7a] text-[10px] mb-1">{label}</div>
        <div className={`font-display font-bold text-lg md:text-xl tracking-tight ${accent || ""}`}>{value}</div>
    </div>
);
