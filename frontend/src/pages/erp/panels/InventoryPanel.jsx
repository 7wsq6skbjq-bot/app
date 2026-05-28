/** Aluminum bar inventory — list, add (with merge), adjust qty +/-, delete.
 *  Shows full bars vs reusable chutes (off-cuts auto-saved on cut confirm). */
import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2, Minus, RefreshCw, Boxes, Scissors as ScissorsIcon } from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";
import { useAuth } from "@/context/AuthContext";

// Each preset has:
//   - `key`     : the exact `profile_key` saved to inventory. MUST MATCH what the
//                 optimizer produces in `display_profile` for matching cut groups —
//                 i.e. `"{manufacturer} #{part_number}"` when a part_number is set,
//                 so that "Confirmer coupes" can find and deduct the right row.
//   - `desc`    : human-readable description shown in the dropdown.
//   - `len`     : default bar length in mm.
const PRESET_KEYS = [
    // ─── AT Fabrication — séries de portes ───
    { key: "AT Fabrication #ATT1005", desc: "ATT1005 — Tête 2¼\" (AT1000 / ATi1000)", len: 6800 },
    { key: "AT Fabrication #AT1000",  desc: "AT1000 — Base 3⅞\" AT1000 / Tête 3⅞\" AT2000 (extrusion partagée)", len: 6800 },
    { key: "AT Fabrication #AT1025",  desc: "AT1025 — Montant charnière 2\" (AT1000 / ATi1000)", len: 6800 },
    { key: "AT Fabrication #AT1020",  desc: "AT1020 — Montant serrure 2⅛\" (AT1000 / ATi1000)", len: 6800 },
    { key: "AT Fabrication #AT2000",  desc: "AT2000 — Base 6⅞\" (AT2000 / ATi2000)", len: 6800 },
    { key: "AT Fabrication #AT2025",  desc: "AT2025 — Jambage charnière 3½\" (AT2000 / ATi2000)", len: 6800 },
    { key: "AT Fabrication #AT2020",  desc: "AT2020 — Jambage serrure 3⅝\" (AT2000 / ATi2000)", len: 6800 },
    { key: "AT Fabrication #ATV1030", desc: "ATV1030 — Cladding vertical ATi1000", len: 6800 },
    { key: "AT Fabrication #ATCHA1035", desc: "ATCHA1035 — Cladding horizontal ATi1000", len: 6800 },
    { key: "AT Fabrication #ATV2030", desc: "ATV2030 — Cladding vertical ATi2000", len: 6800 },
    { key: "AT Fabrication #ATCHA2025", desc: "ATCHA2025 — Cladding horizontal ATi2000", len: 6800 },
    // ─── Trifab Flush Glaze ───
    { key: "Trifab #450CG005", desc: "450CG005 — Tube à poche 1¾\" × 4½\"", len: 7315 },
    { key: "Trifab #450CG011", desc: "450CG011 — Tube escalier 1¾\" × 4½\"", len: 7315 },
    // ─── Kawneer Mur-rideau 1620 ───
    { key: "Kawneer #178-001", desc: "178-001 — Meneau 2\" × 3¾\"", len: 7315 },
    { key: "Kawneer #178-006", desc: "178-006 — Couvercle 2\" × ¾\"", len: 7315 },
    { key: "Kawneer #178-300", desc: "178-300 — Plaque à pression 2\"", len: 7315 },
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
    const [label, setLabel] = useState("");
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
                label: (label.trim() || profileKey.trim()),
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
                <Field label="Profil rapide (code AT Fabrication / Trifab / Kawneer)">
                    <select
                        value=""
                        onChange={(e) => {
                            const p = PRESET_KEYS.find(x => x.key === e.target.value);
                            if (p) {
                                setProfileKey(p.key);
                                setLabel(p.desc);
                                setLength(p.len);
                            }
                        }}
                        className={inputClass}
                        data-testid="inv-preset-select"
                    >
                        <option value="">— Choisir un préréglage —</option>
                        <optgroup label="AT Fabrication — séries portes">
                            {PRESET_KEYS.filter(p => p.key.startsWith("AT Fabrication")).map((p) =>
                                <option key={p.key} value={p.key}>{p.desc} ({p.len} mm)</option>)}
                        </optgroup>
                        <optgroup label="Trifab — Flush Glaze">
                            {PRESET_KEYS.filter(p => p.key.startsWith("Trifab")).map((p) =>
                                <option key={p.key} value={p.key}>{p.desc} ({p.len} mm)</option>)}
                        </optgroup>
                        <optgroup label="Kawneer — Mur-rideau 1620">
                            {PRESET_KEYS.filter(p => p.key.startsWith("Kawneer")).map((p) =>
                                <option key={p.key} value={p.key}>{p.desc} ({p.len} mm)</option>)}
                        </optgroup>
                    </select>
                </Field>
                <Field label="Clé inventaire (doit correspondre au format optimiseur)" required>
                    <input value={profileKey} onChange={(e) => setProfileKey(e.target.value)} className={inputClass}
                        placeholder="ex. AT Fabrication #ATT1005" />
                </Field>
                <Field label="Description (libre, affichée sous la clé)">
                    <input value={label} onChange={(e) => setLabel(e.target.value)} className={inputClass}
                        placeholder="ex. ATT1005 — Tête 2¼ AT1000" />
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
                    Standard Portech : portes AT en barres de <b>6800 mm</b> · Flush Glaze / Mur-rideau en barres de <b>7315 mm</b>.
                    Si une ligne identique existe déjà, la quantité est ajoutée (pas de doublon).
                    <br /><b>Note :</b> l'extrusion <code>AT1000</code> sert à la fois pour la base AT1000 (3⅞") et la tête AT2000 (3⅞") — une seule ligne d'inventaire pour les deux usages.
                </div>
            </div>
        </Modal>
    );
};

export default InventoryPanel;
