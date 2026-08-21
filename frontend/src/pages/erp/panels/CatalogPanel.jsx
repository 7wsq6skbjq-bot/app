import { useCallback, useEffect, useMemo, useState } from "react";
import {
    RefreshCw, Save, Trash2, Search, Upload, DollarSign, Loader2, Check, X,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { inputClass } from "../components/Modal";

const money = (v) => (Number(v) || 0).toLocaleString("fr-CA", { style: "currency", currency: "CAD" });

// Parse pasted rows: TAB-separated preferred, else 2+ spaces. Last numeric cell = USD price.
const parsePasted = (text) =>
    text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).map((line) => {
        const cells = (line.includes("\t") ? line.split("\t") : line.split(/\s{2,}/)).map((c) => c.trim()).filter(Boolean);
        if (cells.length === 0) return null;
        const priceStr = cells[cells.length - 1].replace(/[^0-9.,]/g, "").replace(",", ".");
        const usd = parseFloat(priceStr);
        if (Number.isNaN(usd)) return null;
        const part_number = cells[0];
        const description = cells.slice(1, cells.length - 1).join(" ").trim();
        return { part_number, description, list_price_usd: usd };
    }).filter(Boolean);

export const CatalogPanel = () => {
    const { http } = useAuth();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [q, setQ] = useState("");
    const [notice, setNotice] = useState("");
    const [error, setError] = useState("");

    const [rate, setRate] = useState("");
    const [rateUpdated, setRateUpdated] = useState(null);
    const [rateSaving, setRateSaving] = useState(false);

    const [paste, setPaste] = useState("");
    const [preview, setPreview] = useState(null); // import dry-run result
    const [importing, setImporting] = useState(false);

    const [edit, setEdit] = useState({}); // id -> {cost, price}

    const flash = (m) => { setNotice(m); setTimeout(() => setNotice(""), 3500); };

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [cat, rt] = await Promise.all([
                http.get("/admin/production-hardware"),
                http.get("/admin/settings/exchange-rate"),
            ]);
            setItems(cat.data);
            setRate(String(rt.data.usd_cad));
            setRateUpdated(rt.data.updated_at);
        } catch { setError("Chargement échoué."); }
        finally { setLoading(false); }
    }, [http]);
    useEffect(() => { load(); }, [load]);

    const saveRate = async () => {
        const v = parseFloat(rate);
        if (!v || v <= 0) { setError("Taux invalide."); return; }
        setRateSaving(true);
        try {
            const { data } = await http.put("/admin/settings/exchange-rate", { usd_cad: v });
            setRateUpdated(data.updated_at);
            flash(`Taux USD→CAD enregistré : ${v}`);
        } catch { setError("Enregistrement du taux échoué."); }
        finally { setRateSaving(false); }
    };

    const runPreview = async () => {
        const rows = parsePasted(paste);
        if (rows.length === 0) { setError("Aucune ligne détectée. Format attendu : Nº pièce [tab] description [tab] prix USD."); return; }
        setImporting(true); setError("");
        try {
            const { data } = await http.post("/admin/production-hardware/import", { rows, dry_run: true });
            setPreview(data);
        } catch { setError("Aperçu de l'import échoué."); }
        finally { setImporting(false); }
    };
    const commitImport = async () => {
        const rows = parsePasted(paste);
        setImporting(true);
        try {
            const { data } = await http.post("/admin/production-hardware/import", { rows, dry_run: false });
            flash(`Import terminé : ${data.created} créé(s), ${data.updated} mis à jour.`);
            setPreview(null); setPaste("");
            load();
        } catch { setError("Import échoué."); }
        finally { setImporting(false); }
    };

    const saveItem = async (it) => {
        const patch = edit[it.id] || {};
        try {
            const { data } = await http.put(`/admin/production-hardware/${it.id}`, {
                name: it.name, part_number: it.part_number, category: it.category,
                cost: Number(patch.cost ?? it.cost) || 0,
                price: Number(patch.price ?? it.price) || 0,
            });
            setItems((prev) => prev.map((x) => (x.id === it.id ? data : x)));
            setEdit((e) => { const n = { ...e }; delete n[it.id]; return n; });
            flash("Item enregistré.");
        } catch { setError("Enregistrement échoué."); }
    };
    const delItem = async (it) => {
        if (!window.confirm(`Supprimer « ${it.name || it.part_number} » ?`)) return;
        await http.delete(`/admin/production-hardware/${it.id}`);
        setItems((prev) => prev.filter((x) => x.id !== it.id));
    };

    const filtered = useMemo(() => {
        const s = q.trim().toLowerCase();
        if (!s) return items;
        return items.filter((it) => `${it.name} ${it.part_number} ${it.category}`.toLowerCase().includes(s));
    }, [items, q]);

    return (
        <div data-testid="catalog-panel" className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 className="font-display font-bold uppercase text-2xl tracking-tight">Catalogue quincaillerie</h2>
                    <p className="text-sm text-[#4b5d7a]">Prix coûtants (CAD) et prix vendants. Import de listes de prix fournisseurs (USD → CAD).</p>
                </div>
                <button data-testid="catalog-refresh" onClick={load} className="tech-stamp px-3 py-2 border border-[#dde5f0] text-[#4b5d7a] hover:bg-white flex items-center gap-1"><RefreshCw className="w-4 h-4" /> Rafraîchir</button>
            </div>

            {notice && <div data-testid="catalog-notice" className="p-3 border border-green-300 bg-green-50 text-green-800 text-sm">{notice}</div>}
            {error && <div data-testid="catalog-error" className="p-3 border border-red-300 bg-red-50 text-red-800 text-sm flex justify-between"><span>{error}</span><button onClick={() => setError("")}><X className="w-4 h-4" /></button></div>}

            {/* Exchange rate */}
            <div className="bg-white border border-[#dde5f0] p-4">
                <div className="tech-stamp font-bold text-[#0c182b] mb-2 flex items-center gap-1"><DollarSign className="w-4 h-4" /> Taux de change USD → CAD</div>
                <div className="flex flex-wrap items-end gap-3">
                    <div>
                        <label className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider block mb-1">1 USD =</label>
                        <input data-testid="catalog-rate-input" type="number" step="0.01" className={`${inputClass} !w-32`} value={rate} onChange={(e) => setRate(e.target.value)} />
                    </div>
                    <button data-testid="catalog-rate-save" onClick={saveRate} disabled={rateSaving} className="tech-stamp px-4 py-2 bg-[#0c182b] text-white flex items-center gap-1">{rateSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Enregistrer</button>
                    {rateUpdated && <span className="text-xs text-[#9aa8bd]">Mis à jour : {new Date(rateUpdated).toLocaleString("fr-CA")}</span>}
                </div>
            </div>

            {/* Import */}
            <div className="bg-white border border-[#dde5f0] p-4">
                <div className="tech-stamp font-bold text-[#0c182b] mb-2 flex items-center gap-1"><Upload className="w-4 h-4" /> Importer une liste de prix (USD)</div>
                <p className="text-xs text-[#4b5d7a] mb-2">Colle des lignes : <b>Nº de pièce</b> [tabulation] <b>description</b> [tabulation] <b>prix USD</b>. Chaque prix est converti au taux ci-dessus puis majoré de 30 % (arrondi au 0,05 $). Les pièces existantes sont mises à jour par numéro.</p>
                <textarea data-testid="catalog-paste" rows={5} className={inputClass} placeholder={"4510-01\tDeadlatch 4510\t100.00\n3600CVR\t3600 CVR Exit Device\t250.33"} value={paste} onChange={(e) => setPaste(e.target.value)} />
                <div className="flex gap-2 mt-2">
                    <button data-testid="catalog-preview-btn" onClick={runPreview} disabled={importing} className="tech-stamp px-4 py-2 border border-[#dde5f0] hover:bg-[#f3f6fb] flex items-center gap-1">{importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Aperçu</button>
                    {preview && <button data-testid="catalog-commit-btn" onClick={commitImport} disabled={importing} className="tech-stamp px-4 py-2 bg-[#0c182b] text-white flex items-center gap-1"><Check className="w-4 h-4" /> Importer {preview.count} ligne(s)</button>}
                </div>

                {preview && (
                    <div className="mt-3 border border-[#dde5f0] max-h-72 overflow-auto" data-testid="catalog-preview-table">
                        <table className="w-full text-xs">
                            <thead className="bg-[#f3f6fb] text-[#4b5d7a] sticky top-0"><tr>
                                <th className="text-left px-2 py-1">Nº pièce</th><th className="text-left px-2 py-1">Description</th>
                                <th className="text-right px-2 py-1">USD</th><th className="text-right px-2 py-1">Coûtant CAD</th>
                                <th className="text-right px-2 py-1">Vendant CAD</th><th className="text-left px-2 py-1">Action</th>
                            </tr></thead>
                            <tbody>
                                {preview.items.map((r, i) => (
                                    <tr key={i} className="border-t border-[#eef2f8]">
                                        <td className="px-2 py-1 font-mono">{r.part_number}</td>
                                        <td className="px-2 py-1">{r.description}</td>
                                        <td className="px-2 py-1 text-right">${r.list_price_usd.toFixed(2)}</td>
                                        <td className="px-2 py-1 text-right">{money(r.cost_cad)}</td>
                                        <td className="px-2 py-1 text-right font-bold">{money(r.price_cad)}</td>
                                        <td className="px-2 py-1"><span className={r.action === "update" ? "text-amber-600" : "text-green-600"}>{r.action === "update" ? "MàJ" : "Nouveau"}</span></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Catalog table */}
            <div className="bg-white border border-[#dde5f0]">
                <div className="p-3 border-b border-[#dde5f0] flex items-center justify-between gap-3">
                    <div className="tech-stamp font-bold text-[#0c182b]">Articles ({filtered.length})</div>
                    <div className="relative"><Search className="w-4 h-4 absolute left-2 top-2.5 text-[#9aa8bd]" /><input data-testid="catalog-search" className={`${inputClass} !pl-8 !w-64`} placeholder="Rechercher…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
                </div>
                {loading ? (
                    <div className="py-16 text-center text-[#4b5d7a]"><Loader2 className="w-6 h-6 animate-spin inline" /></div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-[#f3f6fb] text-[#4b5d7a]"><tr>
                                <th className="text-left px-3 py-2">Nom</th><th className="text-left px-3 py-2">Nº pièce</th>
                                <th className="text-left px-3 py-2">Catégorie</th>
                                <th className="text-right px-3 py-2">Coûtant</th><th className="text-right px-3 py-2">Vendant</th><th className="px-3 py-2"></th>
                            </tr></thead>
                            <tbody>
                                {filtered.map((it) => {
                                    const e = edit[it.id];
                                    const dirty = !!e;
                                    return (
                                        <tr key={it.id} data-testid={`catalog-row-${it.id}`} className="border-t border-[#eef2f8]">
                                            <td className="px-3 py-2">{it.name || "—"}</td>
                                            <td className="px-3 py-2 font-mono text-xs">{it.part_number || "—"}</td>
                                            <td className="px-3 py-2 text-xs text-[#4b5d7a]">{it.category || "—"}</td>
                                            <td className="px-3 py-2 text-right"><input type="number" step="0.01" className={`${inputClass} !w-24 text-right`} value={e?.cost ?? it.cost} onChange={(ev) => setEdit((p) => ({ ...p, [it.id]: { ...p[it.id], cost: ev.target.value } }))} /></td>
                                            <td className="px-3 py-2 text-right"><input type="number" step="0.01" className={`${inputClass} !w-24 text-right`} value={e?.price ?? it.price} onChange={(ev) => setEdit((p) => ({ ...p, [it.id]: { ...p[it.id], price: ev.target.value } }))} /></td>
                                            <td className="px-3 py-2 whitespace-nowrap text-right">
                                                {dirty && <button data-testid={`catalog-save-${it.id}`} onClick={() => saveItem(it)} className="p-1.5 text-green-700 hover:bg-green-50 rounded"><Save className="w-4 h-4" /></button>}
                                                <button data-testid={`catalog-del-${it.id}`} onClick={() => delItem(it)} className="p-1.5 text-[#4b5d7a] hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                                            </td>
                                        </tr>
                                    );
                                })}
                                {filtered.length === 0 && <tr><td colSpan={6} className="text-center text-[#9aa8bd] py-10">Aucun article.</td></tr>}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CatalogPanel;
