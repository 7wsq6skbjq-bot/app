/** AT Fabrication door order panel — Phase 1 MVP.
 *
 *  Flow:
 *    1. User clicks "Parser un PDF" → file picker → server-side Gemini OCR.
 *    2. UI shows an editable form pre-filled with the OCR output.
 *    3. User clicks "Generer plan d'atelier" → PDF downloaded.
 *    4. Optional "Enregistrer" persists the order in MongoDB for later access.
 */
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    DoorOpen, Upload, Download, Save, Trash2, RefreshCw, Plus, FileText,
    AlertCircle, Scissors, Copy, CheckCircle2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const SERIES = ["AT1000", "ATi1000", "AT2000", "ATi2000"];
const HANDS = ["GE", "DE", "PE", "GI", "DI", "PI", "unknown"];
const GLAZINGS = ["thermos", "simple", "unknown"];

const emptyOrder = () => ({
    id: "",
    client: "", contact: "", phone: "",
    order_number: "", project_name: "",
    order_date: "", required_date: "",
    finish_exterior: "", finish_interior: "",
    color_code_exterior: "", color_code_interior: "",
    doors: [],
    hardware: {},
    notes: "",
});

const emptyDoor = () => ({
    tag: "", series: "AT1000", width_in: 36, height_in: 84, qty: 1,
    hand: "unknown", glazing: "unknown", notes: "",
    hardware: {},
});

const HARDWARE_KEYS = [
    ["Charnières", [
        ["hinge_4_5x4", "Charnière 4-1/2 x 4 x 0.134"],
        ["hinge_continuous", "Charnière continue"],
        ["hinge_continuous_hd", "Charnière continue HD"],
    ]],
    ["Poignées / Barres", [
        ["pull_9_back_to_back", "Poignées 9\" dos-à-dos"],
        ["pull_9_exterior", "Poignée 9\" extérieure"],
        ["pull_9_interior", "Poignée 9\" intérieure"],
        ["pull_12_back_to_back", "Poignées 12\" dos-à-dos"],
        ["pull_12_exterior", "Poignée 12\" extérieure"],
        ["pull_12_interior", "Poignée 12\" intérieure"],
        ["push_bar_tubular", "Barre à pousser tubulaire"],
    ]],
    ["Serrures / Sécurité", [
        ["lock_4510_ar", "Serrure à ressort 4510 AR"],
        ["lock_4590_ar", "Palette de relâche 4590 AR"],
        ["lock_sm_1850_ar", "Serrure SM 1850 AR"],
        ["panic_8400_ar", "Barre panique 8400 AR"],
        ["panic_8600_ar", "Barre panique 8600 AR"],
        ["cylinder_exterior", "Barillet extérieur"],
        ["cylinder_interior_manual", "Barillet manuel intérieur"],
        ["cylinder_protector", "Protecteur de barillet"],
        ["bolt_protector", "Protège-pêne"],
        ["strike_standard", "Gâche standard"],
        ["strike_electric", "Gâche électrique"],
        ["contact_recessed", "Contact encastré"],
    ]],
    ["Autres", [
        ["astragal", "Astragale"],
        ["flush_bolts", "Verrous affleurés"],
        ["door_sweep", "Balai de porte"],
        ["moulding_thermo", "Moulure thermos (AT1050)"],
        ["moulding_simple", "Moulure verre simple (AT1045)"],
    ]],
];

const inputCls = "w-full bg-white border border-[#dde5f0] text-[#0c182b] focus:border-[#0c182b] outline-none px-3 py-1.5 text-sm";

