import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Pencil, Trash2, RefreshCw, Printer, Send, Download, Search, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Modal, Field, inputClass } from "../components/Modal";
import { DocumentForm } from "../components/DocumentForm";
import {
    STATUS_BADGE,
    OVERDUE_BADGE,
    formatCurrency,
    formatDate,
    newKey,
    overdueState,
    stripKeys,
} from "../utils";

/**
 * Generic panel for invoices / purchase orders. The data model is identical
 * aside from the party key & status options.
 */
export const DocumentPanel = ({
    title,
    eyebrow,
    singular,
    feminineArticle = false,
    kind,
    apiPath,
    partyKind,
    partyKey,
    printPath,
    statuses,
    numberPrefix,
    emptyDoc,
    csvExportPath, // optional CSV export endpoint
}) => {
    const { http } = useAuth();
    const [rows, setRows] = useState([]);
    const [parties, setParties] = useState([]);
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [query, setQuery] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(emptyDoc());
    const [emailModal, setEmailModal] = useState(null); // null | doc
    const [emailTo, setEmailTo] = useState("");
    const [emailMsg, setEmailMsg] = useState("");
    const [emailSending, setEmailSending] = useState(false);
    const [emailError, setEmailError] = useState("");

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const [docs, prts, prods] = await Promise.all([
                http.get(apiPath),
                http.get(`/admin/parties?kind=${partyKind}`),
                http.get("/admin/products"),
            ]);
            setRows(docs.data || []);
            setParties(prts.data || []);
            setProducts(prods.data || []);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally {
            setLoading(false);
        }
    }, [http, apiPath, partyKind]);

    useEffect(() => { load(); }, [load]);

    const openNew = () => { setEditing(null); setForm(emptyDoc()); setModalOpen(true); };
    const openEdit = (d) => {
        setEditing(d);
        setForm({
            ...d,
            items: (d.items || []).map((it) => ({
                _key: newKey(),
                description: it.description,
                quantity: it.quantity,
                unit_price: it.unit_price,
                product_id: it.product_id || null,
            })),
        });
        setModalOpen(true);
    };

    const save = async () => {
        try {
            const payload = {
                ...form,
                items: stripKeys(form.items).map((it) => ({
                    description: it.description,
                    quantity: Number(it.quantity || 0),
                    unit_price: Number(it.unit_price || 0),
                    product_id: it.product_id || null,
                })),
            };
            if (editing) await http.put(`${apiPath}/${editing.id}`, payload);
            else await http.post(apiPath, payload);
            setModalOpen(false);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec de l'enregistrement");
        }
    };

    const remove = async (d) => {
        if (!window.confirm(`Supprimer ${numberPrefix}-${d.number} ?`)) return;
        await http.delete(`${apiPath}/${d.id}`);
        setRows((prev) => prev.filter((x) => x.id !== d.id));
    };

    // Filtering (search bar)
    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return rows;
        return rows.filter((d) => {
            const party = d[partyKey] || {};
            return [
                `${numberPrefix}-${String(d.number).padStart(4, "0")}`,
                party.name, party.city, party.email, party.contact,
                d.status, d.notes, d.date,
                ...(d.items || []).map((it) => it.description),
            ]
                .filter(Boolean)
                .some((v) => String(v).toLowerCase().includes(q));
        });
    }, [rows, query, partyKey, numberPrefix]);

    // Open send-email modal
    const openEmail = (d) => {
        setEmailModal(d);
        setEmailTo((d[partyKey]?.email) || "");
        setEmailMsg("");
        setEmailError("");
    };
    const sendEmail = async () => {
        if (!emailModal || !emailTo) return;
        setEmailSending(true); setEmailError("");
        try {
            await http.post(`${apiPath}/${emailModal.id}/send-email`, {
                to_email: emailTo,
                message: emailMsg || undefined,
            });
            setEmailModal(null);
            await load();
        } catch (e) {
            setEmailError(e?.response?.data?.detail || "Échec de l'envoi");
        } finally {
            setEmailSending(false);
        }
    };

    // CSV export — fetch with credentials, trigger a browser download
    const exportCsv = async () => {
        if (!csvExportPath) return;
        try {
            const resp = await http.get(csvExportPath, { responseType: "blob" });
            const url = window.URL.createObjectURL(resp.data);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${kind}-portech-${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec de l'export");
        }
    };

    // Server-side PDF download
    const downloadPdf = async (d) => {
        try {
            const resp = await http.get(`${apiPath}/${d.id}/pdf`, { responseType: "blob" });
            const url = window.URL.createObjectURL(resp.data);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${numberPrefix}-${String(d.number).padStart(4, "0")}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec du téléchargement PDF");
        }
    };

    // Quick status change: invoices only — mark as "payée"
    const markPaid = async (d) => {
        if (!window.confirm(`Marquer ${numberPrefix}-${String(d.number).padStart(4, "0")} comme payée ?\n\nCela arrêtera les rappels automatiques.`)) return;
        try {
            await http.post(`${apiPath}/${d.id}/mark-paid`);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec");
        }
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <div className="tech-stamp mb-1">{eyebrow}</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">{title}</h1>
                </div>
                <div className="flex gap-2 flex-wrap">
                    {csvExportPath && (
                        <button onClick={exportCsv} data-testid={`erp-export-${kind}`} className="btn-secondary !py-2 !px-3 !text-xs">
                            <Download className="w-3.5 h-3.5" />
                            CSV
                        </button>
                    )}
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={openNew} data-testid={`erp-new-${kind}`} className="btn-primary !py-2 !px-4 !text-xs">
                        <Plus className="w-3.5 h-3.5" />
                        {feminineArticle ? "Nouvelle" : "Nouveau"} {singular}
                    </button>
                </div>
            </div>

            {/* Search bar */}
            <div className="relative max-w-md mb-4">
                <Search className="w-4 h-4 text-[#97b0d0] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                    type="text"
                    placeholder={`Rechercher (numéro, ${partyKind === "customer" ? "client" : "fournisseur"}, description…)`}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    data-testid={`${kind}-search`}
                    className="w-full pl-9 pr-4 py-2 border border-[#c5d4e7] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2f4f7f]"
                />
            </div>

            {error && <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>}

            <div className="border border-[#dde5f0] bg-white">
                <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                    <div className="col-span-2">Numéro</div>
                    <div className="col-span-3">{partyKind === "customer" ? "Client" : "Fournisseur"}</div>
                    <div className="col-span-2">Date</div>
                    <div className="col-span-2 text-right">Total</div>
                    <div className="col-span-1">Statut</div>
                    <div className="col-span-2 text-right">Actions</div>
                </div>
                {filtered.length === 0 && !loading && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">
                        {query ? "Aucun résultat pour cette recherche." : `Aucun${feminineArticle ? "e" : ""} ${singular}. Cliquez sur « ${feminineArticle ? "Nouvelle" : "Nouveau"} ${singular} » pour en créer un${feminineArticle ? "e" : ""}.`}
                    </div>
                )}
                <ul>
                {filtered.map((d) => {
                    const overdue = kind === "invoice" ? overdueState(d) : null;
                    return (
                        <li key={d.id} className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors">
                            <div className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-3 items-center">
                                <div className="col-span-2 font-display font-bold text-sm">{numberPrefix}-{String(d.number).padStart(4, "0")}</div>
                                <div className="col-span-3 text-sm truncate">{d[partyKey]?.name || "—"}</div>
                                <div className="col-span-2 text-sm text-[#4b5d7a]">{formatDate(d.date)}</div>
                                <div className="col-span-2 text-sm text-right font-display font-bold">{formatCurrency(d.total)}</div>
                                <div className="col-span-1 flex flex-col gap-1 items-start">
                                    <span className={`tech-stamp px-2 py-1 border ${STATUS_BADGE[d.status] || "border-[#dde5f0]"}`}>
                                        {d.status}
                                    </span>
                                    {overdue && (
                                        <span
                                            className={`tech-stamp px-2 py-1 border whitespace-nowrap ${OVERDUE_BADGE[overdue.tone]}`}
                                            data-testid={`${kind}-overdue-${d.id}`}
                                            title={overdue.label}
                                        >
                                            {overdue.label}
                                        </span>
                                    )}
                                </div>
                                <div className="col-span-2 flex justify-end gap-1">
                                    {kind === "invoice" && d.status !== "payée" && d.status !== "annulée" && (
                                        <button
                                            onClick={() => markPaid(d)}
                                            data-testid={`${kind}-mark-paid-${d.id}`}
                                            title="Marquer comme payée"
                                            className="p-2 border border-[#8ec79d] hover:bg-[#e6f4ea] text-[#0b6b2f]"
                                        >
                                            <CheckCircle2 className="w-3.5 h-3.5" />
                                        </button>
                                    )}
                                    <button
                                        onClick={() => downloadPdf(d)}
                                        data-testid={`${kind}-pdf-${d.id}`}
                                        title="Télécharger PDF"
                                        className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]"
                                    >
                                        <Download className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                        onClick={() => openEmail(d)}
                                        data-testid={`${kind}-email-${d.id}`}
                                        title="Envoyer par courriel"
                                        className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]"
                                    >
                                        <Send className="w-3.5 h-3.5" />
                                    </button>
                                    <Link
                                        to={`${printPath}/${d.id}`}
                                        target="_blank"
                                        rel="noopener"
                                        title="Imprimer (aperçu HTML)"
                                        className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]"
                                    >
                                        <Printer className="w-3.5 h-3.5" />
                                    </Link>
                                    <button onClick={() => openEdit(d)} title="Modifier" className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]">
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => remove(d)} title="Supprimer" className="p-2 border border-[#dde5f0] hover:bg-red-50 text-red-600">
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                        </li>
                    );
                })}
                </ul>
            </div>

            <Modal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                title={editing ? `Modifier ${feminineArticle ? "la" : "le"} ${singular} ${numberPrefix}-${String(editing.number).padStart(4, "0")}` : `${feminineArticle ? "Nouvelle" : "Nouveau"} ${singular}`}
                testId={`${kind}-modal`}
                wide
                footer={
                    <>
                        <button onClick={() => setModalOpen(false)} className="btn-secondary !py-2 !px-4 !text-xs">Annuler</button>
                        <button onClick={save} data-testid={`${kind}-save`} className="btn-primary !py-2 !px-4 !text-xs">
                            Enregistrer
                        </button>
                    </>
                }
            >
                <DocumentForm
                    kind={kind}
                    parties={parties}
                    products={products}
                    value={form}
                    onChange={setForm}
                    statuses={statuses}
                />
            </Modal>

            {/* === Send-by-email modal === */}
            <Modal
                open={!!emailModal}
                onClose={() => setEmailModal(null)}
                title={
                    emailModal
                        ? `Envoyer par courriel · ${numberPrefix}-${String(emailModal.number).padStart(4, "0")}`
                        : "Envoyer"
                }
                testId={`${kind}-email-modal`}
                footer={
                    <>
                        <button onClick={() => setEmailModal(null)} className="btn-secondary !py-2 !px-4 !text-xs" disabled={emailSending}>
                            Annuler
                        </button>
                        <button
                            onClick={sendEmail}
                            disabled={!emailTo || emailSending}
                            data-testid={`${kind}-email-send`}
                            className="btn-primary !py-2 !px-4 !text-xs disabled:opacity-40"
                        >
                            <Send className="w-3.5 h-3.5" />
                            {emailSending ? "Envoi…" : "Envoyer le PDF"}
                        </button>
                    </>
                }
            >
                {emailModal && (
                    <div className="space-y-4">
                        <p className="text-sm text-[#4b5d7a]">
                            Le PDF généré sera envoyé en pièce jointe via Resend (info@portech.info).
                            Le statut passera automatiquement à <strong className="text-[#0c182b]">{kind === "bill-of-lading" ? "« expédié »" : "« envoyée »"}</strong> si le document était en brouillon.
                        </p>
                        <Field label="Adresse courriel destinataire" required>
                            <input
                                type="email"
                                value={emailTo}
                                onChange={(e) => setEmailTo(e.target.value)}
                                className={inputClass}
                                placeholder="client@exemple.ca"
                                data-testid={`${kind}-email-to`}
                                required
                            />
                        </Field>
                        <Field label="Message personnalisé (optionnel — sinon un message par défaut sera envoyé)">
                            <textarea
                                rows={4}
                                value={emailMsg}
                                onChange={(e) => setEmailMsg(e.target.value)}
                                className={inputClass}
                                placeholder="Bonjour, vous trouverez ci-joint…"
                            />
                        </Field>
                        {emailError && (
                            <div className="p-3 border border-red-400 bg-red-50 text-red-800 text-sm">{emailError}</div>
                        )}
                    </div>
                )}
            </Modal>
        </div>
    );
};
