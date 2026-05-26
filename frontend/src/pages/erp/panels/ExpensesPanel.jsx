/* eslint-disable react-hooks/exhaustive-deps */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Plus, Pencil, Trash2, RefreshCw, Download, Wallet, TrendingDown, Receipt, FileText, Camera, Paperclip, X as XIcon, Sparkles, ScanLine, Mail } from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";
import { DataCard } from "../../../components/mobile/DataCard";
import { FAB } from "../../../components/mobile/FAB";
import { formatCurrency, formatDate } from "../utils";

const TPS_RATE = 0.05;
const TVQ_RATE = 0.09975;

const emptyExpense = () => ({
    date: new Date().toISOString().slice(0, 10),
    supplier_name: "",
    supplier_id: null,
    description: "",
    category: "Matériaux",
    subtotal: 0,
    tps: 0,
    tvq: 0,
    total: 0,
    payment_method: "Carte",
    status: "payée",
    invoice_ref: "",
    notes: "",
});

const monthKey = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;

const CATEGORY_BADGE = {
    "Matériaux":             "bg-[#eaf1fb] text-[#1d3557] border-[#9bb6d8]",
    "Carburant":             "bg-[#fff7e0] text-[#7a5a00] border-[#d4be7a]",
    "Outils":                "bg-[#e0e7f5] text-[#2f4f7f] border-[#a8bcdc]",
    "Véhicule":              "bg-[#fce4ec] text-[#88003a] border-[#d99ab2]",
    "Sous-traitance":        "bg-[#e1f0fd] text-[#0a4a8a] border-[#7bb0e2]",
    "Bureau":                "bg-[#f4f4f5] text-[#52525b] border-[#c5c5cc]",
    "Marketing":             "bg-[#e0f7e8] text-[#0a6b3a] border-[#7bd1a0]",
    "Abonnements logiciels": "bg-[#f5e0f7] text-[#6b0a6b] border-[#cf7bd1]",
    "Repas/Représentation":  "bg-[#fdf2e0] text-[#8a4f1f] border-[#e8b87b]",
    "Téléphonie/Internet":   "bg-[#e7e0f5] text-[#3f1f8a] border-[#a8a0dc]",
    "Loyer":                 "bg-[#fbe8e8] text-[#8a1f1f] border-[#e8a5a5]",
    "Assurances":            "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
    "Formation":             "bg-[#e0f7f5] text-[#0a6b6b] border-[#7bd1cf]",
    "Autre":                 "bg-[#f4f4f5] text-[#52525b] border-[#c5c5cc]",
};

