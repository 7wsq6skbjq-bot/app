import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Field, inputClass } from "./Modal";
import { PartyForm } from "./PartyForm";
import {
    computeTotals,
    emptyLineItem,
    emptyParty,
    formatCurrency,
} from "../utils";

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
    const isInvoice = kind === "invoice";
    const partyKey = isInvoice ? "customer_snapshot" : "supplier_snapshot";
    const partyIdKey = isInvoice ? "customer_id" : "supplier_id";
    const partyLabel = isInvoice ? "Client" : "Fournisseur";
    const dateSecondaryLabel = isInvoice ? "Échéance" : "Livraison attendue";
    const dateSecondaryKey = isInvoice ? "due_date" : "expected_delivery";

    const [partyMode, setPartyMode] = useState(value[partyIdKey] ? "select" : "custom");
    const [showPartyForm, setShowPartyForm] = useState(!value[partyIdKey]);

    const totals = computeTotals(value.items || [], value.taxable);

    const set = (k, v) => onChange({ ...value, [k]: v });

    // Party selection handlers
    const selectParty = (id) => {
        const p = parties.find((x) => x.id === id);
        if (!p) {
            onChange({ ...value, [partyIdKey]: null, [partyKey]: emptyParty(isInvoice ? "customer" : "supplier") });
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
                    <button type="button" onClick={addItem} data-testid={`doc-${kind}-add-item`} className="btn-secondary !py-1.5 !px-3 !text-xs">
                        <Plus className="w-3 h-3" />
                        Ligne
                    </button>
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
        </div>
    );
};
