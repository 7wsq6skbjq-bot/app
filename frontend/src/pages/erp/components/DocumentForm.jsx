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
            // backend LineItem model ignores unknown fields (`extra="ignore"`)
            // so this NEVER hits the PDF or the client-facing quote.
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

            {/* === CONFIDENTIAL profit-margin panel (never shown to client) === */}
            {kind === "quote" && (
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
        </div>
    );
};


/**
 * ProfitMarginPanel — CONFIDENTIAL, ADMIN-ONLY.
 *
 * Renders NEXT TO / BELOW the standard totals block. Displays cost vs.
 * sell for each line item that has a linked product with a `cost_price`,
 * and offers a one-click "bump prices by X %" adjustment. Never visible
 * on the PDF or the emailed quote — the data lives purely in-browser
 * (cost_price is looked up on-the-fly from the products list).
 *
 * Rendering rules:
 *   - Hidden if no line has cost data
 *   - Shows margin coloured red/orange/green based on % threshold
 *   - Bump control: pick a % (or type custom), multiplies every line's
 *     unit_price by (1 + %/100). Rounded to the cent.
 */
const ProfitMarginPanel = ({ items, products, onBumpPrices }) => {
    const [customPct, setCustomPct] = useState("");
    const productMap = Object.fromEntries((products || []).map((p) => [p.id, p]));

    // Enrich items with cost from the products cache
    const rows = (items || []).map((it) => {
        const p = productMap[it.product_id];
        const cost = p && p.cost_price != null ? Number(p.cost_price) : null;
        const qty = Number(it.quantity || 0);
        const sell = Number(it.unit_price || 0);
        return {
            desc: it.description || "—",
            qty, cost, sell,
            hasCost: cost != null && cost > 0,
            lineCost: cost != null ? cost * qty : 0,
            lineSell: sell * qty,
        };
    });

    const withCost = rows.filter((r) => r.hasCost);
    if (withCost.length === 0) {
        return (
            <div className="mt-4 border border-dashed border-[#c5d4e7] bg-[#f9fbfd] p-3 text-xs text-[#4b5d7a] tech-stamp">
                🔒 Panneau de marge : aucune ligne n&apos;a de prix d&apos;achat lié. Ajoute
                un prix d&apos;achat aux produits (onglet « Produits ») pour voir
                automatiquement ta marge ici.
            </div>
        );
    }

    const totalCost = withCost.reduce((s, r) => s + r.lineCost, 0);
    const totalSell = rows.reduce((s, r) => s + r.lineSell, 0);
    const margin = totalSell - totalCost;
    const marginPct = totalCost > 0 ? (margin / totalCost) * 100 : 0;
    const tone = marginPct < 15 ? "text-[#a31a1a]"
               : marginPct < 30 ? "text-[#925800]"
               : "text-[#0f6b3a]";

    const bump = (pct) => {
        const factor = 1 + Number(pct) / 100;
        if (!Number.isFinite(factor) || factor <= 0) return;
        onBumpPrices(factor);
    };

    return (
        <div className="mt-4 border border-[#0c182b] bg-[#0c182b]/5 p-4"
            data-testid="quote-profit-panel">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <div className="tech-stamp text-[#0c182b] font-bold flex items-center gap-1.5">
                    🔒 Marge de profit — <span className="text-[10px] uppercase text-[#a31a1a]">Confidentiel — ne figure pas sur la soumission</span>
                </div>
            </div>
            <div className="overflow-x-auto mb-3">
                <table className="w-full text-xs">
                    <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                        <tr>
                            <th className="text-left py-1">Ligne</th>
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
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs mb-3">
                <div>
                    <div className="text-[10px] uppercase text-[#4b5d7a]">Coût total</div>
                    <div className="font-mono font-bold">{formatCurrency(totalCost)}</div>
                </div>
                <div>
                    <div className="text-[10px] uppercase text-[#4b5d7a]">Vente totale</div>
                    <div className="font-mono font-bold">{formatCurrency(totalSell)}</div>
                </div>
                <div>
                    <div className="text-[10px] uppercase text-[#4b5d7a]">Marge $</div>
                    <div className={`font-mono font-bold ${tone}`}>{formatCurrency(margin)}</div>
                </div>
                <div>
                    <div className="text-[10px] uppercase text-[#4b5d7a]">Marge %</div>
                    <div className={`font-mono font-bold ${tone}`}>{marginPct.toFixed(1)} %</div>
                </div>
            </div>
            <div className="border-t border-[#dde5f0] pt-3">
                <div className="text-[10px] uppercase text-[#4b5d7a] font-bold mb-1">
                    Ajuster les prix de vente en un clic
                </div>
                <div className="flex flex-wrap gap-2 items-center">
                    {[5, 10, 15, 20].map((p) => (
                        <button key={p} type="button" onClick={() => bump(p)}
                            data-testid={`quote-bump-${p}`}
                            className="px-3 py-1.5 border border-[#0c182b] bg-white hover:bg-[#0c182b] hover:text-white tech-stamp text-xs">
                            +{p} %
                        </button>
                    ))}
                    <span className="text-[#dde5f0]">|</span>
                    <input type="number" step="0.5"
                        value={customPct}
                        onChange={(e) => setCustomPct(e.target.value)}
                        placeholder="Personnalisé %"
                        className="w-32 px-2 py-1.5 border border-[#dde5f0] text-xs" />
                    <button type="button"
                        onClick={() => { if (customPct !== "") bump(customPct); }}
                        disabled={customPct === ""}
                        className="px-3 py-1.5 border border-[#0c182b] bg-[#0c182b] text-white hover:bg-[#1a2b4a] tech-stamp text-xs disabled:opacity-40">
                        Appliquer
                    </button>
                    <button type="button"
                        onClick={() => bump(-100 + (100 * totalSell / totalCost * (30 / 100 + 1)) / (totalSell / totalCost))}
                        title="Sans effet — utilise +X % ci-dessus"
                        className="hidden">
                        reset
                    </button>
                </div>
                <div className="text-[10px] text-[#4b5d7a] mt-2 italic">
                    Astuce : « +5 % » multiplie chaque prix de vente par 1,05. Utile pour
                    un nouveau client où tu veux ajouter une marge de sécurité. Tu peux
                    aussi appliquer un pourcentage négatif (ex. -10) pour un rabais.
                </div>
            </div>
        </div>
    );
};
