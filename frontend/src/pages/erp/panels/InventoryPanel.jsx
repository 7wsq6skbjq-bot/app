/** Aluminum bar inventory — list, add (with merge), adjust qty +/-, delete.
 *  Shows full bars vs reusable chutes (off-cuts auto-saved on cut confirm). */
import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2, Minus, RefreshCw, Boxes, Scissors as ScissorsIcon } from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";
import { useAuth } from "@/context/AuthContext";

const PRESET_KEYS = [
    { key: "AT1000 - traverse haute/base 2 1/4\"", len: 6800 },
    { key: "AT1000 - montant 2\"", len: 6800 },
    { key: "AT1000 - montant 2 1/8\" (serrure)", len: 6800 },
    { key: "AT2000 - tête 3 7/8\"", len: 6800 },
    { key: "AT2000 - base 6 7/8\"", len: 6800 },
    { key: "AT2000 - jambage 3 1/2\" (charnière)", len: 6800 },
    { key: "AT2000 - jambage 3 5/8\" (serrure)", len: 6800 },
    { key: "Trifab VG450 #450CG005 Tube à poche", len: 7315 },
    { key: "Trifab VG450 #450CG011 Tube escalier", len: 7315 },
    { key: "Kawneer 1620 #178-001 Meneau", len: 7315 },
    { key: "Kawneer 1620 #178-006 Couvercle", len: 7315 },
    { key: "Kawneer 1620 #178-300 Plaque à pression", len: 7315 },
];

export const InventoryPanel = () => {
    const { http } = useAuth();
    const [bars, setBars] = useState([]);
    const [chutes, setChutes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [addOpen, setAddOpen] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await http.get("/admin/alu-inventory");
            setBars(data.bars || []);
            setChutes(data.chutes || []);
        } finally {
            setLoading(false);
        }
    }, [http]);

    useEffect(() => { load(); }, [load]);

    const adjust = async (row, delta) => {
        try {
            await http.patch(`/admin/alu-inventory/${row.id}`, { delta });
            await load();
        } catch (e) { alert(e?.response?.data?.detail || "Erreur"); }
    };
    const del = async (row) => {
        if (!window.confirm(`Supprimer ${row.profile_key} ${row.bar_length_mm}mm ?`)) return;
        try { await http.delete(`/admin/alu-inventory/${row.id}`); await load(); }
        catch (e) { alert(e?.response?.data?.detail || "Erreur"); }
    };

    return (
        <div className="space-y-4" data-testid="inventory-panel">
            <div className="flex items-center gap-2">
                <Boxes className="w-5 h-5 text-[#0c182b]" />
                <h2 className="font-display font-bold text-xl text-[#0c182b]">Inventaire aluminium</h2>
                <button onClick={load} className="ml-auto btn-secondary !py-1.5 !px-3 !text-xs">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Rafraîchir
                </button>
                <button onClick={() => setAddOpen(true)} data-testid="inv-add" className="btn-primary !py-1.5 !px-3 !text-xs">
                    <Plus className="w-3.5 h-3.5" /> Ajouter
                </button>
            </div>

            <InventoryTable title="Barres pleines" rows={bars} adjust={adjust} del={del} />
            <InventoryTable
                title={<><ScissorsIcon className="w-4 h-4 inline mr-1" />Chutes réutilisables (≥ 600 mm)</>}
                rows={chutes} adjust={adjust} del={del} chute
            />

            {addOpen && <AddInventoryModal onClose={() => setAddOpen(false)} onAdded={load} />}
        </div>
    );
};