export const ExpensesPanel = () => {
    const { http } = useAuth();
    const [meta, setMeta] = useState({ categories: [], payment_methods: [], statuses: [] });
    const [rows, setRows] = useState([]);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [month, setMonth] = useState(monthKey());
    const [filterCat, setFilterCat] = useState("");
    const [filterStatus, setFilterStatus] = useState("");
    const [editOpen, setEditOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [receiptPreview, setReceiptPreview] = useState(null);  // blob URL for preview
    const [uploadBusy, setUploadBusy] = useState(false);
    const [ocrBusy, setOcrBusy] = useState(false);
    const [ocrResult, setOcrResult] = useState(null);  // { confidence, error?, merchant_name?, ... }
    const [pendingTempReceipt, setPendingTempReceipt] = useState(null);  // {temp_filename, ext}
    const fileInputRef = useRef(null);
    const cameraInputRef = useRef(null);
    const ocrInputRef = useRef(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterCat) params.set("category", filterCat);
            if (filterStatus) params.set("status", filterStatus);
            if (month) params.set("month", month);
            const [{ data: m }, { data: list }, { data: sum }] = await Promise.all([
                http.get("/admin/expenses/meta"),
                http.get(`/admin/expenses?${params}`),
                http.get(`/admin/expenses/summary?month=${month}`),
            ]);
            setMeta(m);
            setRows(list || []);
            setSummary(sum);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [month, filterCat, filterStatus]);

    useEffect(() => { load(); }, [load]);

    const openNew = () => {
        setEditing(emptyExpense());
        setReceiptPreview(null);
        setOcrResult(null);
        setPendingTempReceipt(null);
        setEditOpen(true);
    };
    const openEdit = async (e) => {
        setEditing({ ...e });
        setReceiptPreview(null);
        setOcrResult(null);
        setPendingTempReceipt(null);
        setEditOpen(true);
        if (e.receipt_filename && e.id) {
            // Fetch preview as blob (auth header carries the token)
            try {
                const { data } = await http.get(`/admin/expenses/${e.id}/receipt`, { responseType: "blob" });
                setReceiptPreview(URL.createObjectURL(data));
            } catch {
                /* ignore — file maybe deleted */
            }
        }
    };

    /** Upload a freshly-picked file. Saves the expense first if it's new. */
    const handleReceiptFile = async (file) => {
        if (!file) return;
        if (file.size > 8 * 1024 * 1024) {
            alert("Fichier trop volumineux (max 8 MB). Reprenez la photo en qualité plus basse.");
            return;
        }
        setUploadBusy(true);
        try {
            let expId = editing.id;
            // If brand-new expense, save it first so we have an id
            if (!expId) {
                const payload = { ...editing };
                ["supplier_id", "supplier_name", "invoice_ref", "notes"].forEach((k) => {
                    if (payload[k] === "") payload[k] = null;
                });
                const { data: created } = await http.post("/admin/expenses", payload);
                expId = created.id;
                setEditing({ ...editing, id: expId });
            }
            const fd = new FormData();
            fd.append("file", file);
            const { data } = await http.post(`/admin/expenses/${expId}/receipt`, fd, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            setEditing((prev) => ({ ...prev, receipt_filename: data.receipt_filename }));
            // Show preview
            const objectUrl = URL.createObjectURL(file);
            setReceiptPreview(objectUrl);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur lors de l'upload du reçu");
        } finally {
            setUploadBusy(false);
        }
    };

    const removeReceipt = async () => {
        if (!editing?.id || !editing.receipt_filename) return;
        if (!window.confirm("Supprimer la photo de reçu ?")) return;
        try {
            await http.delete(`/admin/expenses/${editing.id}/receipt`);
            setEditing((prev) => ({ ...prev, receipt_filename: null }));
            setReceiptPreview(null);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur");
        }
    };

    /** Apply OCR extracted fields onto the form, only filling fields the user
     *  hasn't already filled (so we don't trample manual input). */
    const applyOcrToForm = (data) => {
        setEditing((prev) => {
            const next = { ...prev };
            if (data.merchant_name && !prev.supplier_name) {
                next.supplier_name = data.merchant_name;
            }
            if (data.date && /^\d{4}-\d{2}-\d{2}$/.test(data.date)) {
                next.date = data.date;
            }
            if (data.suggested_category && meta.categories.includes(data.suggested_category)) {
                next.category = data.suggested_category;
            }
            if (data.invoice_ref && !prev.invoice_ref) {
                next.invoice_ref = data.invoice_ref;
            }
            // Auto-fill description if empty (so the row isn't blank)
            if (!prev.description && data.merchant_name) {
                next.description = `Achat ${data.merchant_name}`;
            }
            // Money: prefer subtotal+taxes if returned, else back-solve from total
            const sub = typeof data.subtotal === "number" ? data.subtotal : null;
            const tps = typeof data.tps === "number" ? data.tps : null;
            const tvq = typeof data.tvq === "number" ? data.tvq : null;
            const tot = typeof data.total === "number" ? data.total : null;
            if (sub !== null && tps !== null && tvq !== null) {
                next.subtotal = sub;
                next.tps = tps;
                next.tvq = tvq;
                next.total = tot !== null ? tot : Math.round((sub + tps + tvq) * 100) / 100;
            } else if (tot !== null) {
                const subBack = Math.round((tot / (1 + TPS_RATE + TVQ_RATE)) * 100) / 100;
                next.subtotal = subBack;
                next.tps = Math.round(subBack * TPS_RATE * 100) / 100;
                next.tvq = Math.round(subBack * TVQ_RATE * 100) / 100;
                next.total = tot;
            }
            return next;
        });
    };

    /** Snap-first OCR: upload a photo, run OCR, auto-fill the form.
     *  The image is held in a temp slot until the expense is saved. */
    const handleOcrScan = async (file) => {
        if (!file) return;
        if (file.size > 8 * 1024 * 1024) {
            alert("Fichier trop volumineux (max 8 MB).");
            return;
        }
        setOcrBusy(true);
        setOcrResult(null);
        try {
            const fd = new FormData();
            fd.append("file", file);
            const { data } = await http.post("/admin/expenses/ocr-scan", fd, {
                headers: { "Content-Type": "multipart/form-data" },
                timeout: 60000,
            });
            // Even if confidence==0, we still keep the temp file so user can attach
            setOcrResult(data);
            if (data.temp_filename) {
                setPendingTempReceipt({ temp_filename: data.temp_filename });
                // Show the local image as preview right away
                const objectUrl = URL.createObjectURL(file);
                setReceiptPreview(objectUrl);
            }
            if (!data.error) {
                applyOcrToForm(data);
            }
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur lors du scan OCR");
        } finally {
            setOcrBusy(false);
        }
    };

    /** Re-scan a receipt that's already attached to an existing expense. */
    const reScanAttachedReceipt = async () => {
        if (!editing?.id || !editing.receipt_filename) return;
        setOcrBusy(true);
        setOcrResult(null);
        try {
            const { data } = await http.post(
                `/admin/expenses/${editing.id}/receipt/ocr`,
                null,
                { timeout: 60000 },
            );
            setOcrResult(data);
            applyOcrToForm(data);
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur lors du scan OCR");
        } finally {
            setOcrBusy(false);
        }
    };

    /** Auto-compute taxes from subtotal */
    const recomputeFromSubtotal = (sub) => {
        const subF = parseFloat(sub) || 0;
        const tps = Math.round(subF * TPS_RATE * 100) / 100;
        const tvq = Math.round(subF * TVQ_RATE * 100) / 100;
        const total = Math.round((subF + tps + tvq) * 100) / 100;
        setEditing((prev) => ({ ...prev, subtotal: subF, tps, tvq, total }));
    };
    /** Auto-compute subtotal from total (back-solve) */
    const recomputeFromTotal = (tot) => {
        const totF = parseFloat(tot) || 0;
        // total = subtotal × (1 + TPS + TVQ)
        const subtotal = Math.round((totF / (1 + TPS_RATE + TVQ_RATE)) * 100) / 100;
        const tps = Math.round(subtotal * TPS_RATE * 100) / 100;
        const tvq = Math.round(subtotal * TVQ_RATE * 100) / 100;
        setEditing((prev) => ({ ...prev, subtotal, tps, tvq, total: totF }));
    };

    const save = async () => {
        try {
            const payload = { ...editing };
            ["supplier_id", "supplier_name", "invoice_ref", "notes"].forEach((k) => {
                if (payload[k] === "") payload[k] = null;
            });
            let expId = editing.id;
            if (expId) {
                await http.put(`/admin/expenses/${expId}`, payload);
            } else {
                const { data: created } = await http.post("/admin/expenses", payload);
                expId = created.id;
            }
            // If we have a temp receipt from OCR scan, attach it now
            if (pendingTempReceipt?.temp_filename && expId) {
                try {
                    await http.post(
                        `/admin/expenses/${expId}/receipt/attach-temp?temp_filename=${encodeURIComponent(pendingTempReceipt.temp_filename)}`,
                    );
                } catch (err) {
                    console.warn("Attach temp receipt failed", err);
                }
            }
            closeEdit();
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur");
        }
    };

    const closeEdit = () => {
        if (receiptPreview && receiptPreview.startsWith("blob:")) {
            URL.revokeObjectURL(receiptPreview);
        }
        setReceiptPreview(null);
        setOcrResult(null);
        setPendingTempReceipt(null);
        setEditOpen(false);
    };

    const remove = async (e) => {
        if (!window.confirm(`Supprimer la dépense « ${e.description.slice(0, 60)} » ?`)) return;
        await http.delete(`/admin/expenses/${e.id}`);
        await load();
    };

    const exportCsv = async () => {
        const url = `/admin/expenses/export.csv?month=${month}`;
        const { data } = await http.get(url, { responseType: "blob" });
        const blob = new Blob([data], { type: "text/csv;charset=utf-8" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `depenses-${month}.csv`;
        link.click();
    };

    const sendRecapToAccountant = async () => {
        try {
            const { data: preview } = await http.get(`/admin/expenses/recap/preview?month=${month}`);
            const target = window.prompt(
                `Envoyer le récap de ${month} (${preview.count} dépense(s), ${preview.total.toFixed(2)} $) au comptable ?\n\nCourriel destinataire :`,
                preview.default_recipient || "",
            );
            if (!target) return;
            const { data } = await http.post(
                `/admin/expenses/recap/send?month=${month}&to=${encodeURIComponent(target)}`,
            );
            alert(`✅ Récap envoyé à ${data.to}\nResend ID : ${data.resend_id || "n/a"}`);
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur lors de l'envoi du récap");
        }
    };

    const monthOptions = useMemo(() => {
        const out = [];
        const now = new Date();
        for (let i = 0; i < 12; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            out.push({ value: monthKey(d), label: d.toLocaleDateString("fr-CA", { month: "long", year: "numeric" }) });
        }
        return out;
    }, []);

    return (
        <div data-testid="expenses-panel" className="space-y-6">
            <div className="hidden md:block">
                <div className="tech-stamp mb-1">Comptabilité</div>
                <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Dépenses</h1>
            </div>

            {/* Summary tiles */}
            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                    <SummaryTile icon={Receipt} label="Dépenses du mois" value={formatCurrency(summary.total)} sub={`${summary.count} dépense(s)`} testid="exp-stat-total" />
                    <SummaryTile icon={Wallet} label="Sous-total HT" value={formatCurrency(summary.subtotal)} testid="exp-stat-subtotal" />
                    <SummaryTile icon={TrendingDown} label="TPS récupérable" value={formatCurrency(summary.tps)} accent="text-[#0b6b2f]" testid="exp-stat-tps" />
                    <SummaryTile icon={TrendingDown} label="TVQ récupérable" value={formatCurrency(summary.tvq)} accent="text-[#0b6b2f]" testid="exp-stat-tvq" />
                </div>
            )}

            {/* Toolbar */}
            <div className="flex flex-wrap items-center gap-2">
                <select
                    data-testid="exp-month-filter"
                    value={month}
                    onChange={(e) => setMonth(e.target.value)}
                    className={inputClass.replace("w-full", "w-auto")}
                >
                    {monthOptions.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
                <select
                    data-testid="exp-cat-filter"
                    value={filterCat}
                    onChange={(e) => setFilterCat(e.target.value)}
                    className={inputClass.replace("w-full", "w-auto")}
                >
                    <option value="">Toutes catégories</option>
                    {meta.categories.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                    data-testid="exp-status-filter"
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className={inputClass.replace("w-full", "w-auto")}
                >
                    <option value="">Tous statuts</option>
                    {meta.statuses.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                <button onClick={exportCsv} data-testid="exp-export-csv" className="btn-secondary !py-2 !px-3 !text-xs">
                    <Download className="w-3.5 h-3.5" /> CSV
                </button>
                <button onClick={sendRecapToAccountant} data-testid="exp-send-recap" className="btn-secondary !py-2 !px-3 !text-xs" title="Envoyer le récap mensuel au comptable">
                    <Mail className="w-3.5 h-3.5" /> Comptable
                </button>
                <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                </button>
                <button onClick={openNew} data-testid="exp-new" className="hidden md:inline-flex btn-primary !py-2 !px-4 !text-xs ml-auto">
                    <Plus className="w-3.5 h-3.5" /> Nouvelle dépense
                </button>
            </div>

            {/* MOBILE cards */}
            <div className="md:hidden space-y-3">
                {!loading && rows.length === 0 && (
                    <div className="p-8 text-center text-[#4b5d7a] text-sm border border-[#dde5f0] bg-white">
                        Aucune dépense ce mois-ci. Appuyez sur + pour ajouter.
                    </div>
                )}
                {rows.map((e) => (
                    <DataCard
                        key={e.id}
                        testid={`exp-card-${e.id}`}
                        stamp={formatDate(e.date)}
                        title={e.description}
                        subtitle={e.supplier_name || "—"}
                        badge={{ label: e.category, className: CATEGORY_BADGE[e.category] || "border-[#dde5f0]" }}
                        extraBadge={
                            e.receipt_filename
                                ? { label: "📎 Reçu", className: "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]" }
                                : (e.status === "à payer" ? { label: "à payer", className: "bg-[#fff7e0] text-[#7a5a00] border-[#d4be7a]" } : null)
                        }
                        primary={formatCurrency(e.total)}
                        secondary={`HT ${formatCurrency(e.subtotal)} · TPS ${formatCurrency(e.tps)} · TVQ ${formatCurrency(e.tvq)}`}
                        onTap={() => openEdit(e)}
                    />
                ))}
            </div>

            {/* DESKTOP table */}
            <div className="hidden md:block border border-[#dde5f0] bg-white">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                    <div className="col-span-1">Date</div>
                    <div className="col-span-2">Fournisseur</div>
                    <div className="col-span-3">Description</div>
                    <div className="col-span-2">Catégorie</div>
                    <div className="col-span-1 text-right">Sous-tot.</div>
                    <div className="col-span-1 text-right">Total</div>
                    <div className="col-span-1">Statut</div>
                    <div className="col-span-1 text-right">Actions</div>
                </div>
                {!loading && rows.length === 0 && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">Aucune dépense ce mois-ci.</div>
                )}
                <ul>
                    {rows.map((e) => (
                        <li key={e.id} className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb]">
                            <div className="grid grid-cols-12 gap-4 px-6 py-3 items-center">
                                <div className="col-span-1 text-xs text-[#4b5d7a]">{formatDate(e.date)}</div>
                                <div className="col-span-2 text-sm truncate">{e.supplier_name || "—"}</div>
                                <div className="col-span-3 text-sm">
                                    <button onClick={() => openEdit(e)} className="hover:underline text-left font-medium text-[#0c182b]">
                                        {e.description}
                                    </button>
                                    <div className="flex items-center gap-3 mt-0.5 text-xs text-[#4b5d7a]">
                                        {e.invoice_ref && <span>Réf : {e.invoice_ref}</span>}
                                        {e.receipt_filename && <span className="text-[#0b6b2f] flex items-center gap-1"><Paperclip className="w-3 h-3" /> Reçu</span>}
                                    </div>
                                </div>
                                <div className="col-span-2">
                                    <span className={`tech-stamp px-2 py-0.5 border text-[10px] ${CATEGORY_BADGE[e.category] || "border-[#dde5f0]"}`}>
                                        {e.category}
                                    </span>
                                </div>
                                <div className="col-span-1 text-sm text-right text-[#4b5d7a]">{formatCurrency(e.subtotal)}</div>
                                <div className="col-span-1 text-right font-display font-bold text-sm">{formatCurrency(e.total)}</div>
                                <div className="col-span-1">
                                    <span className={`tech-stamp px-2 py-0.5 border text-[10px] ${e.status === "payée" ? "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]" : "bg-[#fff7e0] text-[#7a5a00] border-[#d4be7a]"}`}>
                                        {e.status}
                                    </span>
                                </div>
                                <div className="col-span-1 flex justify-end gap-1">
                                    <button onClick={() => openEdit(e)} className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]" aria-label="Modifier">
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => remove(e)} className="p-2 border border-[#dde5f0] hover:bg-red-50 text-red-600" aria-label="Supprimer">
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>

            {/* By-category breakdown */}
            {summary && summary.by_category.length > 0 && (
                <div className="border border-[#dde5f0] bg-white p-4 md:p-6">
                    <div className="tech-stamp text-[#4b5d7a] mb-3 flex items-center gap-2">
                        <FileText className="w-4 h-4" /> Répartition par catégorie
                    </div>
                    <div className="space-y-2">
                        {summary.by_category.map((c) => {
                            const pct = summary.total > 0 ? (c.total / summary.total) * 100 : 0;
                            return (
                                <div key={c.category}>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span>{c.category}</span>
                                        <span className="font-display font-bold">{formatCurrency(c.total)} <span className="text-[#4b5d7a] text-xs">({pct.toFixed(0)}%)</span></span>
                                    </div>
                                    <div className="h-2 bg-[#f3f6fb] border border-[#dde5f0]">
                                        <div className="h-full bg-[#0c182b]" style={{ width: `${pct}%` }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            <FAB onClick={openNew} label="Nouvelle dépense" testid="exp-fab-new" />

            {/* Edit/new modal */}
            {editing && (
                <Modal
                    open={editOpen}
                    onClose={closeEdit}
                    title={editing.id ? "Modifier la dépense" : "Nouvelle dépense"}
                    testId="exp-modal"
                    footer={
                        <>
                            <button onClick={closeEdit} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                            <button data-testid="exp-save" onClick={save} className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">Enregistrer</button>
                        </>
                    }
                >
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Date" required>
                            <input type="date" value={editing.date} onChange={(e) => setEditing({ ...editing, date: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Catégorie" required>
                            <select value={editing.category} onChange={(e) => setEditing({ ...editing, category: e.target.value })} className={inputClass}>
                                {meta.categories.map((c) => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </Field>
                        <Field label="Fournisseur" className="col-span-2">
                            <input value={editing.supplier_name || ""} placeholder="Ex : Quincaillerie Richelieu" onChange={(e) => setEditing({ ...editing, supplier_name: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Description" required className="col-span-2">
                            <input value={editing.description} placeholder="Ex : Lot de 12 ferme-portes LCN 4040" onChange={(e) => setEditing({ ...editing, description: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Sous-total (avant taxes)" required>
                            <input type="number" step="0.01" data-testid="exp-subtotal" value={editing.subtotal} onChange={(e) => recomputeFromSubtotal(e.target.value)} className={inputClass} />
                        </Field>
                        <Field label="Total (avec taxes)" required>
                            <input type="number" step="0.01" data-testid="exp-total" value={editing.total} onChange={(e) => recomputeFromTotal(e.target.value)} className={inputClass} />
                        </Field>
                        <Field label="TPS (5%)">
                            <input type="number" step="0.01" value={editing.tps} onChange={(e) => setEditing({ ...editing, tps: parseFloat(e.target.value) || 0 })} className={inputClass} />
                        </Field>
                        <Field label="TVQ (9.975%)">
                            <input type="number" step="0.01" value={editing.tvq} onChange={(e) => setEditing({ ...editing, tvq: parseFloat(e.target.value) || 0 })} className={inputClass} />
                        </Field>
                        <Field label="Mode de paiement">
                            <select value={editing.payment_method} onChange={(e) => setEditing({ ...editing, payment_method: e.target.value })} className={inputClass}>
                                {meta.payment_methods.map((p) => <option key={p} value={p}>{p}</option>)}
                            </select>
                        </Field>
                        <Field label="Statut">
                            <select value={editing.status} onChange={(e) => setEditing({ ...editing, status: e.target.value })} className={inputClass}>
                                {meta.statuses.map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </Field>
                        <Field label="Réf. facture fournisseur" className="col-span-2">
                            <input value={editing.invoice_ref || ""} placeholder="Ex : QR-2026-1234" onChange={(e) => setEditing({ ...editing, invoice_ref: e.target.value })} className={inputClass} />
                        </Field>

                        {/* Receipt photo / PDF */}
                        <div className="col-span-2">
                            <div className="tech-stamp text-[#4b5d7a] mb-2 flex items-center justify-between">
                                <span className="flex items-center gap-1">
                                    <Receipt className="w-3.5 h-3.5" /> Photo du reçu (optionnel)
                                </span>
                                {editing.receipt_filename && editing.id && (
                                    <button
                                        type="button"
                                        data-testid="exp-rescan-ocr"
                                        onClick={reScanAttachedReceipt}
                                        disabled={ocrBusy}
                                        className="px-2 py-1 border border-[#0c182b] text-[#0c182b] tech-stamp text-[10px] hover:bg-[#f3f6fb] flex items-center gap-1 disabled:opacity-50"
                                    >
                                        <ScanLine className={`w-3 h-3 ${ocrBusy ? "animate-pulse" : ""}`} />
                                        {ocrBusy ? "Scan…" : "Re-scanner"}
                                    </button>
                                )}
                            </div>

                            {/* OCR result banner */}
                            {ocrResult && !ocrResult.error && (
                                <div
                                    data-testid="exp-ocr-result"
                                    className="mb-2 p-2 border border-[#8ec79d] bg-[#e6f4ea] text-[#0b6b2f] text-xs flex items-start gap-2"
                                >
                                    <Sparkles className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                                    <div>
                                        <strong>Scan IA appliqué</strong>
                                        {typeof ocrResult.confidence === "number" && (
                                            <span> · confiance {Math.round((ocrResult.confidence || 0) * 100)}%</span>
                                        )}
                                        . Vérifiez et corrigez les champs si besoin.
                                    </div>
                                </div>
                            )}
                            {ocrResult?.error && (
                                <div className="mb-2 p-2 border border-[#d4be7a] bg-[#fff7e0] text-[#7a5a00] text-xs">
                                    Scan OCR indisponible. Vous pouvez remplir les champs manuellement.
                                </div>
                            )}

                            {editing.receipt_filename || pendingTempReceipt ? (
                                <div className="border border-[#dde5f0] bg-[#f3f6fb] p-3">
                                    {receiptPreview ? (
                                        receiptPreview.endsWith(".pdf") || (editing.receipt_filename || "").endsWith(".pdf") ? (
                                            <a href={receiptPreview} target="_blank" rel="noreferrer" className="block text-center py-8 hover:bg-white">
                                                <FileText className="w-10 h-10 inline text-[#2f4f7f]" />
                                                <div className="text-sm text-[#2f4f7f] mt-2">Ouvrir le PDF</div>
                                            </a>
                                        ) : (
                                            <a href={receiptPreview} target="_blank" rel="noreferrer">
                                                <img src={receiptPreview} alt="Reçu" className="max-h-64 mx-auto object-contain" />
                                            </a>
                                        )
                                    ) : (
                                        <div className="text-center py-6 text-[#4b5d7a] text-sm">Chargement de l'aperçu…</div>
                                    )}
                                    <div className="mt-3 flex justify-between items-center">
                                        <div className="text-xs text-[#4b5d7a] truncate">
                                            {editing.receipt_filename || "Reçu en attente — sera attaché à l'enregistrement"}
                                        </div>
                                        {editing.receipt_filename && (
                                            <button
                                                type="button"
                                                data-testid="exp-remove-receipt"
                                                onClick={removeReceipt}
                                                className="px-3 py-1.5 border border-red-300 text-red-700 tech-stamp text-xs hover:bg-red-50 flex items-center gap-1"
                                            >
                                                <XIcon className="w-3 h-3" /> Retirer
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {/* Primary AI scan button — wide */}
                                    <button
                                        type="button"
                                        data-testid="exp-ocr-scan"
                                        onClick={() => ocrInputRef.current?.click()}
                                        disabled={ocrBusy || uploadBusy}
                                        className="w-full px-4 py-3 border-2 border-[#0c182b] bg-[#0c182b] text-white tech-stamp hover:bg-[#1d3557] flex items-center justify-center gap-2 disabled:opacity-50"
                                    >
                                        <Sparkles className={`w-4 h-4 ${ocrBusy ? "animate-pulse" : ""}`} />
                                        {ocrBusy ? "Analyse IA en cours…" : "Scanner reçu (IA auto-remplit)"}
                                    </button>
                                    <div className="grid grid-cols-2 gap-2">
                                        <button
                                            type="button"
                                            data-testid="exp-take-photo"
                                            onClick={() => cameraInputRef.current?.click()}
                                            disabled={uploadBusy || ocrBusy}
                                            className="px-3 py-2 border border-[#dde5f0] text-[#4b5d7a] tech-stamp text-xs hover:bg-[#f3f6fb] flex items-center justify-center gap-1 disabled:opacity-50"
                                        >
                                            <Camera className="w-3.5 h-3.5" /> Photo sans IA
                                        </button>
                                        <button
                                            type="button"
                                            data-testid="exp-pick-file"
                                            onClick={() => fileInputRef.current?.click()}
                                            disabled={uploadBusy || ocrBusy}
                                            className="px-3 py-2 border border-[#dde5f0] text-[#4b5d7a] tech-stamp text-xs hover:bg-[#f3f6fb] flex items-center justify-center gap-1 disabled:opacity-50"
                                        >
                                            <Paperclip className="w-3.5 h-3.5" /> Galerie / PDF
                                        </button>
                                    </div>
                                </div>
                            )}
                            {uploadBusy && <div className="text-xs text-[#4b5d7a] mt-2 text-center">Upload en cours…</div>}
                            {/* Hidden inputs */}
                            <input
                                ref={ocrInputRef}
                                type="file"
                                accept="image/*,application/pdf"
                                capture="environment"
                                className="hidden"
                                data-testid="exp-ocr-input"
                                onChange={(e) => { handleOcrScan(e.target.files?.[0]); e.target.value = ""; }}
                            />
                            <input
                                ref={cameraInputRef}
                                type="file"
                                accept="image/*"
                                capture="environment"
                                className="hidden"
                                data-testid="exp-camera-input"
                                onChange={(e) => { handleReceiptFile(e.target.files?.[0]); e.target.value = ""; }}
                            />
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*,application/pdf"
                                className="hidden"
                                data-testid="exp-file-input"
                                onChange={(e) => { handleReceiptFile(e.target.files?.[0]); e.target.value = ""; }}
                            />
                        </div>

                        <Field label="Notes" className="col-span-2">
                            <textarea rows={2} value={editing.notes || ""} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} className={inputClass} />
                        </Field>
                        <div className="col-span-2 p-3 bg-[#f3f6fb] border border-[#dde5f0] text-xs text-[#4b5d7a]">
                            💡 Astuce : prenez le reçu en photo avec « Scanner reçu (IA) » — l'IA remplit automatiquement marchand, date, sous-total, TPS, TVQ, total et catégorie. Vous pouvez aussi taper le sous-total ou le total — les taxes se calculent à rebours.
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
};

const SummaryTile = ({ icon: Icon, label, value, sub, accent, testid }) => (
    <div data-testid={testid} className="bg-white p-4 md:p-6">
        <div className="flex items-center gap-2 mb-2 md:mb-3 tech-stamp">
            <Icon className={`w-4 h-4 ${accent || "text-[#2f4f7f]"}`} />
            <span className="truncate">{label}</span>
        </div>
        <div className={`font-display font-bold text-xl md:text-3xl tracking-tight ${accent || ""}`}>{value}</div>
        {sub && <div className="text-xs text-[#4b5d7a] mt-1">{sub}</div>}
    </div>
);
