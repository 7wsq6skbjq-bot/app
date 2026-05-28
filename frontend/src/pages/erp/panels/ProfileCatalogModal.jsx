import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, Copy, BookOpen } from "lucide-react";
import { Modal } from "../components/Modal";
import { useAuth } from "@/context/AuthContext";

/** Read-only catalog of profiles (AT1000/2000, ATi, Trifab, Kawneer).
 *  Opens from CutListPanel → "Catalogue profilés" button.
 *  Lets the user copy a part number to clipboard in one click. */
export const ProfileCatalogModal = ({ open, onClose }) => {
    const { http } = useAuth();
    const [data, setData] = useState(null);
    const [busy, setBusy] = useState(false);
    const [expandedSystem, setExpandedSystem] = useState(null);
    const [filter, setFilter] = useState("");

    useEffect(() => {
        if (!open || data) return;
        setBusy(true);
        http.get("/admin/profile-catalog")
            .then((r) => setData(r.data))
            .catch((e) => alert(e?.response?.data?.detail || "Erreur de chargement du catalogue"))
            .finally(() => setBusy(false));
    }, [open, data, http]);

    const copy = async (text) => {
        try {
            await navigator.clipboard.writeText(text);
        } catch {
            /* noop on insecure context */
        }
    };

    const filterMatch = (s) => {
        if (!filter) return true;
        const q = filter.toLowerCase();
        return (
            s.manufacturer.toLowerCase().includes(q) ||
            s.system.toLowerCase().includes(q) ||
            s.profiles.some(
                (p) => (p.label || "").toLowerCase().includes(q)
                    || (p.part_number || "").toLowerCase().includes(q),
            )
        );
    };

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="📚 Catalogue de profilés Portech"
            testId="catalog-modal"
            wide
            footer={
                <button onClick={onClose} className="px-4 py-2 border border-[#dde5f0] tech-stamp">
                    Fermer
                </button>
            }
        >
            <div className="space-y-4">
                <div>
                    <input
                        type="text"
                        placeholder="Rechercher (ex. AT2000, Kawneer, #450CG005…)"
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm"
                        data-testid="catalog-search"
                    />
                </div>

                {busy && <div className="text-sm text-[#4b5d7a]">Chargement…</div>}

                {data && data.categories.map((cat) => {
                    const sysList = cat.systems.filter(filterMatch);
                    if (sysList.length === 0) return null;
                    return (
                        <section key={cat.id}>
                            <div className="tech-stamp text-[#0c182b] mb-2 pb-1 border-b border-[#dde5f0]">
                                {cat.label}
                            </div>
                            <div className="space-y-2">
                                {sysList.map((sys) => {
                                    const open = expandedSystem === sys.id;
                                    return (
                                        <div key={sys.id}
                                            className="border border-[#dde5f0] bg-white"
                                            data-testid={`catalog-system-${sys.id}`}
                                        >
                                            <button
                                                onClick={() => setExpandedSystem(open ? null : sys.id)}
                                                className="w-full flex items-start gap-3 p-3 hover:bg-[#f3f6fb] text-left"
                                            >
                                                {open
                                                    ? <ChevronDown className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                                    : <ChevronRight className="w-4 h-4 flex-shrink-0 mt-0.5" />}
                                                <div className="flex-1 min-w-0">
                                                    <div className="font-display font-bold text-[#0c182b]">
                                                        {sys.manufacturer} {sys.system}
                                                        {sys.insulated && (
                                                            <span className="ml-2 text-[10px] tech-stamp px-1.5 py-0.5 border border-[#e8d27b] bg-[#fdfae0] text-[#8a7a1f]">
                                                                Isolé
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="text-[11px] text-[#4b5d7a]">{sys.description}</div>
                                                </div>
                                            </button>
                                            {open && (
                                                <div className="border-t border-[#dde5f0] p-3 bg-[#f9fbfd] space-y-3">
                                                    {sys.standard_leaf_mm && (
                                                        <div className="text-[11px] text-[#0c182b]">
                                                            <b>Battant standard (ouverture 36\"×84\"):</b>{" "}
                                                            {sys.standard_leaf_mm.width} × {sys.standard_leaf_mm.height} mm
                                                            {sys.glass_thickness_default_mm
                                                                ? <> · Verre {sys.glass_thickness_default_mm} mm</>
                                                                : null}
                                                        </div>
                                                    )}

                                                    <table className="w-full text-[11px]">
                                                        <thead>
                                                            <tr className="text-[#4b5d7a] border-b border-[#dde5f0]">
                                                                <th className="text-left py-1">Profilé</th>
                                                                <th className="text-left py-1">Dim. po</th>
                                                                <th className="text-left py-1">Dim. mm</th>
                                                                <th className="text-left py-1">N° pièce</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {sys.profiles.map((p, i) => (
                                                                <tr key={i} className="border-b border-[#dde5f0]/50">
                                                                    <td className="py-1.5 pr-2 align-top">
                                                                        <div className="font-medium text-[#0c182b]">{p.label}</div>
                                                                        {p.usage && (
                                                                            <div className="text-[10px] text-[#4b5d7a] italic">{p.usage}</div>
                                                                        )}
                                                                    </td>
                                                                    <td className="py-1.5 pr-2 align-top whitespace-nowrap">{p.dim_in || "—"}</td>
                                                                    <td className="py-1.5 pr-2 align-top whitespace-nowrap">{p.dim_mm || "—"}</td>
                                                                    <td className="py-1.5 align-top whitespace-nowrap">
                                                                        {p.part_number ? (
                                                                            <button
                                                                                onClick={() => copy(p.part_number)}
                                                                                className="inline-flex items-center gap-1 font-mono text-[10px] px-1.5 py-0.5 bg-white border border-[#dde5f0] hover:bg-[#eaf1fb]"
                                                                                title="Copier"
                                                                            >
                                                                                {p.part_number} <Copy className="w-3 h-3" />
                                                                            </button>
                                                                        ) : <span className="text-[#4b5d7a]">—</span>}
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>

                                                    {sys.calculation_rules && sys.calculation_rules.length > 0 && (
                                                        <div className="bg-[#fdf2e0] border border-[#e8b87b] p-2 text-[11px] text-[#8a4f1f]">
                                                            <div className="font-bold mb-1">Règles de calcul :</div>
                                                            <ul className="list-disc pl-4 space-y-0.5">
                                                                {sys.calculation_rules.map((r, i) => <li key={i}>{r}</li>)}
                                                            </ul>
                                                        </div>
                                                    )}

                                                    {sys.hardware_typical && sys.hardware_typical.length > 0 && (
                                                        <div className="text-[11px]">
                                                            <div className="text-[#4b5d7a] font-medium mb-1">Quincaillerie typique :</div>
                                                            <ul className="list-disc pl-4 text-[#0c182b]">
                                                                {sys.hardware_typical.map((h, i) => <li key={i}>{h}</li>)}
                                                            </ul>
                                                        </div>
                                                    )}

                                                    {sys.notes && sys.notes.length > 0 && (
                                                        <div className="text-[11px] text-[#4b5d7a] italic border-t border-[#dde5f0] pt-2">
                                                            <BookOpen className="w-3 h-3 inline mr-1" />
                                                            {sys.notes.join(" · ")}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </section>
                    );
                })}

                {data && (
                    <div className="text-[10px] text-[#4b5d7a] italic">
                        Parclose carrée ¼" standard Portech : <b>{data.parclose_face_mm} mm</b> face.
                        Catalogue {data.total_systems} systèmes — données vérifiées via les DXF officiels AT Fabrication
                        et les plans BMO / Uniprix.
                    </div>
                )}
            </div>
        </Modal>
    );
};
