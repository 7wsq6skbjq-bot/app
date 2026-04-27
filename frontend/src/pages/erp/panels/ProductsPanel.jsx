import { useCallback, useEffect, useState } from "react";
import { Plus, Pencil, Trash2, RefreshCw } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Modal, Field, inputClass } from "../components/Modal";
import { formatCurrency } from "../utils";

const emptyProduct = () => ({
    sku: "",
    name: "",
    description: "",
    unit: "unité",
    unit_price: 0,
    category: "",
    is_service: false,
});

export const ProductsPanel = () => {
    const { http } = useAuth();
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(emptyProduct());

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const { data } = await http.get("/admin/products");
            setRows(data || []);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur");
        } finally {
            setLoading(false);
        }
    }, [http]);

    useEffect(() => { load(); }, [load]);

    const openNew = () => { setEditing(null); setForm(emptyProduct()); setModalOpen(true); };
    const openEdit = (p) => { setEditing(p); setForm({ ...p }); setModalOpen(true); };

    const save = async () => {
        try {
            const payload = { ...form, unit_price: Number(form.unit_price || 0) };
            if (editing) await http.put(`/admin/products/${editing.id}`, payload);
            else await http.post("/admin/products", payload);
            setModalOpen(false);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec");
        }
    };

    const remove = async (p) => {
        if (!window.confirm(`Supprimer ${p.name} ?`)) return;
        await http.delete(`/admin/products/${p.id}`);
        setRows((prev) => prev.filter((x) => x.id !== p.id));
    };

    const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <div className="tech-stamp mb-1">Catalogue interne</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Produits & services</h1>
                </div>
                <div className="flex gap-2">
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={openNew} data-testid="erp-new-product" className="btn-primary !py-2 !px-4 !text-xs">
                        <Plus className="w-3.5 h-3.5" />
                        Nouveau produit
                    </button>
                </div>
            </div>

            {error && <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>}

            <div className="border border-[#dde5f0] bg-white">
                <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                    <div className="col-span-2">SKU</div>
                    <div className="col-span-4">Nom</div>
                    <div className="col-span-2">Catégorie</div>
                    <div className="col-span-2 text-right">Prix unitaire</div>
                    <div className="col-span-2 text-right">Actions</div>
                </div>
                {rows.length === 0 && !loading && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">
                        Aucun produit. Ajoutez vos pièces et services fréquents pour les réutiliser sur les factures.
                    </div>
                )}
                <ul>
                    {rows.map((p) => (
                        <li key={p.id} className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors">
                            <div className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-3 items-center">
                                <div className="col-span-2 text-sm font-mono text-[#4b5d7a]">{p.sku || "—"}</div>
                                <div className="col-span-4 font-display font-semibold uppercase text-sm tracking-tight">{p.name}</div>
                                <div className="col-span-2 text-sm text-[#4b5d7a]">{p.category || "—"}</div>
                                <div className="col-span-2 text-sm text-right font-display font-bold">{formatCurrency(p.unit_price)}</div>
                                <div className="col-span-2 flex justify-end gap-1">
                                    <button onClick={() => openEdit(p)} className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]">
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => remove(p)} className="p-2 border border-[#dde5f0] hover:bg-red-50 text-red-600">
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
                title={editing ? "Modifier le produit" : "Nouveau produit"}
                testId="product-modal"
                footer={
                    <>
                        <button onClick={() => setModalOpen(false)} className="btn-secondary !py-2 !px-4 !text-xs">Annuler</button>
                        <button onClick={save} disabled={!form.name?.trim()} data-testid="product-save" className="btn-primary !py-2 !px-4 !text-xs disabled:opacity-40">
                            Enregistrer
                        </button>
                    </>
                }
            >
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Field label="SKU / Code">
                            <input type="text" value={form.sku || ""} onChange={(e) => set("sku", e.target.value)} className={inputClass} />
                        </Field>
                        <Field label="Catégorie">
                            <input type="text" value={form.category || ""} onChange={(e) => set("category", e.target.value)} className={inputClass} placeholder="ex. Barres antipaniques" />
                        </Field>
                    </div>
                    <Field label="Nom" required>
                        <input type="text" value={form.name} onChange={(e) => set("name", e.target.value)} className={inputClass} required />
                    </Field>
                    <Field label="Description">
                        <textarea rows={2} value={form.description || ""} onChange={(e) => set("description", e.target.value)} className={inputClass} />
                    </Field>
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Unité">
                            <input type="text" value={form.unit || "unité"} onChange={(e) => set("unit", e.target.value)} className={inputClass} />
                        </Field>
                        <Field label="Prix unitaire (CAD)">
                            <input type="number" step="0.01" min="0" value={form.unit_price} onChange={(e) => set("unit_price", e.target.value)} className={inputClass} />
                        </Field>
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={!!form.is_service} onChange={(e) => set("is_service", e.target.checked)} />
                        Service (main-d'œuvre, temps) plutôt qu'un bien
                    </label>
                </div>
            </Modal>
        </div>
    );
};
