/* eslint-disable react-hooks/exhaustive-deps */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Plus, Pencil, Trash2, Search, RefreshCw, Package, DoorClosed, Sliders, Layers, Save, Calculator, X } from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";
import { formatCurrency } from "../utils";

const SECTIONS = [
    { key: "calc", label: "Calculateur de prix", icon: Calculator },
    { key: "hardware", label: "Quincaillerie", icon: Package },
    { key: "doors", label: "Portes standards", icon: DoorClosed },
    { key: "params", label: "Paramètres", icon: Sliders },
    { key: "extrusion", label: "Extrusion / Anodisation", icon: Layers },
];

const emptyHw = () => ({ description: "", color: "", product_code: "", supplier: "", unit_cost: 0, cost_date: "", kanban_min: 0, kanban_order: 0, kanban_max: 0, category: "Autre" });

export const MasterCostsPanel = () => {
    const { http } = useAuth();
    const [section, setSection] = useState("hardware");
    return (
        <div data-testid="master-panel" className="space-y-6">
            <div className="hidden md:block">
                <div className="tech-stamp mb-1">Référence AT Fabrication</div>
                <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Coûts Master</h1>
            </div>
            <div className="flex flex-wrap gap-2" data-testid="master-sections">
                {SECTIONS.map((s) => (
                    <button key={s.key} data-testid={`master-tab-${s.key}`} onClick={() => setSection(s.key)}
                        className={`tech-stamp px-3 py-2 border text-xs flex items-center gap-1.5 ${section === s.key ? "bg-[#0c182b] text-white border-[#0c182b]" : "border-[#dde5f0] text-[#4b5d7a] hover:bg-white"}`}>
                        <s.icon className="w-3.5 h-3.5" /> {s.label}
                    </button>
                ))}
            </div>
            {section === "calc" && <CalculatorSection http={http} />}
            {section === "hardware" && <HardwareSection http={http} />}
            {section === "doors" && <DoorsSection http={http} />}
            {section === "params" && <ParamsSection http={http} />}
            {section === "extrusion" && <ExtrusionSection http={http} />}
        </div>
    );
};

