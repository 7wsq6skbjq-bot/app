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
    AlertCircle, CheckCircle2, Loader2, DraftingCompass, ChevronDown, ChevronUp, ChevronRight,
    Mail, Send, Package,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
    emptyProductionPlan, emptyProductionDoor, emptyHardwareLine,
    PRODUCTION_SERIES, PRODUCTION_CONFIGS, PRODUCTION_STATUSES, PRODUCTION_MENTIONS, PRODUCTION_FINISHES,
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
    const [hwCatalog, setHwCatalog] = useState([]);
    const [hwForm, setHwForm] = useState({ name: "", part_number: "", cost: "", price: "" });
    const [showHwMgr, setShowHwMgr] = useState(false);
    const [loading, setLoading] = useState(true);
    const [form, setForm] = useState(emptyProductionPlan());
    const [editingId, setEditingId] = useState(null);
    const [openDoor, setOpenDoor] = useState(null);
    const [busy, setBusy] = useState(false);
    const [previewing, setPreviewing] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");
    const [emailModal, setEmailModal] = useState(null); // null | plan
    const [emailTo, setEmailTo] = useState("");
    const [emailMsg, setEmailMsg] = useState("");
    const [emailSending, setEmailSending] = useState(false);
    const [emailError, setEmailError] = useState("");
    const formTopRef = useRef(null);
    // ── Master (LDP) integration ──
    const [masterModels, setMasterModels] = useState([]);
    const [masterRate, setMasterRate] = useState(50);
    const [masterHwMarkup, setMasterHwMarkup] = useState(0.35);
    const [hwSearch, setHwSearch] = useState({});
    const [hwResults, setHwResults] = useState({});
    const [pushing, setPushing] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const [{ data: models }, { data: params }] = await Promise.all([
                    http.get("/admin/master/door-models"),
                    http.get("/admin/master/params"),
                ]);
                setMasterModels(Array.isArray(models) ? models : []);
                const r = (params || []).find((p) => /TAUX HORAIRE/i.test(p.label));
                const q = (params || []).find((p) => /QUINCAILLERIE/i.test(p.label));
                if (r) setMasterRate(r.value);
                if (q) setMasterHwMarkup(q.value);
            } catch (_) { /* silent */ }
        })();
    }, [http]);

    // Cost/margin/sell for a door (screen only — never on PDF)
    const doorCost = useCallback((d) => {
        const laborCost = (Number(d.labor_hours) || 0) * masterRate;
        const mlCost = (Number(d.material_cost) || 0) + laborCost;
        const frameCost = Number(d.frame_cost) || 0;
        const frameLabor = (Number(d.frame_hours) || 0) * masterRate;
        const frameTot = frameCost + frameLabor;
        let hwCost = 0, hwSell = 0;
        for (const h of d.hardware || []) {
            if (h.included === false) continue;
            const q = parseFloat(String(h.qty || "1").replace(",", ".")) || 1;
            const c = Number(h.cost) || 0;
            const mp = h.margin_pct != null ? Number(h.margin_pct) : 35;
            hwCost += q * c;
            hwSell += q * c * (1 + mp / 100);
        }
        const profit = Number(d.profit_pct) || 0;   // fraction (0.6 = +60 %)
        const mlSell = mlCost * (1 + profit);
        const frameSell = frameTot * (1 + profit);
        const cost = Math.round((mlCost + frameTot + hwCost) * 100) / 100;
        const sell = Math.round((mlSell + frameSell + hwSell) * 100) / 100;
        const margin = Math.round((sell - cost) * 100) / 100;
        const marginPct = cost ? Math.round((margin / cost) * 1000) / 10 : 0;
        return { cost, sell, margin, marginPct, hwCost, mlCost, frameTot };
    }, [masterRate]);

    const projectTotals = useMemo(() => {
        let cost = 0, sell = 0;
        for (const d of form.doors || []) {
            const q = parseInt(d.qty, 10) || 1;
            const c = doorCost(d);
            cost += c.cost * q; sell += c.sell * q;
        }
        cost = Math.round(cost * 100) / 100; sell = Math.round(sell * 100) / 100;
        const margin = Math.round((sell - cost) * 100) / 100;
        const marginPct = cost ? Math.round((margin / cost) * 1000) / 10 : 0;
        return { cost, sell, margin, marginPct };
    }, [form.doors, doorCost]);

    // Apply a Master LDP model to a door: series, finish, config, hours, cost, default hardware
    const applyMasterModel = (dk, modelKey) => {
        const m = masterModels.find((x) => x.model_key === modelKey);
        if (!m) { updateDoor(dk, "master_model_key", ""); return; }
        const label = m.label || "";
        const seriesTok = (label.split(/[\s·]/)[0] || "").toUpperCase(); // AT1000 / ATI2000...
        const seriesMap = { AT1000: "AT1000", ATI1000: "ATi1000", AT2000: "AT2000", ATI2000: "ATi2000" };
        const series = seriesMap[seriesTok] || "AT1000";
        const config = /paire/i.test(label) ? "pair" : "simple";
        const finish = /noir/i.test(label) ? "Anodisé noir" : "Anodisé clair";
        const isIso = series.startsWith("ATi") || (/isol/i.test(label) && !/non[-\s]?isol/i.test(label));
        const hw = (m.hardware || []).map((h) => ({
            ...emptyHardwareLine(),
            qty: "1",
            description: h.description || "",
            part_number: h.code || "",
            cost: Number(h.cost) || 0,
            margin_pct: 35,
            unit_price: Math.round((Number(h.cost) || 0) * 1.35 * 100) / 100,
            included: true, from_master: true, on_active: true,
        }));
        setForm((f) => ({
            ...f,
            doors: f.doors.map((d) => (d._key === dk ? {
                ...d,
                master_model_key: modelKey,
                series, config,
                finish_ext: finish, finish_int: finish,
                thickness: isIso ? "2-1/4\"" : "1-3/4\"",
                cladding: isIso,
                material_cost: Number(m.material_cost) || 0,
                labor_hours: Number(m.labor_hours) || 3,
                profit_pct: m.profit_pct ?? 0.6,
                profile_head: "", profile_base: "",
                profile_hinge_stile: "", profile_lock_stile: "", profile_lock_stile_inactive: "",
                hardware: hw.length ? hw : d.hardware,
            } : d)),
        }));
    };

    // Master hardware search (per door)
    const searchMasterHw = (dk, q) => {
        setHwSearch((s) => ({ ...s, [dk]: q }));
        if (!q || q.trim().length < 2) { setHwResults((r) => ({ ...r, [dk]: [] })); return; }
        http.get(`/admin/master/hardware?q=${encodeURIComponent(q)}`)
            .then(({ data }) => setHwResults((r) => ({ ...r, [dk]: (data || []).slice(0, 8) })))
            .catch(() => {});
    };
    const addMasterHw = (dk, item) => {
        setForm((f) => ({
            ...f,
            doors: f.doors.map((d) => (d._key === dk ? {
                ...d,
                hardware: [...(d.hardware || []), {
                    ...emptyHardwareLine(),
                    description: item.description || "",
                    part_number: item.product_code || "",
                    cost: Number(item.unit_cost) || 0,
                    margin_pct: 35,
                    unit_price: Math.round((Number(item.unit_cost) || 0) * 1.35 * 100) / 100,
                    included: true, from_master: true, on_active: true,
                }],
            } : d)),
        }));
        setHwSearch((s) => ({ ...s, [dk]: "" }));
        setHwResults((r) => ({ ...r, [dk]: [] }));
    };

    const pushToQuote = async () => {
        if (!form.doors?.length) { setErrorMsg("Ajoutez au moins une porte."); return; }
        setPushing(true); setErrorMsg("");
        try {
            const FRAME_LABELS = { flush_iso: "Cadre Flush glazed isolé", flush_non_iso: "Cadre Flush glazed non isolé", tube_fin: "Cadre Tube à fin", adapteur: "Cadre Adapteur" };
            const items = [];
            (form.doors || []).forEach((d) => {
                const c = doorCost(d);
                const qty = parseInt(d.qty, 10) || 1;
                const label = `Porte ${d.tag || d.series} — ${d.series} ${d.config === "pair" ? "paire" : "simple"} ${d.opening_width_in}×${d.opening_height_in} (quincaillerie incluse)`;
                // Frame as a SEPARATE line (turnkey entrance = frame + door + threshold)
                const frameTot = c.frameTot || 0;
                const doorCostNoFrame = Math.round((c.cost - frameTot) * 100) / 100;
                const profit = Number(d.profit_pct) || 0;
                const frameSell = Math.round(frameTot * (1 + profit) * 100) / 100;
                const doorSellNoFrame = Math.round((c.sell - frameSell) * 100) / 100;
                items.push({ description: label, quantity: qty, unit_price: doorSellNoFrame, cost_price: doorCostNoFrame, cost_category: "Portes", product_id: null });
                if (d.frame_type && frameTot > 0) {
                    items.push({ description: `${FRAME_LABELS[d.frame_type] || "Cadre"} — pour porte ${d.tag || d.series}`, quantity: qty, unit_price: frameSell, cost_price: frameTot, cost_category: "Cadres", product_id: null });
                }
            });
            const { data } = await http.post("/admin/quotes", {
                customer_snapshot: {
                    name: form.client_name || form.project_name || "Client",
                    kind: "customer",
                    email: /\S+@\S+/.test(form.client_contact || "") ? form.client_contact : undefined,
                    address: form.client_address || undefined,
                    phone: form.client_phone || undefined,
                },
                date: todayISO(),
                valid_until: todayISO(),
                taxable: true,
                status: "brouillon",
                notes: `Généré depuis le dessin de production ${form.plan_number || ""} — ${form.project_name || ""}`.trim(),
                items,
            });
            setSuccessMsg(`Soumission SO-${String(data.number).padStart(4, "0")} créée avec ${items.length} porte(s) · vendant ${projectTotals.sell.toFixed(2)} $. Ouvre l'onglet Ventes ▸ Soumissions pour la finaliser.`);
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Échec de la création de la soumission.");
        } finally { setPushing(false); }
    };

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

    const reloadHwCatalog = useCallback(async () => {
        try {
            const { data } = await http.get("/admin/production-hardware");
            setHwCatalog(Array.isArray(data) ? data : []);
        } catch (_) { /* silent */ }
    }, [http]);

    useEffect(() => { reloadHwCatalog(); }, [reloadHwCatalog]);

    const saveHwCatalogItem = async () => {
        const name = (hwForm.name || "").trim();
        if (!name) return;
        try {
            await http.post("/admin/production-hardware",
                { name, part_number: (hwForm.part_number || "").trim(), cost: Number(hwForm.cost || 0) || 0, price: Number(hwForm.price || 0) || 0 });
            setHwForm({ name: "", part_number: "", cost: "", price: "" });
            await reloadHwCatalog();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'ajout au catalogue.");
        }
    };

    const deleteHwCatalogItem = async (id) => {
        try {
            await http.delete(`/admin/production-hardware/${id}`);
            await reloadHwCatalog();
        } catch (_) { /* silent */ }
    };

    const effProfile = (d, field, key) =>
        d[field] || catalog?.defaults?.[d.series]?.[key] || "";
    const optLabel = (o) => `${o.code} · ${o.face_mm} mm`;

    // per-item leaf selector (pairs only) — choose active/inactive leaf
    const leafSelect = (d, field, testid) => (
        d.config === "pair" ? (
            <select value={d[field] || "active"} data-testid={testid}
                onChange={(e) => updateDoor(d._key, field, e.target.value)}
                className="ml-1 px-1 py-0.5 border border-[#dde5f0] text-xs bg-white cursor-pointer">
                <option value="active">actif</option>
                <option value="inactive">inactif</option>
                <option value="both">les deux</option>
            </select>
        ) : null
    );

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
            profile_lock_stile_inactive: "",
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
    const moveHw = (dk, hk, dir) => setForm((f) => ({
        ...f,
        doors: f.doors.map((d) => {
            if (d._key !== dk) return d;
            const hw = [...(d.hardware || [])];
            const i = hw.findIndex((h) => h._key === hk);
            const j = i + dir;
            if (i < 0 || j < 0 || j >= hw.length) return d;
            [hw[i], hw[j]] = [hw[j], hw[i]];
            return { ...d, hardware: hw };
        }),
    }));
    const updateHw = (dk, hk, key, value) => setForm((f) => ({
        ...f,
        doors: f.doors.map((d) => (d._key === dk
            ? {
                ...d,
                hardware: (d.hardware || []).map((h) => {
                    if (h._key !== hk) return h;
                    const next = { ...h, [key]: value };
                    // Auto-recompute selling price when cost or margin % changes
                    if (key === "cost" || key === "margin_pct") {
                        const c = Number(next.cost) || 0;
                        const mp = next.margin_pct != null ? Number(next.margin_pct) : 35;
                        next.unit_price = Math.round(c * (1 + mp / 100) * 100) / 100;
                    }
                    return next;
                }),
            } : d)),
    }));

    // Auto-fill part number + cost + price when a description matches the catalog
    const onHwDescription = (dk, hk, value) => {
        setForm((f) => ({
            ...f,
            doors: f.doors.map((d) => (d._key === dk ? {
                ...d,
                hardware: (d.hardware || []).map((h) => {
                    if (h._key !== hk) return h;
                    const next = { ...h, description: value };
                    const match = hwCatalog.find(
                        (it) => (it.name || "").toLowerCase() === (value || "").trim().toLowerCase());
                    if (match) {
                        if (match.part_number) next.part_number = match.part_number;
                        const cost = Number(match.cost) || 0;
                        if (cost) next.cost = cost;
                        const mp = next.margin_pct != null ? Number(next.margin_pct) : 35;
                        next.unit_price = Number(match.price) > 0
                            ? Number(match.price)
                            : Math.round(cost * (1 + mp / 100) * 100) / 100;
                    }
                    return next;
                }),
            } : d)),
        }));
    };

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
        mention: form.mention || "Pour production",
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
        show_costs: !!form.show_costs,
        anonymous: !!form.anonymous,
        include_hardware_drawings: form.include_hardware_drawings !== false,
        drawing_pages: form.drawing_pages || null,
        status: form.status || "brouillon",
        notes: form.notes || "",
        doors: (form.doors || []).map((d) => ({
            tag: d.tag || "",
            master_model_key: d.master_model_key || "",
            material_cost: Number(d.material_cost || 0) || 0,
            labor_hours: Number(d.labor_hours || 0) || 0,
            profit_pct: Number(d.profit_pct ?? 0.6),
            thickness: d.thickness || "1-3/4\"",
            cladding: !!d.cladding,
            moulure: d.moulure || "AT1045",
            frame_type: d.frame_type || "",
            frame_cost: Number(d.frame_cost || 0) || 0,
            frame_hours: Number(d.frame_hours || 0) || 0,
            series: d.series || "AT1000",
            config: d.config || "simple",
            opening_width_in: Number(d.opening_width_in || 0) || 1,
            opening_height_in: Number(d.opening_height_in || 0) || 1,
            qty: parseInt(d.qty, 10) || 1,
            handing: d.handing || "MD",
            active_leaf: d.active_leaf || "right",
            leaf_active_width_in: Number(d.leaf_active_width_in || 0) || 0,
            leaf_inactive_width_in: Number(d.leaf_inactive_width_in || 0) || 0,
            fab_width_in: Number(d.fab_width_in || 0) || 0,
            fab_height_in: Number(d.fab_height_in || 0) || 0,
            handle_height_in: Number(d.handle_height_in ?? 34.5) || 0,
            handle_length_in: Number(d.handle_length_in ?? 9) || 0,
            handle_both: !!d.handle_both,
            lock_height_in: Number(d.lock_height_in ?? 40) || 0,
            panic_bar: !!d.panic_bar,
            panic_height_in: Number(d.panic_height_in ?? 40) || 0,
            no_hardware: !!d.no_hardware,
            show_handle: d.show_handle !== false,
            show_lock: d.show_lock !== false,
            lever: !!d.lever,
            lever_height_in: Number(d.lever_height_in ?? 40) || 0,
            push_paddle: !!d.push_paddle,
            paddle_height_in: Number(d.paddle_height_in ?? 40) || 0,
            protection_plate: !!d.protection_plate,
            plate_height_in: Number(d.plate_height_in ?? 40) || 0,
            flush_bolt: !!d.flush_bolt,
            door_closer: !!d.door_closer,
            closer_leaf: d.closer_leaf || "active",
            astragal: !!d.astragal,
            handle_leaf: d.handle_leaf || "active",
            lock_leaf: d.lock_leaf || "active",
            lever_leaf: d.lever_leaf || "active",
            paddle_leaf: d.paddle_leaf || "active",
            plate_leaf: d.plate_leaf || "active",
            panic_leaf: d.panic_leaf || "active",
            flush_leaf: d.flush_leaf || "inactive",
            undercut_mm: Number(d.undercut_mm ?? 17.5) || 0,
            finish_ext: d.finish_ext || "",
            finish_int: d.finish_int || "",
            glass: d.glass || "",
            glass_type: d.glass_type || "6mm",
            hinges: d.hinges || "",
            hinge_type: d.hinge_type || "butt45",
            profile_head: effProfile(d, "profile_head", "head"),
            profile_base: effProfile(d, "profile_base", "base"),
            profile_hinge_stile: effProfile(d, "profile_hinge_stile", "hinge"),
            profile_lock_stile: effProfile(d, "profile_lock_stile", "lock"),
            profile_lock_stile_inactive: effProfile(d, "profile_lock_stile_inactive", "lock_inactive"),
            scale_note: d.scale_note || "1:30",
            notes: d.notes || "",
            hardware: stripKeys((d.hardware || []).filter((h) => h.included !== false)).map((h) => ({
                qty: String(h.qty || "1"),
                description: h.description || "",
                part_number: h.part_number || "",
                note: h.note || "",
                unit_price: Number(h.unit_price || 0) || 0,
                cost: Number(h.cost || 0) || 0,
                margin_pct: Number(h.margin_pct ?? 35),
                included: true,
                from_master: !!h.from_master,
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

    const downloadHwReport = (id) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/production-plans/${id}/hardware-report?token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    // ─── Envoi du plan au client par courriel ────────────
    const openEmail = (plan) => {
        setEmailModal(plan);
        const contact = plan?.client_contact || "";
        setEmailTo(/\S+@\S+\.\S+/.test(contact) ? contact : "");
        setEmailMsg("");
        setEmailError("");
    };
    const sendEmail = async () => {
        if (!emailModal || !emailTo) return;
        setEmailSending(true);
        setEmailError("");
        try {
            await http.post(
                `/admin/production-plans/${emailModal.id}/send-email`,
                { to_email: emailTo, message: emailMsg || undefined },
            );
            setEmailModal(null);
            setSuccessMsg(`Dessin de production ${emailModal.plan_number} envoyé à ${emailTo}.`);
        } catch (e) {
            setEmailError(e?.response?.data?.detail || "Échec de l'envoi du courriel.");
        } finally {
            setEmailSending(false);
        }
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
                <h2 className="text-xl font-bold text-[#0c182b]">Dessin de production de porte</h2>
                <span className="text-xs text-[#4b5d7a]">
                    Choisis un modèle Master (LDP) : profilés, quincaillerie et coûts réels pré-remplis. Coûtant &amp; marge visibles à l&apos;écran, jamais sur le PDF client.
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
                        <label className={labelCls}>Mention</label>
                        <select value={form.mention || "Pour production"} data-testid="pp-mention"
                            onChange={(e) => setForm((f) => ({ ...f, mention: e.target.value }))}
                            className={`${inputCls} bg-white`}>
                            {PRODUCTION_MENTIONS.map((m) => <option key={m} value={m}>{m}</option>)}
                        </select>
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
                    <span className="w-px h-5 bg-[#dde5f0]" />
                    <label className="inline-flex items-center gap-2 text-sm text-[#8a5a00] cursor-pointer font-medium">
                        <input type="checkbox" data-testid="pp-show-costs" checked={!!form.show_costs}
                            onChange={(e) => setForm((f) => ({ ...f, show_costs: e.target.checked }))} />
                        Afficher les prix sur le plan (interne)
                    </label>
                    <span className="w-px h-5 bg-[#dde5f0]" />
                    <label className="inline-flex items-center gap-2 text-sm text-[#b3261e] cursor-pointer font-medium">
                        <input type="checkbox" data-testid="pp-anonymous" checked={!!form.anonymous}
                            onChange={(e) => setForm((f) => ({ ...f, anonymous: e.target.checked }))} />
                        Version anonyme (sous-traitance — sans marque Portech)
                    </label>
                    <span className="w-px h-5 bg-[#dde5f0]" />
                    <label className="inline-flex items-center gap-2 text-sm text-[#2f4f7f] cursor-pointer font-medium">
                        <input type="checkbox" data-testid="pp-hw-drawings" checked={form.include_hardware_drawings !== false}
                            onChange={(e) => setForm((f) => ({ ...f, include_hardware_drawings: e.target.checked }))} />
                        Joindre les dessins Adams Rite (auto. selon la quincaillerie)
                    </label>
                    <label className="inline-flex items-center gap-1 text-sm text-[#0c182b]">
                        Jeu Fab. (po)
                        <input type="number" step="0.0625" data-testid="pp-fab-allow" value={form.fab_allowance_in}
                            onChange={(e) => setForm((f) => ({ ...f, fab_allowance_in: e.target.value }))}
                            className="w-20 px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                    </label>
                </div>

                {/* Coûts & marge projet (interne — jamais sur le PDF) */}
                <div className="flex flex-wrap items-center gap-4 border-2 border-[#0c182b] bg-[#0c182b] text-white px-4 py-3" data-testid="pp-cost-banner">
                    <div className="text-[10px] uppercase tracking-wider text-[#8fb4ff]">Interne · jamais sur le PDF</div>
                    <div className="flex items-baseline gap-1"><span className="text-[#c3d2ea] text-xs">Coûtant</span><span className="font-display font-bold text-lg" data-testid="pp-total-cost">{projectTotals.cost.toFixed(2)} $</span></div>
                    <div className="flex items-baseline gap-1"><span className="text-[#4fd1c5] text-xs">Marge</span><span className="font-display font-bold text-lg text-[#4fd1c5]" data-testid="pp-total-margin">{projectTotals.margin.toFixed(2)} $ · {projectTotals.marginPct}%</span></div>
                    <div className="flex items-baseline gap-1"><span className="text-[#ffd27f] text-xs">Vendant</span><span className="font-display font-bold text-xl text-[#ffd27f]" data-testid="pp-total-sell">{projectTotals.sell.toFixed(2)} $</span></div>
                    <button onClick={pushToQuote} disabled={pushing} data-testid="pp-push-quote"
                        className="ml-auto tech-stamp px-4 py-2 bg-[#ffd27f] text-[#0c182b] font-bold flex items-center gap-1 disabled:opacity-50">
                        {pushing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Pousser vers soumission
                    </button>
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
                                            {/* Master model + live cost (interne) */}
                                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-[#eef3fb] border border-[#c5d4e7] p-3">
                                                <div className="sm:col-span-2">
                                                    <label className={labelCls}>Modèle Master (LDP) — pré-remplit profilés, quincaillerie &amp; coûts</label>
                                                    <select value={d.master_model_key || ""} data-testid={`pp-door-master-${idx}`}
                                                        onChange={(e) => applyMasterModel(d._key, e.target.value)}
                                                        className={`${inputCls} bg-white`}>
                                                        <option value="">— Choisir un modèle Master —</option>
                                                        {masterModels.map((m) => <option key={m.model_key} value={m.model_key}>{m.label}</option>)}
                                                    </select>
                                                </div>
                                                {(() => {
                                                    const c = doorCost(d);
                                                    return (
                                                        <div className="flex flex-col justify-end text-xs" data-testid={`pp-door-costpanel-${idx}`}>
                                                            <div className="flex justify-between"><span className="text-[#4b5d7a]">Coûtant unité</span><b>{c.cost.toFixed(2)} $</b></div>
                                                            <div className="flex justify-between text-[#0f6b3a]"><span>Marge</span><b>{c.margin.toFixed(2)} $ · {c.marginPct}%</b></div>
                                                            <div className="flex justify-between text-[#8a5a00]"><span>Vendant unité</span><b>{c.sell.toFixed(2)} $</b></div>
                                                        </div>
                                                    );
                                                })()}
                                                <div className="sm:col-span-3 grid grid-cols-3 gap-3">
                                                    <div>
                                                        <label className={labelCls}>Coût matériel ($)</label>
                                                        <input type="number" step="0.01" value={d.material_cost || 0}
                                                            data-testid={`pp-door-material-${idx}`}
                                                            onChange={(e) => updateDoor(d._key, "material_cost", Number(e.target.value))}
                                                            className={`${inputCls} text-right`} />
                                                    </div>
                                                    <div>
                                                        <label className={labelCls}>Heures M.O.</label>
                                                        <input type="number" step="0.5" value={d.labor_hours || 0}
                                                            data-testid={`pp-door-hours-${idx}`}
                                                            onChange={(e) => updateDoor(d._key, "labor_hours", Number(e.target.value))}
                                                            className={`${inputCls} text-right`} />
                                                    </div>
                                                    <div>
                                                        <label className={labelCls}>Marge matériel (%)</label>
                                                        <input type="number" step="1" value={Math.round((d.profit_pct ?? 0.6) * 100)}
                                                            data-testid={`pp-door-profit-${idx}`}
                                                            onChange={(e) => updateDoor(d._key, "profit_pct", (Number(e.target.value) || 0) / 100)}
                                                            className={`${inputCls} text-right`} />
                                                    </div>
                                                </div>
                                            </div>
                                            {/* Épaisseur · cladding · moulure · cadre */}
                                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[#f6efdc] border border-[#e6d9b3] p-3">
                                                <div>
                                                    <label className={labelCls}>Épaisseur</label>
                                                    <input type="text" value={d.thickness || ""} data-testid={`pp-door-thickness-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "thickness", e.target.value)}
                                                        className={inputCls} />
                                                </div>
                                                <div className="flex items-end pb-2">
                                                    <label className="flex items-center gap-2 text-xs text-[#4b5d7a]">
                                                        <input type="checkbox" checked={!!d.cladding}
                                                            data-testid={`pp-door-cladding-${idx}`}
                                                            onChange={(e) => updateDoor(d._key, "cladding", e.target.checked)} />
                                                        Cladding alu intérieur (ATi)
                                                    </label>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Moulure (suit le vitrage)</label>
                                                    <select value={d.moulure || "AT1045"} data-testid={`pp-door-moulure-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "moulure", e.target.value)}
                                                        className={inputCls}>
                                                        <option value="AT1045">AT1045 (simple)</option>
                                                        <option value="AT1050">AT1050 (isolé / thermos)</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Cadre (entrée complète)</label>
                                                    <select value={d.frame_type || ""} data-testid={`pp-door-frame-${idx}`}
                                                        onChange={(e) => updateDoor(d._key, "frame_type", e.target.value)}
                                                        className={inputCls}>
                                                        <option value="">— Aucun cadre —</option>
                                                        <option value="flush_iso">Flush glazed isolé</option>
                                                        <option value="flush_non_iso">Flush glazed non isolé</option>
                                                        <option value="tube_fin">Tube à fin</option>
                                                        <option value="adapteur">Adapteur</option>
                                                    </select>
                                                </div>
                                                {d.frame_type && (
                                                    <>
                                                        <div>
                                                            <label className={labelCls}>Coût cadre ($)</label>
                                                            <input type="number" step="0.01" value={d.frame_cost || 0}
                                                                data-testid={`pp-door-frame-cost-${idx}`}
                                                                onChange={(e) => updateDoor(d._key, "frame_cost", Number(e.target.value))}
                                                                className={`${inputCls} text-right`} />
                                                        </div>
                                                        <div>
                                                            <label className={labelCls}>Heures M.O. cadre</label>
                                                            <input type="number" step="0.5" value={d.frame_hours || 0}
                                                                data-testid={`pp-door-frame-hours-${idx}`}
                                                                onChange={(e) => updateDoor(d._key, "frame_hours", Number(e.target.value))}
                                                                className={`${inputCls} text-right`} />
                                                        </div>
                                                    </>
                                                )}
                                            </div>
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
                                                    <label className={labelCls}>Type de vitrage</label>
                                                    <select value={d.glass_type || "6mm"} data-testid={`pp-door-glasstype-${idx}`}
                                                        onChange={(e) => {
                                                            const gt = e.target.value;
                                                            setForm((f) => ({
                                                                ...f,
                                                                doors: f.doors.map((x) => (x._key === d._key
                                                                    ? { ...x, glass_type: gt, moulure: gt === "6mm" ? "AT1045" : "AT1050" }
                                                                    : x)),
                                                            }));
                                                        }}
                                                        className={`${inputCls} bg-white`}>
                                                        <option value="6mm">Vitré 6 mm</option>
                                                        <option value="tht">Thermos 25,4 mm (THT)</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className={labelCls}>Vitrage (note)</label>
                                                    <input type="text" value={d.glass}
                                                        onChange={(e) => updateDoor(d._key, "glass", e.target.value)}
                                                        placeholder="VT6 · trempé clair" className={inputCls} />
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
                                                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                                                    {[
                                                        ["Profilé tête", "profile_head", "head", catalog?.heads],
                                                        ["Profilé base", "profile_base", "base", catalog?.bases],
                                                        ["Montant charnière", "profile_hinge_stile", "hinge", catalog?.stiles],
                                                        ["Montant serrure (actif)", "profile_lock_stile", "lock", catalog?.stiles],
                                                        ["Montant serrure (inactif)", "profile_lock_stile_inactive", "lock_inactive", catalog?.stiles],
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
                                                    {d.config === "pair" && (
                                                        <>
                                                            <div>
                                                                <label className={labelCls}>Batt. actif — larg. (po)</label>
                                                                <input type="number" min="0" step="0.125" value={d.leaf_active_width_in}
                                                                    data-testid={`pp-door-leaf-active-${idx}`}
                                                                    onChange={(e) => updateDoor(d._key, "leaf_active_width_in", e.target.value)}
                                                                    className={`${inputCls} text-right`} />
                                                                <span className="text-[10px] text-[#4b5d7a]">{inLabel(d.leaf_active_width_in)}</span>
                                                            </div>
                                                            <div>
                                                                <label className={labelCls}>Batt. inactif — larg. (po)</label>
                                                                <input type="number" min="0" step="0.125" value={d.leaf_inactive_width_in}
                                                                    data-testid={`pp-door-leaf-inactive-${idx}`}
                                                                    onChange={(e) => updateDoor(d._key, "leaf_inactive_width_in", e.target.value)}
                                                                    className={`${inputCls} text-right`} />
                                                                <span className="text-[10px] text-[#4b5d7a]">{inLabel(d.leaf_inactive_width_in)}</span>
                                                            </div>
                                                            <div className="col-span-2 sm:col-span-5 text-[10px] text-[#4b5d7a] -mt-1">
                                                                Laissez un champ à 0 pour l&apos;auto-compléter (ouverture − autre battant). Les deux à 0 = partage 50/50.
                                                            </div>
                                                        </>
                                                    )}
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
                                                <div className="mt-3 border border-[#dde5f0] bg-[#f7f9fc] p-2 space-y-2">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider">Afficher sur le dessin</span>
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#a31a1a] cursor-pointer font-medium">
                                                            <input type="checkbox" data-testid={`pp-door-nohw-${idx}`}
                                                                checked={!!d.no_hardware}
                                                                onChange={(e) => updateDoor(d._key, "no_hardware", e.target.checked)} />
                                                            Aucune quincaillerie
                                                        </label>
                                                    </div>
                                                    <div className={`flex flex-wrap items-center gap-x-5 gap-y-2 ${d.no_hardware ? "opacity-40 pointer-events-none" : ""}`}>
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-showhandle-${idx}`}
                                                                checked={d.show_handle !== false}
                                                                onChange={(e) => updateDoor(d._key, "show_handle", e.target.checked)} />
                                                            Poignée
                                                        </label>
                                                        {d.show_handle !== false && leafSelect(d, "handle_leaf", `pp-door-handleleaf-${idx}`)}
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-handleboth-${idx}`}
                                                                checked={!!d.handle_both}
                                                                onChange={(e) => updateDoor(d._key, "handle_both", e.target.checked)} />
                                                            Poignée sur 2 battants
                                                        </label>
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-showlock-${idx}`}
                                                                checked={d.show_lock !== false}
                                                                onChange={(e) => updateDoor(d._key, "show_lock", e.target.checked)} />
                                                            Serrure / cylindre
                                                        </label>
                                                        {d.show_lock !== false && leafSelect(d, "lock_leaf", `pp-door-lockleaf-${idx}`)}
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-lever-${idx}`}
                                                                checked={!!d.lever}
                                                                onChange={(e) => updateDoor(d._key, "lever", e.target.checked)} />
                                                            Levier (Adams Rite)
                                                        </label>
                                                        {d.lever && leafSelect(d, "lever_leaf", `pp-door-leverleaf-${idx}`)}
                                                        {d.lever && (
                                                            <label className="inline-flex items-center gap-1 text-xs text-[#4b5d7a]">
                                                                Haut. (po)
                                                                <input type="number" min="0" step="0.5" value={d.lever_height_in}
                                                                    data-testid={`pp-door-leverh-${idx}`}
                                                                    onChange={(e) => updateDoor(d._key, "lever_height_in", e.target.value)}
                                                                    className="w-16 px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                                            </label>
                                                        )}
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-paddle-${idx}`}
                                                                checked={!!d.push_paddle}
                                                                onChange={(e) => updateDoor(d._key, "push_paddle", e.target.checked)} />
                                                            Palette de relâche
                                                        </label>
                                                        {d.push_paddle && leafSelect(d, "paddle_leaf", `pp-door-paddleleaf-${idx}`)}
                                                        {d.push_paddle && (
                                                            <label className="inline-flex items-center gap-1 text-xs text-[#4b5d7a]">
                                                                Haut. (po)
                                                                <input type="number" min="0" step="0.5" value={d.paddle_height_in}
                                                                    data-testid={`pp-door-paddleh-${idx}`}
                                                                    onChange={(e) => updateDoor(d._key, "paddle_height_in", e.target.value)}
                                                                    className="w-16 px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                                            </label>
                                                        )}
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-plate-${idx}`}
                                                                checked={!!d.protection_plate}
                                                                onChange={(e) => updateDoor(d._key, "protection_plate", e.target.checked)} />
                                                            Plaque de protection (KROME)
                                                        </label>
                                                        {d.protection_plate && leafSelect(d, "plate_leaf", `pp-door-plateleaf-${idx}`)}
                                                        {d.protection_plate && (
                                                            <label className="inline-flex items-center gap-1 text-xs text-[#4b5d7a]">
                                                                Haut. (po)
                                                                <input type="number" min="0" step="0.5" value={d.plate_height_in}
                                                                    data-testid={`pp-door-plateh-${idx}`}
                                                                    onChange={(e) => updateDoor(d._key, "plate_height_in", e.target.value)}
                                                                    className="w-16 px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                                            </label>
                                                        )}
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-flushbolt-${idx}`}
                                                                checked={!!d.flush_bolt}
                                                                onChange={(e) => updateDoor(d._key, "flush_bolt", e.target.checked)} />
                                                            Verrou affleuré
                                                        </label>
                                                        {d.flush_bolt && leafSelect(d, "flush_leaf", `pp-door-flushleaf-${idx}`)}
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-panic-${idx}`}
                                                                checked={!!d.panic_bar}
                                                                onChange={(e) => updateDoor(d._key, "panic_bar", e.target.checked)} />
                                                            Barre anti-panique
                                                        </label>
                                                        {d.panic_bar && leafSelect(d, "panic_leaf", `pp-door-panicleaf-${idx}`)}
                                                        {d.panic_bar && (
                                                            <label className="inline-flex items-center gap-1 text-xs text-[#4b5d7a]">
                                                                Haut. barre (po)
                                                                <input type="number" min="0" step="0.5" value={d.panic_height_in}
                                                                    data-testid={`pp-door-panich-${idx}`}
                                                                    onChange={(e) => updateDoor(d._key, "panic_height_in", e.target.value)}
                                                                    className="w-16 px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                                            </label>
                                                        )}
                                                        <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                            <input type="checkbox" data-testid={`pp-door-closer-${idx}`}
                                                                checked={!!d.door_closer}
                                                                onChange={(e) => updateDoor(d._key, "door_closer", e.target.checked)} />
                                                            Ferme-porte
                                                        </label>
                                                        {d.door_closer && leafSelect(d, "closer_leaf", `pp-door-closerleaf-${idx}`)}
                                                        {d.config === "pair" && (
                                                            <label className="inline-flex items-center gap-2 text-sm text-[#0c182b] cursor-pointer">
                                                                <input type="checkbox" data-testid={`pp-door-astragal-${idx}`}
                                                                    checked={!!d.astragal}
                                                                    onChange={(e) => updateDoor(d._key, "astragal", e.target.checked)} />
                                                                Astragale
                                                            </label>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Hardware */}
                                            <div>
                                                <div className="flex items-center justify-between mb-1 gap-2 flex-wrap">
                                                    <label className={labelCls}>Quincaillerie (Master — décoche pour retirer)</label>
                                                    <div className="flex items-center gap-2">
                                                        <div className="relative">
                                                            <input type="text" value={hwSearch[d._key] || ""}
                                                                data-testid={`pp-hw-master-search-${idx}`}
                                                                onChange={(e) => searchMasterHw(d._key, e.target.value)}
                                                                placeholder="Rechercher Master (nom / nº pièce)…"
                                                                className="px-2 py-1 border border-[#c5d4e7] text-xs w-64" />
                                                            {(hwResults[d._key] || []).length > 0 && (
                                                                <div className="absolute z-20 right-0 left-0 mt-0.5 bg-white border border-[#dde5f0] shadow-lg max-h-56 overflow-auto">
                                                                    {(hwResults[d._key] || []).map((r) => (
                                                                        <button type="button" key={r.id} onClick={() => addMasterHw(d._key, r)}
                                                                            className="block w-full text-left px-2 py-1.5 text-xs hover:bg-[#eaf1fb] border-b border-[#f0f3f8]">
                                                                            {r.description} <span className="font-mono text-[#2f4f7f]">{r.product_code}</span> — {(Number(r.unit_cost) || 0).toFixed(2)} $
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                        <button onClick={() => addHw(d._key)}
                                                            className="text-[#1d4ed8] hover:underline text-xs inline-flex items-center gap-1"
                                                            data-testid={`pp-add-hw-${idx}`}>
                                                            <Plus className="w-3 h-3" /> Ligne libre
                                                        </button>
                                                    </div>
                                                </div>
                                                <table className="w-full text-sm">
                                                    <thead className="text-[10px] uppercase text-[#4b5d7a] bg-[#f3f6fb]">
                                                        <tr>
                                                            <th className="text-center px-1 py-1 w-10">Inclus</th>
                                                            <th className="text-left px-2 py-1 w-14">Qté</th>
                                                            <th className="text-left px-2 py-1">Description</th>
                                                            <th className="text-left px-2 py-1 w-32">N° de pièce</th>
                                                            <th className="text-right px-2 py-1 w-20">Coût ($)</th>
                                                            <th className="text-right px-2 py-1 w-16">Marge %</th>
                                                            <th className="text-right px-2 py-1 w-20">Prix U. ($)</th>
                                                            <th className="text-center px-1 py-1 w-12">Actif</th>
                                                            <th className="text-center px-1 py-1 w-12">Inact.</th>
                                                            <th className="w-8"></th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {(d.hardware || []).map((h, hi) => (
                                                            <tr key={h._key} className={`border-b border-[#f3f6fb] ${h.included === false ? "opacity-40" : ""}`}>
                                                                <td className="px-1 py-1 text-center">
                                                                    <input type="checkbox" data-testid={`pp-hw-incl-${idx}`}
                                                                        checked={h.included !== false}
                                                                        onChange={(e) => updateHw(d._key, h._key, "included", e.target.checked)} />
                                                                </td>
                                                                <td className="px-1 py-1">
                                                                    <input type="text" value={h.qty}
                                                                        onChange={(e) => updateHw(d._key, h._key, "qty", e.target.value)}
                                                                        className="w-full px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                                                </td>
                                                                <td className="px-1 py-1">
                                                                    <input type="text" value={h.description} list="pp-hw-catalog"
                                                                        data-testid={`pp-hw-desc-${idx}`}
                                                                        onChange={(e) => onHwDescription(d._key, h._key, e.target.value)}
                                                                        placeholder="Choisir ou taper — ex : Barre panique 8400 AR"
                                                                        className="w-full px-2 py-1 border border-[#dde5f0] text-sm" />
                                                                </td>
                                                                <td className="px-1 py-1">
                                                                    <input type="text" value={h.part_number}
                                                                        onChange={(e) => updateHw(d._key, h._key, "part_number", e.target.value)}
                                                                        placeholder="Ex : 8400"
                                                                        className="w-full px-2 py-1 border border-[#dde5f0] text-sm font-mono" />
                                                                </td>
                                                                <td className="px-1 py-1">
                                                                    <input type="number" min="0" step="0.01" value={h.cost ?? 0}
                                                                        data-testid={`pp-hw-cost-${idx}`}
                                                                        onChange={(e) => updateHw(d._key, h._key, "cost", Number(e.target.value))}
                                                                        className="w-full px-2 py-1 border border-[#e6d9b3] bg-[#fffdf5] text-sm text-right" />
                                                                </td>
                                                                <td className="px-1 py-1">
                                                                    <input type="number" min="0" step="1" value={h.margin_pct ?? 35}
                                                                        data-testid={`pp-hw-margin-${idx}`}
                                                                        onChange={(e) => updateHw(d._key, h._key, "margin_pct", Number(e.target.value))}
                                                                        className="w-full px-2 py-1 border border-[#e6d9b3] bg-[#fffdf5] text-sm text-right" />
                                                                </td>
                                                                <td className="px-1 py-1">
                                                                    <input type="number" min="0" step="0.01" value={h.unit_price ?? 0}
                                                                        data-testid={`pp-hw-price-${idx}`}
                                                                        onChange={(e) => updateHw(d._key, h._key, "unit_price", e.target.value)}
                                                                        className="w-full px-2 py-1 border border-[#dde5f0] text-sm text-right" />
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
                                                                <td className="px-1 py-1 text-right whitespace-nowrap">
                                                                    <button type="button" onClick={() => moveHw(d._key, h._key, -1)}
                                                                        disabled={hi === 0} title="Monter"
                                                                        data-testid={`pp-hw-up-${idx}-${hi}`}
                                                                        className="text-[#2f4f7f] hover:bg-[#eaf1fb] p-1 disabled:opacity-25 disabled:cursor-not-allowed">
                                                                        <ChevronUp className="w-3.5 h-3.5" />
                                                                    </button>
                                                                    <button type="button" onClick={() => moveHw(d._key, h._key, 1)}
                                                                        disabled={hi === (d.hardware || []).length - 1} title="Descendre"
                                                                        data-testid={`pp-hw-down-${idx}-${hi}`}
                                                                        className="text-[#2f4f7f] hover:bg-[#eaf1fb] p-1 disabled:opacity-25 disabled:cursor-not-allowed">
                                                                        <ChevronDown className="w-3.5 h-3.5" />
                                                                    </button>
                                                                    <button onClick={() => removeHw(d._key, h._key)} title="Supprimer"
                                                                        className="text-[#a31a1a] hover:bg-[#fde7e7] p-1">
                                                                        <Trash2 className="w-3.5 h-3.5" />
                                                                    </button>
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                    <tfoot>
                                                        <tr className="border-t border-[#dde5f0] bg-[#fff8e6]">
                                                            <td colSpan={4} className="px-2 py-1 text-right text-xs font-bold text-[#8a5a00]">
                                                                Coût quincaillerie incluse (interne)
                                                            </td>
                                                            <td className="px-2 py-1 text-right text-xs font-bold text-[#8a5a00]" data-testid={`pp-door-cost-${idx}`}>
                                                                {(() => {
                                                                    const t = (d.hardware || []).reduce((s, h) => {
                                                                        if (h.included === false) return s;
                                                                        const q = parseFloat(String(h.qty || "1").replace(",", ".")) || 1;
                                                                        return s + q * (Number(h.cost) || 0);
                                                                    }, 0);
                                                                    return t > 0 ? `${t.toFixed(2)} $` : "—";
                                                                })()}
                                                            </td>
                                                            <td colSpan={5}></td>
                                                        </tr>
                                                    </tfoot>
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
                    <datalist id="pp-hw-catalog">
                        {hwCatalog.map((it) => (
                            <option key={it.id} value={it.name}>
                                {it.part_number ? `${it.part_number}` : ""}
                            </option>
                        ))}
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
                    {editingId && (
                        <button onClick={() => downloadHwReport(editingId)}
                            className="btn-secondary !py-2 !px-3 !text-sm" data-testid="pp-hw-report">
                            <Package className="w-4 h-4" /> Rapport quincaillerie
                        </button>
                    )}
                    {editingId && (
                        <button onClick={() => openEmail({ id: editingId, plan_number: form.plan_number, client_contact: form.client_contact })}
                            className="btn-secondary !py-2 !px-3 !text-sm" data-testid="pp-email-editor">
                            <Mail className="w-4 h-4" /> Envoyer au client
                        </button>
                    )}
                </div>
            </div>

            {/* ─── Hardware catalog manager ─────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4" data-testid="pp-hw-catalog-card">
                <button type="button" onClick={() => setShowHwMgr((v) => !v)}
                    className="w-full flex items-center gap-2 text-left" data-testid="pp-hw-mgr-toggle">
                    {showHwMgr ? <ChevronDown className="w-4 h-4 text-[#4b5d7a]" />
                              : <ChevronRight className="w-4 h-4 text-[#4b5d7a]" />}
                    <h3 className="tech-stamp text-[#0c182b] font-bold">Catalogue de quincaillerie</h3>
                    <span className="text-xs text-[#4b5d7a]">
                        {hwCatalog.length} produit(s) · réutilisables dans le menu déroulant
                    </span>
                </button>
                {showHwMgr && (
                    <div className="mt-3 space-y-3">
                        <div className="flex flex-wrap items-end gap-2">
                            <div className="flex-1 min-w-[200px]">
                                <label className={labelCls}>Nom / description</label>
                                <input type="text" value={hwForm.name} data-testid="pp-hw-new-name"
                                    onChange={(e) => setHwForm((f) => ({ ...f, name: e.target.value }))}
                                    placeholder="Ex : Barre panique Von Duprin 99" className={inputCls} />
                            </div>
                            <div className="w-40">
                                <label className={labelCls}>N° de pièce</label>
                                <input type="text" value={hwForm.part_number} data-testid="pp-hw-new-pn"
                                    onChange={(e) => setHwForm((f) => ({ ...f, part_number: e.target.value }))}
                                    placeholder="Ex : 9957" className={`${inputCls} font-mono`} />
                            </div>
                            <div className="w-28">
                                <label className={labelCls}>Coût ($)</label>
                                <input type="number" min="0" step="0.01" value={hwForm.cost} data-testid="pp-hw-new-cost"
                                    onChange={(e) => setHwForm((f) => ({ ...f, cost: e.target.value }))}
                                    placeholder="0.00" className={`${inputCls} text-right`} />
                            </div>
                            <div className="w-28">
                                <label className={labelCls}>Prix vente ($)</label>
                                <input type="number" min="0" step="0.01" value={hwForm.price} data-testid="pp-hw-new-price"
                                    onChange={(e) => setHwForm((f) => ({ ...f, price: e.target.value }))}
                                    placeholder="0.00" className={`${inputCls} text-right`} />
                            </div>
                            <button onClick={saveHwCatalogItem} data-testid="pp-hw-add"
                                className="btn-secondary !py-2 !px-3 !text-sm">
                                <Plus className="w-4 h-4" /> Ajouter
                            </button>
                        </div>
                        {hwCatalog.length === 0 ? (
                            <div className="text-sm italic text-[#4b5d7a]">
                                Aucun produit. Les descriptions saisies sur un plan s&apos;ajoutent aussi automatiquement ici.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm" data-testid="pp-hw-catalog-table">
                                    <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                                        <tr>
                                            <th className="text-left px-2 py-1.5">Nom / description</th>
                                            <th className="text-left px-2 py-1.5 w-40">N° de pièce</th>
                                            <th className="text-right px-2 py-1.5 w-20">Coût ($)</th>
                                            <th className="text-right px-2 py-1.5 w-24">Vente ($)</th>
                                            <th className="px-2 py-1.5 w-10"></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {hwCatalog.map((it) => (
                                            <tr key={it.id} className="border-b border-[#f3f6fb] hover:bg-[#f7f9fc]">
                                                <td className="px-2 py-1.5 text-[#0c182b]">{it.name}</td>
                                                <td className="px-2 py-1.5 font-mono text-[#4b5d7a]">{it.part_number || "—"}</td>
                                                <td className="px-2 py-1.5 text-right text-[#4b5d7a]">{it.cost ? `${Number(it.cost).toFixed(2)}` : "—"}</td>
                                                <td className="px-2 py-1.5 text-right text-[#4b5d7a]">{it.price ? `${Number(it.price).toFixed(2)}` : "—"}</td>
                                                <td className="px-2 py-1.5 text-right">
                                                    <button onClick={() => deleteHwCatalogItem(it.id)}
                                                        className="p-1 hover:bg-[#fde7e7] text-[#a31a1a]" title="Supprimer"
                                                        data-testid={`pp-hw-del-${it.id}`}>
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
                )}
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
                                            <button onClick={() => downloadHwReport(p.id)} className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Rapport de quincaillerie consommée"
                                                data-testid={`pp-hw-report-${p.id}`}>
                                                <Package className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => openEmail(p)} className="p-1 hover:bg-[#eaf1fb] text-[#2f4f7f]" title="Envoyer au client par courriel"
                                                data-testid={`pp-email-${p.id}`}>
                                                <Mail className="w-3.5 h-3.5" />
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

            {/* ─── Modale d'envoi au client ─────────────────── */}
            {emailModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
                    data-testid="pp-email-modal" onClick={() => !emailSending && setEmailModal(null)}>
                    <div className="bg-white border border-[#dde5f0] w-full max-w-lg shadow-xl"
                        onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-5 py-3 border-b border-[#dde5f0] bg-[#f7f9fc]">
                            <h3 className="tech-stamp text-[#0c182b] font-bold">
                                Envoyer le dessin de production {emailModal.plan_number || ""}
                            </h3>
                            <button onClick={() => !emailSending && setEmailModal(null)}
                                className="text-[#4b5d7a] hover:text-[#0c182b] text-xl leading-none">×</button>
                        </div>
                        <div className="p-5 space-y-4">
                            <p className="text-sm text-[#4b5d7a]">
                                Le PDF du dessin de production <strong className="text-[#0c182b]">enregistré</strong> sera
                                envoyé en pièce jointe au client via Resend (info@portech.info).
                                Enregistrez d&apos;abord vos modifications pour les inclure.
                            </p>
                            <div>
                                <label className={labelCls}>Adresse courriel destinataire *</label>
                                <input type="email" value={emailTo}
                                    onChange={(e) => setEmailTo(e.target.value)}
                                    placeholder="client@exemple.ca" className={inputCls}
                                    data-testid="pp-email-to" required />
                            </div>
                            <div>
                                <label className={labelCls}>Message personnalisé (optionnel)</label>
                                <textarea rows={4} value={emailMsg}
                                    onChange={(e) => setEmailMsg(e.target.value)}
                                    placeholder="Bonjour, vous trouverez ci-joint le dessin de production…"
                                    className={inputCls} data-testid="pp-email-message" />
                            </div>
                            {emailError && (
                                <div className="p-3 border border-red-400 bg-red-50 text-red-800 text-sm"
                                    data-testid="pp-email-error">{emailError}</div>
                            )}
                        </div>
                        <div className="flex justify-end gap-2 px-5 py-3 border-t border-[#dde5f0] bg-[#f7f9fc]">
                            <button onClick={() => setEmailModal(null)} disabled={emailSending}
                                className="btn-secondary !py-2 !px-4 !text-sm">Annuler</button>
                            <button onClick={sendEmail} disabled={!emailTo || emailSending}
                                className="btn-primary !py-2 !px-4 !text-sm disabled:opacity-40"
                                data-testid="pp-email-send">
                                {emailSending
                                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Envoi…</>
                                    : <><Send className="w-4 h-4" /> Envoyer le PDF</>}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProductionPlansPanel;
