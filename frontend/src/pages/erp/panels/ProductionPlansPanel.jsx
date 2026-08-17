/** Dessins de production — production drawings generator.
 *
 *  A fill-in template : project + client info and a list of doors (dimensions,
 *  series, config, finishes, glass, hardware). Generates a branded, multi-page
 *  landscape PDF (cover + one to-scale elevation per door + standard plan /
 *  section / anchor detail pages).
 *
 *  Lives inside the Fabrication tab.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    Plus, Save, Trash2, RefreshCw, Download, Eye, FileText,
    AlertCircle, CheckCircle2, Loader2, DraftingCompass, ChevronDown, ChevronRight,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
    emptyProductionPlan, emptyProductionDoor, emptyHardwareLine,
    PRODUCTION_SERIES, PRODUCTION_CONFIGS, PRODUCTION_STATUSES, PRODUCTION_FINISHES,
    HINGE_TYPES, INSTALL_PARTIES, HANDING_OPTIONS,
    newKey, stripKeys, todayISO, formatDate,
} from "../utils";

const inLabel = (v) => {
    const n = Number(v || 0);
    if (!n) return "";
    return `${(n * 25.4).toFixed(0)} mm`;
};

export const ProductionPlansPanel = () => {
    const { http, getToken } = useAuth();
    const [plans, setPlans] = useState([]);
    const [catalog, setCatalog] = useState(null);
    const [loading, setLoading] = useState(true);
    const [form, setForm] = useState(emptyProductionPlan());
    const [editingId, setEditingId] = useState(null);
    const [openDoor, setOpenDoor] = useState(null);
    const [busy, setBusy] = useState(false);
    const [previewing, setPreviewing] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");
    const formTopRef = useRef(null);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const { data } = await http.get("/admin/production-plans");
                if (!cancelled) {
                    setPlans(Array.isArray(data) ? data : []);
                    setLoading(false);
                }
            } catch (e) {
                if (!cancelled) {
                    setErrorMsg(e?.response?.data?.detail || "Erreur de chargement.");
                    setLoading(false);
                }
            }
        })();
        return () => { cancelled = true; };
    }, [http]);

    const reload = useCallback(async () => {
        try {
            const { data } = await http.get("/admin/production-plans");
            setPlans(Array.isArray(data) ? data : []);
        } catch (_) { /* silent */ }
    }, [http]);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const { data } = await http.get("/admin/production-plans/profile-catalog");
                if (!cancelled) setCatalog(data);
            } catch (_) { /* silent */ }
        })();
        return () => { cancelled = true; };
    }, [http]);

    const effProfile = (d, field, key) =>
        d[field] || catalog?.defaults?.[d.series]?.[key] || "";
    const optLabel = (o) => `${o.code} · ${o.face_mm} mm`;

    // ─── door helpers ────────────────────────────────────
    const addDoor = () => {
        const d = emptyProductionDoor();
        setForm((f) => ({ ...f, doors: [...f.doors, d] }));
        setOpenDoor(d._key);
    };
    const removeDoor = (k) => setForm((f) => ({
        ...f, doors: f.doors.filter((d) => d._key !== k),
    }));
    const updateDoor = (k, key, value) => setForm((f) => ({
        ...f,
        doors: f.doors.map((d) => (d._key === k ? { ...d, [key]: value } : d)),
    }));
    const changeSeries = (k, series) => setForm((f) => ({
        ...f,
        doors: f.doors.map((d) => (d._key === k ? {
            ...d, series,
            profile_head: "", profile_base: "",
            profile_hinge_stile: "", profile_lock_stile: "",
        } : d)),
    }));

    // ─── hardware helpers ────────────────────────────────
    const addHw = (dk) => setForm((f) => ({
        ...f,
        doors: f.doors.map((d) => (d._key === dk
            ? { ...d, hardware: [...(d.hardware || []), emptyHardwareLine()] } : d)),
    }));
    const removeHw = (dk, hk) => setForm((f) => ({
        ...f,
        doors: f.doors.map((d) => (d._key === dk
            ? { ...d, hardware: (d.hardware || []).filter((h) => h._key !== hk) } : d)),
    }));
    const updateHw = (dk, hk, key, value) => setForm((f) => ({
        ...f,
        doors: f.doors.map((d) => (d._key === dk
            ? {
                ...d,
                hardware: (d.hardware || []).map((h) =>
                    (h._key === hk ? { ...h, [key]: value } : h)),
            } : d)),
    }));

    // ─── new / edit ──────────────────────────────────────
    const resetForm = () => {
        const empty = emptyProductionPlan();
        setForm(empty);
        setEditingId(null);
        setOpenDoor(empty.doors[0]?._key || null);
        setSuccessMsg("");
        setErrorMsg("");
        formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    const openEdit = (p) => {
        const doors = (p.doors || []).map((d) => ({
            ...d,
            _key: newKey(),
            hardware: (d.hardware || []).map((h) => ({ ...h, _key: newKey() })),
        }));
        setForm({ ...emptyProductionPlan(), ...p, doors: doors.length ? doors : emptyProductionPlan().doors });
        setEditingId(p.id);
        setOpenDoor(doors[0]?._key || null);
        setSuccessMsg("");
        setErrorMsg("");
        formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    const buildPayload = () => ({
        project_name: form.project_name || "",
        project_number: form.project_number || "",
        production_name: form.production_name || "",
        production_note: form.production_note || "",
        revision: form.revision || "no00",
        date: form.date || todayISO(),
        client_name: form.client_name || "",
        client_address: form.client_address || "",
        client_contact: form.client_contact || "",
        client_phone: form.client_phone || "",
        machining_by: form.machining_by || "A.T. Fabrication",
        installer: form.installer || "Portech",
        fab_auto: form.fab_auto !== false,
        fab_allowance_in: Number(form.fab_allowance_in || 0) || 0,
        include_plan_details: !!form.include_plan_details,
        include_section_details: !!form.include_section_details,
        include_anchors: !!form.include_anchors,
        status: form.status || "brouillon",
        notes: form.notes || "",
        doors: (form.doors || []).map((d) => ({
            tag: d.tag || "",
            series: d.series || "AT1000",
            config: d.config || "simple",
            opening_width_in: Number(d.opening_width_in || 0) || 1,
            opening_height_in: Number(d.opening_height_in || 0) || 1,
            qty: parseInt(d.qty, 10) || 1,
            handing: d.handing || "MD",
            active_leaf: d.active_leaf || "right",
            fab_width_in: Number(d.fab_width_in || 0) || 0,
            fab_height_in: Number(d.fab_height_in || 0) || 0,
            handle_height_in: Number(d.handle_height_in ?? 34.5) || 0,
            handle_length_in: Number(d.handle_length_in ?? 9) || 0,
            handle_both: !!d.handle_both,
            lock_height_in: Number(d.lock_height_in ?? 40) || 0,
            panic_bar: !!d.panic_bar,
            panic_height_in: Number(d.panic_height_in ?? 40) || 0,
            undercut_mm: Number(d.undercut_mm ?? 17.5) || 0,
            finish_ext: d.finish_ext || "",
            finish_int: d.finish_int || "",
            glass: d.glass || "",
            hinges: d.hinges || "",
            hinge_type: d.hinge_type || "butt45",
            profile_head: effProfile(d, "profile_head", "head"),
            profile_base: effProfile(d, "profile_base", "base"),
            profile_hinge_stile: effProfile(d, "profile_hinge_stile", "hinge"),
            profile_lock_stile: effProfile(d, "profile_lock_stile", "lock"),
            scale_note: d.scale_note || "1:30",
            notes: d.notes || "",
            hardware: stripKeys(d.hardware || []).map((h) => ({
                qty: String(h.qty || "1"),
                description: h.description || "",
                part_number: h.part_number || "",
                note: h.note || "",
                on_active: !!h.on_active,
                on_inactive: !!h.on_inactive,
            })),
        })),
    });

    const validate = () => {
        if (!form.doors?.length) return "Ajoutez au moins une porte.";
        for (const d of form.doors) {
            if (!(Number(d.opening_width_in) > 0) || !(Number(d.opening_height_in) > 0)) {
                return `Dimensions invalides pour "${d.tag || "(sans repère)"}".`;
            }
        }
        return "";
    };

    const save = async () => {
        const err = validate();
        if (err) { setErrorMsg(err); return; }
        setBusy(true);
        setErrorMsg("");
        try {
            const payload = buildPayload();
            const url = editingId
                ? `/admin/production-plans/${editingId}`
                : "/admin/production-plans";
            const method = editingId ? "put" : "post";
            const { data } = await http[method](url, payload);
            setSuccessMsg(editingId
                ? `Plan ${data.plan_number} mis à jour.`
                : `Plan ${data.plan_number} créé · ${data.doors.length} porte(s).`);
            openEdit(data);
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'enregistrement.");
        } finally { setBusy(false); }
    };

    const removePlan = async (id) => {
        if (!window.confirm("Supprimer ce plan de production ?")) return;
        try {
            await http.delete(`/admin/production-plans/${id}`);
            if (editingId === id) resetForm();
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur de suppression.");
        }
    };

    // ─── PDF ─────────────────────────────────────────────
    const downloadPdf = (id) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/production-plans/${id}/pdf?token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const previewPdf = async () => {
        const err = validate();
        if (err) { setErrorMsg(err); return; }
        setPreviewing(true);
        setErrorMsg("");
        try {
            const res = await http.post(
                "/admin/production-plans/preview-pdf", buildPayload(),
                { responseType: "blob" },
            );
            const blobUrl = URL.createObjectURL(
                new Blob([res.data], { type: "application/pdf" }));
            window.open(blobUrl, "_blank");
            setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
        } catch (e) {
            setErrorMsg("Erreur lors de la génération de l'aperçu.");
        } finally { setPreviewing(false); }
    };

    const totalDoors = useMemo(
        () => form.doors.reduce((s, d) => s + (parseInt(d.qty, 10) || 0), 0),
        [form.doors],
    );

    const inputCls = "w-full px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]";
    const labelCls = "block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1";

    // ──────────────────────────────────────────────────────
    return (
        <div className="space-y-6" ref={formTopRef}>
            <div className="flex items-center gap-3 flex-wrap">
                <DraftingCompass className="w-6 h-6 text-[#0c182b]" />
                <h2 className="text-xl font-bold text-[#0c182b]">Dessins de production</h2>
                <span className="text-xs text-[#4b5d7a]">
                    Génère un plan complet (présentation · élévations à l&apos;échelle · détails) à partir des dimensions.
                </span>
                <button onClick={resetForm} className="ml-auto btn-secondary !py-1.5 !px-3 !text-xs"
                    data-testid="pp-new">
                    <Plus className="w-3.5 h-3.5" /> Nouveau plan
                </button>
            </div>

            {errorMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#fde7e7] border border-[#e89a9a] text-[#a31a1a] text-sm"
                    data-testid="pp-error">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{errorMsg}</div>
                    <button onClick={() => setErrorMsg("")} className="text-[#a31a1a] hover:underline text-xs">Fermer</button>
                </div>
            )}
            {successMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#e6f7ee] border border-[#86c9a4] text-[#0f6b3a] text-sm"
                    data-testid="pp-success">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{successMsg}</div>
                    <button onClick={() => setSuccessMsg("")} className="text-[#0f6b3a] hover:underline text-xs">Fermer</button>
                </div>
            )}

            {/* ─── Form ───────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-5" data-testid="pp-form">
                <h3 className="tech-stamp text-[#0c182b] font-bold">
                    {editingId ? `Modifier ${form.plan_number || ""}` : "Nouveau plan"}
                </h3>

                {/* Project + production */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label className={labelCls}>Nom du projet</label>
                        <input type="text" data-testid="pp-project-name" value={form.project_name}
                            onChange={(e) => setForm((f) => ({ ...f, project_name: e.target.value }))}
                            placeholder="Ex : Uniprix St-Martin" className={inputCls} />
                    </div>
                    <div>
                        <label className={labelCls}>N° de projet</label>
                        <input type="text" data-testid="pp-project-number" value={form.project_number}
                            onChange={(e) => setForm((f) => ({ ...f, project_number: e.target.value }))}
                            placeholder="Ex : 123904" className={inputCls} />
                    </div>
                    <div>
                        <label className={labelCls}>Date</label>
                        <input type="date" value={form.date || todayISO()}
                            onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                            className={inputCls} />
                    </div>
                    <div>
                        <label className={labelCls}>Responsable production</label>
                        <input type="text" value={form.production_name}
                            onChange={(e) => setForm((f) => ({ ...f, production_name: e.target.value }))}
                            placeholder="Ex : Pascal Fortin" className={inputCls} />
                    </div>
                    <div className="sm:col-span-2">
                        <label className={labelCls}>Note production (optionnel)</label>
                        <input type="text" value={form.production_note}
                            onChange={(e) => setForm((f) => ({ ...f, production_note: e.target.value }))}
                            placeholder="Ex : RELACHE 1 = LES PAIRES DE PORTE" className={inputCls} />
                    </div>
                </div>

                {/* Client */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                    <div>
                        <label className={labelCls}>Client</label>
                        <input type="text" data-testid="pp-client-name" value={form.client_name}
                            onChange={(e) => setForm((f) => ({ ...f, client_name: e.target.value }))}
                            placeholder="Ex : Groupe Picotte Inc." className={inputCls} />
                    </div>
                    <div>
                        <label className={labelCls}>Adresse</label>
                        <input type="text" value={form.client_address}
                            onChange={(e) => setForm((f) => ({ ...f, client_address: e.target.value }))}
                            className={inputCls} />
                    </div>
                    <div>
                        <label className={labelCls}>Contact</label>
                        <input type="text" value={form.client_contact}
                            onChange={(e) => setForm((f) => ({ ...f, client_contact: e.target.value }))}
                            className={inputCls} />
                    </div>
                    <div>
                        <label className={labelCls}>Téléphone</label>
                        <input type="text" value={form.client_phone}
                            onChange={(e) => setForm((f) => ({ ...f, client_phone: e.target.value }))}
                            className={inputCls} />
                    </div>
                    <div>
                        <label className={labelCls}>Révision</label>
                        <input type="text" value={form.revision}
                            onChange={(e) => setForm((f) => ({ ...f, revision: e.target.value }))}
                            placeholder="no00" className={inputCls} />
                    </div>
                    <div>
                        <label className={labelCls}>Statut</label>
                        <select value={form.status}
                            onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                            className={`${inputCls} bg-white`}>
                            {PRODUCTION_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className={labelCls}>Usinage par</label>
                        <select value={form.machining_by} data-testid="pp-machining-by"
                            onChange={(e) => setForm((f) => ({ ...f, machining_by: e.target.value }))}
                            className={`${inputCls} bg-white`}>
                            {INSTALL_PARTIES.map((p) => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className={labelCls}>Installation quincaillerie par</label>
                        <select value={form.installer} data-testid="pp-installer"
                            onChange={(e) => setForm((f) => ({ ...f, installer: e.target.value }))}
                            className={`${inputCls} bg-white`}>
                            {INSTALL_PARTIES.map((p) => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </div>
                </div>

                {/* Detail pages toggles */}
                <div className="flex flex-wrap gap-4 items-center bg-[#f3f6fb] border border-[#dde5f0] px-3 py-2">
                    <span className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider">Pages incluses :</span>
                    {[
                        ["include_plan_details", "Détails en plan (300)"],
                        ["include_section_details", "Détails en coupe (400)"],
                        ["include_anchors", "Ancrages (500)"],
                    ].map(([key, lbl]) => (
                        <label key={key} className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                            <input type="checkbox" data-testid={`pp-toggle-${key}`} checked={!!form[key]}
                                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.checked }))} />
                            {lbl}
                        </label>
                    ))}
                    <span className="w-px h-5 bg-[#dde5f0]" />
                    <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                        <input type="checkbox" data-testid="pp-fab-auto" checked={form.fab_auto !== false}
                            onChange={(e) => setForm((f) => ({ ...f, fab_auto: e.target.checked }))} />
                        Cote Fab. auto
                    </label>
                    <label className="inline-flex items-center gap-1 text-sm text-[#0c182b]">
                        Jeu Fab. (po)
                        <input type="number" step="0.0625" data-testid="pp-fab-allow" value={form.fab_allowance_in}
                            onChange={(e) => setForm((f) => ({ ...f, fab_allowance_in: e.target.value }))}
                            className="w-20 px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                    </label>
                </div>

                {/* Doors */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <label className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider">
                            Portes / ouvertures (dimensions en pouces)
                        </label>
                        <button onClick={addDoor} className="text-[#1d4ed8] hover:underline text-xs inline-flex items-center gap-1"
                            data-testid="pp-add-door">
                            <Plus className="w-3 h-3" /> Ajouter une porte
                        </button>
                    </div>

                    <div className="space-y-3">
                        {form.doors.map((d, idx) => {
                            const isOpen = openDoor === d._key;
                            return (
                                <div key={d._key} className="border border-[#dde5f0]" data-testid={`pp-door-${idx}`}>
                                    <button type="button"
                                        onClick={() => setOpenDoor(isOpen ? null : d._key)}
                                        className="w-full flex items-center gap-2 px-3 py-2 bg-[#f7f9fc] hover:bg-[#eef3fa] text-left">
                                        {isOpen ? <ChevronDown className="w-4 h-4 text-[#4b5d7a]" />
                                                : <ChevronRight className="w-4 h-4 text-[#4b5d7a]" />}
                                        <span className="font-bold text-[#0c182b] text-sm">
                                            {d.tag || `Porte ${idx + 1}`}
                                        </span>
                                        <span className="text-xs text-[#4b5d7a]">
                                            {d.series} · {d.config === "pair" ? "Paire" : "Simple"} ·{" "}
                                            {d.opening_width_in}″ × {d.opening_height_in}″ · Qté {d.qty}
                                        </span>
                                        <Trash2 className="w-3.5 h-3.5 ml-auto text-[#a31a1a] hover:scale-110"
                                            onClick={(e) => { e.stopPropagation(); removeDoor(d._key); }} />
                                    </button>

                                    {isOpen && (
                                        <div className="p-3 space-y-3 border-t border-[#dde5f0]">
                                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                                <div>
                                                    <label className={labelCls}>Repère / Tag</label>
                                                    <input type="text" data-testid={`pp-door-tag-${idx}`} value={d.tag}
                                                        onChange={(e) => updateDoor(d._key, "tag", e.target.value)}
                                                        placeholder="Ex : P-104" className={inputCls} />
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Série</label>
                                                    <select value={d.series} data-testid={`pp-door-series-${idx}`}
                                                        onChange={(e) => changeSeries(d._key, e.target.value)}
                                                        className={`${inputCls} bg-white`}>
                                                        {PRODUCTION_SERIES.map((s) => <option key={s} value={s}>{s}</option>)}
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Configuration</label>
                                                    <select value={d.config} data-testid={`pp-door-config-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "config", e.target.value)}
                                                        className={`${inputCls} bg-white`}>
                                                        {PRODUCTION_CONFIGS.map((c) => <option key={c.v} value={c.v}>{c.lbl}</option>)}
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Quantité</label>
                                                    <input type="number" min="1" step="1" value={d.qty}
                                                        onChange={(e) => updateDoor(d._key, "qty", e.target.value)}
                                                        className={`${inputCls} text-right`} />
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Sens d&apos;ouverture (main)</label>
                                                    <select value={d.handing || "MD"} data-testid={`pp-door-handing-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "handing", e.target.value)}
                                                        className={`${inputCls} bg-white`}>
                                                        {HANDING_OPTIONS.map((o) => <option key={o.v} value={o.v}>{o.lbl}</option>)}
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Ouverture — largeur (po)</label>
                                                    <input type="number" min="1" step="0.125" value={d.opening_width_in}
                                                        data-testid={`pp-door-width-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "opening_width_in", e.target.value)}
                                                        className={`${inputCls} text-right`} />
                                                    <span className="text-[10px] text-[#4b5d7a]">{inLabel(d.opening_width_in)}</span>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Ouverture — hauteur (po)</label>
                                                    <input type="number" min="1" step="0.125" value={d.opening_height_in}
                                                        data-testid={`pp-door-height-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "opening_height_in", e.target.value)}
                                                        className={`${inputCls} text-right`} />
                                                    <span className="text-[10px] text-[#4b5d7a]">{inLabel(d.opening_height_in)}</span>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Fab. — largeur (po, optionnel)</label>
                                                    <input type="number" min="0" step="0.125" value={d.fab_width_in}
                                                        data-testid={`pp-door-fabw-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "fab_width_in", e.target.value)}
                                                        className={`${inputCls} text-right`} />
                                                    <span className="text-[10px] text-[#4b5d7a]">{inLabel(d.fab_width_in)}</span>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Fab. — hauteur (po, optionnel)</label>
                                                    <input type="number" min="0" step="0.125" value={d.fab_height_in}
                                                        data-testid={`pp-door-fabh-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "fab_height_in", e.target.value)}
                                                        className={`${inputCls} text-right`} />
                                                    <span className="text-[10px] text-[#4b5d7a]">{inLabel(d.fab_height_in)}</span>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Échelle (note)</label>
                                                    <input type="text" value={d.scale_note}
                                                        onChange={(e) => updateDoor(d._key, "scale_note", e.target.value)}
                                                        placeholder="1:30" className={inputCls} />
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Vitrage</label>
                                                    <input type="text" value={d.glass}
                                                        onChange={(e) => updateDoor(d._key, "glass", e.target.value)}
                                                        placeholder="VT6 · 6mm trempé clair" className={inputCls} />
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Fini extérieur</label>
                                                    <input type="text" list="pp-finishes" value={d.finish_ext}
                                                        onChange={(e) => updateDoor(d._key, "finish_ext", e.target.value)}
                                                        className={inputCls} />
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Fini intérieur</label>
                                                    <input type="text" list="pp-finishes" value={d.finish_int}
                                                        onChange={(e) => updateDoor(d._key, "finish_int", e.target.value)}
                                                        className={inputCls} />
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Type de charnière</label>
                                                    <select value={d.hinge_type || "butt45"} data-testid={`pp-door-hingetype-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "hinge_type", e.target.value)}
                                                        className={`${inputCls} bg-white`}>
                                                        {HINGE_TYPES.map((h) => <option key={h.v} value={h.v}>{h.lbl}</option>)}
                                                    </select>
                                                </div>
                                                <div className="sm:col-span-2">
                                                    <label className={labelCls}>Charnières / pentures (détail)</label>
                                                    <input type="text" value={d.hinges}
                                                        onChange={(e) => updateDoor(d._key, "hinges", e.target.value)}
                                                        placeholder="Ex : 2 charnières continues HD" className={inputCls} />
                                                </div>
                                            </div>

                                            {/* Aluminium profiles (real dimensions from inventory) */}
                                            <div>
                                                <label className={labelCls}>Profilés d&apos;aluminium (dimensions réelles A.T. Fabrication)</label>
                                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                                    {[
                                                        ["Profilé tête", "profile_head", "head", catalog?.heads],
                                                        ["Profilé base", "profile_base", "base", catalog?.bases],
                                                        ["Montant charnière", "profile_hinge_stile", "hinge", catalog?.stiles],
                                                        ["Montant serrure/central", "profile_lock_stile", "lock", catalog?.stiles],
                                                    ].map(([lbl, field, key, opts]) => (
                                                        <div key={field}>
                                                            <label className={labelCls}>{lbl}</label>
                                                            <select value={effProfile(d, field, key)}
                                                                data-testid={`pp-door-${field}-${idx}`}
                                                                onChange={(e) => updateDoor(d._key, field, e.target.value)}
                                                                className={`${inputCls} bg-white`}>
                                                                {(opts || []).map((o) => (
                                                                    <option key={o.code} value={o.code}>{optLabel(o)}</option>
                                                                ))}
                                                            </select>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            {/* Hardware placement on the elevation (editable heights) */}
                                            <div>
                                                <label className={labelCls}>Quincaillerie sur le dessin (hauteurs modifiables · 0 = masquer)</label>
                                                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                                                    <div>
                                                        <label className={labelCls}>Battant actif (paire)</label>
                                                        <select value={d.active_leaf || "right"} data-testid={`pp-door-active-${idx}`}
                                                            onChange={(e) => updateDoor(d._key, "active_leaf", e.target.value)}
                                                            className={`${inputCls} bg-white`}>
                                                            <option value="right">Droite</option>
                                                            <option value="left">Gauche</option>
                                                        </select>
                                                    </div>
                                                    <div>
                                                        <label className={labelCls}>Haut. poignée (po)</label>
                                                        <input type="number" min="0" step="0.125" value={d.handle_height_in}
                                                            data-testid={`pp-door-handleh-${idx}`}
                                                            onChange={(e) => updateDoor(d._key, "handle_height_in", e.target.value)}
                                                            className={`${inputCls} text-right`} />
                                                    </div>
                                                    <div>
                                                        <label className={labelCls}>Long. poignée (po)</label>
                                                        <input type="number" min="0" step="0.5" value={d.handle_length_in}
                                                            onChange={(e) => updateDoor(d._key, "handle_length_in", e.target.value)}
                                                            className={`${inputCls} text-right`} />
                                                    </div>
                                                    <div>
                                                        <label className={labelCls}>Haut. serrure (po)</label>
                                                        <input type="number" min="0" step="0.125" value={d.lock_height_in}
                                                            data-testid={`pp-door-lockh-${idx}`}
                                                            onChange={(e) => updateDoor(d._key, "lock_height_in", e.target.value)}
                                                            className={`${inputCls} text-right`} />
                                                    </div>
                                                    <div>
                                                        <label className={labelCls}>Jeu sous porte (mm)</label>
                                                        <input type="number" min="0" step="0.5" value={d.undercut_mm}
                                                            onChange={(e) => updateDoor(d._key, "undercut_mm", e.target.value)}
                                                            className={`${inputCls} text-right`} />
                                                    </div>
                                                </div>
                                                <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer mt-2">
                                                    <input type="checkbox" data-testid={`pp-door-handleboth-${idx}`}
                                                        checked={!!d.handle_both}
                                                        onChange={(e) => updateDoor(d._key, "handle_both", e.target.checked)} />
                                                    Poignée sur les 2 battants (paire)
                                                </label>
                                                <div className="flex flex-wrap items-center gap-3 mt-2">
                                                    <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                        <input type="checkbox" data-testid={`pp-door-panic-${idx}`}
                                                            checked={!!d.panic_bar}
                                                            onChange={(e) => updateDoor(d._key, "panic_bar", e.target.checked)} />
                                                        Barre anti-panique (battant actif)
                                                    </label>
                                                    <label className="inline-flex items-center gap-1 text-sm text-[#0c182b]">
                                                        Haut. barre (po)
                                                        <input type="number" min="0" step="0.5" value={d.panic_height_in}
                                                            data-testid={`pp-door-panich-${idx}`}
                                                            onChange={(e) => updateDoor(d._key, "panic_height_in", e.target.value)}
                                                            className="w-20 px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                                    </label>
                                                </div>
                                            </div>

                                            {/* Hardware */}
                                            <div>
                                                <div className="flex items-center justify-between mb-1">
                                                    <label className={labelCls}>Quincaillerie (libre)</label>
                                                    <button onClick={() => addHw(d._key)}
                                                        className="text-[#1d4ed8] hover:underline text-xs inline-flex items-center gap-1"
                                                        data-testid={`pp-add-hw-${idx}`}>
                                                        <Plus className="w-3 h-3" /> Ajouter une ligne
                                                    </button>
                                                </div>
                                                <table className="w-full text-sm">
                                                    <thead className="text-[10px] uppercase text-[#4b5d7a] bg-[#f3f6fb]">
                                                        <tr>
                                                            <th className="text-left px-2 py-1 w-14">Qté</th>
                                                            <th className="text-left px-2 py-1">Description</th>
                                                            <th className="text-left px-2 py-1 w-36">N° de pièce</th>
                                                            <th className="text-center px-1 py-1 w-12">Actif</th>
                                                            <th className="text-center px-1 py-1 w-12">Inact.</th>
                                                            <th className="w-8"></th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {(d.hardware || []).map((h) => (
                                                            <tr key={h._key} className="border-b border-[#f3f6fb]">
                                                                <td className="px-1 py-1">
                                                                    <input type="text" value={h.qty}
                                                                        onChange={(e) => updateHw(d._key, h._key, "qty", e.target.value)}
                                                                        className="w-full px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                                                </td>
                                                                <td className="px-1 py-1">
                                                                    <input type="text" value={h.description}
                                                                        onChange={(e) => updateHw(d._key, h._key, "description", e.target.value)}
                                                                        placeholder="Ex : Barre panique 8400 AR"
                                                                        className="w-full px-2 py-1 border border-[#dde5f0] text-sm" />
                                                                </td>
                                                                <td className="px-1 py-1">
                                                                    <input type="text" value={h.part_number}
                                                                        onChange={(e) => updateHw(d._key, h._key, "part_number", e.target.value)}
                                                                        placeholder="Ex : 8400"
                                                                        className="w-full px-2 py-1 border border-[#dde5f0] text-sm font-mono" />
                                                                </td>
                                                                <td className="px-1 py-1 text-center">
                                                                    <input type="checkbox" data-testid={`pp-hw-active-${idx}`}
                                                                        checked={!!h.on_active}
                                                                        onChange={(e) => updateHw(d._key, h._key, "on_active", e.target.checked)} />
                                                                </td>
                                                                <td className="px-1 py-1 text-center">
                                                                    <input type="checkbox" data-testid={`pp-hw-inactive-${idx}`}
                                                                        checked={!!h.on_inactive}
                                                                        onChange={(e) => updateHw(d._key, h._key, "on_inactive", e.target.checked)} />
                                                                </td>
                                                                <td className="px-1 py-1 text-right">
                                                                    <button onClick={() => removeHw(d._key, h._key)}
                                                                        className="text-[#a31a1a] hover:bg-[#fde7e7] p-1">
                                                                        <Trash2 className="w-3.5 h-3.5" />
                                                                    </button>
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>

                                            <div>
                                                <label className={labelCls}>Note sur cette porte (optionnel)</label>
                                                <input type="text" value={d.notes}
                                                    onChange={(e) => updateDoor(d._key, "notes", e.target.value)}
                                                    placeholder="Ex : Préparer la quincaillerie sans installer."
                                                    className={inputCls} />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                    <datalist id="pp-finishes">
                        {PRODUCTION_FINISHES.map((f) => <option key={f} value={f} />)}
                    </datalist>
                    <div className="mt-2 text-xs text-[#4b5d7a]">
                        {form.doors.length} type(s) de porte · {totalDoors} unité(s) au total
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-wrap pt-3 border-t border-[#dde5f0]">
                    <button onClick={save} disabled={busy} data-testid="pp-save"
                        className="btn-primary !py-2 !px-4 !text-sm">
                        {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Enregistrement…</>
                              : <><Save className="w-4 h-4" /> {editingId ? "Mettre à jour" : "Enregistrer"}</>}
                    </button>
                    <button onClick={previewPdf} disabled={previewing} data-testid="pp-preview"
                        className="btn-secondary !py-2 !px-3 !text-sm">
                        {previewing ? <><Loader2 className="w-4 h-4 animate-spin" /> Génération…</>
                                    : <><Eye className="w-4 h-4" /> Aperçu PDF</>}
                    </button>
                    {editingId && (
                        <button onClick={() => downloadPdf(editingId)}
                            className="btn-secondary !py-2 !px-3 !text-sm" data-testid="pp-download">
                            <Download className="w-4 h-4" /> Télécharger PDF
                        </button>
                    )}
                </div>
            </div>

            {/* ─── List ───────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">Plans émis</h3>
                    <button onClick={reload} className="text-xs text-[#1d4ed8] hover:underline inline-flex items-center gap-1">
                        <RefreshCw className="w-3 h-3" /> Rafraîchir
                    </button>
                </div>
                {loading ? (
                    <div className="text-sm italic text-[#4b5d7a]">Chargement…</div>
                ) : plans.length === 0 ? (
                    <div className="text-sm italic text-[#4b5d7a]">Aucun plan émis pour l&apos;instant.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm" data-testid="pp-list-table">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                                <tr>
                                    <th className="text-left px-2 py-1.5">N°</th>
                                    <th className="text-left px-2 py-1.5">Projet</th>
                                    <th className="text-left px-2 py-1.5 hidden sm:table-cell">Client</th>
                                    <th className="text-right px-2 py-1.5">Portes</th>
                                    <th className="text-left px-2 py-1.5 hidden sm:table-cell">Date</th>
                                    <th className="text-left px-2 py-1.5">Statut</th>
                                    <th className="px-2 py-1.5"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {plans.map((p) => (
                                    <tr key={p.id} className="border-b border-[#f3f6fb] hover:bg-[#f7f9fc]">
                                        <td className="px-2 py-1.5 font-mono text-[#0c182b]">{p.plan_number}</td>
                                        <td className="px-2 py-1.5 text-[#0c182b]">
                                            <div>{p.project_name || "—"}</div>
                                            <div className="text-[10px] text-[#4b5d7a]"># {p.project_number || "—"}</div>
                                        </td>
                                        <td className="px-2 py-1.5 hidden sm:table-cell text-[#4b5d7a]">{p.client_name || "—"}</td>
                                        <td className="px-2 py-1.5 text-right font-bold text-[#0c182b]">{(p.doors || []).length}</td>
                                        <td className="px-2 py-1.5 text-[11px] text-[#4b5d7a] whitespace-nowrap hidden sm:table-cell">
                                            {p.date ? formatDate(p.date) : "—"}
                                        </td>
                                        <td className="px-2 py-1.5 text-[11px]">
                                            <span className="px-2 py-0.5 border border-[#dde5f0] bg-[#f3f6fb] text-[#0c182b] uppercase tracking-wider text-[9px]">
                                                {p.status || "brouillon"}
                                            </span>
                                        </td>
                                        <td className="px-2 py-1.5 text-right whitespace-nowrap">
                                            <button onClick={() => openEdit(p)} className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Modifier"
                                                data-testid={`pp-edit-${p.id}`}>
                                                <FileText className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => downloadPdf(p.id)} className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Télécharger PDF">
                                                <Download className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => removePlan(p.id)} className="p-1 hover:bg-[#fde7e7] text-[#a31a1a]" title="Supprimer">
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
        </div>
    );
};

export default ProductionPlansPanel;
