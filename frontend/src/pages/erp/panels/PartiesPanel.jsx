import { useCallback, useEffect, useState } from "react";
import { Plus, Pencil, Trash2, RefreshCw } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Modal } from "../components/Modal";
import { PartyForm } from "../components/PartyForm";
import { emptyParty } from "../utils";

export const PartiesPanel = ({ kind }) => {
    const { http } = useAuth();
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [editing, setEditing] = useState(null); // null | party object
    const [form, setForm] = useState(emptyParty(kind));

    const title = kind === "customer" ? "Clients" : "Fournisseurs";
    const singular = kind === "customer" ? "client" : "fournisseur";

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const { data } = await http.get(`/admin/parties?kind=${kind}`);
            setRows(data || []);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally {
            setLoading(false);
        }
    }, [http, kind]);

    useEffect(() => { load(); }, [load]);

    const openNew = () => {
        setEditing(null);
        setForm(emptyParty(kind));
        setModalOpen(true);
    };

    const openEdit = (p) => {
        setEditing(p);
        setForm({ ...p });
        setModalOpen(true);
    };

    const save = async () => {
        try {
            const payload = { ...form, kind };
            if (editing) {
                await http.put(`/admin/parties/${editing.id}`, payload);
            } else {
                await http.post("/admin/parties", payload);
            }
            setModalOpen(false);
            await load();
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec de l'enregistrement");
        }
    };

    const remove = async (p) => {
        if (!window.confirm(`Supprimer ${p.name} ?`)) return;
        try {
            await http.delete(`/admin/parties/${p.id}`);
            setRows((prev) => prev.filter((x) => x.id !== p.id));
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec de la suppression");
        }
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <div className="tech-stamp mb-1">Base de données</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">{title}</h1>
                </div>
                <div className="flex gap-2">
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={openNew} data-testid={`erp-new-${kind}`} className="btn-primary !py-2 !px-4 !text-xs">
                        <Plus className="w-3.5 h-3.5" />
                        Nouveau {singular}
                    </button>
                </div>
            </div>

            {error && (
                <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>
            )}

            <div className="border border-[#dde5f0] bg-white">
                <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                    <div className="col-span-4">Nom</div>
                    <div className="col-span-3">Ville</div>
                    <div className="col-span-3">Courriel</div>
                    <div className="col-span-2 text-right">Actions</div>
                </div>
                {rows.length === 0 && !loading && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">
                        Aucun {singular} enregistré. Cliquez sur « Nouveau {singular} » pour commencer.
                    </div>
                )}
                <ul>
                    {rows.map((p) => (
                        <li
                            key={p.id}
                            className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors"
                        >
                            <div className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-3 items-center">
                                <div className="col-span-4 font-display font-semibold uppercase text-sm tracking-tight">
                                    {p.name}
                                </div>
                                <div className="col-span-3 text-sm text-[#4b5d7a]">{p.city || "—"}</div>
                                <div className="col-span-3 text-sm text-[#2f4f7f] truncate">{p.email || "—"}</div>
                                <div className="col-span-2 flex justify-end gap-1">
                                    <button
                                        onClick={() => openEdit(p)}
                                        data-testid={`party-edit-${p.id}`}
                                        className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]"
                                        aria-label="Modifier"
                                    >
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                        onClick={() => remove(p)}
                                        data-testid={`party-delete-${p.id}`}
                                        className="p-2 border border-[#dde5f0] hover:bg-red-50 text-red-600"
                                        aria-label="Supprimer"
                                    >
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
                title={editing ? `Modifier ${singular}` : `Nouveau ${singular}`}
                testId={`party-modal-${kind}`}
                wide
                footer={
                    <>
                        <button onClick={() => setModalOpen(false)} className="btn-secondary !py-2 !px-4 !text-xs">
                            Annuler
                        </button>
                        <button
                            onClick={save}
                            disabled={!form.name?.trim()}
                            data-testid="party-save"
                            className="btn-primary !py-2 !px-4 !text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            Enregistrer
                        </button>
                    </>
                }
            >
                <PartyForm value={form} onChange={setForm} hideKind />
            </Modal>
        </div>
    );
};
