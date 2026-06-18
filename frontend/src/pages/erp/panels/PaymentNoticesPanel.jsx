/** Payment Notices (Avis de paiement) — prove suppliers you've paid them.
 *
 *  Generates a branded "Avis de paiement" PDF and optionally emails it.
 *  Used to stop suppliers from following up while a bank transfer is still
 *  in transit ("3 à 5 jours ouvrables" — printed on the PDF).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    Wallet, Plus, Save, Trash2, RefreshCw, Download, Send, FileText,
    AlertCircle, CheckCircle2, Loader2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
    PAYMENT_METHODS, emptyPaymentNotice, emptyPaymentNoticeItem,
    emptyParty, formatCurrency, formatDate, newKey, stripKeys, todayISO,
} from "../utils";

export const PaymentNoticesPanel = () => {
    const { http, getToken } = useAuth();
    const [notices, setNotices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [form, setForm] = useState(emptyPaymentNotice());
    const [editingId, setEditingId] = useState(null);
    const [suppliers, setSuppliers] = useState([]);
    const [supplierQuery, setSupplierQuery] = useState("");
    const [showSupplierSuggest, setShowSupplierSuggest] = useState(false);
    const [busy, setBusy] = useState(false);
    const [sendingId, setSendingId] = useState(null);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");
    const formTopRef = useRef(null);

    // ─── Initial load ─────────────────────────────────────────
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [n, s] = await Promise.all([
                    http.get("/admin/payment-notices"),
                    http.get("/admin/parties?kind=supplier"),
                ]);
                if (!cancelled) {
                    setNotices(Array.isArray(n.data) ? n.data : []);
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

    const reload = async () => {
        try {
            const { data } = await http.get("/admin/payment-notices");
            setNotices(Array.isArray(data) ? data : []);
        } catch (_) { /* silent */ }
    };

    // ─── Supplier autocomplete ────────────────────────────────
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
            supplier_id: null,        // disconnect from saved party — manual edit
            supplier_snapshot: { ...f.supplier_snapshot, [key]: value },
        }));
    };

    // ─── Items ────────────────────────────────────────────────
    const addItem = () => setForm((f) => ({
        ...f, items: [...f.items, emptyPaymentNoticeItem()],
    }));
    const removeItem = (k) => setForm((f) => ({
        ...f, items: f.items.filter((it) => it._key !== k),
    }));
    const updateItem = (k, key, value) => setForm((f) => ({
        ...f,
        items: f.items.map((it) => (it._key === k ? { ...it, [key]: value } : it)),
    }));

    const total = useMemo(
        () => form.items.reduce((s, it) => s + Number(it.amount || 0), 0),
        [form.items],
    );

    // ─── Save / Edit ──────────────────────────────────────────
    const newNotice = () => {
        setForm(emptyPaymentNotice());
        setSupplierQuery("");
        setEditingId(null);
        setSuccessMsg("");
        setErrorMsg("");
        formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    const openEdit = (notice) => {
        setForm({
            ...notice,
            items: (notice.items || []).map((it) => ({ ...it, _key: newKey() })),
        });
        setSupplierQuery(notice.supplier_snapshot?.name || "");
        setEditingId(notice.id);
        setSuccessMsg("");
        setErrorMsg("");
        formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    const save = async () => {
        if (!form.supplier_snapshot?.name) {
            setErrorMsg("Le nom du fournisseur est requis.");
            return;
        }
        if (!form.items?.length) {
            setErrorMsg("Au moins une ligne de facture est requise.");
            return;
        }
        setBusy(true);
        setErrorMsg("");
        try {
            const payload = {
                supplier_id: form.supplier_id || null,
                supplier_snapshot: form.supplier_snapshot,
                date: form.date,
                payment_date: form.payment_date,
                payment_method: form.payment_method,
                reference_number: form.reference_number || "",
                items: stripKeys(form.items).map((it) => ({
                    invoice_number: it.invoice_number || "",
                    description: it.description || "",
                    amount: Number(it.amount || 0),
                })),
                notes: form.notes || "",
            };
            const url = editingId
                ? `/admin/payment-notices/${editingId}`
                : "/admin/payment-notices";
            const method = editingId ? "put" : "post";
            const { data } = await http[method](url, payload);
            setSuccessMsg(editingId
                ? `Avis ${data.notice_number} mis à jour.`
                : `Avis ${data.notice_number} créé · Total ${formatCurrency(data.total)}.`);
            setEditingId(data.id);
            setForm({
                ...data,
                items: (data.items || []).map((it) => ({ ...it, _key: newKey() })),
            });
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'enregistrement.");
        } finally { setBusy(false); }
    };

    const removeNotice = async (id) => {
        if (!window.confirm("Supprimer cet avis de paiement ?")) return;
        try {
            await http.delete(`/admin/payment-notices/${id}`);
            if (editingId === id) newNotice();
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur de suppression.");
        }
    };

    // ─── PDF download / email send ────────────────────────────
    const downloadPdf = (id, number) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/payment-notices/${id}/pdf?token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const sendEmail = async (notice) => {
        const defaultEmail = notice.supplier_snapshot?.email || "";
        const to = window.prompt(
            `Envoyer l'avis ${notice.notice_number} à quelle adresse ?`,
            defaultEmail,
        );
        if (!to) return;
        setSendingId(notice.id);
        setErrorMsg("");
        try {
            await http.post(`/admin/payment-notices/${notice.id}/send-email`, {
                to_email: to,
            });
            setSuccessMsg(`Avis ${notice.notice_number} envoyé à ${to}.`);
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'envoi.");
        } finally { setSendingId(null); }
    };

    // ──────────────────────────────────────────────────────────
    return (
        <div className="space-y-6" ref={formTopRef}>
            <div className="flex items-center gap-3 flex-wrap">
                <Wallet className="w-6 h-6 text-[#0c182b]" />
                <h2 className="text-xl font-bold text-[#0c182b]">Avis de paiement</h2>
                <span className="text-xs text-[#4b5d7a]">
                    Preuve de paiement à envoyer aux fournisseurs (3-5 jours ouvrables avant arrivée).
                </span>
                <button onClick={newNotice} className="ml-auto btn-secondary !py-1.5 !px-3 !text-xs"
                    data-testid="pn-new">
                    <Plus className="w-3.5 h-3.5" /> Nouveau
                </button>
            </div>

            {errorMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#fde7e7] border border-[#e89a9a] text-[#a31a1a] text-sm"
                    data-testid="pn-error">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{errorMsg}</div>
                    <button onClick={() => setErrorMsg("")} className="text-[#a31a1a] hover:underline text-xs">Fermer</button>
                </div>
            )}
            {successMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#e6f7ee] border border-[#86c9a4] text-[#0f6b3a] text-sm"
                    data-testid="pn-success">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{successMsg}</div>
                    <button onClick={() => setSuccessMsg("")} className="text-[#0f6b3a] hover:underline text-xs">Fermer</button>
                </div>
            )}

            {/* ─── Form ─────────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-4">
                <div className="flex items-center gap-2">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">
                        {editingId ? `Modifier ${form.notice_number || ""}` : "Nouvel avis"}
                    </h3>
                </div>

                {/* Supplier */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Fournisseur
                    </label>
                    <div className="relative">
                        <input
                            type="text"
                            data-testid="pn-supplier-name"
                            value={form.supplier_snapshot?.name || ""}
                            onChange={(e) => {
                                updateSupplierField("name", e.target.value);
                                setSupplierQuery(e.target.value);
                                setShowSupplierSuggest(true);
                            }}
                            onFocus={() => setShowSupplierSuggest(true)}
                            onBlur={() => setTimeout(() => setShowSupplierSuggest(false), 200)}
                            placeholder="Nom du fournisseur (commence à taper pour autocompléter)"
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]"
                            autoComplete="off"
                        />
                        {showSupplierSuggest && supplierSuggestions.length > 0 && (
                            <div className="absolute z-10 left-0 right-0 top-full mt-0.5 bg-white border border-[#dde5f0] shadow-lg max-h-64 overflow-y-auto"
                                data-testid="pn-supplier-suggestions">
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
                        <input type="email" placeholder="Courriel fournisseur" data-testid="pn-supplier-email"
                            value={form.supplier_snapshot?.email || ""}
                            onChange={(e) => updateSupplierField("email", e.target.value)}
                            className="px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]" />
                        <input type="text" placeholder="Contact (optionnel)"
                            value={form.supplier_snapshot?.contact || ""}
                            onChange={(e) => updateSupplierField("contact", e.target.value)}
                            className="px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]" />
                        <input type="text" placeholder="Adresse"
                            value={form.supplier_snapshot?.address_line1 || ""}
                            onChange={(e) => updateSupplierField("address_line1", e.target.value)}
                            className="sm:col-span-2 px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]" />
                    </div>
                </div>

                {/* Payment meta */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Date d&apos;émission
                        </label>
                        <input type="date" data-testid="pn-date" value={form.date || todayISO()}
                            onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Date du paiement
                        </label>
                        <input type="date" data-testid="pn-payment-date" value={form.payment_date || todayISO()}
                            onChange={(e) => setForm((f) => ({ ...f, payment_date: e.target.value }))}
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            Méthode
                        </label>
                        <select data-testid="pn-method" value={form.payment_method}
                            onChange={(e) => setForm((f) => ({ ...f, payment_method: e.target.value }))}
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm bg-white">
                            {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                            N° référence
                        </label>
                        <input type="text" data-testid="pn-ref" value={form.reference_number || ""}
                            onChange={(e) => setForm((f) => ({ ...f, reference_number: e.target.value }))}
                            placeholder="Ex : numéro de transaction, n° de chèque"
                            className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>
                </div>

                {/* Items */}
                <div>
                    <div className="flex items-center justify-between mb-1">
                        <label className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider">
                            Factures payées
                        </label>
                        <button onClick={addItem} className="text-[#1d4ed8] hover:underline text-xs inline-flex items-center gap-1"
                            data-testid="pn-add-item">
                            <Plus className="w-3 h-3" /> Ajouter une facture
                        </button>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm" data-testid="pn-items-table">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0] bg-[#f3f6fb]">
                                <tr>
                                    <th className="text-left px-2 py-1.5 w-40">N° facture</th>
                                    <th className="text-left px-2 py-1.5">Description</th>
                                    <th className="text-right px-2 py-1.5 w-32">Montant</th>
                                    <th className="w-10"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {form.items.map((it) => (
                                    <tr key={it._key} className="border-b border-[#f3f6fb]">
                                        <td className="px-2 py-1">
                                            <input type="text" value={it.invoice_number}
                                                onChange={(e) => updateItem(it._key, "invoice_number", e.target.value)}
                                                placeholder="INV-1234"
                                                data-testid={`pn-item-invoice-${it._key}`}
                                                className="w-full px-2 py-1 border border-[#dde5f0] text-sm font-mono" />
                                        </td>
                                        <td className="px-2 py-1">
                                            <input type="text" value={it.description}
                                                onChange={(e) => updateItem(it._key, "description", e.target.value)}
                                                placeholder="Ex : Profilés AT1000"
                                                className="w-full px-2 py-1 border border-[#dde5f0] text-sm" />
                                        </td>
                                        <td className="px-2 py-1">
                                            <input type="number" step="0.01" value={it.amount}
                                                onChange={(e) => updateItem(it._key, "amount", e.target.value)}
                                                data-testid={`pn-item-amount-${it._key}`}
                                                className="w-full px-2 py-1 border border-[#dde5f0] text-sm text-right" />
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
                                    <td colSpan={2} className="px-2 py-2 font-bold uppercase text-xs">Total payé</td>
                                    <td className="px-2 py-2 text-right font-bold" data-testid="pn-total">{formatCurrency(total)}</td>
                                    <td></td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>

                {/* Notes */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Notes (optionnel)
                    </label>
                    <textarea data-testid="pn-notes" rows={2} value={form.notes || ""}
                        onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                        placeholder="Ex : Merci pour la livraison rapide."
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-[#dde5f0]">
                    <button onClick={save} disabled={busy} data-testid="pn-save"
                        className="btn-primary !py-2 !px-4 !text-sm">
                        {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Enregistrement…</>
                              : <><Save className="w-4 h-4" /> {editingId ? "Mettre à jour" : "Enregistrer"}</>}
                    </button>
                    {editingId && (
                        <>
                            <button onClick={() => downloadPdf(editingId, form.notice_number)}
                                className="btn-secondary !py-2 !px-3 !text-sm"
                                data-testid="pn-download">
                                <Download className="w-4 h-4" /> Télécharger PDF
                            </button>
                            <button onClick={() => sendEmail({ ...form, id: editingId })}
                                disabled={sendingId === editingId}
                                className="btn-secondary !py-2 !px-3 !text-sm"
                                data-testid="pn-send">
                                <Send className="w-4 h-4" />
                                {sendingId === editingId ? "Envoi…" : "Envoyer par courriel"}
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* ─── List ──────────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">Avis émis</h3>
                    <button onClick={reload} className="text-xs text-[#1d4ed8] hover:underline inline-flex items-center gap-1">
                        <RefreshCw className="w-3 h-3" /> Rafraîchir
                    </button>
                </div>
                {loading ? (
                    <div className="text-sm italic text-[#4b5d7a]">Chargement…</div>
                ) : notices.length === 0 ? (
                    <div className="text-sm italic text-[#4b5d7a]">Aucun avis émis pour l&apos;instant.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm" data-testid="pn-list-table">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                                <tr>
                                    <th className="text-left px-2 py-1.5">N°</th>
                                    <th className="text-left px-2 py-1.5">Fournisseur</th>
                                    <th className="text-left px-2 py-1.5 hidden sm:table-cell">Méthode</th>
                                    <th className="text-left px-2 py-1.5">Paiement</th>
                                    <th className="text-right px-2 py-1.5">Total</th>
                                    <th className="text-left px-2 py-1.5 hidden sm:table-cell">Envoyé</th>
                                    <th className="px-2 py-1.5"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {notices.map((n) => (
                                    <tr key={n.id} className="border-b border-[#f3f6fb] hover:bg-[#f7f9fc]">
                                        <td className="px-2 py-1.5 font-mono text-[#0c182b]">
                                            {n.notice_number}
                                        </td>
                                        <td className="px-2 py-1.5">
                                            <div className="text-[#0c182b]">{n.supplier_snapshot?.name}</div>
                                            <div className="text-[10px] text-[#4b5d7a]">{n.supplier_snapshot?.email}</div>
                                        </td>
                                        <td className="px-2 py-1.5 text-[11px] text-[#4b5d7a] hidden sm:table-cell">
                                            {n.payment_method}
                                        </td>
                                        <td className="px-2 py-1.5 text-[11px] text-[#4b5d7a] whitespace-nowrap">
                                            {formatDate(n.payment_date)}
                                        </td>
                                        <td className="px-2 py-1.5 text-right font-bold text-[#0c182b]">
                                            {formatCurrency(n.total)}
                                        </td>
                                        <td className="px-2 py-1.5 hidden sm:table-cell">
                                            {n.sent_at ? (
                                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#0f6b3a]">
                                                    <CheckCircle2 className="w-3 h-3" /> Envoyé
                                                </span>
                                            ) : (
                                                <span className="text-[10px] text-[#4b5d7a]">—</span>
                                            )}
                                        </td>
                                        <td className="px-2 py-1.5 text-right whitespace-nowrap">
                                            <button onClick={() => openEdit(n)}
                                                className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Modifier"
                                                data-testid={`pn-edit-${n.id}`}>
                                                <FileText className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => downloadPdf(n.id, n.notice_number)}
                                                className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Télécharger PDF">
                                                <Download className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => sendEmail(n)} disabled={sendingId === n.id}
                                                className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Envoyer par courriel">
                                                {sendingId === n.id
                                                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                    : <Send className="w-3.5 h-3.5" />}
                                            </button>
                                            <button onClick={() => removeNotice(n.id)}
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

export default PaymentNoticesPanel;
