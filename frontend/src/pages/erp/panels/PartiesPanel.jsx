import { useCallback, useEffect, useState } from "react";
import { Plus, Pencil, Trash2, RefreshCw, Phone } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Modal } from "../components/Modal";
import { PartyForm } from "../components/PartyForm";
import { DataCard } from "../../../components/mobile/DataCard";
import { FAB } from "../../../components/mobile/FAB";
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
            <div className="flex items-center justify-between mb-6 flex-col md:flex-row gap-3">
                <div className="hidden md:block">
                    <div className="tech-stamp mb-1">Base de données</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">{title}</h1>
                </div>
                <div className="flex gap-2 w-full md:w-auto">
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={openNew} data-testid={`erp-new-${kind}`} className="hidden md:inline-flex btn-primary !py-2 !px-4 !text-xs">
                        <Plus className="w-3.5 h-3.5" />
                        Nouveau {singular}
                    </button>
                </div>
            </div>

            {error && (
                <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>
            )}

            {/* MOBILE: cards */}
            <div className="md:hidden space-y-3">
                {rows.length === 0 && !loading && (
                    <div className="p-8 text-center text-[#4b5d7a] text-sm border border-[#dde5f0] bg-white">
                        Aucun {singular}. Appuyez sur + pour commencer.
                    </div>
                )}
                {rows.map((p) => (
                    <DataCard
                        key={p.id}
                        testid={`party-card-${p.id}`}
                        title={p.name}
                        subtitle={[p.city, p.email].filter(Boolean).join(" · ")}
                        primary={p.phone || ""}
                        actions={p.phone ? [{
                            icon: Phone,
                            onClick: () => { window.location.href = `tel:${p.phone}`; },
                            label: "Appeler",
                            color: "border-[#8ec79d] bg-[#e6f4ea] text-[#0b6b2f] active:bg-[#cdebd6]",
                            testid: `party-call-${p.id}`,
                        }] : []}
                        onTap={() => openEdit(p)}
                    />
                ))}
            </div>

            {/* DESKTOP: table */}
            <div className="hidden md:block border border-[#dde5f0] bg-white">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
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
                            <div className="grid grid-cols-12 gap-4 px-6 py-3 items-center">
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

            <FAB onClick={openNew} label={`Nouveau ${singular}`} testid={`erp-fab-new-${kind}`} />

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
