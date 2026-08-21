import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    Plus, RefreshCw, Trash2, ChevronLeft, ChevronRight, X,
    Mail, Link2, AlertTriangle, Clock, FileText, Loader2, Save,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Modal, Field, inputClass } from "../components/Modal";
import { formatDate } from "../utils";

const STAGES = [
    { key: "a_approuver", label: "À approuver", color: "#64748b" },
    { key: "depot_recu", label: "Dépôt reçu (50%)", color: "#0ea5e9" },
    { key: "en_fabrication", label: "En fabrication", color: "#f59e0b" },
    { key: "pret", label: "Prêt", color: "#8b5cf6" },
    { key: "livre", label: "Livré", color: "#14b8a6" },
    { key: "facture", label: "Facturé", color: "#6366f1" },
    { key: "paye", label: "Payé", color: "#22c55e" },
];
const ALL_STAGES = [...STAGES, { key: "annule", label: "Annulé", color: "#ef4444" }];
const STAGE_LABEL = Object.fromEntries(ALL_STAGES.map((s) => [s.key, s.label]));
const DOC_TYPES = [
    { key: "quote", label: "Soumission" },
    { key: "production_plan", label: "Plan de production" },
    { key: "purchase_order", label: "Bon de commande" },
    { key: "mosquito_order", label: "Moustiquaires" },
    { key: "bol", label: "Connaissement" },
    { key: "invoice", label: "Facture" },
    { key: "payment_notice", label: "Avis de paiement" },
    { key: "expert_report", label: "Rapport d'expertise" },
];
const DOC_LABEL = Object.fromEntries(DOC_TYPES.map((d) => [d.key, d.label]));

const money = (v) =>
    (Number(v) || 0).toLocaleString("fr-CA", { style: "currency", currency: "CAD" });

const todayISO = () => new Date().toISOString().slice(0, 10);
const daysUntil = (d) => {
    if (!d) return null;
    const t = new Date(d + "T00:00:00");
    return Math.round((t - new Date(todayISO() + "T00:00:00")) / 86400000);
};