/* ── QUINCAILLERIE (CRUD complet + recherche) ─────────────────── */
const HardwareSection = ({ http }) => {
    const [rows, setRows] = useState([]);
    const [meta, setMeta] = useState({ suppliers: [], categories: [], count: 0 });
    const [q, setQ] = useState("");
    const [supplier, setSupplier] = useState("");
    const [category, setCategory] = useState("");
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(null);
    const [open, setOpen] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (q) params.set("q", q);
            if (supplier) params.set("supplier", supplier);
            if (category) params.set("category", category);
            const [{ data: list }, { data: m }] = await Promise.all([
                http.get(`/admin/master/hardware?${params}`),
                http.get("/admin/master/hardware/meta"),
            ]);
            setRows(list); setMeta(m);
        } finally { setLoading(false); }
    }, [q, supplier, category]);
    useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

    const save = async () => {
        if (!editing.description?.trim()) { alert("La description est requise."); return; }
        const payload = { ...editing, unit_cost: Number(editing.unit_cost) || 0 };
        if (editing.id) await http.put(`/admin/master/hardware/${editing.id}`, payload);
        else await http.post("/admin/master/hardware", payload);
        setOpen(false); setEditing(null); load();
    };
    const remove = async (r) => { if (window.confirm(`Supprimer « ${r.description.slice(0, 40)}… » ?`)) { await http.delete(`/admin/master/hardware/${r.id}`); load(); } };

    return (
        <div className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                <Tile label="Items quincaillerie" value={meta.count} />
                <Tile label="Fournisseurs" value={meta.suppliers.length} />
                <Tile label="Catégories" value={meta.categories.length} />
                <Tile label="Somme des coûts unitaires" value={formatCurrency(meta.total_cost || 0)} />
            </div>
            <div className="flex flex-wrap items-center gap-2">
                <div className="relative flex-1 min-w-[200px]">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#93a3bd]" />
                    <input data-testid="master-hw-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher par description ou code produit…" className={`${inputClass} !pl-9`} />
                </div>
                <select data-testid="master-hw-supplier" value={supplier} onChange={(e) => setSupplier(e.target.value)} className={inputClass.replace("w-full", "w-auto")}>
                    <option value="">Tous fournisseurs</option>
                    {meta.suppliers.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                <select data-testid="master-hw-category" value={category} onChange={(e) => setCategory(e.target.value)} className={inputClass.replace("w-full", "w-auto")}>
                    <option value="">Toutes catégories</option>
                    {meta.categories.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <button onClick={() => { setEditing(emptyHw()); setOpen(true); }} data-testid="master-hw-new" className="btn-primary !py-2 !px-4 !text-xs ml-auto"><Plus className="w-3.5 h-3.5" /> Ajouter</button>
            </div>

            <div className="border border-[#dde5f0] bg-white overflow-x-auto">
                <table className="w-full text-sm min-w-[900px]">
                    <thead><tr className="bg-[#f3f6fb] tech-stamp text-left">
                        <th className="px-3 py-2">Description</th><th className="px-3 py-2">Couleur</th>
                        <th className="px-3 py-2">Code produit</th><th className="px-3 py-2">Fournisseur</th>
                        <th className="px-3 py-2">Catégorie</th><th className="px-3 py-2 text-right">Coût unit.</th>
                        <th className="px-3 py-2 text-right">Kanban</th><th className="px-3 py-2 text-right">Actions</th>
                    </tr></thead>
                    <tbody>
                        {!loading && rows.length === 0 && <tr><td colSpan={8} className="p-8 text-center text-[#4b5d7a]">Aucun résultat.</td></tr>}
                        {rows.map((r) => (
                            <tr key={r.id} data-testid={`master-hw-row-${r.id}`} className="border-t border-[#eef2f8] hover:bg-[#f8fafd]">
                                <td className="px-3 py-2 max-w-[320px]">{r.description}</td>
                                <td className="px-3 py-2 text-[#4b5d7a] text-xs">{r.color || "—"}</td>
                                <td className="px-3 py-2 font-mono text-xs text-[#2f4f7f]">{r.product_code || "—"}</td>
                                <td className="px-3 py-2 text-xs">{r.supplier || "—"}</td>
                                <td className="px-3 py-2 text-xs">{r.category}</td>
                                <td className="px-3 py-2 text-right font-display font-bold">{formatCurrency(r.unit_cost)}</td>
                                <td className="px-3 py-2 text-right text-xs text-[#4b5d7a]">{r.kanban_min}/{r.kanban_order}/{r.kanban_max}</td>
                                <td className="px-3 py-2 text-right whitespace-nowrap">
                                    <button onClick={() => { setEditing(r); setOpen(true); }} className="p-1.5 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]"><Pencil className="w-3.5 h-3.5" /></button>
                                    <button onClick={() => remove(r)} className="p-1.5 border border-[#dde5f0] hover:bg-red-50 text-red-600 ml-1"><Trash2 className="w-3.5 h-3.5" /></button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {editing && (
                <Modal open={open} onClose={() => { setOpen(false); setEditing(null); }} title={editing.id ? "Modifier la pièce" : "Nouvelle pièce"} testId="master-hw-modal"
                    footer={<><button onClick={() => { setOpen(false); setEditing(null); }} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button><button data-testid="master-hw-save" onClick={save} className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">Enregistrer</button></>}>
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Description" required className="col-span-2"><input className={inputClass} value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} /></Field>
                        <Field label="Code produit"><input className={inputClass} value={editing.product_code || ""} onChange={(e) => setEditing({ ...editing, product_code: e.target.value })} /></Field>
                        <Field label="Fournisseur"><input className={inputClass} value={editing.supplier || ""} onChange={(e) => setEditing({ ...editing, supplier: e.target.value })} /></Field>
                        <Field label="Couleur / fini"><input className={inputClass} value={editing.color || ""} onChange={(e) => setEditing({ ...editing, color: e.target.value })} /></Field>
                        <Field label="Catégorie"><input className={inputClass} value={editing.category || ""} onChange={(e) => setEditing({ ...editing, category: e.target.value })} /></Field>
                        <Field label="Coût unitaire ($)" required><input type="number" step="0.01" data-testid="master-hw-cost" className={inputClass} value={editing.unit_cost} onChange={(e) => setEditing({ ...editing, unit_cost: e.target.value })} /></Field>
                        <Field label="Date du prix"><input className={inputClass} value={editing.cost_date || ""} onChange={(e) => setEditing({ ...editing, cost_date: e.target.value })} /></Field>
                        <Field label="Kanban min"><input type="number" className={inputClass} value={editing.kanban_min} onChange={(e) => setEditing({ ...editing, kanban_min: Number(e.target.value) })} /></Field>
                        <Field label="Kanban commande"><input type="number" className={inputClass} value={editing.kanban_order} onChange={(e) => setEditing({ ...editing, kanban_order: Number(e.target.value) })} /></Field>
                        <Field label="Kanban max"><input type="number" className={inputClass} value={editing.kanban_max} onChange={(e) => setEditing({ ...editing, kanban_max: Number(e.target.value) })} /></Field>
                    </div>
                </Modal>
            )}
        </div>
    );
};

/* ── PORTES STANDARDS (édition en ligne des prix) ─────────────── */
const DoorsSection = ({ http }) => {
    const [rows, setRows] = useState([]);
    const load = useCallback(async () => { const { data } = await http.get("/admin/master/door-prices"); setRows(data); }, []);
    useEffect(() => { load(); }, [load]);
    const saveRow = async (r, patch) => {
        const next = { ...r, ...patch };
        setRows((rs) => rs.map((x) => (x.id === r.id ? next : x)));
        await http.put(`/admin/master/door-prices/${r.id}`, next);
    };
    const GROUPS = [["group_a", "1"], ["group_b", "2-5"], ["group_c", "6-10"], ["group_d", "11-20"], ["group_e", "21+"]];
    return (
        <div className="border border-[#dde5f0] bg-white overflow-x-auto">
            <table className="w-full text-sm min-w-[800px]">
                <thead><tr className="bg-[#f3f6fb] tech-stamp text-left">
                    <th className="px-3 py-2">Nº pièce</th><th className="px-3 py-2">Description</th>
                    {GROUPS.map(([k, l]) => <th key={k} className="px-3 py-2 text-right">Gr. {l}</th>)}
                </tr></thead>
                <tbody>
                    {rows.map((r) => (
                        <tr key={r.id} data-testid={`master-door-${r.id}`} className="border-t border-[#eef2f8]">
                            <td className="px-3 py-2 font-mono text-xs text-[#2f4f7f]">{r.part_number}</td>
                            <td className="px-3 py-2 text-xs max-w-[260px]">{r.description}</td>
                            {GROUPS.map(([k]) => (
                                <td key={k} className="px-2 py-1 text-right">
                                    {typeof r[k] === "number" ? (
                                        <input type="number" defaultValue={r[k]} onBlur={(e) => { const v = Number(e.target.value); if (v !== r[k]) saveRow(r, { [k]: v }); }}
                                            className="w-20 text-right border border-[#dde5f0] px-2 py-1 text-sm" />
                                    ) : <span className="text-xs text-[#93a3bd]">{r[k]}</span>}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

/* ── PARAMÈTRES MASTER (édition en ligne) ─────────────────────── */
const ParamsSection = ({ http }) => {
    const [rows, setRows] = useState([]);
    const load = useCallback(async () => { const { data } = await http.get("/admin/master/params"); setRows(data); }, []);
    useEffect(() => { load(); }, [load]);
    const save = async (r, value) => {
        setRows((rs) => rs.map((x) => (x.id === r.id ? { ...x, value } : x)));
        await http.put(`/admin/master/params/${r.id}`, { label: r.label, value });
    };
    const isPct = (l) => /POURCENTAGE|PROFIT/i.test(l);
    return (
        <div className="border border-[#dde5f0] bg-white divide-y divide-[#eef2f8]">
            {rows.map((r) => (
                <div key={r.id} data-testid={`master-param-${r.id}`} className="flex items-center gap-4 px-4 py-2.5">
                    <span className="flex-1 text-sm text-[#0c182b]">{r.label}</span>
                    <div className="flex items-center gap-1">
                        <input type="number" step="0.01" defaultValue={r.value} onBlur={(e) => { const v = Number(e.target.value); if (v !== r.value) save(r, v); }}
                            className="w-24 text-right border border-[#dde5f0] px-2 py-1 text-sm font-display font-bold" />
                        <span className="text-xs text-[#93a3bd] w-8">{isPct(r.label) ? "×" : "$"}</span>
                    </div>
                </div>
            ))}
        </div>
    );
};

/* ── EXTRUSION / ANODISATION (édition en ligne) ───────────────── */
const ExtrusionSection = ({ http }) => {
    const [rows, setRows] = useState([]);
    const load = useCallback(async () => { const { data } = await http.get("/admin/master/extrusion"); setRows(data); }, []);
    useEffect(() => { load(); }, [load]);
    const saveRow = async (r, patch) => {
        const next = { ...r, ...patch };
        setRows((rs) => rs.map((x) => (x.id === r.id ? next : x)));
        await http.put(`/admin/master/extrusion/${r.id}`, next);
    };
    const COLS = [["price_per_kg", "Prix/kg"], ["cost_per_length_mill", "Coût/long. (mill)"], ["anod_clair_per_length", "Anod. clair/long."], ["anod_noir_per_length", "Anod. noir/long."]];
    return (
        <div className="border border-[#dde5f0] bg-white overflow-x-auto">
            <table className="w-full text-sm min-w-[700px]">
                <thead><tr className="bg-[#f3f6fb] tech-stamp text-left">
                    <th className="px-3 py-2">Nº pièce</th><th className="px-3 py-2">Description</th>
                    {COLS.map(([k, l]) => <th key={k} className="px-3 py-2 text-right">{l}</th>)}
                </tr></thead>
                <tbody>
                    {rows.map((r) => (
                        <tr key={r.id} data-testid={`master-ext-${r.id}`} className="border-t border-[#eef2f8]">
                            <td className="px-3 py-2 font-mono text-xs text-[#2f4f7f]">{r.part_number}</td>
                            <td className="px-3 py-2 text-xs">{r.description}</td>
                            {COLS.map(([k]) => (
                                <td key={k} className="px-2 py-1 text-right">
                                    <input type="number" step="0.01" defaultValue={r[k] ?? ""} onBlur={(e) => { const v = e.target.value === "" ? null : Number(e.target.value); if (v !== r[k]) saveRow(r, { [k]: v }); }}
                                        className="w-24 text-right border border-[#dde5f0] px-2 py-1 text-sm" />
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

/* ── CALCULATEUR DE PRIX DE PORTE (moteur LDP) ────────────────── */
const CalculatorSection = ({ http }) => {
    const [models, setModels] = useState([]);
    const [rate, setRate] = useState(50);
    const [hwMarkup, setHwMarkup] = useState(0.35);
    const [modelKey, setModelKey] = useState("");
    const [hw, setHw] = useState([]);
    const [profitPct, setProfitPct] = useState(0.6);
    const [laborHours, setLaborHours] = useState(3);
    const [materialCost, setMaterialCost] = useState(0);
    const [addQ, setAddQ] = useState("");
    const [addResults, setAddResults] = useState([]);

    useEffect(() => {
        (async () => {
            const [{ data: m }, { data: params }] = await Promise.all([
                http.get("/admin/master/door-models"),
                http.get("/admin/master/params"),
            ]);
            setModels(m);
            const r = params.find((p) => /TAUX HORAIRE/i.test(p.label));
            const q = params.find((p) => /QUINCAILLERIE/i.test(p.label));
            if (r) setRate(r.value);
            if (q) setHwMarkup(q.value);
        })();
    }, []);

    const selectModel = (key) => {
        setModelKey(key);
        const m = models.find((x) => x.model_key === key);
        if (!m) return;
        setHw(m.hardware.map((h) => ({ ...h })));
        setProfitPct(m.profit_pct);
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
    }, [addQ]);

    const laborCost = Math.round(laborHours * rate * 100) / 100;
    const mlCost = Math.round((materialCost + laborCost) * 100) / 100;
    const hwCost = Math.round(hw.reduce((s, h) => s + (Number(h.cost) || 0), 0) * 100) / 100;
    const mlProfit = Math.round(mlCost * profitPct * 100) / 100;
    const hwProfit = Math.round(hwCost * hwMarkup * 100) / 100;
    const costTotal = Math.round((mlCost + hwCost) * 100) / 100;
    const sellTotal = Math.round((mlCost + mlProfit + hwCost + hwProfit) * 100) / 100;
    const margin = Math.round((sellTotal - costTotal) * 100) / 100;
    const marginPct = costTotal ? Math.round((margin / costTotal) * 1000) / 10 : 0;

    return (
        <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-4">
                <div className="border border-[#dde5f0] bg-white p-4 space-y-3">
                    <Field label="Modèle de porte (base LDP)">
                        <select data-testid="calc-model" value={modelKey} onChange={(e) => selectModel(e.target.value)} className={inputClass}>
                            <option value="">— Choisir un modèle —</option>
                            {models.map((m) => <option key={m.model_key} value={m.model_key}>{m.label}</option>)}
                        </select>
                    </Field>
                    {modelKey && (
                        <div className="grid grid-cols-3 gap-3">
                            <Field label="Matériel ($)"><input type="number" step="0.01" data-testid="calc-material" className={inputClass} value={materialCost} onChange={(e) => setMaterialCost(Number(e.target.value))} /></Field>
                            <Field label="Heures M.O."><input type="number" step="0.5" data-testid="calc-hours" className={inputClass} value={laborHours} onChange={(e) => setLaborHours(Number(e.target.value))} /></Field>
                            <Field label="Profit matériel (×)"><input type="number" step="0.05" data-testid="calc-profit" className={inputClass} value={profitPct} onChange={(e) => setProfitPct(Number(e.target.value))} /></Field>
                        </div>
                    )}
                </div>

                {modelKey && (
                    <div className="border border-[#dde5f0] bg-white p-4 space-y-2">
                        <div className="tech-stamp text-[#4b5d7a] flex items-center justify-between">
                            <span>Quincaillerie ({hw.length})</span>
                            <span>{formatCurrency(hwCost)}</span>
                        </div>
                        {hw.map((h, i) => (
                            <div key={i} data-testid={`calc-hw-${i}`} className="flex items-center gap-2 text-sm border-b border-[#f0f3f8] pb-1.5">
                                <span className="flex-1">{h.description}<span className="text-[#93a3bd] text-xs ml-1">{h.code}</span></span>
                                <span className="text-[#4b5d7a]">{formatCurrency(h.cost)}</span>
                                <button onClick={() => setHw(hw.filter((_, j) => j !== i))} className="text-red-500 hover:text-red-700"><X className="w-3.5 h-3.5" /></button>
                            </div>
                        ))}
                        <div className="relative pt-2">
                            <Search className="w-4 h-4 absolute left-3 top-1/2 text-[#93a3bd]" />
                            <input data-testid="calc-add-hw" value={addQ} onChange={(e) => setAddQ(e.target.value)} placeholder="Ajouter une quincaillerie (code ou nom)…" className={`${inputClass} !pl-9`} />
                            {addResults.length > 0 && (
                                <div className="absolute z-10 left-0 right-0 bg-white border border-[#dde5f0] shadow-lg max-h-56 overflow-auto">
                                    {addResults.map((r) => (
                                        <button key={r.id} onClick={() => { setHw([...hw, { code: r.product_code, description: r.description, cost: r.unit_cost }]); setAddQ(""); setAddResults([]); }}
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

            {/* Résultat */}
            <div className="border-2 border-[#0c182b] bg-[#0c182b] text-white p-6 h-fit sticky top-4">
                <div className="tech-stamp text-[#8fb4ff] mb-4">Calcul du prix (comme LDP)</div>
                {!modelKey ? (
                    <p className="text-[#8fb4ff] text-sm">Choisis un modèle pour calculer le prix, le coûtant et la marge.</p>
                ) : (
                    <div className="space-y-2 text-sm">
                        <Row l="Matériel + M.O." v={formatCurrency(mlCost)} sub={`(${formatCurrency(materialCost)} + ${laborHours}h × ${formatCurrency(rate)})`} />
                        <Row l={`Profit matériel (×${profitPct})`} v={formatCurrency(mlProfit)} />
                        <Row l="Quincaillerie (coût)" v={formatCurrency(hwCost)} />
                        <Row l={`Profit quincaillerie (×${hwMarkup})`} v={formatCurrency(hwProfit)} />
                        <div className="border-t border-[#2a3d5c] my-2" />
                        <div className="flex justify-between items-center">
                            <span className="text-[#8fb4ff]">COÛTANT</span>
                            <span data-testid="calc-cost" className="font-display font-bold text-lg">{formatCurrency(costTotal)}</span>
                        </div>
                        <div className="flex justify-between items-center text-[#4fd1c5]">
                            <span>MARGE</span>
                            <span data-testid="calc-margin">{formatCurrency(margin)} · {marginPct}%</span>
                        </div>
                        <div className="border-t border-[#2a3d5c] my-2" />
                        <div className="flex justify-between items-center">
                            <span className="text-[#ffd27f] font-semibold">PRIX VENDANT</span>
                            <span data-testid="calc-sell" className="font-display font-bold text-3xl text-[#ffd27f]">{formatCurrency(sellTotal)}</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

const Row = ({ l, v, sub }) => (
    <div className="flex justify-between items-baseline">
        <span className="text-[#c3d2ea]">{l}{sub && <span className="text-[#6b7f9e] text-xs ml-1">{sub}</span>}</span>
        <span>{v}</span>
    </div>
);

const Tile = ({ label, value }) => (
    <div className="bg-white p-4">
        <div className="tech-stamp text-[#4b5d7a] mb-1 truncate">{label}</div>
        <div className="font-display font-bold text-xl md:text-2xl">{value}</div>
    </div>
);
