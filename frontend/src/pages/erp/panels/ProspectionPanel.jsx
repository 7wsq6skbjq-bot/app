/* eslint-disable react-hooks/exhaustive-deps */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { RefreshCw, Search, Mail, Send, Trash2, Plus, Download, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";

const REGIONS = [
    { key: "montreal",  label: "Grand Montréal" },
    { key: "laval",     label: "Laval" },
    { key: "rive-sud",  label: "Rive-Sud" },
    { key: "rive-nord", label: "Rive-Nord" },
];

const STATUS_BADGE = {
    "nouveau":         "bg-[#eaf1fb] text-[#1d3557] border-[#9bb6d8]",
    "à contacter":     "bg-[#fff7e0] text-[#7a5a00] border-[#d4be7a]",
    "envoyé":          "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
    "ouvert":          "bg-[#e1f0fd] text-[#0a4a8a] border-[#7bb0e2]",
    "cliqué":          "bg-[#e0f7e8] text-[#0a6b3a] border-[#7bd1a0]",
    "répondu":         "bg-[#fce4ec] text-[#88003a] border-[#d99ab2]",
    "client":          "bg-[#0c182b] text-white border-[#0c182b]",
    "non-intéressé":   "bg-[#f4f4f5] text-[#52525b] border-[#c5c5cc]",
    "invalide":        "bg-[#fbe8e8] text-[#8a1f1f] border-[#e8a5a5]",
};

const SUB_TABS = [
    { key: "prospects", label: "Vitreries" },
    { key: "campaigns", label: "Campagnes" },
    { key: "send",      label: "Envoi" },
    { key: "outbox",    label: "Historique" },
];

export const ProspectionPanel = () => {
    const [sub, setSub] = useState("prospects");
    return (
        <div data-testid="prospection-panel" className="space-y-6">
            <div>
                <h1 className="font-display font-black text-3xl text-[#0c182b] uppercase tracking-tight">
                    Prospection · Vitreries
                </h1>
                <p className="text-[#4b5d7a] mt-1 text-sm">
                    Scrapez les vitreries du Grand Montréal et envoyez-leur une offre de sous-traitance quincaillerie.
                </p>
            </div>

            <div className="flex items-center gap-2 border-b border-[#dde5f0] overflow-x-auto">
                {SUB_TABS.map((t) => (
                    <button
                        key={t.key}
                        data-testid={`prospection-sub-${t.key}`}
                        onClick={() => setSub(t.key)}
                        className={`tech-stamp px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap ${
                            sub === t.key
                                ? "border-[#0c182b] text-[#0c182b] font-bold"
                                : "border-transparent text-[#4b5d7a] hover:text-[#0c182b]"
                        }`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {sub === "prospects" && <ProspectsTab />}
            {sub === "campaigns" && <CampaignsTab />}
            {sub === "send"      && <SendTab />}
            {sub === "outbox"    && <OutboxTab />}
        </div>
    );
};

// ============================================================================
// Stats banner
// ============================================================================
const StatsBanner = ({ stats }) => {
    if (!stats) return null;
    const pct = stats.hourly_limit ? Math.round((stats.sent_last_hour / stats.hourly_limit) * 100) : 0;
    return (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Tile testid="stat-total" label="Prospects" value={stats.total_prospects} />
            <Tile testid="stat-with-email" label="Avec courriel" value={stats.with_email} />
            <Tile testid="stat-sent-today" label="Envoyés (24h)" value={stats.sent_today} />
            <Tile testid="stat-sent-hour" label="Envoyés (1h)" value={`${stats.sent_last_hour}/${stats.hourly_limit}`} hint={`${pct}% du quota`} />
            <Tile testid="stat-remaining" label="Restant cette heure" value={stats.remaining_this_hour} />
        </div>
    );
};

const Tile = ({ label, value, hint, testid }) => (
    <div data-testid={testid} className="border border-[#dde5f0] bg-white p-3">
        <div className="tech-stamp text-[#4b5d7a]">{label}</div>
        <div className="font-display font-black text-2xl text-[#0c182b]">{value}</div>
        {hint && <div className="text-xs text-[#71717a] mt-1">{hint}</div>}
    </div>
);

// ============================================================================
// PROSPECTS TAB
// ============================================================================
const ProspectsTab = () => {
    const { http } = useAuth();
    const [prospects, setProspects] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filterRegion, setFilterRegion] = useState("");
    const [filterStatus, setFilterStatus] = useState("");
    const [searchQ, setSearchQ] = useState("");
    const [scrapeOpen, setScrapeOpen] = useState(false);
    const [scrapeRegion, setScrapeRegion] = useState("montreal");
    const [scrapeMax, setScrapeMax] = useState(30);
    const [scrapeLoading, setScrapeLoading] = useState(false);
    const [scrapeResult, setScrapeResult] = useState(null);
    const [editOpen, setEditOpen] = useState(false);
    const [editing, setEditing] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterRegion) params.set("region", filterRegion);
            if (filterStatus) params.set("status", filterStatus);
            const [{ data: list }, { data: s }] = await Promise.all([
                http.get(`/admin/prospection/prospects?${params}`),
                http.get("/admin/prospection/stats"),
            ]);
            setProspects(list || []);
            setStats(s);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [filterRegion, filterStatus]);

    useEffect(() => { load(); }, [load]);

    const filtered = useMemo(() => {
        const q = searchQ.trim().toLowerCase();
        if (!q) return prospects;
        return prospects.filter((p) =>
            (p.name || "").toLowerCase().includes(q) ||
            (p.city || "").toLowerCase().includes(q) ||
            (p.email || "").toLowerCase().includes(q),
        );
    }, [prospects, searchQ]);

    const runScrape = async () => {
        setScrapeLoading(true);
        setScrapeResult(null);
        try {
            const { data } = await http.post("/admin/prospection/prospects/scrape", {
                query: "vitrerie",
                location: scrapeRegion,
                max_results: scrapeMax,
            });
            setScrapeResult(data);
            await load();
        } catch (e) {
            setScrapeResult({ error: e?.response?.data?.detail || "Erreur scrape" });
        } finally {
            setScrapeLoading(false);
        }
    };

    const openEdit = (p) => { setEditing({ ...p }); setEditOpen(true); };
    const openNew = () => {
        setEditing({ name: "", contact_name: "", email: "", phone: "", website: "", city: "", region: "montreal", notes: "", status: "nouveau" });
        setEditOpen(true);
    };

    const saveProspect = async () => {
        try {
            const payload = { ...editing };
            delete payload.id; delete payload.created_at; delete payload.send_count;
            delete payload.last_sent_at; delete payload.last_opened_at; delete payload.last_clicked_at;
            delete payload.unsubscribed;
            // Empty strings → null to keep validators happy
            ["email", "phone", "website", "address", "city", "region", "notes", "contact_name"].forEach((k) => {
                if (payload[k] === "") payload[k] = null;
            });
            if (editing.id) {
                await http.put(`/admin/prospection/prospects/${editing.id}`, payload);
            } else {
                await http.post("/admin/prospection/prospects", payload);
            }
            setEditOpen(false);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur sauvegarde");
        }
    };

    const deleteProspect = async (id) => {
        if (!window.confirm("Supprimer ce prospect ?")) return;
        await http.delete(`/admin/prospection/prospects/${id}`);
        await load();
    };

    return (
        <div className="space-y-4">
            <StatsBanner stats={stats} />

            <div className="flex flex-wrap items-center gap-2">
                <button
                    data-testid="btn-scrape-open"
                    onClick={() => setScrapeOpen(true)}
                    className="px-4 py-2 bg-[#0c182b] text-white tech-stamp hover:bg-[#1e3457] flex items-center gap-2"
                >
                    <Download className="w-4 h-4" /> Scraper des vitreries
                </button>
                <button
                    data-testid="btn-new-prospect"
                    onClick={openNew}
                    className="px-4 py-2 border border-[#0c182b] text-[#0c182b] tech-stamp hover:bg-[#f3f6fb] flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" /> Ajouter manuellement
                </button>
                <button
                    onClick={load}
                    className="px-3 py-2 border border-[#dde5f0] text-[#4b5d7a] tech-stamp hover:bg-[#f3f6fb] flex items-center gap-2"
                >
                    <RefreshCw className="w-4 h-4" /> Rafraîchir
                </button>
            </div>

            <div className="flex flex-wrap items-center gap-3 p-3 border border-[#dde5f0] bg-white">
                <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                    <Search className="w-4 h-4 text-[#4b5d7a]" />
                    <input
                        data-testid="prospects-search"
                        value={searchQ}
                        onChange={(e) => setSearchQ(e.target.value)}
                        placeholder="Rechercher par nom, ville, courriel…"
                        className="flex-1 outline-none text-sm"
                    />
                </div>
                <select
                    data-testid="filter-region"
                    value={filterRegion}
                    onChange={(e) => setFilterRegion(e.target.value)}
                    className={inputClass.replace("w-full", "w-auto")}
                >
                    <option value="">Toutes régions</option>
                    {REGIONS.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
                </select>
                <select
                    data-testid="filter-status"
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className={inputClass.replace("w-full", "w-auto")}
                >
                    <option value="">Tous statuts</option>
                    {Object.keys(STATUS_BADGE).map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
            </div>

            <div className="border border-[#dde5f0] bg-white overflow-x-auto">
                <table className="w-full text-sm">
                    <thead className="bg-[#f3f6fb] tech-stamp text-[#4b5d7a]">
                        <tr>
                            <th className="text-left px-3 py-2.5">Nom</th>
                            <th className="text-left px-3 py-2.5">Ville</th>
                            <th className="text-left px-3 py-2.5">Courriel</th>
                            <th className="text-left px-3 py-2.5">Téléphone</th>
                            <th className="text-left px-3 py-2.5">Statut</th>
                            <th className="text-left px-3 py-2.5">Envois</th>
                            <th className="px-3 py-2.5 w-24"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && (
                            <tr><td colSpan={7} className="px-3 py-6 text-center text-[#71717a]">Chargement…</td></tr>
                        )}
                        {!loading && filtered.length === 0 && (
                            <tr><td colSpan={7} className="px-3 py-6 text-center text-[#71717a]">Aucun prospect. Lancez un scrape pour en charger.</td></tr>
                        )}
                        {filtered.map((p) => (
                            <tr key={p.id} data-testid={`prospect-row-${p.id}`} className="border-t border-[#eef2f7] hover:bg-[#f8fafc]">
                                <td className="px-3 py-2.5">
                                    <button onClick={() => openEdit(p)} className="font-semibold text-[#0c182b] hover:underline text-left">
                                        {p.name}
                                    </button>
                                    {p.website && (
                                        <a href={p.website.startsWith("http") ? p.website : `https://${p.website}`} target="_blank" rel="noreferrer" className="block text-xs text-[#4b5d7a] hover:text-[#0c182b] truncate max-w-[240px]">{p.website}</a>
                                    )}
                                </td>
                                <td className="px-3 py-2.5">{p.city || "—"}</td>
                                <td className="px-3 py-2.5">
                                    {p.email ? (
                                        <a href={`mailto:${p.email}`} className="text-[#1d4ed8] hover:underline">{p.email}</a>
                                    ) : <span className="text-[#a1a1aa]">—</span>}
                                </td>
                                <td className="px-3 py-2.5">{p.phone || "—"}</td>
                                <td className="px-3 py-2.5">
                                    <span className={`inline-block tech-stamp px-2 py-0.5 border text-[10px] ${STATUS_BADGE[p.status] || ""}`}>
                                        {p.status}
                                    </span>
                                </td>
                                <td className="px-3 py-2.5">{p.send_count || 0}</td>
                                <td className="px-3 py-2.5 text-right">
                                    <button onClick={() => deleteProspect(p.id)} className="text-[#8a1f1f] hover:text-red-700 p-1" aria-label="Supprimer">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Scrape modal */}
            <Modal
                open={scrapeOpen}
                onClose={() => { setScrapeOpen(false); setScrapeResult(null); }}
                title="Scraper vitreries (OpenStreetMap)"
                testId="scrape-modal"
                footer={
                    <>
                        <button onClick={() => setScrapeOpen(false)} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Fermer</button>
                        <button
                            data-testid="btn-run-scrape"
                            onClick={runScrape}
                            disabled={scrapeLoading}
                            className="px-4 py-2 bg-[#0c182b] text-white tech-stamp disabled:opacity-50"
                        >
                            {scrapeLoading ? "Scraping…" : "Lancer le scrape"}
                        </button>
                    </>
                }
            >
                <div className="space-y-4">
                    <p className="text-sm text-[#4b5d7a]">
                        Source : OpenStreetMap / Overpass — 100 % gratuit, sans clé API. Le scraper recherche les commerces tagués <code>shop=glaziery</code>, <code>craft=glaziery</code>, et les noms contenant « vitrerie » dans la région choisie.
                    </p>
                    <Field label="Région" required>
                        <select data-testid="scrape-region" value={scrapeRegion} onChange={(e) => setScrapeRegion(e.target.value)} className={inputClass}>
                            {REGIONS.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
                            <option value="tout">Toutes les régions</option>
                        </select>
                    </Field>
                    <Field label="Maximum de résultats">
                        <input type="number" min="1" max="60" data-testid="scrape-max" value={scrapeMax} onChange={(e) => setScrapeMax(Number(e.target.value))} className={inputClass} />
                    </Field>
                    {scrapeResult && (
                        <div data-testid="scrape-result" className={`p-3 border ${scrapeResult.error ? "border-red-300 bg-red-50 text-red-800" : "border-green-300 bg-green-50 text-green-800"} text-sm`}>
                            {scrapeResult.error ? (
                                <div><AlertTriangle className="w-4 h-4 inline mr-1" /> {scrapeResult.error}</div>
                            ) : (
                                <div>
                                    <CheckCircle2 className="w-4 h-4 inline mr-1" />
                                    <b>{scrapeResult.new}</b> nouveau(x) prospect(s) ajouté(s) · {scrapeResult.skipped_duplicates} doublon(s) ignoré(s) · {scrapeResult.scraped} trouvé(s) sur OSM.
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </Modal>

            {/* Edit/new modal */}
            {editing && (
                <Modal
                    open={editOpen}
                    onClose={() => setEditOpen(false)}
                    title={editing.id ? "Modifier le prospect" : "Nouveau prospect"}
                    testId="prospect-modal"
                    footer={
                        <>
                            <button onClick={() => setEditOpen(false)} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                            <button
                                data-testid="prospect-save"
                                onClick={saveProspect}
                                className="px-4 py-2 bg-[#0c182b] text-white tech-stamp"
                            >
                                Enregistrer
                            </button>
                        </>
                    }
                >
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Nom" required className="col-span-2">
                            <input data-testid="prospect-name" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Personne contact">
                            <input value={editing.contact_name || ""} onChange={(e) => setEditing({ ...editing, contact_name: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Courriel">
                            <input data-testid="prospect-email" type="email" value={editing.email || ""} onChange={(e) => setEditing({ ...editing, email: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Téléphone">
                            <input value={editing.phone || ""} onChange={(e) => setEditing({ ...editing, phone: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Site web">
                            <input value={editing.website || ""} onChange={(e) => setEditing({ ...editing, website: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Ville">
                            <input value={editing.city || ""} onChange={(e) => setEditing({ ...editing, city: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Région">
                            <select value={editing.region || "montreal"} onChange={(e) => setEditing({ ...editing, region: e.target.value })} className={inputClass}>
                                {REGIONS.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
                            </select>
                        </Field>
                        <Field label="Statut" className="col-span-2">
                            <select value={editing.status || "nouveau"} onChange={(e) => setEditing({ ...editing, status: e.target.value })} className={inputClass}>
                                {Object.keys(STATUS_BADGE).map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </Field>
                        <Field label="Notes" className="col-span-2">
                            <textarea rows={3} value={editing.notes || ""} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} className={inputClass} />
                        </Field>
                    </div>
                </Modal>
            )}
        </div>
    );
};

// ============================================================================
// CAMPAIGNS TAB
// ============================================================================
const CampaignsTab = () => {
    const { http } = useAuth();
    const [campaigns, setCampaigns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(null);
    const [open, setOpen] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await http.get("/admin/prospection/campaigns");
            setCampaigns(data || []);
        } finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const newFromTemplate = async () => {
        const { data } = await http.get("/admin/prospection/campaigns/default");
        setEditing({
            name: "Sous-traitance vitreries — Grand Montréal",
            subject: data.subject,
            from_name: data.from_name,
            from_email: data.from_email,
            body_html: data.body_html,
        });
        setOpen(true);
    };

    const openEdit = (c) => { setEditing({ ...c }); setOpen(true); };

    const save = async () => {
        try {
            const payload = {
                name: editing.name,
                subject: editing.subject,
                from_name: editing.from_name,
                from_email: editing.from_email,
                body_html: editing.body_html,
            };
            if (editing.id) {
                await http.put(`/admin/prospection/campaigns/${editing.id}`, payload);
            } else {
                await http.post("/admin/prospection/campaigns", payload);
            }
            setOpen(false);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur");
        }
    };

    const remove = async (id) => {
        if (!window.confirm("Supprimer cette campagne ?")) return;
        await http.delete(`/admin/prospection/campaigns/${id}`);
        await load();
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <button
                    data-testid="btn-new-campaign-template"
                    onClick={newFromTemplate}
                    className="px-4 py-2 bg-[#0c182b] text-white tech-stamp hover:bg-[#1e3457] flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" /> Nouvelle campagne (modèle FR)
                </button>
                <button onClick={load} className="px-3 py-2 border border-[#dde5f0] text-[#4b5d7a] tech-stamp hover:bg-[#f3f6fb] flex items-center gap-2">
                    <RefreshCw className="w-4 h-4" /> Rafraîchir
                </button>
            </div>

            <div className="border border-[#dde5f0] bg-white">
                <table className="w-full text-sm">
                    <thead className="bg-[#f3f6fb] tech-stamp text-[#4b5d7a]">
                        <tr>
                            <th className="text-left px-3 py-2.5">Nom</th>
                            <th className="text-left px-3 py-2.5">Objet</th>
                            <th className="text-left px-3 py-2.5">Expéditeur</th>
                            <th className="text-left px-3 py-2.5">Modifiée le</th>
                            <th className="px-3 py-2.5 w-24"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && <tr><td colSpan={5} className="px-3 py-6 text-center text-[#71717a]">Chargement…</td></tr>}
                        {!loading && campaigns.length === 0 && (
                            <tr><td colSpan={5} className="px-3 py-6 text-center text-[#71717a]">Aucune campagne. Cliquez « Nouvelle campagne (modèle FR) ».</td></tr>
                        )}
                        {campaigns.map((c) => (
                            <tr key={c.id} className="border-t border-[#eef2f7]">
                                <td className="px-3 py-2.5">
                                    <button onClick={() => openEdit(c)} className="font-semibold text-[#0c182b] hover:underline text-left">{c.name}</button>
                                </td>
                                <td className="px-3 py-2.5">{c.subject}</td>
                                <td className="px-3 py-2.5 text-xs text-[#4b5d7a]">{c.from_name}<br/>{c.from_email}</td>
                                <td className="px-3 py-2.5 text-xs text-[#4b5d7a]">{new Date(c.updated_at).toLocaleDateString("fr-CA")}</td>
                                <td className="px-3 py-2.5 text-right">
                                    <button onClick={() => remove(c.id)} className="text-[#8a1f1f] p-1" aria-label="Supprimer">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {editing && (
                <Modal
                    open={open}
                    onClose={() => setOpen(false)}
                    title={editing.id ? "Modifier la campagne" : "Nouvelle campagne"}
                    testId="campaign-modal"
                    wide
                    footer={
                        <>
                            <button onClick={() => setOpen(false)} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                            <button data-testid="campaign-save" onClick={save} className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">Enregistrer</button>
                        </>
                    }
                >
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Nom interne" required className="col-span-2">
                            <input data-testid="campaign-name" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Objet" required className="col-span-2">
                            <input data-testid="campaign-subject" value={editing.subject} onChange={(e) => setEditing({ ...editing, subject: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Nom expéditeur">
                            <input value={editing.from_name} onChange={(e) => setEditing({ ...editing, from_name: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Courriel expéditeur">
                            <input value={editing.from_email} onChange={(e) => setEditing({ ...editing, from_email: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Corps HTML (variables: {{Nom_Vitrerie}}, {{contact_name}}, {{city}})" className="col-span-2">
                            <textarea
                                data-testid="campaign-body"
                                rows={14}
                                value={editing.body_html}
                                onChange={(e) => setEditing({ ...editing, body_html: e.target.value })}
                                className={`${inputClass} font-mono text-xs`}
                            />
                        </Field>
                        <div className="col-span-2 border border-[#dde5f0] bg-[#f3f6fb] p-3">
                            <div className="tech-stamp text-[#4b5d7a] mb-2">Aperçu</div>
                            <div className="bg-white border border-[#dde5f0] p-3 max-h-[300px] overflow-y-auto" dangerouslySetInnerHTML={{ __html: editing.body_html }} />
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
};

// ============================================================================
// SEND TAB
// ============================================================================
const SendTab = () => {
    const { http } = useAuth();
    const [campaigns, setCampaigns] = useState([]);
    const [prospects, setProspects] = useState([]);
    const [stats, setStats] = useState(null);
    const [campaignId, setCampaignId] = useState("");
    const [selected, setSelected] = useState(new Set());
    const [confirm, setConfirm] = useState(false);
    const [busy, setBusy] = useState(false);
    const [result, setResult] = useState(null);
    const [testOpen, setTestOpen] = useState(false);
    const [testEmail, setTestEmail] = useState("portech.infos@gmail.com");
    const [testBusy, setTestBusy] = useState(false);
    const [testResult, setTestResult] = useState(null);

    const load = useCallback(async () => {
        const [{ data: cs }, { data: ps }, { data: s }] = await Promise.all([
            http.get("/admin/prospection/campaigns"),
            http.get("/admin/prospection/prospects?has_email=true"),
            http.get("/admin/prospection/stats"),
        ]);
        setCampaigns(cs || []);
        setProspects(ps || []);
        setStats(s);
        if (!campaignId && cs?.length) setCampaignId(cs[0].id);
    }, [campaignId]);

    useEffect(() => { load(); }, []);

    const toggle = (id) => {
        const next = new Set(selected);
        if (next.has(id)) next.delete(id); else next.add(id);
        setSelected(next);
    };
    const selectAll = () => setSelected(new Set(prospects.filter((p) => p.status !== "envoyé" && p.status !== "client" && p.status !== "non-intéressé").map((p) => p.id)));
    const clearAll = () => setSelected(new Set());

    const sendNow = async () => {
        if (!campaignId) { alert("Sélectionnez une campagne"); return; }
        if (selected.size === 0) { alert("Sélectionnez au moins un prospect"); return; }
        if (!confirm) { alert("Cochez « Je confirme l'envoi »"); return; }
        setBusy(true); setResult(null);
        try {
            const { data } = await http.post("/admin/prospection/campaigns/send", {
                campaign_id: campaignId,
                prospect_ids: Array.from(selected),
                confirm: true,
            });
            setResult(data);
            setConfirm(false);
            setSelected(new Set());
            await load();
        } catch (e) {
            setResult({ error: e?.response?.data?.detail || "Erreur" });
        } finally {
            setBusy(false);
        }
    };

    const sendTest = async () => {
        if (!campaignId) return;
        setTestBusy(true); setTestResult(null);
        try {
            const { data } = await http.post("/admin/prospection/campaigns/send", {
                campaign_id: campaignId,
                prospect_ids: ["test"],
                confirm: true,
                test_only: true,
                test_email: testEmail,
            });
            setTestResult(data);
        } catch (e) {
            setTestResult({ error: e?.response?.data?.detail || "Erreur" });
        } finally {
            setTestBusy(false);
        }
    };

    const selectedCount = selected.size;
    const quotaRemaining = stats?.remaining_this_hour ?? 0;
    const willTruncate = selectedCount > quotaRemaining;

    return (
        <div className="space-y-4">
            <StatsBanner stats={stats} />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border border-[#dde5f0] bg-white p-4 space-y-3">
                    <h3 className="font-display font-bold uppercase text-sm tracking-tight">1 · Campagne</h3>
                    <select
                        data-testid="send-campaign-select"
                        value={campaignId}
                        onChange={(e) => setCampaignId(e.target.value)}
                        className={inputClass}
                    >
                        <option value="">— Choisir —</option>
                        {campaigns.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                    {campaignId && campaigns.find((c) => c.id === campaignId) && (
                        <div className="text-xs text-[#4b5d7a] bg-[#f3f6fb] p-2 border border-[#dde5f0]">
                            <b>De :</b> {campaigns.find((c) => c.id === campaignId).from_name} &lt;{campaigns.find((c) => c.id === campaignId).from_email}&gt;<br/>
                            <b>Objet :</b> {campaigns.find((c) => c.id === campaignId).subject}
                        </div>
                    )}
                    <button
                        data-testid="btn-send-test"
                        onClick={() => setTestOpen(true)}
                        disabled={!campaignId}
                        className="px-3 py-1.5 border border-[#0c182b] text-[#0c182b] tech-stamp hover:bg-[#f3f6fb] disabled:opacity-50 text-xs flex items-center gap-1"
                    >
                        <Mail className="w-3 h-3" /> Envoyer un test
                    </button>
                </div>

                <div className="border border-[#dde5f0] bg-white p-4 space-y-3">
                    <h3 className="font-display font-bold uppercase text-sm tracking-tight">2 · Confirmation</h3>
                    <div className="text-sm text-[#4b5d7a]">
                        <b>{selectedCount}</b> prospect(s) sélectionné(s)<br/>
                        Quota restant cette heure : <b>{quotaRemaining}</b> / {stats?.hourly_limit || 50}
                        {willTruncate && selectedCount > 0 && (
                            <div className="mt-2 p-2 bg-orange-50 border border-orange-300 text-orange-800 text-xs">
                                <AlertTriangle className="w-3 h-3 inline mr-1" />
                                La sélection dépasse le quota — seuls les {quotaRemaining} premiers seront envoyés maintenant.
                            </div>
                        )}
                    </div>
                    <label className="flex items-start gap-2 cursor-pointer">
                        <input
                            data-testid="send-confirm-checkbox"
                            type="checkbox"
                            checked={confirm}
                            onChange={(e) => setConfirm(e.target.checked)}
                            className="mt-1"
                        />
                        <span className="text-sm">Je confirme l'envoi du courriel commercial aux prospects sélectionnés. Je comprends que cet envoi est définitif.</span>
                    </label>
                    <button
                        data-testid="btn-send-now"
                        onClick={sendNow}
                        disabled={busy || !confirm || selectedCount === 0 || !campaignId}
                        className="w-full px-4 py-3 bg-[#8a1f1f] text-white tech-stamp hover:bg-red-800 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        <Send className="w-4 h-4" /> {busy ? "Envoi en cours…" : `Envoyer maintenant (${Math.min(selectedCount, quotaRemaining)})`}
                    </button>
                    {result && (
                        <div data-testid="send-result" className={`p-3 border text-sm ${result.error ? "border-red-300 bg-red-50 text-red-800" : "border-green-300 bg-green-50 text-green-800"}`}>
                            {result.error ? (
                                <><AlertTriangle className="w-4 h-4 inline mr-1" /> {result.error}</>
                            ) : (
                                <><CheckCircle2 className="w-4 h-4 inline mr-1" /> Envoyés : <b>{result.sent}</b> · Échecs : {result.failed} · Sans courriel : {result.skipped_no_email} · Hors quota : {result.skipped_over_quota}</>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div>
                <div className="flex items-center justify-between mb-2">
                    <h3 className="font-display font-bold uppercase text-sm tracking-tight">3 · Sélection des destinataires (avec courriel uniquement)</h3>
                    <div className="flex items-center gap-2">
                        <button data-testid="btn-select-all" onClick={selectAll} className="px-3 py-1 border border-[#dde5f0] text-[#4b5d7a] tech-stamp text-xs">Tout sélectionner</button>
                        <button data-testid="btn-clear-selection" onClick={clearAll} className="px-3 py-1 border border-[#dde5f0] text-[#4b5d7a] tech-stamp text-xs">Effacer</button>
                    </div>
                </div>
                <div className="border border-[#dde5f0] bg-white max-h-[450px] overflow-y-auto">
                    {prospects.length === 0 ? (
                        <div className="p-6 text-center text-[#71717a]">Aucun prospect avec courriel. Lancez un scrape d'abord.</div>
                    ) : (
                        <table className="w-full text-sm">
                            <thead className="bg-[#f3f6fb] tech-stamp text-[#4b5d7a] sticky top-0">
                                <tr>
                                    <th className="w-8"></th>
                                    <th className="text-left px-3 py-2">Nom</th>
                                    <th className="text-left px-3 py-2">Ville</th>
                                    <th className="text-left px-3 py-2">Courriel</th>
                                    <th className="text-left px-3 py-2">Statut</th>
                                    <th className="text-left px-3 py-2">Envois</th>
                                </tr>
                            </thead>
                            <tbody>
                                {prospects.map((p) => (
                                    <tr key={p.id} className="border-t border-[#eef2f7] hover:bg-[#f8fafc]">
                                        <td className="px-2">
                                            <input
                                                type="checkbox"
                                                data-testid={`select-${p.id}`}
                                                checked={selected.has(p.id)}
                                                onChange={() => toggle(p.id)}
                                            />
                                        </td>
                                        <td className="px-3 py-2 font-semibold text-[#0c182b]">{p.name}</td>
                                        <td className="px-3 py-2">{p.city || "—"}</td>
                                        <td className="px-3 py-2 text-[#1d4ed8]">{p.email}</td>
                                        <td className="px-3 py-2">
                                            <span className={`inline-block tech-stamp px-2 py-0.5 border text-[10px] ${STATUS_BADGE[p.status] || ""}`}>{p.status}</span>
                                        </td>
                                        <td className="px-3 py-2">{p.send_count || 0}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            <Modal
                open={testOpen}
                onClose={() => { setTestOpen(false); setTestResult(null); }}
                title="Envoyer un test"
                testId="test-modal"
                footer={
                    <>
                        <button onClick={() => setTestOpen(false)} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Fermer</button>
                        <button
                            data-testid="btn-run-test"
                            onClick={sendTest}
                            disabled={testBusy}
                            className="px-4 py-2 bg-[#0c182b] text-white tech-stamp"
                        >
                            {testBusy ? "Envoi…" : "Envoyer"}
                        </button>
                    </>
                }
            >
                <div className="space-y-3">
                    <p className="text-sm text-[#4b5d7a]">Envoyer le courriel à une adresse de votre choix pour valider le rendu. Aucun prospect ne sera affecté.</p>
                    <Field label="Adresse de test" required>
                        <input type="email" value={testEmail} onChange={(e) => setTestEmail(e.target.value)} className={inputClass} />
                    </Field>
                    {testResult && (
                        <div className={`p-3 border text-sm ${testResult.error || !testResult.sent ? "border-red-300 bg-red-50 text-red-800" : "border-green-300 bg-green-50 text-green-800"}`}>
                            {testResult.error || !testResult.sent ? (
                                <>Erreur : {testResult.error || "Échec d'envoi"}</>
                            ) : (
                                <>Envoyé à <b>{testResult.to}</b> (Resend id: <code>{testResult.resend_id}</code>)</>
                            )}
                        </div>
                    )}
                </div>
            </Modal>
        </div>
    );
};

// ============================================================================
// OUTBOX TAB
// ============================================================================
const OutboxTab = () => {
    const { http } = useAuth();
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await http.get("/admin/prospection/outbox");
            setRows(data || []);
        } finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    return (
        <div className="space-y-3">
            <button onClick={load} className="px-3 py-2 border border-[#dde5f0] text-[#4b5d7a] tech-stamp hover:bg-[#f3f6fb] flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> Rafraîchir
            </button>
            <div className="border border-[#dde5f0] bg-white overflow-x-auto">
                <table className="w-full text-sm">
                    <thead className="bg-[#f3f6fb] tech-stamp text-[#4b5d7a]">
                        <tr>
                            <th className="text-left px-3 py-2.5">Date</th>
                            <th className="text-left px-3 py-2.5">Destinataire</th>
                            <th className="text-left px-3 py-2.5">Statut</th>
                            <th className="text-left px-3 py-2.5">ID Resend</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && <tr><td colSpan={4} className="px-3 py-6 text-center text-[#71717a]">Chargement…</td></tr>}
                        {!loading && rows.length === 0 && (
                            <tr><td colSpan={4} className="px-3 py-6 text-center text-[#71717a]">Aucun envoi pour le moment.</td></tr>
                        )}
                        {rows.map((r) => (
                            <tr key={r.id} className="border-t border-[#eef2f7]">
                                <td className="px-3 py-2.5 text-xs">{new Date(r.sent_at).toLocaleString("fr-CA")}</td>
                                <td className="px-3 py-2.5">{r.to_email}</td>
                                <td className="px-3 py-2.5">
                                    <span className={`tech-stamp px-2 py-0.5 border text-[10px] ${r.status === "sent" ? "bg-green-50 text-green-800 border-green-300" : "bg-red-50 text-red-800 border-red-300"}`}>
                                        {r.status}
                                    </span>
                                </td>
                                <td className="px-3 py-2.5 text-xs text-[#4b5d7a]">{r.resend_id || "—"}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