export const JobsPanel = () => {
    const { http } = useAuth();
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");

    const [createOpen, setCreateOpen] = useState(false);
    const [form, setForm] = useState({});
    const [saving, setSaving] = useState(false);

    const [quotePicker, setQuotePicker] = useState(null); // null | array
    const [detail, setDetail] = useState(null); // job object
    const [briefing, setBriefing] = useState(null); // preview data
    const [briefBusy, setBriefBusy] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const { data } = await http.get("/admin/jobs");
            setJobs(data);
        } catch (e) {
            setError("Impossible de charger les jobs.");
        } finally {
            setLoading(false);
        }
    }, [http]);

    useEffect(() => { load(); }, [load]);

    const flashTimer = useRef(null);
    const flash = (msg) => {
        setNotice(msg);
        if (flashTimer.current) clearTimeout(flashTimer.current);
        flashTimer.current = setTimeout(() => setNotice(""), 3500);
    };

    const grouped = useMemo(() => {
        const g = Object.fromEntries(STAGES.map((s) => [s.key, []]));
        jobs.forEach((j) => { if (g[j.stage]) g[j.stage].push(j); });
        return g;
    }, [jobs]);

    const cancelled = useMemo(() => jobs.filter((j) => j.stage === "annule"), [jobs]);

    // ── Create ──────────────────────────────
    const openCreate = () => {
        setForm({ title: "", client_name: "", client_email: "", total: "", target_date: "", priority: "normal", notes: "" });
        setCreateOpen(true);
    };
    const submitCreate = async () => {
        if (!form.title?.trim()) { setError("Le titre est requis."); return; }
        setSaving(true);
        try {
            await http.post("/admin/jobs", {
                title: form.title.trim(),
                client_name: form.client_name || "",
                client_email: form.client_email || null,
                total: Number(form.total) || 0,
                target_date: form.target_date || null,
                priority: form.priority || "normal",
                notes: form.notes || "",
            });
            setCreateOpen(false);
            flash("Job créée.");
            load();
        } catch (e) {
            setError("Création échouée.");
        } finally { setSaving(false); }
    };

    // ── From quote ──────────────────────────
    const openQuotePicker = async () => {
        try {
            const { data } = await http.get("/admin/quotes");
            setQuotePicker(data);
        } catch { setError("Impossible de charger les soumissions."); }
    };
    const createFromQuote = async (qid) => {
        try {
            const { data } = await http.post(`/admin/jobs/from-quote/${qid}`);
            setQuotePicker(null);
            flash(`Job ${data.job_number} liée à la soumission.`);
            load();
        } catch { setError("Création depuis la soumission échouée."); }
    };

    // ── Stage move ──────────────────────────
    const moveStage = async (job, dir) => {
        const idx = STAGES.findIndex((s) => s.key === job.stage);
        if (idx < 0) return; // e.g. 'annule' — not on the active board
        const next = STAGES[idx + dir];
        if (!next) return;
        try {
            const { data } = await http.patch(`/admin/jobs/${job.id}/stage`, { stage: next.key });
            setJobs((prev) => prev.map((j) => (j.id === job.id ? data : j)));
            if (detail?.id === job.id) setDetail(data);
        } catch { setError("Changement d'étape échoué."); }
    };
    const setStageDirect = async (job, stage) => {
        try {
            const { data } = await http.patch(`/admin/jobs/${job.id}/stage`, { stage });
            setJobs((prev) => prev.map((j) => (j.id === job.id ? data : j)));
            setDetail(data);
        } catch { setError("Changement d'étape échoué."); }
    };

    // ── Briefing ────────────────────────────
    const openBriefing = async () => {
        setBriefBusy(true);
        try {
            const { data } = await http.get("/admin/jobs-briefing/preview");
            setBriefing(data);
        } catch { setError("Aperçu du briefing indisponible."); }
        finally { setBriefBusy(false); }
    };
    const sendBriefing = async () => {
        setBriefBusy(true);
        try {
            const { data } = await http.post("/admin/jobs-briefing/send");
            if (data.sent) flash(`Briefing envoyé à ${data.to}.`);
            else setError(data.error || "Envoi du briefing échoué.");
            setBriefing(null);
        } catch { setError("Envoi du briefing échoué."); }
        finally { setBriefBusy(false); }
    };

    return (
        <div data-testid="jobs-panel" className="space-y-4">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 className="font-display font-bold uppercase text-2xl tracking-tight">Suivi des jobs</h2>
                    <p className="text-sm text-[#4b5d7a]">Où en sont mes projets — de la soumission au paiement.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <button data-testid="jobs-refresh" onClick={load} className="tech-stamp px-3 py-2 border border-[#dde5f0] text-[#4b5d7a] hover:bg-white flex items-center gap-1">
                        <RefreshCw className="w-4 h-4" /> Rafraîchir
                    </button>
                    <button data-testid="jobs-briefing-btn" onClick={openBriefing} disabled={briefBusy} className="tech-stamp px-3 py-2 border border-[#dde5f0] text-[#2f4f7f] hover:bg-white flex items-center gap-1">
                        <Mail className="w-4 h-4" /> Briefing
                    </button>
                    <button data-testid="jobs-from-quote-btn" onClick={openQuotePicker} className="tech-stamp px-3 py-2 border border-[#dde5f0] text-[#2f4f7f] hover:bg-white flex items-center gap-1">
                        <FileText className="w-4 h-4" /> Depuis une soumission
                    </button>
                    <button data-testid="jobs-new-btn" onClick={openCreate} className="tech-stamp px-3 py-2 bg-[#0c182b] text-white hover:bg-[#16283f] flex items-center gap-1">
                        <Plus className="w-4 h-4" /> Nouvelle job
                    </button>
                </div>
            </div>

            {notice && <div data-testid="jobs-notice" className="p-3 border border-green-300 bg-green-50 text-green-800 text-sm">{notice}</div>}
            {error && <div data-testid="jobs-error" className="p-3 border border-red-300 bg-red-50 text-red-800 text-sm flex justify-between"><span>{error}</span><button onClick={() => setError("")}><X className="w-4 h-4" /></button></div>}

            {loading ? (
                <div className="py-20 text-center text-[#4b5d7a]"><Loader2 className="w-6 h-6 animate-spin inline" /> Chargement…</div>
            ) : (
              <>
                <div className="hidden sm:block overflow-x-auto pb-3">
                    <div className="flex gap-3 min-w-max">
                        {STAGES.map((s) => (
                            <div key={s.key} data-testid={`jobs-col-${s.key}`} className="w-64 flex-shrink-0 bg-[#eef2f8] border border-[#dde5f0] rounded">
                                <div className="px-3 py-2 border-b border-[#dde5f0] flex items-center justify-between" style={{ borderTop: `3px solid ${s.color}` }}>
                                    <span className="tech-stamp font-bold text-[#0c182b]">{s.label}</span>
                                    <span className="text-xs font-bold text-white px-2 py-0.5 rounded-full" style={{ background: s.color }}>{grouped[s.key].length}</span>
                                </div>
                                <div className="p-2 space-y-2 min-h-[120px]">
                                    {grouped[s.key].map((j) => {
                                        const d = daysUntil(j.target_date);
                                        const overdue = d !== null && d < 0;
                                        const soon = d !== null && d >= 0 && d <= 7;
                                        return (
                                            <div key={j.id} data-testid={`job-card-${j.id}`} onClick={() => setDetail(j)}
                                                className="bg-white border border-[#dde5f0] rounded p-2.5 cursor-pointer hover:border-[#0c182b] transition-colors">
                                                <div className="flex items-center justify-between">
                                                    <span className="tech-stamp text-[#2f4f7f] font-bold">{j.job_number}</span>
                                                    {j.priority === "urgent" && <span className="w-2 h-2 rounded-full bg-red-500" title="Urgent" />}
                                                </div>
                                                <div className="text-sm font-semibold text-[#0c182b] mt-0.5 leading-snug line-clamp-2">{j.title}</div>
                                                <div className="text-xs text-[#4b5d7a] mt-1">{j.client_name || "—"}</div>
                                                {j.total > 0 && <div className="text-xs font-bold text-[#0c182b] mt-1">{money(j.total)}</div>}
                                                {j.target_date && (
                                                    <div className={`text-xs mt-1 flex items-center gap-1 ${overdue ? "text-red-600 font-bold" : soon ? "text-amber-600" : "text-[#4b5d7a]"}`}>
                                                        {overdue ? <AlertTriangle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                                                        {formatDate(j.target_date)}{overdue ? " (retard)" : soon ? ` (${d}j)` : ""}
                                                    </div>
                                                )}
                                                <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#eef2f8]">
                                                    <button data-testid={`job-prev-${j.id}`} onClick={(e) => { e.stopPropagation(); moveStage(j, -1); }} disabled={s.key === STAGES[0].key} className="p-1 text-[#4b5d7a] hover:text-[#0c182b] disabled:opacity-20"><ChevronLeft className="w-4 h-4" /></button>
                                                    {j.links?.length > 0 && <span className="text-[10px] text-[#4b5d7a] flex items-center gap-0.5"><Link2 className="w-3 h-3" />{j.links.length}</span>}
                                                    <button data-testid={`job-next-${j.id}`} onClick={(e) => { e.stopPropagation(); moveStage(j, 1); }} disabled={s.key === STAGES[STAGES.length - 1].key} className="p-1 text-[#4b5d7a] hover:text-[#0c182b] disabled:opacity-20"><ChevronRight className="w-4 h-4" /></button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                    {grouped[s.key].length === 0 && <div className="text-xs text-[#9aa8bd] text-center py-4">Vide</div>}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Mobile — liste compacte par étape */}
                <div className="sm:hidden space-y-4">
                    {STAGES.map((s) => (
                        grouped[s.key].length === 0 ? null : (
                            <div key={s.key} data-testid={`jobs-mcol-${s.key}`}>
                                <div className="flex items-center gap-2 mb-1.5" style={{ color: s.color }}>
                                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: s.color }} />
                                    <span className="tech-stamp font-bold text-[#0c182b]">{s.label}</span>
                                    <span className="text-xs font-bold text-[#4b5d7a]">({grouped[s.key].length})</span>
                                </div>
                                <div className="space-y-2">
                                    {grouped[s.key].map((j) => {
                                        const d = daysUntil(j.target_date);
                                        const overdue = d !== null && d < 0;
                                        return (
                                            <div key={j.id} data-testid={`job-mrow-${j.id}`} onClick={() => setDetail(j)}
                                                className="bg-white border border-[#dde5f0] rounded p-3 flex items-center gap-3 active:bg-[#f3f6fb]">
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2">
                                                        <span className="tech-stamp text-[#2f4f7f] font-bold">{j.job_number}</span>
                                                        {j.priority === "urgent" && <span className="w-2 h-2 rounded-full bg-red-500" />}
                                                    </div>
                                                    <div className="text-sm font-semibold text-[#0c182b] truncate">{j.title}</div>
                                                    <div className="text-xs text-[#4b5d7a] truncate">
                                                        {j.client_name || "—"}
                                                        {j.total > 0 ? ` · ${money(j.total)}` : ""}
                                                        {j.target_date ? <span className={overdue ? "text-red-600 font-bold" : ""}> · {formatDate(j.target_date)}{overdue ? " (retard)" : ""}</span> : null}
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-1.5">
                                                    <button data-testid={`job-mprev-${j.id}`} onClick={(e) => { e.stopPropagation(); moveStage(j, -1); }} disabled={s.key === STAGES[0].key} className="p-2 border border-[#dde5f0] rounded text-[#4b5d7a] disabled:opacity-30"><ChevronLeft className="w-4 h-4" /></button>
                                                    <button data-testid={`job-mnext-${j.id}`} onClick={(e) => { e.stopPropagation(); moveStage(j, 1); }} disabled={s.key === STAGES[STAGES.length - 1].key} className="p-2 border border-[#dde5f0] rounded text-[#4b5d7a] disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )
                    ))}
                    {jobs.filter((j) => j.stage !== "annule").length === 0 && (
                        <div className="text-center text-[#9aa8bd] py-10 text-sm">Aucune job active. Touchez « Nouvelle job » pour commencer.</div>
                    )}
                </div>
              </>
            )}

            {cancelled.length > 0 && (
                <details className="text-sm">
                    <summary className="cursor-pointer text-[#4b5d7a]">Annulées ({cancelled.length})</summary>
                    <div className="flex flex-wrap gap-2 mt-2">
                        {cancelled.map((j) => (
                            <button key={j.id} onClick={() => setDetail(j)} className="px-2 py-1 border border-[#dde5f0] bg-white text-xs text-[#4b5d7a] line-through">{j.job_number} · {j.title}</button>
                        ))}
                    </div>
                </details>
            )}

            {/* Create modal */}
            <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Nouvelle job" testId="jobs-create-modal"
                footer={<div className="flex justify-end gap-2"><button onClick={() => setCreateOpen(false)} className="tech-stamp px-4 py-2 border border-[#dde5f0]">Annuler</button><button data-testid="jobs-create-submit" onClick={submitCreate} disabled={saving} className="tech-stamp px-4 py-2 bg-[#0c182b] text-white flex items-center gap-1">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Créer</button></div>}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <Field label="Titre *"><input data-testid="jobs-create-title" className={inputClass} value={form.title || ""} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Ex. Portes d'entrée — Pharmacie X" /></Field>
                    <Field label="Client"><input className={inputClass} value={form.client_name || ""} onChange={(e) => setForm({ ...form, client_name: e.target.value })} /></Field>
                    <Field label="Courriel client"><input className={inputClass} value={form.client_email || ""} onChange={(e) => setForm({ ...form, client_email: e.target.value })} /></Field>
                    <Field label="Valeur ($)"><input type="number" className={inputClass} value={form.total || ""} onChange={(e) => setForm({ ...form, total: e.target.value })} /></Field>
                    <Field label="Échéance visée"><input type="date" className={inputClass} value={form.target_date || ""} onChange={(e) => setForm({ ...form, target_date: e.target.value })} /></Field>
                    <Field label="Priorité"><select className={inputClass} value={form.priority || "normal"} onChange={(e) => setForm({ ...form, priority: e.target.value })}><option value="normal">Normale</option><option value="urgent">Urgente</option></select></Field>
                    <div className="md:col-span-2"><Field label="Notes"><textarea rows={3} className={inputClass} value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field></div>
                </div>
            </Modal>

            {/* Quote picker */}
            <Modal open={!!quotePicker} onClose={() => setQuotePicker(null)} title="Créer une job depuis une soumission" testId="jobs-quote-picker">
                <div className="space-y-1 max-h-[60vh] overflow-y-auto">
                    {(quotePicker || []).length === 0 && <div className="text-sm text-[#4b5d7a]">Aucune soumission.</div>}
                    {(quotePicker || []).map((q) => (
                        <button key={q.id} data-testid={`jobs-pick-quote-${q.id}`} onClick={() => createFromQuote(q.id)}
                            className="w-full text-left px-3 py-2 border border-[#dde5f0] hover:bg-[#f3f6fb] flex items-center justify-between">
                            <span className="text-sm"><b>SO-{String(q.number).padStart(4, "0")}</b> · {q.customer_snapshot?.name || "—"} <span className="text-[#4b5d7a]">({q.status})</span></span>
                            <span className="text-sm font-bold">{money(q.total)}</span>
                        </button>
                    ))}
                </div>
            </Modal>

            {/* Detail modal */}
            {detail && <JobDetail http={http} job={detail} onClose={() => setDetail(null)} onChange={(j) => { setDetail(j); setJobs((prev) => prev.map((x) => (x.id === j.id ? j : x))); }} onDeleted={(id) => { setDetail(null); setJobs((prev) => prev.filter((x) => x.id !== id)); flash("Job supprimée."); }} setStageDirect={setStageDirect} />}

            {/* Briefing modal */}
            <Modal open={!!briefing} onClose={() => setBriefing(null)} title="Briefing quotidien" testId="jobs-briefing-modal" wide
                footer={<div className="flex justify-between items-center gap-2"><span className="text-xs text-[#4b5d7a]">Envoyé automatiquement chaque matin à 7h30 à {briefing?.to}</span><button data-testid="jobs-briefing-send" onClick={sendBriefing} disabled={briefBusy} className="tech-stamp px-4 py-2 bg-[#0c182b] text-white flex items-center gap-1">{briefBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />} Envoyer maintenant</button></div>}>
                {briefing && <div className="border border-[#dde5f0] p-3 bg-white text-sm" dangerouslySetInnerHTML={{ __html: briefing.html }} />}
            </Modal>
        </div>
    );
};

// ── Detail panel ────────────────────────────────────────────
const PICKABLE = {
    quote: "/admin/quotes",
    invoice: "/admin/invoices",
    purchase_order: "/admin/purchase-orders",
    bol: "/admin/bills-of-lading",
    production_plan: "/admin/production-plans",
};
const OPENABLE = new Set(["quote", "invoice", "purchase_order", "bol", "production_plan"]);
const DOC_PREFIX = { quote: "SO-", invoice: "FAC-", purchase_order: "BC-", bol: "CN-" };
const docNum = (type, d) =>
    d.plan_number || (d.number != null ? `${DOC_PREFIX[type] || ""}${String(d.number).padStart(4, "0")}` : String(d.id || "").slice(0, 6));
const docName = (d) =>
    d.customer_snapshot?.name || d.supplier_snapshot?.name || d.project_name || d.client_name || "";

const JobDetail = ({ http, job, onClose, onChange, onDeleted, setStageDirect }) => {
    const [f, setF] = useState(job);
    const [saving, setSaving] = useState(false);
    const [linkType, setLinkType] = useState("invoice");
    const [linkRef, setLinkRef] = useState("");
    const [pickList, setPickList] = useState(null); // real docs for pickable types
    const [pickId, setPickId] = useState("");
    useEffect(() => { setF(job); }, [job]);

    // Fetch real documents when a pickable type is selected.
    useEffect(() => {
        let alive = true;
        setPickList(null); setPickId("");
        if (PICKABLE[linkType]) {
            http.get(PICKABLE[linkType]).then(({ data }) => { if (alive) setPickList(data); }).catch(() => {});
        }
        return () => { alive = false; };
    }, [linkType, http]);

    const money2 = (v) => (Number(v) || 0).toLocaleString("fr-CA", { style: "currency", currency: "CAD" });

    const openDoc = async (l) => {
        const id = l.doc_id;
        if (!OPENABLE.has(l.doc_type) || String(id).startsWith("ref:")) return;
        if (l.doc_type === "invoice") window.open(`/admin/imprimer/facture/${id}`, "_blank");
        else if (l.doc_type === "purchase_order") window.open(`/admin/imprimer/bon-commande/${id}`, "_blank");
        else if (l.doc_type === "bol") window.open(`/admin/imprimer/connaissement/${id}`, "_blank");
        else {
            const url = l.doc_type === "quote" ? `/admin/quotes/${id}/pdf` : `/admin/production-plans/${id}/pdf`;
            try {
                const res = await http.get(url, { responseType: "blob" });
                window.open(URL.createObjectURL(res.data), "_blank");
            } catch { /* ignore */ }
        }
    };
    const isOpenable = (l) => OPENABLE.has(l.doc_type) && !String(l.doc_id).startsWith("ref:");

    const save = async () => {
        setSaving(true);
        try {
            const { data } = await http.put(`/admin/jobs/${job.id}`, {
                title: f.title, client_name: f.client_name, client_email: f.client_email || null,
                total: Number(f.total) || 0, target_date: f.target_date || null,
                priority: f.priority, notes: f.notes,
            });
            onChange(data);
        } finally { setSaving(false); }
    };
    const del = async () => {
        if (!window.confirm("Supprimer cette job ? (les documents liés ne sont pas supprimés)")) return;
        await http.delete(`/admin/jobs/${job.id}`);
        onDeleted(job.id);
    };
    const addLink = async () => {
        let payload;
        if (PICKABLE[linkType]) {
            if (!pickId) return;
            const d = (pickList || []).find((x) => x.id === pickId);
            const num = d ? docNum(linkType, d) : pickId;
            payload = { doc_type: linkType, doc_id: pickId, number: num,
                        label: `${DOC_LABEL[linkType]} ${num}` };
        } else {
            if (!linkRef.trim()) return;
            payload = { doc_type: linkType, doc_id: `ref:${linkRef.trim()}`, number: linkRef.trim(),
                        label: `${DOC_LABEL[linkType]} ${linkRef.trim()}` };
        }
        const { data } = await http.post(`/admin/jobs/${job.id}/links`, payload);
        onChange(data); setLinkRef(""); setPickId("");
    };
    const removeLink = async (l) => {
        const { data } = await http.post(`/admin/jobs/${job.id}/unlink`, {
            doc_type: l.doc_type, doc_id: l.doc_id,
        });
        onChange(data);
    };

    return (
        <Modal open onClose={onClose} title={`${job.job_number} · ${job.title}`} testId="jobs-detail-modal" wide
            footer={<div className="flex justify-between gap-2"><button data-testid="jobs-detail-delete" onClick={del} className="tech-stamp px-4 py-2 border border-red-300 text-red-700 hover:bg-red-50 flex items-center gap-1"><Trash2 className="w-4 h-4" /> Supprimer</button><button data-testid="jobs-detail-save" onClick={save} disabled={saving} className="tech-stamp px-4 py-2 bg-[#0c182b] text-white flex items-center gap-1">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Enregistrer</button></div>}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                    <Field label="Étape">
                        <select data-testid="jobs-detail-stage" className={inputClass} value={f.stage} onChange={(e) => setStageDirect(job, e.target.value)}>
                            {ALL_STAGES.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                        </select>
                    </Field>
                    <Field label="Titre"><input className={inputClass} value={f.title || ""} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
                    <Field label="Client"><input className={inputClass} value={f.client_name || ""} onChange={(e) => setF({ ...f, client_name: e.target.value })} /></Field>
                    <Field label="Courriel client"><input className={inputClass} value={f.client_email || ""} onChange={(e) => setF({ ...f, client_email: e.target.value })} /></Field>
                    <div className="grid grid-cols-2 gap-3">
                        <Field label="Valeur ($)"><input type="number" className={inputClass} value={f.total || ""} onChange={(e) => setF({ ...f, total: e.target.value })} /></Field>
                        <Field label="Échéance"><input type="date" className={inputClass} value={f.target_date || ""} onChange={(e) => setF({ ...f, target_date: e.target.value })} /></Field>
                    </div>
                    <Field label="Priorité"><select className={inputClass} value={f.priority || "normal"} onChange={(e) => setF({ ...f, priority: e.target.value })}><option value="normal">Normale</option><option value="urgent">Urgente</option></select></Field>
                    <div className="text-xs text-[#4b5d7a]">Dépôt attendu (50%) : <b>{money2(job.deposit_expected)}</b></div>
                    <Field label="Notes"><textarea rows={3} className={inputClass} value={f.notes || ""} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
                </div>

                <div className="space-y-4">
                    <div>
                        <div className="tech-stamp font-bold text-[#0c182b] mb-2">Documents liés</div>
                        <div className="space-y-1">
                            {(f.links || []).length === 0 && <div className="text-sm text-[#9aa8bd]">Aucun document lié.</div>}
                            {(f.links || []).map((l) => (
                                <div key={l.doc_type + l.doc_id} className="flex items-center justify-between px-2 py-1.5 border border-[#dde5f0] bg-white text-sm">
                                    {isOpenable(l) ? (
                                        <button data-testid={`jobs-link-open-${l.doc_type}`} onClick={() => openDoc(l)} className="text-left hover:underline text-[#0c182b] flex-1 mr-2">
                                            <span className="tech-stamp text-[#2f4f7f]">{DOC_LABEL[l.doc_type] || l.doc_type}</span> · {l.number || l.label} <span className="text-[#2f4f7f] text-xs">(ouvrir ↗)</span>
                                        </button>
                                    ) : (
                                        <span className="flex-1 mr-2"><span className="tech-stamp text-[#2f4f7f]">{DOC_LABEL[l.doc_type] || l.doc_type}</span> · {l.number || l.label || l.doc_id}</span>
                                    )}
                                    <button data-testid={`jobs-link-remove-${l.doc_type}-${l.doc_id}`} onClick={() => removeLink(l)} className="text-[#4b5d7a] hover:text-red-600"><X className="w-4 h-4" /></button>
                                </div>
                            ))}
                        </div>
                        <div className="flex flex-col sm:flex-row gap-2 mt-2">
                            <select className={`${inputClass} sm:!w-44`} value={linkType} onChange={(e) => setLinkType(e.target.value)} data-testid="jobs-link-type">
                                {DOC_TYPES.map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
                            </select>
                            {PICKABLE[linkType] ? (
                                <select className={inputClass} value={pickId} onChange={(e) => setPickId(e.target.value)} data-testid="jobs-link-pick">
                                    <option value="">{pickList === null ? "Chargement…" : "— Choisir un document —"}</option>
                                    {(pickList || []).map((d) => (
                                        <option key={d.id} value={d.id}>{docNum(linkType, d)}{docName(d) ? ` · ${docName(d)}` : ""}</option>
                                    ))}
                                </select>
                            ) : (
                                <input className={inputClass} placeholder="Nº / référence" value={linkRef} onChange={(e) => setLinkRef(e.target.value)} data-testid="jobs-link-ref" />
                            )}
                            <button data-testid="jobs-link-add" onClick={addLink} className="tech-stamp px-3 py-2 border border-[#dde5f0] hover:bg-[#f3f6fb] whitespace-nowrap">Lier</button>
                        </div>
                    </div>

                    <div>
                        <div className="tech-stamp font-bold text-[#0c182b] mb-2">Historique</div>
                        <div className="space-y-1 max-h-40 overflow-y-auto text-xs">
                            {(f.history || []).slice().reverse().map((h, i) => (
                                <div key={i} className="flex justify-between border-b border-[#eef2f8] py-1">
                                    <span className="text-[#0c182b]">{STAGE_LABEL[h.stage] || h.stage}{h.note ? ` — ${h.note}` : ""}</span>
                                    <span className="text-[#9aa8bd]">{formatDate(h.at)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </Modal>
    );
};

export default JobsPanel;