const InventoryTable = ({ title, rows, adjust, del, chute = false }) => (
    <div className="bg-white border border-[#dde5f0]">
        <div className="px-3 py-2 bg-[#f3f6fb] border-b border-[#dde5f0] tech-stamp text-[#0c182b] text-xs">
            {title} — {rows.length}
        </div>
        {rows.length === 0 ? (
            <div className="p-3 text-sm text-[#4b5d7a] italic">Aucune entrée.</div>
        ) : (
            <table className="w-full text-sm">
                <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                    <tr>
                        <th className="text-left px-3 py-1.5">Profilé</th>
                        <th className="text-right px-3 py-1.5">Longueur</th>
                        <th className="text-right px-3 py-1.5">Qté</th>
                        <th className="text-right px-3 py-1.5">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((r) => (
                        <tr key={r.id} className="border-b border-[#dde5f0]/50">
                            <td className="px-3 py-1.5">
                                <div className="text-[#0c182b]">{r.profile_key}</div>
                                {r.label && r.label !== r.profile_key && (
                                    <div className="text-[10px] text-[#4b5d7a]">{r.label}</div>
                                )}
                            </td>
                            <td className="px-3 py-1.5 text-right font-mono text-xs">{r.bar_length_mm.toFixed(0)} mm</td>
                            <td className="px-3 py-1.5 text-right">
                                <div className="inline-flex items-center gap-1">
                                    <button onClick={() => adjust(r, -1)} className="p-1 border border-[#dde5f0] hover:bg-[#fee]" aria-label="-1">
                                        <Minus className="w-3 h-3" />
                                    </button>
                                    <span className={`w-8 text-center font-bold ${r.qty_available === 0 ? "text-red-600" : "text-[#0c182b]"}`}>
                                        {r.qty_available}
                                    </span>
                                    <button onClick={() => adjust(r, 1)} className="p-1 border border-[#dde5f0] hover:bg-[#efe]" aria-label="+1">
                                        <Plus className="w-3 h-3" />
                                    </button>
                                </div>
                            </td>
                            <td className="px-3 py-1.5 text-right">
                                <button onClick={() => del(r)} className="p-1 text-red-600 hover:bg-red-50">
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        )}
    </div>
);

const AddInventoryModal = ({ onClose, onAdded }) => {
    const { http } = useAuth();
    const [profileKey, setProfileKey] = useState("");
    const [length, setLength] = useState(6800);
    const [qty, setQty] = useState(1);
    const [busy, setBusy] = useState(false);

    const submit = async () => {
        if (!profileKey.trim() || qty < 1 || length <= 0) {
            alert("Profil, longueur et quantité requis.");
            return;
        }
        setBusy(true);
        try {
            await http.post("/admin/alu-inventory", {
                profile_key: profileKey.trim(),
                label: profileKey.trim(),
                bar_length_mm: length,
                qty_available: qty,
                is_chute: false,
            });
            await onAdded();
            onClose();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur");
        } finally { setBusy(false); }
    };

    return (
        <Modal
            open
            onClose={onClose}
            title="Ajouter au stock"
            testId="inv-add-modal"
            footer={
                <>
                    <button onClick={onClose} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                    <button onClick={submit} disabled={busy} data-testid="inv-add-submit" className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">
                        {busy ? "Ajout…" : "Ajouter"}
                    </button>
                </>
            }
        >
            <div className="space-y-3">
                <Field label="Profil rapide">
                    <select
                        value=""
                        onChange={(e) => {
                            const p = PRESET_KEYS.find(x => x.key === e.target.value);
                            if (p) { setProfileKey(p.key); setLength(p.len); }
                        }}
                        className={inputClass}
                    >
                        <option value="">— Choisir un préréglage —</option>
                        {PRESET_KEYS.map((p) => <option key={p.key} value={p.key}>{p.key} ({p.len} mm)</option>)}
                    </select>
                </Field>
                <Field label="Profil (texte libre, OK)" required>
                    <input value={profileKey} onChange={(e) => setProfileKey(e.target.value)} className={inputClass}
                        placeholder="ex. AT2000 — tête 3 7/8&quot;" />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                    <Field label="Longueur (mm)" required>
                        <input type="number" step="1" value={length}
                            onChange={(e) => setLength(parseFloat(e.target.value) || 0)}
                            className={inputClass} />
                    </Field>
                    <Field label="Quantité" required>
                        <input type="number" min="1" value={qty}
                            onChange={(e) => setQty(parseInt(e.target.value, 10) || 1)}
                            className={inputClass} />
                    </Field>
                </div>
                <div className="text-[11px] text-[#4b5d7a]">
                    Standard Portech : portes en barres de <b>6800 mm</b> · Flush Glaze / Mur-rideau en barres de <b>7315 mm</b>.
                    Si une ligne identique existe déjà, la quantité est ajoutée (pas de doublon).
                </div>
            </div>
        </Modal>
    );
};

export default InventoryPanel;
