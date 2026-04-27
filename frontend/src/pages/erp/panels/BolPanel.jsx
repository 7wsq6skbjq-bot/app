import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Pencil, Trash2, RefreshCw, Printer, Send, Download, Search } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Modal, Field, inputClass } from "../components/Modal";
import { PartyForm } from "../components/PartyForm";
import {
    BOL_STATUSES,
    STATUS_BADGE,
    emptyBOL,
    emptyBolItem,
    formatDate,
} from "../utils";

export const BolPanel = () => {
    const { http } = useAuth();
    const [rows, setRows] = useState([]);
    const [parties, setParties] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [query, setQuery] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(emptyBOL());
    const [emailModal, setEmailModal] = useState(null);
    const [emailTo, setEmailTo] = useState("");
    const [emailMsg, setEmailMsg] = useState("");
    const [emailSending, setEmailSending] = useState(false);
    const [emailError, setEmailError] = useState("");

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const [bols, prts] = await Promise.all([
                http.get("/admin/bills-of-lading"),
                http.get("/admin/parties"),
            ]);
            setRows(bols.data || []);
            setParties(prts.data || []);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur");
        } finally {
            setLoading(false);
        }
    }, [http]);

    useEffect(() => { load(); }, [load]);

    const openNew = () => { setEditing(null); setForm(emptyBOL()); setModalOpen(true); };
    const openEdit = (d) => {
        setEditing(d);
        setForm({
            ...d,
            items: (d.items || []).map((it) => ({
                description: it.description,
                quantity: it.quantity,
                unit: it.unit || "unité",
                weight_kg: it.weight_kg ?? "",
                dimensions: it.dimensions || "",
            })),
        });
        setModalOpen(true);
    };

    const save = async () => {
        try {
            const payload = {
                ...form,
                total_weight_kg: form.total_weight_kg === "" ? null : Number(form.total_weight_kg),
                items: form.items.map((it) => ({
                    description: it.description,
                    quantity: Number(it.quantity || 0),
                    unit: it.unit || "unité",
                    weight_kg: it.weight_kg === "" ? null : Number(it.weight_kg),
                    dimensions: it.dimensions || null,
                })),
            };
            if (editing) await http.put(`/admin/bills-of-lading/${editing.id}`, payload);
            else await http.post("/admin/bills-of-lading", payload);
            setModalOpen(false);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec");
        }
    };

    const remove = async (d) => {
        if (!window.confirm(`Supprimer CONN-${String(d.number).padStart(4, "0")} ?`)) return;
        await http.delete(`/admin/bills-of-lading/${d.id}`);
        setRows((prev) => prev.filter((x) => x.id !== d.id));
    };

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return rows;
        return rows.filter((d) =>
            [
                `CONN-${String(d.number).padStart(4, "0")}`,
                d.shipper_snapshot?.name, d.consignee_snapshot?.name,
                d.carrier, d.status,
                ...(d.items || []).map((it) => it.description),
            ].filter(Boolean).some((v) => String(v).toLowerCase().includes(q)),
        );
    }, [rows, query]);

    const openEmail = (d) => {
        setEmailModal(d);
        setEmailTo(d.consignee_snapshot?.email || "");
        setEmailMsg("");
        setEmailError("");
    };
    const sendEmail = async () => {
        if (!emailModal || !emailTo) return;
        setEmailSending(true); setEmailError("");
        try {
            await http.post(`/admin/bills-of-lading/${emailModal.id}/send-email`, {
                to_email: emailTo, message: emailMsg || undefined,
            });
            setEmailModal(null);
            await load();
        } catch (e) {
            setEmailError(e?.response?.data?.detail || "Échec");
        } finally {
            setEmailSending(false);
        }
    };
    const downloadPdf = async (d) => {
        try {
            const resp = await http.get(`/admin/bills-of-lading/${d.id}/pdf`, { responseType: "blob" });
            const url = window.URL.createObjectURL(resp.data);
            const a = document.createElement("a");
            a.href = url;
            a.download = `CONN-${String(d.number).padStart(4, "0")}.pdf`;
            document.body.appendChild(a); a.click(); a.remove();
            window.URL.revokeObjectURL(url);
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec");
        }
    };

    const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
    const updateItem = (idx, patch) => setForm((f) => ({ ...f, items: f.items.map((it, i) => (i === idx ? { ...it, ...patch } : it)) }));
    const addItem = () => setForm((f) => ({ ...f, items: [...f.items, emptyBolItem()] }));
    const removeItem = (idx) => setForm((f) => {
        const items = f.items.filter((_, i) => i !== idx);
        return { ...f, items: items.length ? items : [emptyBolItem()] };
    });

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <div className="tech-stamp mb-1">Gestion · Expédition</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Connaissements</h1>
                </div>
                <div className="flex gap-2">
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={openNew} data-testid="erp-new-bol" className="btn-primary !py-2 !px-4 !text-xs">
                        <Plus className="w-3.5 h-3.5" />
                        Nouveau connaissement
                    </button>
                </div>
            </div>

            {error && <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>}

            <div className="border border-[#dde5f0] bg-white">
                <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                    <div className="col-span-2">Numéro</div>
                    <div className="col-span-3">Expéditeur</div>
                    <div className="col-span-3">Destinataire</div>
                    <div className="col-span-1">Date</div>
                    <div className="col-span-1">Statut</div>
                    <div className="col-span-2 text-right">Actions</div>
                </div>
                {rows.length === 0 && !loading && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">Aucun connaissement.</div>
                )}
                <ul>
                    {filtered.map((d) => (
                        <li key={d.id} className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors">
                            <div className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-3 items-center">
                                <div className="col-span-2 font-display font-bold text-sm">CONN-{String(d.number).padStart(4, "0")}</div>
                                <div className="col-span-3 text-sm truncate">{d.shipper_snapshot?.name}</div>
                                <div className="col-span-3 text-sm truncate">{d.consignee_snapshot?.name}</div>
                                <div className="col-span-1 text-xs text-[#4b5d7a]">{formatDate(d.date)}</div>
                                <div className="col-span-1">
                                    <span className={`tech-stamp px-2 py-1 border ${STATUS_BADGE[d.status] || "border-[#dde5f0]"}`}>{d.status}</span>
                                </div>
                                <div className="col-span-2 flex justify-end gap-1">
                                    <button onClick={() => downloadPdf(d)} title="Télécharger PDF" className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]">
                                        <Download className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => openEmail(d)} title="Envoyer par courriel" className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]">
                                        <Send className="w-3.5 h-3.5" />
                                    </button>
                                    <Link to={`/admin/imprimer/connaissement/${d.id}`} target="_blank" rel="noopener" title="Aperçu HTML" className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]">
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
                    ))}
                </ul>
            </div>

            <Modal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                title={editing ? `Modifier le connaissement CONN-${String(editing.number).padStart(4, "0")}` : "Nouveau connaissement"}
                testId="bol-modal"
                wide
                footer={
                    <>
                        <button onClick={() => setModalOpen(false)} className="btn-secondary !py-2 !px-4 !text-xs">Annuler</button>
                        <button onClick={save} data-testid="bol-save" className="btn-primary !py-2 !px-4 !text-xs">Enregistrer</button>
                    </>
                }
            >
                <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="border border-[#dde5f0] p-4 bg-[#f9fbfd]">
                            <div className="tech-stamp mb-3">Expéditeur (Shipper)</div>
                            <PartyForm value={form.shipper_snapshot} onChange={(v) => set("shipper_snapshot", v)} hideKind compact />
                        </div>
                        <div className="border border-[#dde5f0] p-4 bg-[#f9fbfd]">
                            <div className="tech-stamp mb-3">Destinataire (Consignee)</div>
                            <PartyForm value={form.consignee_snapshot} onChange={(v) => set("consignee_snapshot", v)} hideKind compact />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <Field label="Date" required>
                            <input type="date" value={form.date} onChange={(e) => set("date", e.target.value)} className={inputClass} />
                        </Field>
                        <Field label="Livraison attendue">
                            <input type="date" value={form.expected_delivery || ""} onChange={(e) => set("expected_delivery", e.target.value)} className={inputClass} />
                        </Field>
                        <Field label="Transporteur">
                            <input type="text" value={form.carrier || ""} onChange={(e) => set("carrier", e.target.value)} className={inputClass} placeholder="ex. Purolator, Transport SG" />
                        </Field>
                        <Field label="Statut">
                            <select value={form.status} onChange={(e) => set("status", e.target.value)} className={inputClass}>
                                {BOL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </Field>
                    </div>

                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <div className="tech-stamp">Articles transportés</div>
                            <button type="button" onClick={addItem} className="btn-secondary !py-1.5 !px-3 !text-xs">
                                <Plus className="w-3 h-3" />
                                Article
                            </button>
                        </div>
                        <div className="border border-[#dde5f0] bg-white">
                            <div className="hidden md:grid grid-cols-12 gap-2 px-3 py-2 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp text-[10px]">
                                <div className="col-span-5">Description</div>
                                <div className="col-span-1 text-right">Qté</div>
                                <div className="col-span-2">Unité</div>
                                <div className="col-span-1 text-right">Poids (kg)</div>
                                <div className="col-span-2">Dimensions</div>
                                <div className="col-span-1" />
                            </div>
                            {form.items.map((it, idx) => (
                                <div key={idx} className="grid grid-cols-1 md:grid-cols-12 gap-2 px-3 py-2 items-center border-b border-[#dde5f0] last:border-b-0">
                                    <div className="md:col-span-5">
                                        <input type="text" value={it.description} onChange={(e) => updateItem(idx, { description: e.target.value })} className={inputClass + " !text-xs"} />
                                    </div>
                                    <div className="md:col-span-1">
                                        <input type="number" step="0.01" min="0" value={it.quantity} onChange={(e) => updateItem(idx, { quantity: e.target.value })} className={inputClass + " !text-xs text-right"} />
                                    </div>
                                    <div className="md:col-span-2">
                                        <input type="text" value={it.unit} onChange={(e) => updateItem(idx, { unit: e.target.value })} className={inputClass + " !text-xs"} />
                                    </div>
                                    <div className="md:col-span-1">
                                        <input type="number" step="0.01" min="0" value={it.weight_kg} onChange={(e) => updateItem(idx, { weight_kg: e.target.value })} className={inputClass + " !text-xs text-right"} />
                                    </div>
                                    <div className="md:col-span-2">
                                        <input type="text" value={it.dimensions} onChange={(e) => updateItem(idx, { dimensions: e.target.value })} className={inputClass + " !text-xs"} placeholder="40×30×20 cm" />
                                    </div>
                                    <div className="md:col-span-1 flex justify-end">
                                        <button type="button" onClick={() => removeItem(idx)} className="p-1.5 border border-[#dde5f0] hover:bg-red-50 text-red-600">
                                            <Trash2 className="w-3 h-3" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Field label="Poids total (kg)">
                            <input type="number" step="0.01" min="0" value={form.total_weight_kg} onChange={(e) => set("total_weight_kg", e.target.value)} className={inputClass} />
                        </Field>
                        <Field label="Instructions spéciales">
                            <textarea rows={2} value={form.special_instructions || ""} onChange={(e) => set("special_instructions", e.target.value)} className={inputClass} />
                        </Field>
                    </div>
                </div>
            </Modal>
        </div>
    );
};
