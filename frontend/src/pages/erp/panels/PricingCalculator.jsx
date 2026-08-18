/**
 * Portech — Calculateur de prix & rentabilité (Phase 1), intégré aux Soumissions.
 * Règles exactes : markup = profit/coût ; marge = profit/vente ;
 * prix depuis marge cible = coût / (1 - marge). Ne confond jamais les deux.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Calculator, ChevronDown, ChevronRight, Plus, Trash2, Save, AlertTriangle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const CATS = [
    { v: "porte", l: "Porte" },
    { v: "quincaillerie", l: "Quincaillerie" },
    { v: "main_doeuvre", l: "Main-d'œuvre" },
    { v: "deplacement", l: "Déplacement" },
    { v: "forfait", l: "Forfait" },
    { v: "expertise", l: "Expertise" },
    { v: "fabrication", l: "Fabrication" },
    { v: "usinage", l: "Usinage" },
    { v: "autre", l: "Autre" },
];
const CAT_L = Object.fromEntries(CATS.map((c) => [c.v, c.l]));
const SIM_PCTS = [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100];
const TARGETS = [30, 35, 40, 45, 50, 55, 60];

const money = (v) => `${(Number(v) || 0).toLocaleString("fr-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} $`;
const pct = (f) => (f === null || f === undefined ? "—" : `${(f * 100).toFixed(2)} %`);
const num = (v, d = 0) => { const n = parseFloat(String(v ?? "").replace(",", ".")); return Number.isFinite(n) ? n : d; };

const emptyLine = () => ({
    _k: Math.random().toString(36).slice(2),
    description: "", category: "quincaillerie",
    qty: 1, per_n_doors: 0, unit_cost: 0, unit_price: 0,
});

export const PricingCalculator = () => {
    const { http } = useAuth();
    const [open, setOpen] = useState(false);
    const [doors, setDoors] = useState(0);
    const [lines, setLines] = useState([emptyLine()]);
    const [settings, setSettings] = useState(null);
    const [savingCfg, setSavingCfg] = useState(false);
    const [target, setTarget] = useState("");
    const [customSim, setCustomSim] = useState("");

    const loadSettings = useCallback(async () => {
        try { const { data } = await http.get("/admin/pricing/settings"); setSettings(data); }
        catch (_) { /* silent */ }
    }, [http]);
    useEffect(() => { loadSettings(); }, [loadSettings]);

    const upd = (k, field, val) => setLines((ls) => ls.map((l) => (l._k === k ? { ...l, [field]: val } : l)));
    const addLine = () => setLines((ls) => [...ls, emptyLine()]);
    const delLine = (k) => setLines((ls) => (ls.length > 1 ? ls.filter((l) => l._k !== k) : ls));

    const lineQty = useCallback((l) => {
        const pn = num(l.per_n_doors), d = num(doors);
        if (pn > 0 && d > 0) return Math.ceil(d / pn);
        return num(l.qty, 1);
    }, [doors]);

    const marginMin = settings?.margin_min ?? null;
    const marginTarget = settings?.margin_target ?? null;

    const summary = useMemo(() => {
        const rows = lines.map((l) => {
            const q = lineQty(l);
            const cost = q * num(l.unit_cost), sell = q * num(l.unit_price);
            const profit = sell - cost;
            return {
                ...l, q, cost, sell, profit,
                markup: cost > 0 ? profit / cost : null,
                margin: sell > 0 ? profit / sell : null,
            };
        });
        const byCat = {};
        let tc = 0, ts = 0;
        rows.forEach((r) => {
            tc += r.cost; ts += r.sell;
            const c = (byCat[r.category] = byCat[r.category] || { cost: 0, sell: 0 });
            c.cost += r.cost; c.sell += r.sell;
        });
        Object.values(byCat).forEach((c) => {
            c.profit = c.sell - c.cost;
            c.markup = c.cost > 0 ? c.profit / c.cost : null;
            c.margin = c.sell > 0 ? c.profit / c.sell : null;
        });
        const profit = ts - tc;
        const margin = ts > 0 ? profit / ts : null;
        return {
            rows, byCat, cost: tc, sell: ts, profit,
            markup: tc > 0 ? profit / tc : null, margin,
            belowMin: marginMin != null && margin != null && margin < marginMin,
        };
    }, [lines, lineQty, marginMin]);

    const saveSettings = async () => {
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

    const setRate = (key, val) => setSettings((s) => ({ ...s, labor_rates: { ...(s?.labor_rates || {}), [key]: val === "" ? null : num(val) } }));

    const inp = "w-full px-2 py-1 border border-[#dde5f0] text-sm";
    const RATES = [["standard", "Standard"], ["specialized", "Spécialisée"], ["fabrication", "Fabrication"], ["machining", "Usinage"], ["expertise", "Expertise/dessin"]];

    return (
        <div className="mb-4 bg-white border border-[#1f3a5f]" data-testid="pricing-calculator">
            <button type="button" onClick={() => setOpen((v) => !v)}
                className="w-full flex items-center gap-2 px-4 py-3 bg-[#0c182b] text-white" data-testid="pricing-toggle">
                {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <Calculator className="w-4 h-4 text-[#4fd1c5]" />
                <span className="font-bold tracking-wide">Calculateur de prix & rentabilité</span>
                <span className="ml-auto text-xs text-[#9fb3d1]">Coût · Vente · Profit · Markup · Marge</span>
            </button>

            {open && (
                <div className="p-4 space-y-5">
                    {/* Settings */}
                    <div className="border border-[#dde5f0] bg-[#f7f9fc] p-3">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-[11px] uppercase font-bold tracking-wider text-[#0c182b]">Paramètres (modifiables)</span>
                            <button onClick={saveSettings} disabled={savingCfg} data-testid="pricing-save-settings"
                                className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-[#1f3a5f] text-white disabled:opacity-50">
                                <Save className="w-3 h-3" /> {savingCfg ? "…" : "Enregistrer"}
                            </button>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                            {RATES.map(([k, lbl]) => {
                                const val = settings?.labor_rates?.[k];
                                return (
                                    <div key={k}>
                                        <label className="block text-[#4b5d7a] mb-0.5">Taux {lbl} ($/h)</label>
                                        <input type="number" step="1" min="0" value={val ?? ""} placeholder="DONNÉE MANQUANTE"
                                            data-testid={`pricing-rate-${k}`}
                                            onChange={(e) => setRate(k, e.target.value)}
                                            className={`${inp} ${val == null ? "bg-[#fff3cf] placeholder-[#b48a2a]" : ""}`} />
                                    </div>
                                );
                            })}
                            <div>
                                <label className="block text-[#4b5d7a] mb-0.5">Taux km ($/km)</label>
                                <input type="number" step="0.01" min="0" value={settings?.km_rate ?? ""} data-testid="pricing-kmrate"
                                    onChange={(e) => setSettings((s) => ({ ...s, km_rate: num(e.target.value) }))} className={inp} />
                            </div>
                            <div>
                                <label className="block text-[#4b5d7a] mb-0.5">Marge MINI (%)</label>
                                <input type="number" step="1" value={settings?.margin_min != null ? settings.margin_min * 100 : ""}
                                    placeholder="—" data-testid="pricing-marginmin"
                                    onChange={(e) => setSettings((s) => ({ ...s, margin_min: e.target.value === "" ? null : num(e.target.value) / 100 }))}
                                    className={`${inp} ${settings?.margin_min == null ? "bg-[#fff3cf]" : ""}`} />
                            </div>
                            <div>
                                <label className="block text-[#4b5d7a] mb-0.5">Marge CIBLE (%)</label>
                                <input type="number" step="1" value={settings?.margin_target != null ? settings.margin_target * 100 : ""}
                                    placeholder="—" data-testid="pricing-margintarget"
                                    onChange={(e) => setSettings((s) => ({ ...s, margin_target: e.target.value === "" ? null : num(e.target.value) / 100 }))}
                                    className={`${inp} ${settings?.margin_target == null ? "bg-[#fff3cf]" : ""}`} />
                            </div>
                            <div>
                                <label className="block text-[#4b5d7a] mb-0.5">Nb portes (projet)</label>
                                <input type="number" step="1" min="0" value={doors} data-testid="pricing-doors"
                                    onChange={(e) => setDoors(num(e.target.value))} className={inp} />
                            </div>
                        </div>
                    </div>

                    {/* Lines */}
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm" data-testid="pricing-lines">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                                <tr>
                                    <th className="text-left px-2 py-1.5">Description</th>
                                    <th className="text-left px-2 py-1.5 w-32">Catégorie</th>
                                    <th className="text-right px-1 py-1.5 w-16">Qté</th>
                                    <th className="text-right px-1 py-1.5 w-20">1 / N portes</th>
                                    <th className="text-right px-1 py-1.5 w-24">Coût U. ($)</th>
                                    <th className="text-right px-1 py-1.5 w-24">Vente U. ($)</th>
                                    <th className="text-right px-2 py-1.5 w-24">Profit</th>
                                    <th className="text-right px-2 py-1.5 w-20">Marge</th>
                                    <th className="w-8"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {summary.rows.map((r) => (
                                    <tr key={r._k} className="border-b border-[#f3f6fb]">
                                        <td className="px-1 py-1">
                                            <input value={r.description} onChange={(e) => upd(r._k, "description", e.target.value)}
                                                placeholder="Ex : Deadlock Adams Rite" className={inp} data-testid="pricing-desc" />
                                        </td>
                                        <td className="px-1 py-1">
                                            <select value={r.category} onChange={(e) => upd(r._k, "category", e.target.value)} className={`${inp} bg-white`}>
                                                {CATS.map((c) => <option key={c.v} value={c.v}>{c.l}</option>)}
                                            </select>
                                        </td>
                                        <td className="px-1 py-1"><input type="number" step="0.5" value={r.qty} onChange={(e) => upd(r._k, "qty", e.target.value)} className={`${inp} text-right`} /></td>
                                        <td className="px-1 py-1"><input type="number" step="1" min="0" value={r.per_n_doors} onChange={(e) => upd(r._k, "per_n_doors", e.target.value)} placeholder="0" className={`${inp} text-right`} data-testid="pricing-pern" /></td>
                                        <td className="px-1 py-1"><input type="number" step="0.01" value={r.unit_cost} onChange={(e) => upd(r._k, "unit_cost", e.target.value)} className={`${inp} text-right`} /></td>
                                        <td className="px-1 py-1"><input type="number" step="0.01" value={r.unit_price} onChange={(e) => upd(r._k, "unit_price", e.target.value)} className={`${inp} text-right`} data-testid="pricing-sell" /></td>
                                        <td className="px-2 py-1 text-right text-[#0b6b2f]">{money(r.profit)}</td>
                                        <td className="px-2 py-1 text-right text-[#4b5d7a]">{pct(r.margin)}{r.per_n_doors > 0 && doors > 0 ? <span className="block text-[9px] text-[#8a97a8]">×{r.q}</span> : null}</td>
                                        <td className="px-1 py-1 text-right"><button onClick={() => delLine(r._k)} className="p-1 text-[#a31a1a] hover:bg-[#fde7e7]"><Trash2 className="w-3.5 h-3.5" /></button></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <button onClick={addLine} data-testid="pricing-addline" className="inline-flex items-center gap-1 text-sm text-[#1d4ed8] hover:underline">
                        <Plus className="w-4 h-4" /> Ajouter une ligne
                    </button>

                    {/* Summary + alert */}
                    <div className="grid md:grid-cols-2 gap-4">
                        <div className="border border-[#1f3a5f] bg-[#0c182b] text-white p-3" data-testid="pricing-summary">
                            <div className="text-[11px] uppercase tracking-wider text-[#9fb3d1] mb-2">Rentabilité du projet</div>
                            <div className="grid grid-cols-2 gap-y-1 text-sm">
                                <span className="text-[#9fb3d1]">Coût total</span><span className="text-right">{money(summary.cost)}</span>
                                <span className="text-[#9fb3d1]">Prix de vente</span><span className="text-right font-bold">{money(summary.sell)}</span>
                                <span className="text-[#9fb3d1]">Profit brut</span><span className="text-right text-[#4fd1c5] font-bold">{money(summary.profit)}</span>
                                <span className="text-[#9fb3d1]">Markup</span><span className="text-right">{pct(summary.markup)}</span>
                                <span className="text-[#9fb3d1]">Marge brute</span><span className="text-right font-bold">{pct(summary.margin)}</span>
                            </div>
                            {summary.belowMin && (
                                <div className="mt-2 flex items-center gap-2 bg-[#a31a1a] text-white text-xs px-2 py-1.5" data-testid="pricing-alert">
                                    <AlertTriangle className="w-4 h-4" /> MARGE SOUS LA CIBLE (mini {pct(marginMin)})
                                </div>
                            )}
                            {marginTarget != null && summary.margin != null && !summary.belowMin && summary.margin < marginTarget && (
                                <div className="mt-2 text-[11px] text-[#ffd27f]" data-testid="pricing-undertarget">Sous la marge cible ({pct(marginTarget)})</div>
                            )}
                        </div>

                        <div className="border border-[#dde5f0] p-3" data-testid="pricing-bycat">
                            <div className="text-[11px] uppercase tracking-wider text-[#4b5d7a] mb-2">Profit par catégorie</div>
                            <table className="w-full text-xs">
                                <tbody>
                                    {Object.entries(summary.byCat).filter(([, c]) => c.sell || c.cost).map(([k, c]) => (
                                        <tr key={k} className="border-b border-[#f3f6fb]">
                                            <td className="py-1 text-[#0c182b]">{CAT_L[k] || k}</td>
                                            <td className="py-1 text-right text-[#0b6b2f]">{money(c.profit)}</td>
                                            <td className="py-1 text-right text-[#4b5d7a]">{pct(c.margin)}</td>
                                        </tr>
                                    ))}
                                    {!Object.keys(summary.byCat).length && <tr><td className="py-1 text-[#8a97a8] italic">Aucune ligne</td></tr>}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Simulator + target solver */}
                    <div className="grid md:grid-cols-2 gap-4">
                        <div className="border border-[#dde5f0] p-3" data-testid="pricing-simulator">
                            <div className="text-[11px] uppercase tracking-wider text-[#4b5d7a] mb-2">Simulateur — markup sur le coût ({money(summary.cost)})</div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                    <thead className="text-[#8a97a8]"><tr><th className="text-left py-1">Markup</th><th className="text-right py-1">Prix vente</th><th className="text-right py-1">Profit</th><th className="text-right py-1">Marge</th></tr></thead>
                                    <tbody>
                                        {SIM_PCTS.concat(customSim !== "" ? [num(customSim)] : []).map((p, i) => {
                                            const sell = summary.cost * (1 + p / 100);
                                            const profit = sell - summary.cost;
                                            const margin = sell > 0 ? profit / sell : null;
                                            return (
                                                <tr key={`${p}-${i}`} className="border-b border-[#f3f6fb]">
                                                    <td className="py-1">+{p} %</td>
                                                    <td className="py-1 text-right font-medium">{money(sell)}</td>
                                                    <td className="py-1 text-right text-[#0b6b2f]">{money(profit)}</td>
                                                    <td className="py-1 text-right">{pct(margin)}</td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                            <div className="mt-2 flex items-center gap-2 text-xs">
                                <span className="text-[#4b5d7a]">Markup personnalisé (%)</span>
                                <input type="number" value={customSim} onChange={(e) => setCustomSim(e.target.value)} className="w-20 px-2 py-1 border border-[#dde5f0] text-right" data-testid="pricing-customsim" />
                            </div>
                        </div>

                        <div className="border border-[#dde5f0] p-3" data-testid="pricing-target">
                            <div className="text-[11px] uppercase tracking-wider text-[#4b5d7a] mb-2">Prix requis pour une marge cible</div>
                            <div className="text-[11px] text-[#8a97a8] mb-2">Prix = coût / (1 − marge). Coût = {money(summary.cost)}</div>
                            <table className="w-full text-xs">
                                <thead className="text-[#8a97a8]"><tr><th className="text-left py-1">Marge visée</th><th className="text-right py-1">Prix requis</th><th className="text-right py-1">Profit</th><th className="text-right py-1">Markup</th></tr></thead>
                                <tbody>
                                    {TARGETS.concat(target !== "" ? [num(target)] : []).map((m, i) => {
                                        const f = m / 100;
                                        const sell = f < 1 ? summary.cost / (1 - f) : null;
                                        const profit = sell != null ? sell - summary.cost : null;
                                        const markup = sell != null && summary.cost > 0 ? profit / summary.cost : null;
                                        return (
                                            <tr key={`${m}-${i}`} className="border-b border-[#f3f6fb]">
                                                <td className="py-1">{m} %</td>
                                                <td className="py-1 text-right font-bold">{sell != null ? money(sell) : "—"}</td>
                                                <td className="py-1 text-right text-[#0b6b2f]">{profit != null ? money(profit) : "—"}</td>
                                                <td className="py-1 text-right">{pct(markup)}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                            <div className="mt-2 flex items-center gap-2 text-xs">
                                <span className="text-[#4b5d7a]">Marge cible personnalisée (%)</span>
                                <input type="number" value={target} onChange={(e) => setTarget(e.target.value)} className="w-20 px-2 py-1 border border-[#dde5f0] text-right" data-testid="pricing-customtarget" />
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PricingCalculator;