export const ATOrdersPanel = () => {
    const { http, getToken } = useAuth();
    const [orders, setOrders] = useState([]);
    const [order, setOrder] = useState(emptyOrder());
    const [parsing, setParsing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");
    const [creatingCutList, setCreatingCutList] = useState(false);
    const fileRef = useRef(null);

    // ── Helpers ────────────────────────────────────────────────
    // Legacy v1 orders stored hardware at the top level; new orders nest it
    // inside each door. Migrate on load so the UI always sees per-door HW.
    const _migrateOrder = (raw) => {
        if (!raw) return emptyOrder();
        const next = { ...emptyOrder(), ...raw };
        const topHw = next.hardware && Object.keys(next.hardware).length ? next.hardware : null;
        next.doors = (next.doors || []).map((d) => {
            const hw = d.hardware && Object.keys(d.hardware).length ? d.hardware : (topHw || {});
            return { ...emptyDoor(), ...d, hardware: { ...hw } };
        });
        // We no longer use the global hardware once doors carry it.
        next.hardware = {};
        return next;
    };

    const loadList = useCallback(async () => {
        try {
            const { data } = await http.get("/admin/at-orders");
            setOrders(data.orders || []);
        } catch (e) {
            console.error(e);
        }
    }, [http]);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const { data } = await http.get("/admin/at-orders");
                if (!cancelled) setOrders(data.orders || []);
            } catch {
                /* silent — user can hit Rafraîchir */
            }
        })();
        return () => { cancelled = true; };
    }, [http]);

    const onUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setParsing(true);
        setErrorMsg("");
        const form = new FormData();
        form.append("file", file);
        try {
            const { data } = await http.post("/admin/at-orders/parse", form, {
                headers: { "Content-Type": "multipart/form-data" },
                timeout: 90000,
            });
            setOrder(_migrateOrder(data));
        } catch (err) {
            setErrorMsg(err?.response?.data?.detail || "Erreur OCR — le PDF n'a pas pu être lu.");
        } finally {
            setParsing(false);
            if (fileRef.current) fileRef.current.value = "";
        }
    };

    const setField = (k, v) => setOrder((o) => ({ ...o, [k]: v }));
    const setDoor = (idx, k, v) => {
        setOrder((o) => {
            const next = [...(o.doors || [])];
            next[idx] = { ...next[idx], [k]: v };
            return { ...o, doors: next };
        });
    };
    const addDoor = () => setOrder((o) => ({ ...o, doors: [...(o.doors || []), emptyDoor()] }));
    const removeDoor = (idx) => setOrder((o) => ({
        ...o, doors: (o.doors || []).filter((_, i) => i !== idx),
    }));
    const toggleHardware = (doorIdx, k) => setOrder((o) => {
        const doors = [...(o.doors || [])];
        if (!doors[doorIdx]) return o;
        const hw = { ...(doors[doorIdx].hardware || {}) };
        hw[k] = !hw[k];
        doors[doorIdx] = { ...doors[doorIdx], hardware: hw };
        return { ...o, doors };
    });
    const copyHardwareToAll = (fromIdx) => setOrder((o) => {
        const src = o.doors?.[fromIdx]?.hardware || {};
        const doors = (o.doors || []).map((d, i) =>
            i === fromIdx ? d : { ...d, hardware: { ...src } });
        return { ...o, doors };
    });

    const save = async () => {
        if (!order.doors?.length) {
            setErrorMsg("Au moins une porte est requise avant d'enregistrer.");
            return;
        }
        setSaving(true);
        try {
            const payload = { ...order };
            if (!payload.id) delete payload.id;
            const { data } = await http.post("/admin/at-orders", payload);
            setOrder(_migrateOrder(data));
            await loadList();
            setSuccessMsg("Commande enregistrée.");
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'enregistrement.");
        } finally { setSaving(false); }
    };

    const generatePdf = async () => {
        if (!order.doors?.length) {
            setErrorMsg("Aucune porte — impossible de générer le plan.");
            return;
        }
        setGenerating(true);
        try {
            // Stateless POST so the user can preview without saving.
            const { data } = await http.post(
                "/admin/at-orders/shop-drawing.pdf",
                order,
                { responseType: "blob", timeout: 60000 },
            );
            const blob = new Blob([data], { type: "application/pdf" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `plan-atelier-${order.order_number || "atorder"}.pdf`;
            a.click();
            setTimeout(() => URL.revokeObjectURL(url), 5000);
        } catch (e) {
            setErrorMsg("Erreur lors de la génération du PDF.");
        } finally { setGenerating(false); }
    };

    const openSaved = async (id) => {
        try {
            const { data } = await http.get(`/admin/at-orders/${id}`);
            setOrder(_migrateOrder(data));
            window.scrollTo({ top: 0, behavior: "smooth" });
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur");
        }
    };

    const deleteSaved = async (id) => {
        if (!window.confirm("Supprimer cette commande ?")) return;
        try {
            await http.delete(`/admin/at-orders/${id}`);
            if (order.id === id) setOrder(emptyOrder());
            await loadList();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur");
        }
    };

    const downloadSaved = (id) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/at-orders/${id}/shop-drawing.pdf?token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const createCutList = async () => {
        if (!order.doors?.length) {
            setErrorMsg("Aucune porte — impossible de créer une liste de coupe.");
            return;
        }
        setCreatingCutList(true);
        setErrorMsg("");
        try {
            const { data } = await http.post("/admin/at-orders/to-cut-list", order);
            setSuccessMsg(
                `Liste de coupe créée : « ${data.name} » (${data.items_count} pièces). `
                + `Ouvrez l'onglet « Liste de coupe » pour la consulter.`,
            );
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur lors de la création de la liste de coupe.");
        } finally { setCreatingCutList(false); }
    };

    const totalDoors = useMemo(
        () => (order.doors || []).reduce((s, d) => s + (parseInt(d.qty, 10) || 1), 0),
        [order.doors],
    );

    return (
        <div className="space-y-4" data-testid="at-orders-panel">
            {/* ─── Header ──────────────────────────────────────── */}
            <div className="flex items-center gap-2 flex-wrap">
                <DoorOpen className="w-5 h-5 text-[#0c182b]" />
                <h2 className="font-display font-bold text-xl text-[#0c182b]">Commandes AT Fabrication</h2>
                <button onClick={loadList} className="ml-auto btn-secondary !py-1.5 !px-3 !text-xs">
                    <RefreshCw className="w-3.5 h-3.5" /> Rafraîchir
                </button>
                <input ref={fileRef} type="file" accept="application/pdf" onChange={onUpload} className="hidden"
                    data-testid="at-orders-upload" />
                <button onClick={() => fileRef.current?.click()} disabled={parsing}
                    className="btn-primary !py-1.5 !px-3 !text-xs"
                    data-testid="at-orders-parse-btn">
                    <Upload className="w-3.5 h-3.5" /> {parsing ? "Lecture…" : "Parser un PDF"}
                </button>
                <button onClick={() => setOrder(emptyOrder())} className="btn-secondary !py-1.5 !px-3 !text-xs">
                    <FileText className="w-3.5 h-3.5" /> Nouveau (vide)
                </button>
                <button
                    onClick={() => {
                        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
                        const token = encodeURIComponent(getToken() || "");
                        const url = `${base}/api/admin/at-order-form.pdf?token=${token}`;
                        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
                        if (isMobile) window.location.href = url; else window.open(url, "_blank");
                    }}
                    className="btn-secondary !py-1.5 !px-3 !text-xs"
                    data-testid="at-orders-form-btn"
                    title="Télécharger le formulaire vierge pour les vitreries clients"
                >
                    <Download className="w-3.5 h-3.5" /> Formulaire client vierge
                </button>
            </div>

            {errorMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#fde7e7] border border-[#e89a9a] text-[#a31a1a] text-sm">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{errorMsg}</div>
                    <button onClick={() => setErrorMsg("")} className="text-[#a31a1a] hover:underline text-xs">Fermer</button>
                </div>
            )}

            {successMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#e6f7ee] border border-[#86c9a4] text-[#0f6b3a] text-sm"
                    data-testid="at-orders-success-banner">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{successMsg}</div>
                    <button onClick={() => setSuccessMsg("")} className="text-[#0f6b3a] hover:underline text-xs">Fermer</button>
                </div>
            )}

            {/* ─── Form ──────────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-4">
                <h3 className="tech-stamp text-[#0c182b] font-bold">Informations commande</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <Field label="Client">
                        <input value={order.client || ""} onChange={(e) => setField("client", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Responsable">
                        <input value={order.contact || ""} onChange={(e) => setField("contact", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Téléphone">
                        <input value={order.phone || ""} onChange={(e) => setField("phone", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="N° commande">
                        <input value={order.order_number || ""} onChange={(e) => setField("order_number", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Projet">
                        <input value={order.project_name || ""} onChange={(e) => setField("project_name", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Date commande">
                        <input type="date" value={order.order_date || ""} onChange={(e) => setField("order_date", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Date requise">
                        <input type="date" value={order.required_date || ""} onChange={(e) => setField("required_date", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Fini extérieur">
                        <input value={order.finish_exterior || ""} onChange={(e) => setField("finish_exterior", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Code couleur ext.">
                        <input value={order.color_code_exterior || ""} onChange={(e) => setField("color_code_exterior", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Fini intérieur">
                        <input value={order.finish_interior || ""} onChange={(e) => setField("finish_interior", e.target.value)} className={inputCls} />
                    </Field>
                    <Field label="Code couleur int.">
                        <input value={order.color_code_interior || ""} onChange={(e) => setField("color_code_interior", e.target.value)} className={inputCls} />
                    </Field>
                </div>
            </div>

            {/* ─── Doors ──────────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-3">
                <div className="flex items-center gap-2">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">
                        Portes ({order.doors?.length || 0} ligne(s) — total {totalDoors} unité(s))
                    </h3>
                    <button onClick={addDoor} className="ml-auto btn-secondary !py-1 !px-2 !text-xs">
                        <Plus className="w-3.5 h-3.5" /> Ajouter
                    </button>
                </div>
                {(order.doors || []).length === 0 ? (
                    <div className="text-sm italic text-[#4b5d7a]">Aucune porte — parse un PDF ou ajoute une ligne.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm min-w-[800px]">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                                <tr>
                                    <th className="text-left px-2 py-1.5">TAG</th>
                                    <th className="text-left px-2 py-1.5">Série</th>
                                    <th className="text-right px-2 py-1.5">Largeur (po)</th>
                                    <th className="text-right px-2 py-1.5">Hauteur (po)</th>
                                    <th className="text-right px-2 py-1.5">Qté</th>
                                    <th className="text-left px-2 py-1.5">Sens</th>
                                    <th className="text-left px-2 py-1.5">Verre</th>
                                    <th className="px-2 py-1.5"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {order.doors.map((d, i) => (
                                    <tr key={i} className="border-b border-[#dde5f0]/50" data-testid={`door-row-${i}`}>
                                        <td className="px-2 py-1.5">
                                            <input value={d.tag || ""} onChange={(e) => setDoor(i, "tag", e.target.value)} className={inputCls + " !min-w-[100px]"} />
                                        </td>
                                        <td className="px-2 py-1.5">
                                            <select value={d.series} onChange={(e) => setDoor(i, "series", e.target.value)} className={inputCls + " !min-w-[110px]"}>
                                                {SERIES.map((s) => <option key={s} value={s}>{s}</option>)}
                                            </select>
                                        </td>
                                        <td className="px-2 py-1.5 text-right">
                                            <input type="number" step="0.125" value={d.width_in} onChange={(e) => setDoor(i, "width_in", parseFloat(e.target.value) || 0)} className={inputCls + " !w-24 text-right"} />
                                        </td>
                                        <td className="px-2 py-1.5 text-right">
                                            <input type="number" step="0.125" value={d.height_in} onChange={(e) => setDoor(i, "height_in", parseFloat(e.target.value) || 0)} className={inputCls + " !w-24 text-right"} />
                                        </td>
                                        <td className="px-2 py-1.5 text-right">
                                            <input type="number" min="1" value={d.qty} onChange={(e) => setDoor(i, "qty", parseInt(e.target.value, 10) || 1)} className={inputCls + " !w-16 text-right"} />
                                        </td>
                                        <td className="px-2 py-1.5">
                                            <select value={d.hand} onChange={(e) => setDoor(i, "hand", e.target.value)} className={inputCls + " !min-w-[80px]"}>
                                                {HANDS.map((h) => <option key={h} value={h}>{h}</option>)}
                                            </select>
                                        </td>
                                        <td className="px-2 py-1.5">
                                            <select value={d.glazing} onChange={(e) => setDoor(i, "glazing", e.target.value)} className={inputCls + " !min-w-[110px]"}>
                                                {GLAZINGS.map((g) => <option key={g} value={g}>{g}</option>)}
                                            </select>
                                        </td>
                                        <td className="px-2 py-1.5 text-right">
                                            <button onClick={() => removeDoor(i)} className="p-1 text-red-600 hover:bg-red-50" data-testid={`door-remove-${i}`}>
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* ─── Hardware matrix (per door) ─────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-3" data-testid="hardware-matrix">
                <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">
                        Quincaillerie — matrice par porte
                    </h3>
                    <span className="text-[10px] text-[#4b5d7a]">
                        Une coche par cellule = quincaillerie posée sur cette porte.
                    </span>
                </div>
                {(order.doors || []).length === 0 ? (
                    <div className="text-sm italic text-[#4b5d7a]">Ajoute au moins une porte pour saisir la quincaillerie.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm min-w-[640px]">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0] bg-[#f3f6fb]">
                                <tr>
                                    <th className="text-left px-2 py-1.5 sticky left-0 bg-[#f3f6fb]">Pièce</th>
                                    {order.doors.map((d, i) => (
                                        <th key={i} className="px-2 py-1.5 text-center min-w-[80px]">
                                            <div className="font-mono text-[#0c182b]">{d.tag || `D${i + 1}`}</div>
                                            <button
                                                onClick={() => copyHardwareToAll(i)}
                                                className="mt-0.5 px-1 py-0.5 text-[9px] border border-[#dde5f0] hover:bg-white tech-stamp inline-flex items-center gap-0.5"
                                                title="Copier la quincaillerie de cette porte vers toutes les autres"
                                                data-testid={`hardware-copy-from-${i}`}>
                                                <Copy className="w-2.5 h-2.5" /> Copier
                                            </button>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {HARDWARE_KEYS.map(([group, items]) => (
                                    <Fragment key={group}>
                                        <tr className="bg-[#7d9ac2]">
                                            <td colSpan={order.doors.length + 1}
                                                className="px-2 py-1 text-[10px] uppercase tracking-wider text-white font-bold">
                                                {group}
                                            </td>
                                        </tr>
                                        {items.map(([key, label], rowIdx) => (
                                            <tr key={key} className={rowIdx % 2 === 0 ? "bg-white" : "bg-[#f7f9fc]"}>
                                                <td className="px-2 py-1 text-[#0c182b] sticky left-0 bg-inherit">{label}</td>
                                                {order.doors.map((d, i) => (
                                                    <td key={i} className="px-2 py-1 text-center">
                                                        <input
                                                            type="checkbox"
                                                            data-testid={`hardware-${i}-${key}`}
                                                            checked={!!d.hardware?.[key]}
                                                            onChange={() => toggleHardware(i, key)}
                                                            className="w-4 h-4 accent-[#0c182b] cursor-pointer" />
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </Fragment>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* ─── Notes ──────────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-2">
                <h3 className="tech-stamp text-[#0c182b] font-bold">Notes</h3>
                <textarea rows={3} value={order.notes || ""} onChange={(e) => setField("notes", e.target.value)}
                    className={inputCls + " resize-none"} />
            </div>

            {/* ─── Actions ──────────────────────────────────────── */}
            <div className="flex items-center gap-2 flex-wrap sticky bottom-2 z-10 bg-white/80 backdrop-blur p-2 border border-[#dde5f0]">
                <button onClick={save} disabled={saving} data-testid="at-orders-save"
                    className="btn-secondary !py-2 !px-4 !text-sm">
                    <Save className="w-4 h-4" /> {saving ? "Sauvegarde…" : "Enregistrer"}
                </button>
                <button onClick={generatePdf} disabled={generating} data-testid="at-orders-generate"
                    className="btn-primary !py-2 !px-4 !text-sm">
                    <Download className="w-4 h-4" /> {generating ? "Génération…" : "Générer plan d'atelier"}
                </button>
                <button onClick={createCutList} disabled={creatingCutList} data-testid="at-orders-create-cutlist"
                    className="btn-secondary !py-2 !px-4 !text-sm">
                    <Scissors className="w-4 h-4" /> {creatingCutList ? "Création…" : "Créer liste de coupe"}
                </button>
            </div>

            {/* ─── Saved orders list ──────────────────────────────────────── */}
            {orders.length > 0 && (
                <div className="bg-white border border-[#dde5f0]">
                    <div className="px-3 py-2 bg-[#f3f6fb] border-b border-[#dde5f0] tech-stamp text-[#0c182b] text-xs">
                        Commandes enregistrées — {orders.length}
                    </div>
                    <table className="w-full text-sm">
                        <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                            <tr>
                                <th className="text-left px-3 py-1.5">N° commande</th>
                                <th className="text-left px-3 py-1.5">Client</th>
                                <th className="text-left px-3 py-1.5">Projet</th>
                                <th className="text-right px-3 py-1.5">Portes</th>
                                <th className="text-right px-3 py-1.5">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.map((o) => (
                                <tr key={o.id} className="border-b border-[#dde5f0]/50">
                                    <td className="px-3 py-1.5 font-mono text-xs">{o.order_number || "—"}</td>
                                    <td className="px-3 py-1.5">{o.client || "—"}</td>
                                    <td className="px-3 py-1.5">{o.project_name || "—"}</td>
                                    <td className="px-3 py-1.5 text-right">{(o.doors || []).reduce((s, d) => s + (d.qty || 1), 0)}</td>
                                    <td className="px-3 py-1.5 text-right">
                                        <button onClick={() => openSaved(o.id)} className="px-2 py-0.5 text-xs border border-[#dde5f0] hover:bg-[#f3f6fb] tech-stamp mr-1">Ouvrir</button>
                                        <button onClick={() => downloadSaved(o.id)} className="px-2 py-0.5 text-xs border border-[#dde5f0] hover:bg-[#f3f6fb] tech-stamp mr-1">PDF</button>
                                        <button onClick={() => deleteSaved(o.id)} className="px-2 py-0.5 text-xs text-red-600 hover:bg-red-50">
                                            <Trash2 className="w-3 h-3 inline" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

const Field = ({ label, children }) => (
    <div>
        <div className="text-[10px] uppercase tracking-wider text-[#4b5d7a] font-bold mb-1">{label}</div>
        {children}
    </div>
);

export default ATOrdersPanel;
