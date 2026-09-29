import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Trash2, Calculator, AlertTriangle, Save, DoorClosed, Search, X, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Field, inputClass, Modal } from "./Modal";
import { PartyForm } from "./PartyForm";
import {
    computeTotals,
    emptyLineItem,
    emptyParty,
    formatCurrency,
} from "../utils";

const pctFmt = (f) => (f === null || f === undefined ? "—" : `${(f * 100).toFixed(1)} %`);
const SIM_PCTS = [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100];
const TARGETS = [30, 35, 40, 45, 50, 55, 60];

/**
 * QuoteAttachments — upload/list/delete client-chosen annex files (PDF/images)
 * that get appended to the quote PDF. Persisted server-side in GridFS.
 */
const QuoteAttachments = ({ http, quoteId, attachments, onChange }) => {
    const [busy, setBusy] = useState(false);
    const [err, setErr] = useState("");

    const upload = async (file) => {
        if (!file) return;
        setBusy(true); setErr("");
        try {
            const fd = new FormData();
            fd.append("file", file);
            const { data } = await http.post(`/admin/quotes/${quoteId}/attachments`, fd, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            onChange(data.attachments || []);
        } catch (e) {
            setErr(e?.response?.data?.detail || "Échec du téléversement");
        } finally { setBusy(false); }
    };

    const remove = async (attId) => {
        setBusy(true); setErr("");
        try {
            const { data } = await http.delete(`/admin/quotes/${quoteId}/attachments/${attId}`);
            onChange(data.attachments || []);
        } catch (e) {
            setErr(e?.response?.data?.detail || "Échec de la suppression");
        } finally { setBusy(false); }
    };

    return (
        <div className="mt-4 border border-[#dde5f0] bg-white p-4" data-testid="quote-attachments">
            <div className="tech-stamp text-[#0c182b] font-bold mb-1">Fichiers en annexe (PDF / images)</div>
            <p className="text-xs text-[#4b5d7a] mb-3">
                Ajoutez vos propres fichiers (fiche technique, photo, plan) — ils seront
                joints à la fin du PDF de la soumission. Vous contrôlez exactement ce qui est envoyé.
            </p>
            {err && <div className="mb-2 text-xs text-red-600">{err}</div>}
            <ul className="space-y-1 mb-3">
                {(attachments || []).map((a) => (
                    <li key={a.id} data-testid={`quote-attachment-${a.id}`}
                        className="flex items-center justify-between gap-3 text-sm border border-[#eef2f8] px-3 py-2">
                        <span className="truncate">{a.filename}</span>
                        <button type="button" onClick={() => remove(a.id)} disabled={busy}
                            data-testid={`quote-attachment-del-${a.id}`}
                            className="p-1.5 border border-[#dde5f0] hover:bg-red-50 text-red-600 disabled:opacity-40">
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    </li>
                ))}
                {(!attachments || attachments.length === 0) && (
                    <li className="text-xs text-[#9aa8bd] italic">Aucun fichier joint.</li>
                )}
            </ul>
            <label className="btn-secondary !py-1.5 !px-3 !text-xs inline-flex items-center gap-1 cursor-pointer">
                <Plus className="w-3 h-3" /> {busy ? "Téléversement…" : "Ajouter un fichier"}
                <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.heif"
                    data-testid="quote-attachment-input"
                    onChange={(e) => { upload(e.target.files?.[0]); e.target.value = ""; }} />
            </label>
        </div>
    );
};

/**
 * DoorBuilderModal — CONFIDENTIAL door pricing engine embedded in the quote/
 * invoice builder. Replicates the exact LDP Excel formulas (same math as the
 * standalone Coûts Master calculator) and, on confirm, appends a real line item
 * carrying the computed sell price + hidden cost_price/cost_category so the
 * profit panel below shows live cost & margin per line and total.
 */
const DoorBuilderModal = ({ http, onAdd, onClose }) => {
    const [models, setModels] = useState([]);
    const [rate, setRate] = useState(50);
    const [hwMarkup, setHwMarkup] = useState(0.35);
    const [modelKey, setModelKey] = useState("");
    const [hw, setHw] = useState([]);
    const [profitPct, setProfitPct] = useState(0.6);
    const [laborHours, setLaborHours] = useState(3);
    const [materialCost, setMaterialCost] = useState(0);
    const [qty, setQty] = useState(1);
    const [addQ, setAddQ] = useState("");
    const [addResults, setAddResults] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const [{ data: m }, { data: params }] = await Promise.all([
                    http.get("/admin/master/door-models"),
                    http.get("/admin/master/params"),
                ]);
                setModels(m);
                const r = params.find((p) => /TAUX HORAIRE/i.test(p.label));
                const q = params.find((p) => /QUINCAILLERIE/i.test(p.label));
                if (r) setRate(r.value);
                if (q) setHwMarkup(q.value);
            } finally { setLoading(false); }
        })();
    }, [http]);

    const selectModel = (key) => {
        setModelKey(key);
        const m = models.find((x) => x.model_key === key);
        if (!m) return;
        setHw((m.hardware || []).map((h) => ({ ...h })));
        setProfitPct(m.profit_pct ?? 0.6);
        setLaborHours(m.labor_hours || 3);
        setMaterialCost(m.material_cost || 0);
    };

    useEffect(() => {
        if (!addQ) { setAddResults([]); return; }
        const t = setTimeout(async () => {
            const { data } = await http.get(`/admin/master/hardware?q=${encodeURIComponent(addQ)}`);
            setAddResults(data.slice(0, 8));
        }, 250);
        return () => clearTimeout(t);
    }, [addQ, http]);

    const model = models.find((x) => x.model_key === modelKey);
    const laborCost = Math.round(laborHours * rate * 100) / 100;
    const mlCost = Math.round((materialCost + laborCost) * 100) / 100;
    const hwCost = Math.round(hw.reduce((s, h) => s + (Number(h.cost) || 0), 0) * 100) / 100;
    const mlProfit = Math.round(mlCost * profitPct * 100) / 100;
    const hwProfit = Math.round(hwCost * hwMarkup * 100) / 100;
    const costTotal = Math.round((mlCost + hwCost) * 100) / 100;
    const sellTotal = Math.round((mlCost + mlProfit + hwCost + hwProfit) * 100) / 100;
    const margin = Math.round((sellTotal - costTotal) * 100) / 100;
    const marginPct = costTotal ? Math.round((margin / costTotal) * 1000) / 10 : 0;

    const confirm = () => {
        if (!model) return;
        const q = Number(qty) || 1;
        onAdd({
            ...emptyLineItem(),
            description: `Porte — ${model.label} (quincaillerie incluse)`,
            quantity: q,
            unit_price: sellTotal,
            cost_price: costTotal,
            cost_category: "Portes",
            product_id: null,
        });
        onClose();
    };

    return (
        <Modal open onClose={onClose} wide testId="door-builder-modal"
            title="Ajouter une porte — calculateur LDP"
            footer={<div className="flex items-center justify-between gap-3 w-full">
                <span className="text-xs text-[#4b5d7a]">
                    {model ? <>Coûtant <b>{formatCurrency(costTotal)}</b> · Marge <b className="text-[#0f6b3a]">{formatCurrency(margin)} ({marginPct} %)</b></> : "Choisis un modèle"}
                </span>
                <button type="button" data-testid="door-builder-add" onClick={confirm} disabled={!model}
                    className="tech-stamp px-4 py-2 bg-[#0c182b] text-white flex items-center gap-1 disabled:opacity-40">
                    <Plus className="w-4 h-4" /> Ajouter à la soumission
                </button>
            </div>}>
            {loading ? (
                <div className="py-10 text-center text-[#4b5d7a]"><Loader2 className="w-5 h-5 animate-spin inline" /></div>
            ) : (
                <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-4">
                        <div className="border border-[#dde5f0] bg-white p-4 space-y-3">
                            <Field label="Modèle de porte (base LDP)">
                                <select data-testid="door-builder-model" value={modelKey} onChange={(e) => selectModel(e.target.value)} className={inputClass}>
                                    <option value="">— Choisir un modèle —</option>
                                    {models.map((m) => <option key={m.model_key} value={m.model_key}>{m.label}</option>)}
                                </select>
                            </Field>
                            {model && (
                                <div className="grid grid-cols-2 gap-3">
                                    <Field label="Matériel ($)"><input type="number" step="0.01" data-testid="door-builder-material" className={inputClass} value={materialCost} onChange={(e) => setMaterialCost(Number(e.target.value))} /></Field>
                                    <Field label="Heures M.O."><input type="number" step="0.5" data-testid="door-builder-hours" className={inputClass} value={laborHours} onChange={(e) => setLaborHours(Number(e.target.value))} /></Field>
                                    <Field label="Profit matériel (×)"><input type="number" step="0.05" data-testid="door-builder-profit" className={inputClass} value={profitPct} onChange={(e) => setProfitPct(Number(e.target.value))} /></Field>
                                    <Field label="Quantité"><input type="number" step="1" min="1" data-testid="door-builder-qty" className={inputClass} value={qty} onChange={(e) => setQty(e.target.value)} /></Field>
                                </div>
                            )}
                        </div>

                        {model && (
                            <div className="border border-[#dde5f0] bg-white p-4 space-y-2">
                                <div className="tech-stamp text-[#4b5d7a] flex items-center justify-between">
                                    <span>Quincaillerie ({hw.length})</span>
                                    <span>{formatCurrency(hwCost)}</span>
                                </div>
                                {hw.map((h, i) => (
                                    <div key={i} className="flex items-center gap-2 text-sm border-b border-[#f0f3f8] pb-1.5">
                                        <span className="flex-1">{h.description}<span className="text-[#93a3bd] text-xs ml-1">{h.code}</span></span>
                                        <span className="text-[#4b5d7a]">{formatCurrency(h.cost)}</span>
                                        <button type="button" onClick={() => setHw(hw.filter((_, j) => j !== i))} className="text-red-500 hover:text-red-700"><X className="w-3.5 h-3.5" /></button>
                                    </div>
                                ))}
                                <div className="relative pt-2">
                                    <Search className="w-4 h-4 absolute left-3 top-1/2 text-[#93a3bd]" />
                                    <input data-testid="door-builder-add-hw" value={addQ} onChange={(e) => setAddQ(e.target.value)} placeholder="Ajouter une quincaillerie (code ou nom)…" className={`${inputClass} !pl-9`} />
                                    {addResults.length > 0 && (
                                        <div className="absolute z-10 left-0 right-0 bg-white border border-[#dde5f0] shadow-lg max-h-56 overflow-auto">
                                            {addResults.map((r) => (
                                                <button type="button" key={r.id} onClick={() => { setHw([...hw, { code: r.product_code, description: r.description, cost: r.unit_cost }]); setAddQ(""); setAddResults([]); }}
                                                    className="block w-full text-left px-3 py-2 text-sm hover:bg-[#eaf1fb] border-b border-[#f0f3f8]">
                                                    {r.description} <span className="text-[#2f4f7f] font-mono text-xs">{r.product_code}</span> — {formatCurrency(r.unit_cost)} <span className="text-[#93a3bd]">({r.supplier})</span>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="border-2 border-[#0c182b] bg-[#0c182b] text-white p-6 h-fit md:sticky md:top-4">
                        <div className="tech-stamp text-[#8fb4ff] mb-4">Calcul du prix (comme LDP)</div>
                        {!model ? (
                            <p className="text-[#8fb4ff] text-sm">Choisis un modèle pour calculer le prix, le coûtant et la marge.</p>
                        ) : (
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between items-baseline"><span className="text-[#c3d2ea]">Matériel + M.O.<span className="text-[#6b7f9e] text-xs ml-1">({formatCurrency(materialCost)} + {laborHours}h × {formatCurrency(rate)})</span></span><span>{formatCurrency(mlCost)}</span></div>
                                <div className="flex justify-between items-baseline"><span className="text-[#c3d2ea]">Profit matériel (×{profitPct})</span><span>{formatCurrency(mlProfit)}</span></div>
                                <div className="flex justify-between items-baseline"><span className="text-[#c3d2ea]">Quincaillerie (coût)</span><span>{formatCurrency(hwCost)}</span></div>
                                <div className="flex justify-between items-baseline"><span className="text-[#c3d2ea]">Profit quincaillerie (×{hwMarkup})</span><span>{formatCurrency(hwProfit)}</span></div>
                                <div className="border-t border-[#2a3d5c] my-2" />
                                <div className="flex justify-between items-center"><span className="text-[#8fb4ff]">COÛTANT (unité)</span><span data-testid="door-builder-cost" className="font-display font-bold text-lg">{formatCurrency(costTotal)}</span></div>
                                <div className="flex justify-between items-center text-[#4fd1c5]"><span>MARGE</span><span data-testid="door-builder-margin">{formatCurrency(margin)} · {marginPct}%</span></div>
                                <div className="border-t border-[#2a3d5c] my-2" />
                                <div className="flex justify-between items-center"><span className="text-[#ffd27f] font-semibold">PRIX VENDANT (unité)</span><span data-testid="door-builder-sell" className="font-display font-bold text-2xl text-[#ffd27f]">{formatCurrency(sellTotal)}</span></div>
                                {Number(qty) > 1 && <div className="flex justify-between items-center text-xs text-[#c3d2ea] pt-1">× {qty} portes = <span className="font-bold">{formatCurrency(sellTotal * Number(qty))}</span></div>}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </Modal>
    );
};


/**
 * DocumentForm — shared UI for Invoice and Purchase Order (same shape).
 * Props:
 * - kind: "invoice" | "purchase-order"
 * - parties: list of parties of the right kind (customers for invoices, suppliers for POs)
 * - products: list of products (for quick-pick)
 * - value: the form state (customer_snapshot / supplier_snapshot, items, date, etc.)
 * - onChange: (next) => void
 * - statuses: list of valid status labels
 */
export const DocumentForm = ({
    kind,
    parties,
    products,
    value,
    onChange,
    statuses,
}) => {
    const { http } = useAuth();
    const isInvoice = kind === "invoice";
    const isQuote = kind === "quote";
    const usesCustomer = isInvoice || isQuote;
    const partyKey = usesCustomer ? "customer_snapshot" : "supplier_snapshot";
    const partyIdKey = usesCustomer ? "customer_id" : "supplier_id";
    const partyLabel = usesCustomer ? "Client" : "Fournisseur";
    const dateSecondaryLabel = isInvoice
        ? "Échéance"
        : (isQuote ? "Valide jusqu'au" : "Livraison attendue");
    const dateSecondaryKey = isInvoice
        ? "due_date"
        : (isQuote ? "valid_until" : "expected_delivery");

    const [partyMode, setPartyMode] = useState(value[partyIdKey] ? "select" : "custom");
    const [showPartyForm, setShowPartyForm] = useState(!value[partyIdKey]);
    const [doorOpen, setDoorOpen] = useState(false);
    const showDoorBuilder = isQuote || isInvoice;

    const addDoorLine = (line) => {
        const base = (value.items || []).filter((it) => it.description || Number(it.unit_price));
        onChange({ ...value, items: [...base, line] });
    };

    const totals = computeTotals(value.items || [], value.taxable);

    const set = (k, v) => onChange({ ...value, [k]: v });

    // Party selection handlers
    const selectParty = (id) => {
        const p = parties.find((x) => x.id === id);
        if (!p) {
            onChange({ ...value, [partyIdKey]: null, [partyKey]: emptyParty(usesCustomer ? "customer" : "supplier") });
            return;
        }
        onChange({ ...value, [partyIdKey]: p.id, [partyKey]: { ...p } });
    };

    // Line items helpers
    const updateItem = (idx, patch) => {
        const items = value.items.map((it, i) => (i === idx ? { ...it, ...patch } : it));
        onChange({ ...value, items });
    };
    const addItem = () => onChange({ ...value, items: [...value.items, emptyLineItem()] });
    const removeItem = (idx) => {
        const items = value.items.filter((_, i) => i !== idx);
        onChange({ ...value, items: items.length ? items : [emptyLineItem()] });
    };
    const pickProduct = (idx, productId) => {
        if (!productId) return;
        const p = products.find((x) => x.id === productId);
        if (!p) return;
        updateItem(idx, {
            description: p.name + (p.description ? ` — ${p.description}` : ""),
            unit_price: Number(p.unit_price || 0),
            product_id: p.id,
            // Cost price is used for the admin-only profit margin panel — the
            // backend LineItem model now persists cost_price/cost_category as
            // CONFIDENTIAL fields (never rendered on the PDF or client quote).
            cost_price: p.cost_price != null ? Number(p.cost_price) : null,
            cost_category: p.category || null,
            _cost_price: p.cost_price != null ? Number(p.cost_price) : null,
        });
    };

    return (
        <div className="space-y-6">
            {/* === Party === */}
            <div className="border border-[#dde5f0] p-5 bg-[#f9fbfd]">
                <div className="tech-stamp mb-3">{partyLabel}</div>
                <div className="flex gap-2 mb-4">
                    <button
                        type="button"
                        onClick={() => { setPartyMode("select"); setShowPartyForm(false); }}
                        className={`tech-stamp px-3 py-1.5 border ${partyMode === "select" ? "bg-[#0c182b] text-white border-[#0c182b]" : "border-[#dde5f0] text-[#4b5d7a]"}`}
                    >
                        Depuis la base
                    </button>
                    <button
                        type="button"
                        onClick={() => { setPartyMode("custom"); setShowPartyForm(true); set(partyIdKey, null); }}
                        className={`tech-stamp px-3 py-1.5 border ${partyMode === "custom" ? "bg-[#0c182b] text-white border-[#0c182b]" : "border-[#dde5f0] text-[#4b5d7a]"}`}
                    >
                        Nouveau (ponctuel)
                    </button>
                </div>

                {partyMode === "select" && (
                    <Field label={`Choisir un ${partyLabel.toLowerCase()}`}>
                        <select
                            value={value[partyIdKey] || ""}
                            onChange={(e) => selectParty(e.target.value)}
                            className={inputClass}
                            data-testid={`doc-${kind}-party-select`}
                        >
                            <option value="">— Sélectionner —</option>
                            {parties.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.name}{p.city ? ` · ${p.city}` : ""}
                                </option>
                            ))}
                        </select>
                    </Field>
                )}

                {(partyMode === "custom" || showPartyForm) && (
                    <div className="mt-2">
                        <PartyForm
                            value={value[partyKey]}
                            onChange={(next) => set(partyKey, next)}
                            hideKind
                            compact
                        />
                    </div>
                )}

                {partyMode === "select" && value[partyIdKey] && (
                    <button
                        type="button"
                        onClick={() => setShowPartyForm((s) => !s)}
                        className="mt-3 tech-stamp text-[#2f4f7f] underline"
                    >
                        {showPartyForm ? "Masquer les coordonnées" : "Voir/modifier les coordonnées (snapshot)"}
                    </button>
                )}
            </div>

            {/* === Dates + status === */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Field label="Date du document" required>
                    <input type="date" value={value.date || ""} onChange={(e) => set("date", e.target.value)} className={inputClass} required />
                </Field>
                <Field label={dateSecondaryLabel}>
                    <input type="date" value={value[dateSecondaryKey] || ""} onChange={(e) => set(dateSecondaryKey, e.target.value)} className={inputClass} />
                </Field>
                <Field label="Statut">
                    <select value={value.status} onChange={(e) => set("status", e.target.value)} className={inputClass}>
                        {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                </Field>
            </div>

            {/* === Items === */}
            <div>
                <div className="flex items-center justify-between mb-3">
                    <div className="tech-stamp">Lignes</div>
                    <div className="flex items-center gap-2">
                        {showDoorBuilder && (
                            <button type="button" onClick={() => setDoorOpen(true)} data-testid={`doc-${kind}-add-door`}
                                className="btn-primary !py-1.5 !px-3 !text-xs flex items-center gap-1">
                                <DoorClosed className="w-3 h-3" />
                                Ajouter une porte (LDP)
                            </button>
                        )}
                        <button type="button" onClick={addItem} data-testid={`doc-${kind}-add-item`} className="btn-secondary !py-1.5 !px-3 !text-xs">
                            <Plus className="w-3 h-3" />
                            Ligne
                        </button>
                    </div>
                </div>
                <div className="border border-[#dde5f0] bg-white">
                    <div className="hidden md:grid grid-cols-12 gap-2 px-3 py-2 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp text-[10px]">
                        <div className="col-span-5">Description</div>
                        <div className="col-span-2">Produit</div>
                        <div className="col-span-1 text-right">Qté</div>
                        <div className="col-span-2 text-right">Prix unitaire</div>
                        <div className="col-span-1 text-right">Total</div>
                        <div className="col-span-1" />
                    </div>
                    {value.items.map((it, idx) => {
                        const lineTotal = Number(it.quantity || 0) * Number(it.unit_price || 0);
                        return (
                            <div key={it._key || `row-${idx}`} className="grid grid-cols-1 md:grid-cols-12 gap-2 px-3 py-2 items-center border-b border-[#dde5f0] last:border-b-0">
                                <div className="md:col-span-5">
                                    <input
                                        type="text"
                                        placeholder="Description"
                                        value={it.description}
                                        onChange={(e) => updateItem(idx, { description: e.target.value })}
                                        className={inputClass + " !text-xs"}
                                        data-testid={`doc-${kind}-item-desc-${idx}`}
                                    />
                                </div>
                                <div className="md:col-span-2">
                                    <select
                                        value={it.product_id || ""}
                                        onChange={(e) => pickProduct(idx, e.target.value)}
                                        className={inputClass + " !text-xs"}
                                    >
                                        <option value="">— Produit —</option>
                                        {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                                    </select>
                                </div>
                                <div className="md:col-span-1">
                                    <input type="number" step="0.01" min="0" value={it.quantity} onChange={(e) => updateItem(idx, { quantity: e.target.value })} className={inputClass + " !text-xs text-right"} />
                                </div>
                                <div className="md:col-span-2">
                                    <input type="number" step="0.01" min="0" value={it.unit_price} onChange={(e) => updateItem(idx, { unit_price: e.target.value })} className={inputClass + " !text-xs text-right"} />
                                </div>
                                <div className="md:col-span-1 text-right text-sm font-display font-bold">
                                    {formatCurrency(lineTotal)}
                                </div>
                                <div className="md:col-span-1 flex justify-end">
                                    <button type="button" onClick={() => removeItem(idx)} className="p-1.5 border border-[#dde5f0] hover:bg-red-50 text-red-600">
                                        <Trash2 className="w-3 h-3" />
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* === Taxes toggle + Totals === */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
                <div>
                    <label className="inline-flex items-center gap-2 text-sm">
                        <input
                            type="checkbox"
                            checked={!!value.taxable}
                            onChange={(e) => set("taxable", e.target.checked)}
                            data-testid={`doc-${kind}-taxable`}
                        />
                        Appliquer TPS (5 %) + TVQ (9,975 %)
                    </label>
                    {isQuote && (
                        <label className="flex items-center gap-2 text-sm mt-3">
                            <input
                                type="checkbox"
                                checked={!!value.include_sales_conditions}
                                onChange={(e) => set("include_sales_conditions", e.target.checked)}
                                data-testid="doc-quote-sales-conditions"
                            />
                            Joindre les conditions de vente (annexe contrat)
                        </label>
                    )}
                    <Field label="Notes" className="mt-4">
                        <textarea rows={3} value={value.notes || ""} onChange={(e) => set("notes", e.target.value)} className={inputClass} />
                    </Field>
                </div>

                <div className="border border-[#dde5f0] bg-[#f3f6fb] p-5">
                    <div className="flex justify-between text-sm py-1"><span>Sous-total</span><span className="font-display font-bold">{formatCurrency(totals.subtotal)}</span></div>
                    <div className="flex justify-between text-sm py-1"><span>TPS (5 %)</span><span className="font-display font-bold">{formatCurrency(totals.tps)}</span></div>
                    <div className="flex justify-between text-sm py-1"><span>TVQ (9,975 %)</span><span className="font-display font-bold">{formatCurrency(totals.tvq)}</span></div>
                    <div className="flex justify-between py-2 mt-2 border-t-2 border-[#0c182b] text-lg"><span className="font-display font-bold uppercase">Total</span><span className="font-display font-bold">{formatCurrency(totals.total)}</span></div>
                </div>
            </div>

            {/* === Client-chosen annex attachments (quotes only, after save) === */}
            {isQuote && value.id && (
                <QuoteAttachments
                    http={http}
                    quoteId={value.id}
                    attachments={value.attachments || []}
                    onChange={(atts) => onChange({ ...value, attachments: atts })}
                />
            )}

            {/* === CONFIDENTIAL profit-margin panel (never shown to client) === */}
            {(kind === "quote" || kind === "invoice") && (
                <ProfitMarginPanel
                    items={value.items}
                    products={products}
                    onBumpPrices={(factor) => onChange({
                        ...value,
                        items: value.items.map((it) => ({
                            ...it,
                            unit_price: Math.round(Number(it.unit_price || 0) * factor * 100) / 100,
                        })),
                    })}
                />
            )}

            {doorOpen && (
                <DoorBuilderModal http={http} onAdd={addDoorLine} onClose={() => setDoorOpen(false)} />
            )}
        </div>
    );
};


/**
 * ProfitMarginPanel — CONFIDENTIAL, ADMIN-ONLY. Single integrated pricing &
 * profitability tool for quotes (merged from the old standalone calculator).
 *
 * Works directly on the REAL quote line items. Shows per-line cost/sell/margin,
 * per-category profit, project totals (markup + margin), a markup simulator,
 * a target-margin price solver, a margin-min/target alert, and a one-click
 * "bump all prices by X %" adjustment. Never visible on the PDF or the
 * emailed quote — cost_price is looked up in-browser from the products cache.
 */
const ProfitMarginPanel = ({ items, products, onBumpPrices }) => {
    const { http } = useAuth();
    const [customPct, setCustomPct] = useState("");
    const [settings, setSettings] = useState(null);
    const [savingCfg, setSavingCfg] = useState(false);
    const [customSim, setCustomSim] = useState("");
    const [customTarget, setCustomTarget] = useState("");

    const loadSettings = useCallback(async () => {
        try { const { data } = await http.get("/admin/pricing/settings"); setSettings(data); }
        catch (_) { /* silent */ }
    }, [http]);
    useEffect(() => { loadSettings(); }, [loadSettings]);

    const marginMin = settings?.margin_min ?? null;
    const marginTarget = settings?.margin_target ?? null;

    const productMap = useMemo(
        () => Object.fromEntries((products || []).map((p) => [p.id, p])), [products]);

    const { rows, byCat, totalCost, totalSell } = useMemo(() => {
        const rws = (items || []).map((it) => {
            const p = productMap[it.product_id];
            let cost = p && p.cost_price != null ? Number(p.cost_price) : null;
            if (cost == null && it.cost_price != null) cost = Number(it.cost_price);
            if (cost == null && it._cost_price != null) cost = Number(it._cost_price);
            const category = (p && p.category) || it.cost_category || "Sans catégorie";
            const qty = Number(it.quantity || 0);
            const sell = Number(it.unit_price || 0);
            return {
                desc: it.description || "—",
                category,
                qty, cost, sell,
                hasCost: cost != null && cost > 0,
                lineCost: cost != null ? cost * qty : 0,
                lineSell: sell * qty,
            };
        });
        const bc = {};
        rws.forEach((r) => {
            const c = (bc[r.category] = bc[r.category] || { cost: 0, sell: 0 });
            c.cost += r.lineCost; c.sell += r.lineSell;
        });
        Object.values(bc).forEach((c) => {
            c.profit = c.sell - c.cost;
            c.margin = c.sell > 0 ? c.profit / c.sell : null;
        });
        const tc = rws.filter((r) => r.hasCost).reduce((s, r) => s + r.lineCost, 0);
        const ts = rws.reduce((s, r) => s + r.lineSell, 0);
        return { rows: rws, byCat: bc, totalCost: tc, totalSell: ts };
    }, [items, productMap]);

    const withCost = rows.filter((r) => r.hasCost);

    const saveMargins = async () => {
        setSavingCfg(true);
        try {
            const s = settings || {};
            await http.put("/admin/pricing/settings", {
                labor_rates: s.labor_rates || {},
                km_rate: s.km_rate ?? 0.85,
                margin_min: s.margin_min ?? null,
                margin_target: s.margin_target ?? null,
            });
            await loadSettings();
        } finally { setSavingCfg(false); }
    };

    if (withCost.length === 0) {
        return (
            <div className="mt-4 border border-dashed border-[#c5d4e7] bg-[#f9fbfd] p-3 text-xs text-[#4b5d7a] tech-stamp"
                data-testid="quote-profit-panel">
                🔒 Calculateur de prix & marge : aucune ligne n&apos;a de prix d&apos;achat lié.
                Choisis un produit du catalogue (colonne « Produit ») ou ajoute un prix
                d&apos;achat dans l&apos;onglet « Produits » pour voir automatiquement ta
                marge, le simulateur et le solveur de marge cible ici.
            </div>
        );
    }

    const margin = totalSell - totalCost;
    const marginRatio = totalSell > 0 ? margin / totalSell : null;
    const markupRatio = totalCost > 0 ? margin / totalCost : null;
    const marginPct = totalCost > 0 ? (margin / totalCost) * 100 : 0;
    const belowMin = marginMin != null && marginRatio != null && marginRatio < marginMin;
    const underTarget = marginTarget != null && marginRatio != null
        && !belowMin && marginRatio < marginTarget;
    const tone = marginPct < 15 ? "text-[#a31a1a]" : marginPct < 30 ? "text-[#925800]" : "text-[#0f6b3a]";

    const bump = (p) => {
        const factor = 1 + Number(p) / 100;
        if (!Number.isFinite(factor) || factor <= 0) return;
        onBumpPrices(factor);
    };

    return (
        <div className="mt-4 border border-[#1f3a5f] bg-[#0c182b]/5" data-testid="quote-profit-panel">
            <div className="flex items-center gap-2 px-4 py-2.5 bg-[#0c182b] text-white">
                <Calculator className="w-4 h-4 text-[#4fd1c5]" />
                <span className="font-bold tracking-wide text-sm">Calculateur de prix &amp; rentabilité</span>
                <span className="ml-auto text-[10px] uppercase text-[#ffb4b4]">Confidentiel — ne figure pas sur la soumission</span>
            </div>

            <div className="p-4 space-y-5">
                {/* Margin targets */}
                <div className="border border-[#dde5f0] bg-[#f7f9fc] p-3">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] uppercase font-bold tracking-wider text-[#0c182b]">Objectifs de marge</span>
                        <button type="button" onClick={saveMargins} disabled={savingCfg} data-testid="quote-pricing-save-settings"
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-[#1f3a5f] text-white disabled:opacity-50">
                            <Save className="w-3 h-3" /> {savingCfg ? "…" : "Enregistrer"}
                        </button>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs max-w-md">
                        <div>
                            <label className="block text-[#4b5d7a] mb-0.5">Marge MINI (%)</label>
                            <input type="number" step="1" data-testid="quote-marginmin"
                                value={settings?.margin_min != null ? settings.margin_min * 100 : ""} placeholder="—"
                                onChange={(e) => setSettings((s) => ({ ...(s || {}), margin_min: e.target.value === "" ? null : Number(e.target.value) / 100 }))}
                                className={`w-full px-2 py-1 border border-[#dde5f0] ${marginMin == null ? "bg-[#fff3cf]" : ""}`} />
                        </div>
                        <div>
                            <label className="block text-[#4b5d7a] mb-0.5">Marge CIBLE (%)</label>
                            <input type="number" step="1" data-testid="quote-margintarget"
                                value={settings?.margin_target != null ? settings.margin_target * 100 : ""} placeholder="—"
                                onChange={(e) => setSettings((s) => ({ ...(s || {}), margin_target: e.target.value === "" ? null : Number(e.target.value) / 100 }))}
                                className={`w-full px-2 py-1 border border-[#dde5f0] ${marginTarget == null ? "bg-[#fff3cf]" : ""}`} />
                        </div>
                    </div>
                </div>

                {/* Per-line table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                        <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                            <tr>
                                <th className="text-left py-1">Ligne</th>
                                <th className="text-left py-1">Catégorie</th>
                                <th className="text-right py-1">Qté</th>
                                <th className="text-right py-1">Coût unit.</th>
                                <th className="text-right py-1">Vente unit.</th>
                                <th className="text-right py-1">Marge</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((r, i) => (
                                <tr key={i} className="border-b border-[#f3f6fb]">
                                    <td className="py-1 truncate max-w-xs">{r.desc}</td>
                                    <td className="py-1 text-[#4b5d7a]">{r.category}</td>
                                    <td className="py-1 text-right font-mono">{r.qty}</td>
                                    <td className="py-1 text-right font-mono">
                                        {r.hasCost ? formatCurrency(r.cost) : <span className="text-[#a31a1a]">—</span>}
                                    </td>
                                    <td className="py-1 text-right font-mono">{formatCurrency(r.sell)}</td>
                                    <td className={`py-1 text-right font-mono font-bold ${r.hasCost ? (r.sell - r.cost >= 0 ? "text-[#0f6b3a]" : "text-[#a31a1a]") : "text-[#4b5d7a]"}`}>
                                        {r.hasCost ? formatCurrency((r.sell - r.cost) * r.qty) : "—"}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Summary + per-category */}
                <div className="grid md:grid-cols-2 gap-4">
                    <div className="border border-[#1f3a5f] bg-[#0c182b] text-white p-3" data-testid="quote-pricing-summary">
                        <div className="text-[11px] uppercase tracking-wider text-[#9fb3d1] mb-2">Rentabilité du projet</div>
                        <div className="grid grid-cols-2 gap-y-1 text-sm">
                            <span className="text-[#9fb3d1]">Coût total</span><span className="text-right">{formatCurrency(totalCost)}</span>
                            <span className="text-[#9fb3d1]">Prix de vente</span><span className="text-right font-bold">{formatCurrency(totalSell)}</span>
                            <span className="text-[#9fb3d1]">Profit brut</span><span className={`text-right font-bold ${tone === "text-[#0f6b3a]" ? "text-[#4fd1c5]" : ""}`}>{formatCurrency(margin)}</span>
                            <span className="text-[#9fb3d1]">Markup</span><span className="text-right">{pctFmt(markupRatio)}</span>
                            <span className="text-[#9fb3d1]">Marge brute</span><span className="text-right font-bold">{pctFmt(marginRatio)}</span>
                        </div>
                        {belowMin && (
                            <div className="mt-2 flex items-center gap-2 bg-[#a31a1a] text-white text-xs px-2 py-1.5" data-testid="quote-pricing-alert">
                                <AlertTriangle className="w-4 h-4" /> MARGE SOUS LE MINIMUM ({pctFmt(marginMin)})
                            </div>
                        )}
                        {underTarget && (
                            <div className="mt-2 text-[11px] text-[#ffd27f]" data-testid="quote-pricing-undertarget">Sous la marge cible ({pctFmt(marginTarget)})</div>
                        )}
                    </div>

                    <div className="border border-[#dde5f0] bg-white p-3" data-testid="quote-pricing-bycat">
                        <div className="text-[11px] uppercase tracking-wider text-[#4b5d7a] mb-2">Profit par catégorie</div>
                        <table className="w-full text-xs">
                            <tbody>
                                {Object.entries(byCat).filter(([, c]) => c.sell || c.cost).map(([k, c]) => (
                                    <tr key={k} className="border-b border-[#f3f6fb]">
                                        <td className="py-1 text-[#0c182b]">{k}</td>
                                        <td className="py-1 text-right text-[#0b6b2f]">{formatCurrency(c.profit)}</td>
                                        <td className="py-1 text-right text-[#4b5d7a]">{pctFmt(c.margin)}</td>
                                    </tr>
                                ))}
                                {!Object.keys(byCat).length && <tr><td className="py-1 text-[#8a97a8] italic">Aucune ligne</td></tr>}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Simulator + target solver */}
                <div className="grid md:grid-cols-2 gap-4">
                    <div className="border border-[#dde5f0] bg-white p-3" data-testid="quote-pricing-simulator">
                        <div className="text-[11px] uppercase tracking-wider text-[#4b5d7a] mb-2">Simulateur — markup sur le coût ({formatCurrency(totalCost)})</div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs">
                                <thead className="text-[#8a97a8]"><tr><th className="text-left py-1">Markup</th><th className="text-right py-1">Prix vente</th><th className="text-right py-1">Profit</th><th className="text-right py-1">Marge</th></tr></thead>
                                <tbody>
                                    {SIM_PCTS.concat(customSim !== "" ? [Number(customSim)] : []).map((p, i) => {
                                        const sell = totalCost * (1 + p / 100);
                                        const profit = sell - totalCost;
                                        const m = sell > 0 ? profit / sell : null;
                                        return (
                                            <tr key={`${p}-${i}`} className="border-b border-[#f3f6fb]">
                                                <td className="py-1">+{p} %</td>
                                                <td className="py-1 text-right font-medium">{formatCurrency(sell)}</td>
                                                <td className="py-1 text-right text-[#0b6b2f]">{formatCurrency(profit)}</td>
                                                <td className="py-1 text-right">{pctFmt(m)}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                        <div className="mt-2 flex items-center gap-2 text-xs">
                            <span className="text-[#4b5d7a]">Markup personnalisé (%)</span>
                            <input type="number" value={customSim} onChange={(e) => setCustomSim(e.target.value)} className="w-20 px-2 py-1 border border-[#dde5f0] text-right" data-testid="quote-pricing-customsim" />
                        </div>
                    </div>

                    <div className="border border-[#dde5f0] bg-white p-3" data-testid="quote-pricing-target">
                        <div className="text-[11px] uppercase tracking-wider text-[#4b5d7a] mb-2">Prix requis pour une marge cible</div>
                        <div className="text-[11px] text-[#8a97a8] mb-2">Prix = coût / (1 − marge). Coût = {formatCurrency(totalCost)}</div>
                        <table className="w-full text-xs">
                            <thead className="text-[#8a97a8]"><tr><th className="text-left py-1">Marge visée</th><th className="text-right py-1">Prix requis</th><th className="text-right py-1">Profit</th><th className="text-right py-1">Markup</th></tr></thead>
                            <tbody>
                                {TARGETS.concat(customTarget !== "" ? [Number(customTarget)] : []).map((m, i) => {
                                    const f = m / 100;
                                    const sell = f < 1 ? totalCost / (1 - f) : null;
                                    const profit = sell != null ? sell - totalCost : null;
                                    const mk = sell != null && totalCost > 0 ? profit / totalCost : null;
                                    return (
                                        <tr key={`${m}-${i}`} className="border-b border-[#f3f6fb]">
                                            <td className="py-1">{m} %</td>
                                            <td className="py-1 text-right font-bold">{sell != null ? formatCurrency(sell) : "—"}</td>
                                            <td className="py-1 text-right text-[#0b6b2f]">{profit != null ? formatCurrency(profit) : "—"}</td>
                                            <td className="py-1 text-right">{pctFmt(mk)}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                        <div className="mt-2 flex items-center gap-2 text-xs">
                            <span className="text-[#4b5d7a]">Marge cible personnalisée (%)</span>
                            <input type="number" value={customTarget} onChange={(e) => setCustomTarget(e.target.value)} className="w-20 px-2 py-1 border border-[#dde5f0] text-right" data-testid="quote-pricing-customtarget" />
                        </div>
                    </div>
                </div>

                {/* One-click bump */}
                <div className="border-t border-[#dde5f0] pt-3">
                    <div className="text-[10px] uppercase text-[#4b5d7a] font-bold mb-1">
                        Ajuster les prix de vente de TOUTES les lignes en un clic
                    </div>
                    <div className="flex flex-wrap gap-2 items-center">
                        {[5, 10, 15, 20].map((p) => (
                            <button key={p} type="button" onClick={() => bump(p)} data-testid={`quote-bump-${p}`}
                                className="px-3 py-1.5 border border-[#0c182b] bg-white hover:bg-[#0c182b] hover:text-white tech-stamp text-xs">
                                +{p} %
                            </button>
                        ))}
                        <span className="text-[#dde5f0]">|</span>
                        <input type="number" step="0.5" value={customPct} onChange={(e) => setCustomPct(e.target.value)}
                            placeholder="Personnalisé %" className="w-32 px-2 py-1.5 border border-[#dde5f0] text-xs" />
                        <button type="button" onClick={() => { if (customPct !== "") bump(customPct); }} disabled={customPct === ""}
                            className="px-3 py-1.5 border border-[#0c182b] bg-[#0c182b] text-white hover:bg-[#1a2b4a] tech-stamp text-xs disabled:opacity-40">
                            Appliquer
                        </button>
                    </div>
                    <div className="text-[10px] text-[#4b5d7a] mt-2 italic">
                        Astuce : « +5 % » multiplie chaque prix de vente par 1,05. Applique un
                        pourcentage négatif (ex. -10) pour un rabais.
                    </div>
                </div>
            </div>
        </div>
    );
};
