import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Pencil, Trash2, RefreshCw, Printer } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Modal } from "../components/Modal";
import { DocumentForm } from "../components/DocumentForm";
import {
    STATUS_BADGE,
    formatCurrency,
    formatDate,
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
}) => {
    const { http } = useAuth();
    const [rows, setRows] = useState([]);
    const [parties, setParties] = useState([]);
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(emptyDoc());

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
                items: form.items.map((it) => ({
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

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <div className="tech-stamp mb-1">{eyebrow}</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">{title}</h1>
                </div>
                <div className="flex gap-2">
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={openNew} data-testid={`erp-new-${kind}`} className="btn-primary !py-2 !px-4 !text-xs">
                        <Plus className="w-3.5 h-3.5" />
                        {feminineArticle ? "Nouvelle" : "Nouveau"} {singular}
                    </button>
                </div>
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
                {rows.length === 0 && !loading && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">
                        Aucun{feminineArticle ? "e" : ""} {singular}. Cliquez sur « {feminineArticle ? "Nouvelle" : "Nouveau"} {singular} » pour en créer un{feminineArticle ? "e" : ""}.
                    </div>
                )}
                <ul>
                    {rows.map((d) => (
                        <li key={d.id} className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors">
                            <div className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-3 items-center">
                                <div className="col-span-2 font-display font-bold text-sm">{numberPrefix}-{String(d.number).padStart(4, "0")}</div>
                                <div className="col-span-3 text-sm truncate">{d[partyKey]?.name || "—"}</div>
                                <div className="col-span-2 text-sm text-[#4b5d7a]">{formatDate(d.date)}</div>
                                <div className="col-span-2 text-sm text-right font-display font-bold">{formatCurrency(d.total)}</div>
                                <div className="col-span-1">
                                    <span className={`tech-stamp px-2 py-1 border ${STATUS_BADGE[d.status] || "border-[#dde5f0]"}`}>
                                        {d.status}
                                    </span>
                                </div>
                                <div className="col-span-2 flex justify-end gap-1">
                                    <Link
                                        to={`${printPath}/${d.id}`}
                                        target="_blank"
                                        rel="noopener"
                                        data-testid={`${kind}-print-${d.id}`}
                                        className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]"
                                        aria-label="Imprimer / PDF"
                                    >
                                        <Printer className="w-3.5 h-3.5" />
                                    </Link>
                                    <button onClick={() => openEdit(d)} className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]">
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => remove(d)} className="p-2 border border-[#dde5f0] hover:bg-red-50 text-red-600">
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
        </div>
    );
};
