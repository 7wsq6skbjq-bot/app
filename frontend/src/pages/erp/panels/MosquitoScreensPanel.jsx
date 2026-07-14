/** Moustiquaires — fabrication orders panel.
 *
 *  Lets Cédrick capture a list of mosquito screens (dimensions, qty, frame,
 *  mesh, attachment) and either fabricate in-house or send a branded
 *  "Bon de fabrication moustiquaires" PDF to a supplier by email.
 *
 *  Lives inside the Fabrication tab, alongside the classic Cut-list panel.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    Plus, Save, Trash2, RefreshCw, Download, Send, FileText,
    AlertCircle, CheckCircle2, Loader2, Bug,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
    emptyMosquitoScreen, emptyMosquitoScreenItem,
    MOSQUITO_FRAME_COLORS, MOSQUITO_MESH_TYPES, MOSQUITO_ATTACHMENT_TYPES,
    MOSQUITO_SCREEN_STATUSES,
    emptyParty, formatDate, newKey, stripKeys, todayISO,
} from "../utils";

export const MosquitoScreensPanel = () => {
    const { http, getToken } = useAuth();
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [form, setForm] = useState(emptyMosquitoScreen());
    const [editingId, setEditingId] = useState(null);
    const [suppliers, setSuppliers] = useState([]);
    const [supplierQuery, setSupplierQuery] = useState("");
    const [showSupplierSuggest, setShowSupplierSuggest] = useState(false);
    const [busy, setBusy] = useState(false);
    const [sendingId, setSendingId] = useState(null);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");
    const formTopRef = useRef(null);

    // ─── Load ───────────────────────────────────────────────
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [o, s] = await Promise.all([
                    http.get("/admin/mosquito-screens"),
                    http.get("/admin/parties?kind=supplier"),
                ]);
                if (!cancelled) {
                    setOrders(Array.isArray(o.data) ? o.data : []);
                    setSuppliers(Array.isArray(s.data) ? s.data : []);
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
            const { data } = await http.get("/admin/mosquito-screens");
            setOrders(Array.isArray(data) ? data : []);
        } catch (_) { /* silent */ }
    }, [http]);

    // ─── Supplier autocomplete ───────────────────────────
    const supplierSuggestions = useMemo(() => {
        const q = (supplierQuery || form.supplier_snapshot?.name || "").trim().toLowerCase();
        if (!q || q.length < 2) return [];
        return suppliers.filter((p) =>
            (p.name || "").toLowerCase().includes(q) ||
            (p.email || "").toLowerCase().includes(q),
        ).slice(0, 6);
    }, [supplierQuery, form.supplier_snapshot, suppliers]);

    const pickSupplier = (p) => {
        setForm((f) => ({
            ...f,
            supplier_id: p.id,
            supplier_snapshot: { ...emptyParty("supplier"), ...p },
        }));
        setSupplierQuery(p.name || "");
        setShowSupplierSuggest(false);
    };

    const updateSupplierField = (key, value) => {
        setForm((f) => ({
            ...f,
            supplier_id: null,
            supplier_snapshot: { ...(f.supplier_snapshot || emptyParty("supplier")), [key]: value },
        }));
    };

    // ─── Items ───────────────────────────────────────────
    const addItem = () => setForm((f) => ({
        ...f, items: [...f.items, emptyMosquitoScreenItem()],
    }));
    const removeItem = (k) => setForm((f) => ({
        ...f, items: f.items.filter((it) => it._key !== k),
    }));
    const updateItem = (k, key, value) => setForm((f) => ({
        ...f,
        items: f.items.map((it) => (it._key === k ? { ...it, [key]: value } : it)),
    }));

    const totalQty = useMemo(
        () => form.items.reduce((s, it) => s + (parseInt(it.qty, 10) || 0), 0),
        [form.items],
    );

    // ─── New / edit / save / delete ─────────────────────
    const newOrder = () => {
        setForm(emptyMosquitoScreen());
        setSupplierQuery("");
        setEditingId(null);
        setSuccessMsg("");
        setErrorMsg("");
        formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    const openEdit = (o) => {
        setForm({
            ...o,
            supplier_snapshot: o.supplier_snapshot || emptyParty("supplier"),
            items: (o.items || []).map((it) => ({ ...it, _key: newKey() })),
            needed_by: o.needed_by || "",
        });
        setSupplierQuery(o.supplier_snapshot?.name || "");
        setEditingId(o.id);
        setSuccessMsg("");
        setErrorMsg("");
        formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    const save = async () => {
        if (!form.items?.length) {
            setErrorMsg("Au moins une moustiquaire est requise.");
            return;
        }
        if (form.mode === "fournisseur" && !form.supplier_snapshot?.name) {
            setErrorMsg("Le nom du fournisseur est requis en mode 'Envoyer au fournisseur'.");
            return;
        }
        for (const it of form.items) {
            if (!it.name?.trim()) {
                setErrorMsg("Chaque moustiquaire doit avoir un identifiant / nom.");
                return;
            }
            if (!(it.width_mm > 0) || !(it.height_mm > 0)) {
                setErrorMsg(`Dimensions invalides pour "${it.name || "(sans nom)"}".`);
                return;
            }
        }
        setBusy(true);
        setErrorMsg("");
        try {
            const payload = {
                mode: form.mode,
                supplier_id: form.mode === "fournisseur" ? (form.supplier_id || null) : null,
                supplier_snapshot: form.mode === "fournisseur" ? form.supplier_snapshot : null,
                customer_name: form.customer_name || "",
                project_ref: form.project_ref || "",
                project_address: form.project_address || "",
                date: form.date,
                needed_by: form.needed_by || null,
                status: form.status || "brouillon",
                items: stripKeys(form.items).map((it) => ({
                    name: it.name || "",
                    width_mm: Number(it.width_mm || 0),
                    height_mm: Number(it.height_mm || 0),
                    qty: parseInt(it.qty, 10) || 1,
                    frame_color: it.frame_color || "Blanc",
                    mesh_type: it.mesh_type || "Fibre de verre standard",
                    attachment_type: it.attachment_type || "Accroches (clips)",
                    notes: it.notes || "",
                })),
                notes: form.notes || "",
            };
            const url = editingId
                ? `/admin/mosquito-screens/${editingId}`
                : "/admin/mosquito-screens";
            const method = editingId ? "put" : "post";
            const { data } = await http[method](url, payload);
            setSuccessMsg(editingId
                ? `Bon ${data.order_number} mis à jour.`
                : `Bon ${data.order_number} créé · ${data.total_qty} unité(s) au total.`);
            setEditingId(data.id);
            setForm({
                ...data,
                supplier_snapshot: data.supplier_snapshot || emptyParty("supplier"),
                items: (data.items || []).map((it) => ({ ...it, _key: newKey() })),
                needed_by: data.needed_by || "",
            });
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'enregistrement.");
        } finally { setBusy(false); }
    };

    const removeOrder = async (id) => {
        if (!window.confirm("Supprimer ce bon de fabrication ?")) return;
        try {
            await http.delete(`/admin/mosquito-screens/${id}`);
            if (editingId === id) newOrder();
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur de suppression.");
        }
    };

    // ─── PDF & email ─────────────────────────────────────
    const downloadPdf = (id) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/mosquito-screens/${id}/pdf?token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const sendEmail = async (order) => {
        const defaultEmail = order.supplier_snapshot?.email || "";
        const to = window.prompt(
            `Envoyer le bon ${order.order_number} à quelle adresse ?`,
            defaultEmail,
        );
        if (!to) return;
        setSendingId(order.id);
        setErrorMsg("");
        try {
            await http.post(`/admin/mosquito-screens/${order.id}/send-email`, {
                to_email: to,
            });
            setSuccessMsg(`Bon ${order.order_number} envoyé à ${to}.`);
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'envoi.");
        } finally { setSendingId(null); }
    };

    // ──────────────────────────────────────────────────────
    return (
        <div className="space-y-6" ref={formTopRef}>
            <div className="flex items-center gap-3 flex-wrap">
                <Bug className="w-6 h-6 text-[#0c182b]" />
                <h2 className="text-xl font-bold text-[#0c182b]">Moustiquaires · Bons de fabrication</h2>
                <span className="text-xs text-[#4b5d7a]">
                    Fabrication à l&apos;interne ou envoi à un fournisseur (PDF + courriel).
                </span>
                <button onClick={newOrder} className="ml-auto btn-secondary !py-1.5 !px-3 !text-xs"
                    data-testid="ms-new">
                    <Plus className="w-3.5 h-3.5" /> Nouveau bon
                </button>
            </div>

            {errorMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#fde7e7] border border-[#e89a9a] text-[#a31a1a] text-sm"
                    data-testid="ms-error">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{errorMsg}</div>
                    <button onClick={() => setErrorMsg("")} className="text-[#a31a1a] hover:underline text-xs">Fermer</button>
                </div>
            )}
            {successMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#e6f7ee] border border-[#86c9a4] text-[#0f6b3a] text-sm"
                    data-testid="ms-success">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{successMsg}</div>
                    <button onClick={() => setSuccessMsg("")} className="text-[#0f6b3a] hover:underline text-xs">Fermer</button>
                </div>
            )}

            {/* ─── Form ───────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-4">
                <div className="flex items-center gap-2">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">
                        {editingId ? `Modifier ${form.order_number || ""}` : "Nouveau bon"}
                    </h3>
                </div>

                {/* Mode toggle */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Mode de fabrication
                    </label>
                    <div className="flex gap-2 flex-wrap" data-testid="ms-mode-toggle">
                        {[
                            { v: "interne", lbl: "Fabrication à l'interne (atelier Portech)" },
                            { v: "fournisseur", lbl: "Envoyer à un fournisseur" },
                        ].map((opt) => (
                            <button
                                type="button"
                                key={opt.v}
                                data-testid={`ms-mode-${opt.v}`}
                                onClick={() => setForm((f) => ({ ...f, mode: opt.v }))}
                                className={`px-3 py-2 border text-sm ${
                                    form.mode === opt.v
                                        ? "bg-[#0c182b] text-white border-[#0c182b]"
                                        : "bg-white text-[#0c182b] border-[#dde5f0] hover:bg-[#f3f6fb]"
                                }`}
                            >
                                {opt.lbl}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Supplier (only when fournisseur mode) */}
                {form.mode === "fournisseur" && (
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Fournisseur — fabrication
                        </label>
                        <div className="relative">
                            <input
                                type="text"
                                data-testid="ms-supplier-name"
                                value={form.supplier_snapshot?.name || ""}
                                onChange={(e) => {
                                    updateSupplierField("name", e.target.value);
                                    setSupplierQuery(e.target.value);
                                    setShowSupplierSuggest(true);
                                }}
                                onFocus={() => setShowSupplierSuggest(true)}
                                onBlur={() => setTimeout(() => setShowSupplierSuggest(false), 200)}
                                placeholder="Nom du fournisseur (autocomplète)"
                                className="w-full px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]"
                                autoComplete="off"
                            />
                            {showSupplierSuggest && supplierSuggestions.length > 0 && (
                                <div className="absolute z-10 left-0 right-0 top-full mt-0.5 bg-white border border-[#dde5f0] shadow-lg max-h-64 overflow-y-auto"
                                    data-testid="ms-supplier-suggestions">
                                    {supplierSuggestions.map((p) => (
                                        <button
                                            key={p.id}
                                            type="button"
                                            onMouseDown={(e) => e.preventDefault()}
                                            onClick={() => pickSupplier(p)}
                                            className="w-full text-left px-3 py-2 hover:bg-[#f3f6fb] border-b border-[#f3f6fb] last:border-0 text-sm">
                                            <div className="font-bold text-[#0c182b]">{p.name}</div>
                                            <div className="text-xs text-[#4b5d7a]">
                                                {p.email || "—"}{p.contact ? ` · ${p.contact}` : ""}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                            <input type="email" placeholder="Courriel fournisseur" data-testid="ms-supplier-email"
                                value={form.supplier_snapshot?.email || ""}
                                onChange={(e) => updateSupplierField("email", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]" />
                            <input type="text" placeholder="Contact (optionnel)"
                                value={form.supplier_snapshot?.contact || ""}
                                onChange={(e) => updateSupplierField("contact", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]" />
                        </div>
                    </div>
                )}

                {/* Project meta */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Client final (optionnel)
                        </label>
                        <input type="text" data-testid="ms-customer" value={form.customer_name || ""}
                            onChange={(e) => setForm((f) => ({ ...f, customer_name: e.target.value }))}
                            placeholder="Ex : M. Tremblay"
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Réf. projet (optionnel)
                        </label>
                        <input type="text" data-testid="ms-project-ref" value={form.project_ref || ""}
                            onChange={(e) => setForm((f) => ({ ...f, project_ref: e.target.value }))}
                            placeholder="Ex : Résidence rue Peel"
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>
                    <div className="sm:col-span-2">
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Adresse du projet (optionnel)
                        </label>
                        <input type="text" value={form.project_address || ""}
                            onChange={(e) => setForm((f) => ({ ...f, project_address: e.target.value }))}
                            placeholder="Ex : 1234 rue Sainte-Catherine, Montréal QC"
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Date d&apos;émission
                        </label>
                        <input type="date" data-testid="ms-date" value={form.date || todayISO()}
                            onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Requis pour
                        </label>
                        <input type="date" data-testid="ms-needed-by" value={form.needed_by || ""}
                            onChange={(e) => setForm((f) => ({ ...f, needed_by: e.target.value }))}
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Statut
                        </label>
                        <select data-testid="ms-status" value={form.status}
                            onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm bg-white">
                            {MOSQUITO_SCREEN_STATUSES.map((st) => (
                                <option key={st} value={st}>{st}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Items */}
                <div>
                    <div className="flex items-center justify-between mb-1">
                        <label className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider">
                            Moustiquaires à fabriquer (dimensions en mm)
                        </label>
                        <button onClick={addItem} className="text-[#1d4ed8] hover:underline text-xs inline-flex items-center gap-1"
                            data-testid="ms-add-item">
                            <Plus className="w-3 h-3" /> Ajouter une moustiquaire
                        </button>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm" data-testid="ms-items-table">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0] bg-[#f3f6fb]">
                                <tr>
                                    <th className="text-left px-2 py-1.5 w-40">Identifiant / Nom</th>
                                    <th className="text-right px-2 py-1.5 w-20">Larg. (mm)</th>
                                    <th className="text-right px-2 py-1.5 w-20">Haut. (mm)</th>
                                    <th className="text-right px-2 py-1.5 w-16">Qté</th>
                                    <th className="text-left px-2 py-1.5">Cadre</th>
                                    <th className="text-left px-2 py-1.5">Toile</th>
                                    <th className="text-left px-2 py-1.5">Attache</th>
                                    <th className="text-left px-2 py-1.5">Notes</th>
                                    <th className="w-10"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {form.items.map((it) => (
                                    <tr key={it._key} className="border-b border-[#f3f6fb] align-top">
                                        <td className="px-2 py-1">
                                            <input type="text" value={it.name}
                                                onChange={(e) => updateItem(it._key, "name", e.target.value)}
                                                placeholder="M-01 · Cuisine"
                                                data-testid={`ms-item-name-${it._key}`}
                                                className="w-full px-2 py-1 border border-[#dde5f0] text-sm" />
                                        </td>
                                        <td className="px-2 py-1">
                                            <input type="number" min="0" step="1" value={it.width_mm}
                                                onChange={(e) => updateItem(it._key, "width_mm", e.target.value)}
                                                data-testid={`ms-item-width-${it._key}`}
                                                className="w-full px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                        </td>
                                        <td className="px-2 py-1">
                                            <input type="number" min="0" step="1" value={it.height_mm}
                                                onChange={(e) => updateItem(it._key, "height_mm", e.target.value)}
                                                data-testid={`ms-item-height-${it._key}`}
                                                className="w-full px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                        </td>
                                        <td className="px-2 py-1">
                                            <input type="number" min="1" step="1" value={it.qty}
                                                onChange={(e) => updateItem(it._key, "qty", e.target.value)}
                                                data-testid={`ms-item-qty-${it._key}`}
                                                className="w-full px-2 py-1 border border-[#dde5f0] text-sm text-right" />
                                        </td>
                                        <td className="px-2 py-1">
                                            <select value={it.frame_color}
                                                onChange={(e) => updateItem(it._key, "frame_color", e.target.value)}
                                                className="w-full px-1 py-1 border border-[#dde5f0] text-sm bg-white">
                                                {MOSQUITO_FRAME_COLORS.map((c) => <option key={c} value={c}>{c}</option>)}
                                            </select>
                                        </td>
                                        <td className="px-2 py-1">
                                            <select value={it.mesh_type}
                                                onChange={(e) => updateItem(it._key, "mesh_type", e.target.value)}
                                                className="w-full px-1 py-1 border border-[#dde5f0] text-sm bg-white">
                                                {MOSQUITO_MESH_TYPES.map((c) => <option key={c} value={c}>{c}</option>)}
                                            </select>
                                        </td>
                                        <td className="px-2 py-1">
                                            <select value={it.attachment_type}
                                                onChange={(e) => updateItem(it._key, "attachment_type", e.target.value)}
                                                className="w-full px-1 py-1 border border-[#dde5f0] text-sm bg-white">
                                                {MOSQUITO_ATTACHMENT_TYPES.map((c) => <option key={c} value={c}>{c}</option>)}
                                            </select>
                                        </td>
                                        <td className="px-2 py-1">
                                            <input type="text" value={it.notes || ""}
                                                onChange={(e) => updateItem(it._key, "notes", e.target.value)}
                                                placeholder="—"
                                                className="w-full px-2 py-1 border border-[#dde5f0] text-sm" />
                                        </td>
                                        <td className="px-2 py-1 text-right">
                                            <button onClick={() => removeItem(it._key)}
                                                disabled={form.items.length <= 1}
                                                className="text-[#a31a1a] hover:bg-[#fde7e7] p-1 disabled:opacity-30 disabled:cursor-not-allowed">
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot>
                                <tr className="bg-[#0c182b] text-white">
                                    <td colSpan={3} className="px-2 py-2 font-bold uppercase text-xs">Qté totale</td>
                                    <td className="px-2 py-2 text-right font-bold" data-testid="ms-total-qty">{totalQty}</td>
                                    <td colSpan={5}></td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>

                {/* Notes */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Notes générales (optionnel)
                    </label>
                    <textarea data-testid="ms-notes" rows={2} value={form.notes || ""}
                        onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                        placeholder="Ex : Livraison à l'atelier. Facturer à la fin du projet."
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-[#dde5f0]">
                    <button onClick={save} disabled={busy} data-testid="ms-save"
                        className="btn-primary !py-2 !px-4 !text-sm">
                        {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Enregistrement…</>
                              : <><Save className="w-4 h-4" /> {editingId ? "Mettre à jour" : "Enregistrer"}</>}
                    </button>
                    {editingId && (
                        <>
                            <button onClick={() => downloadPdf(editingId)}
                                className="btn-secondary !py-2 !px-3 !text-sm"
                                data-testid="ms-download">
                                <Download className="w-4 h-4" /> Télécharger PDF
                            </button>
                            {form.mode === "fournisseur" && (
                                <button onClick={() => sendEmail({ ...form, id: editingId })}
                                    disabled={sendingId === editingId}
                                    className="btn-secondary !py-2 !px-3 !text-sm"
                                    data-testid="ms-send">
                                    <Send className="w-4 h-4" />
                                    {sendingId === editingId ? "Envoi…" : "Envoyer au fournisseur"}
                                </button>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* ─── List ───────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">Bons émis</h3>
                    <button onClick={reload} className="text-xs text-[#1d4ed8] hover:underline inline-flex items-center gap-1">
                        <RefreshCw className="w-3 h-3" /> Rafraîchir
                    </button>
                </div>
                {loading ? (
                    <div className="text-sm italic text-[#4b5d7a]">Chargement…</div>
                ) : orders.length === 0 ? (
                    <div className="text-sm italic text-[#4b5d7a]">Aucun bon émis pour l&apos;instant.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm" data-testid="ms-list-table">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                                <tr>
                                    <th className="text-left px-2 py-1.5">N°</th>
                                    <th className="text-left px-2 py-1.5">Mode</th>
                                    <th className="text-left px-2 py-1.5 hidden sm:table-cell">Fournisseur / Client</th>
                                    <th className="text-left px-2 py-1.5">Projet</th>
                                    <th className="text-right px-2 py-1.5">Qté</th>
                                    <th className="text-left px-2 py-1.5 hidden sm:table-cell">Requis pour</th>
                                    <th className="text-left px-2 py-1.5">Statut</th>
                                    <th className="px-2 py-1.5"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {orders.map((o) => (
                                    <tr key={o.id} className="border-b border-[#f3f6fb] hover:bg-[#f7f9fc]">
                                        <td className="px-2 py-1.5 font-mono text-[#0c182b]">
                                            {o.order_number}
                                        </td>
                                        <td className="px-2 py-1.5 text-[11px] text-[#4b5d7a]">
                                            {o.mode === "fournisseur" ? "Fournisseur" : "Interne"}
                                        </td>
                                        <td className="px-2 py-1.5 hidden sm:table-cell">
                                            <div className="text-[#0c182b]">
                                                {o.mode === "fournisseur"
                                                    ? (o.supplier_snapshot?.name || "—")
                                                    : (o.customer_name || "—")}
                                            </div>
                                            <div className="text-[10px] text-[#4b5d7a]">
                                                {o.mode === "fournisseur"
                                                    ? (o.supplier_snapshot?.email || "")
                                                    : ""}
                                            </div>
                                        </td>
                                        <td className="px-2 py-1.5 text-[11px] text-[#4b5d7a]">
                                            {o.project_ref || "—"}
                                        </td>
                                        <td className="px-2 py-1.5 text-right font-bold text-[#0c182b]">
                                            {o.total_qty}
                                        </td>
                                        <td className="px-2 py-1.5 text-[11px] text-[#4b5d7a] whitespace-nowrap hidden sm:table-cell">
                                            {o.needed_by ? formatDate(o.needed_by) : "—"}
                                        </td>
                                        <td className="px-2 py-1.5 text-[11px]">
                                            <span className="px-2 py-0.5 border border-[#dde5f0] bg-[#f3f6fb] text-[#0c182b] uppercase tracking-wider text-[9px]">
                                                {o.status || "brouillon"}
                                            </span>
                                        </td>
                                        <td className="px-2 py-1.5 text-right whitespace-nowrap">
                                            <button onClick={() => openEdit(o)}
                                                className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Modifier"
                                                data-testid={`ms-edit-${o.id}`}>
                                                <FileText className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => downloadPdf(o.id)}
                                                className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Télécharger PDF">
                                                <Download className="w-3.5 h-3.5" />
                                            </button>
                                            {o.mode === "fournisseur" && (
                                                <button onClick={() => sendEmail(o)} disabled={sendingId === o.id}
                                                    className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Envoyer par courriel">
                                                    {sendingId === o.id
                                                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                        : <Send className="w-3.5 h-3.5" />}
                                                </button>
                                            )}
                                            <button onClick={() => removeOrder(o.id)}
                                                className="p-1 hover:bg-[#fde7e7] text-[#a31a1a]" title="Supprimer">
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

export default MosquitoScreensPanel;
