/** Template-based deterministic elevation builder (no IA).
 *  User fills a form, backend computes every cut with correct profile names
 *  + part numbers + auto-calculated bris-thermique / garniture totals.
 */
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";
import { useAuth } from "@/context/AuthContext";

const KIND_LABELS = {
    at_door: "Porte AT seule",
    flush_glaze: "Flush Glaze (Trifab VG450)",
    curtain_wall: "Mur-rideau (Kawneer 1620)",
};

const SERIES_OPTIONS = ["AT1000", "AT2000", "ATi1000", "ATi2000", "AT1000-base-AT2000"];
const HANDING_OPTIONS = ["", "MD", "MG", "MDR", "MGR"];

const emptyLengthRow = () => ({ length_mm: 0, qty: 1 });
const emptyGlassRow = () => ({ width_mm: 0, height_mm: 0, thickness_mm: 6, qty: 1 });

export const TemplateBuilderModal = ({ open, onClose, onItemsBuilt }) => {
    const { http } = useAuth();
    const [kind, setKind] = useState("at_door");
    const [code, setCode] = useState("E1");
    const [totalW, setTotalW] = useState(0);
    const [totalH, setTotalH] = useState(0);
    const [finishExt, setFinishExt] = useState("Anodisé Noir");
    const [finishInt, setFinishInt] = useState("");

    // Door fields
    const [series, setSeries] = useState("AT2000");
    const [leafW, setLeafW] = useState(723.1);
    const [leafH, setLeafH] = useState(2114.5);
    const [glassT, setGlassT] = useState(6);
    const [doorNumber, setDoorNumber] = useState("");
    const [handing, setHanding] = useState("");
    const [hasIntegratedDoor, setHasIntegratedDoor] = useState(false);

    // FG/MR rows
    const [verticals, setVerticals] = useState([emptyLengthRow()]);
    const [horizontalsPoche, setHorizontalsPoche] = useState([emptyLengthRow()]);
    const [horizontalsEscalier, setHorizontalsEscalier] = useState([]);
    const [horizontalsKawneer, setHorizontalsKawneer] = useState([emptyLengthRow()]);
    const [glasses, setGlasses] = useState([emptyGlassRow()]);

    const [busy, setBusy] = useState(false);

    const reset = () => {
        setCode("E1"); setTotalW(0); setTotalH(0);
        setFinishExt("Anodisé Noir"); setFinishInt("");
        setSeries("AT2000"); setLeafW(723.1); setLeafH(2114.5); setGlassT(6);
        setDoorNumber(""); setHanding(""); setHasIntegratedDoor(false);
        setVerticals([emptyLengthRow()]); setHorizontalsPoche([emptyLengthRow()]);
        setHorizontalsEscalier([]); setHorizontalsKawneer([emptyLengthRow()]);
        setGlasses([emptyGlassRow()]);
    };

    const buildPayload = () => {
        const base = { kind, code };
        if (kind === "at_door") {
            return {
                ...base,
                series, leaf_width_mm: leafW, leaf_height_mm: leafH,
                glass_thickness_mm: glassT, door_number: doorNumber || null, handing: handing || null,
            };
        }
        const ev = {
            ...base,
            total_width_mm: totalW, total_height_mm: totalH,
            finish_ext: finishExt, finish_int: finishInt || finishExt,
            verticals: verticals.filter(v => v.length_mm > 0),
            glasses: glasses.filter(g => g.width_mm > 0 && g.height_mm > 0),
        };
        if (kind === "flush_glaze") {
            ev.horizontals_poche = horizontalsPoche.filter(h => h.length_mm > 0);
            ev.horizontals_escalier = horizontalsEscalier.filter(h => h.length_mm > 0);
        } else {
            ev.horizontals = horizontalsKawneer.filter(h => h.length_mm > 0);
        }
        if (hasIntegratedDoor) {
            ev.door = {
                series, leaf_width_mm: leafW, leaf_height_mm: leafH,
                glass_thickness_mm: glassT,
                door_number: doorNumber || null, handing: handing || null,
            };
        }
        return ev;
    };

    const submit = async () => {
        if (!code.trim()) { alert("Code d'élévation requis."); return; }
        setBusy(true);
        try {
            const { data } = await http.post("/admin/cuts/template-build", buildPayload());
            onItemsBuilt(data);
            reset();
            onClose();
        } catch (e) {
            alert(e?.response?.data?.detail || "Erreur build template");
        } finally {
            setBusy(false);
        }
    };

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="📐 Gabarit guidé — calcul déterministe"
            testId="cuts-template-builder"
            wide
            footer={
                <>
                    <button onClick={onClose} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                    <button
                        onClick={submit}
                        disabled={busy}
                        data-testid="cuts-template-build-submit"
                        className="px-4 py-2 bg-[#0c182b] text-white tech-stamp disabled:opacity-50"
                    >
                        {busy ? "Calcul…" : "Calculer et ajouter à la liste"}
                    </button>
                </>
            }
        >
            <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <Field label="Type de gabarit" required>
                        <select value={kind} onChange={e => setKind(e.target.value)} className={inputClass} data-testid="cuts-template-kind">
                            {Object.entries(KIND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                        </select>
                    </Field>
                    <Field label="Code d'élévation" required>
                        <input value={code} onChange={e => setCode(e.target.value)} className={inputClass}
                            placeholder="ex. MR1, FG01, P-101" data-testid="cuts-template-code" />
                    </Field>
                    {kind !== "at_door" && (
                        <Field label="Fini extérieur">
                            <input value={finishExt} onChange={e => setFinishExt(e.target.value)} className={inputClass} />
                        </Field>
                    )}
                </div>

                {kind !== "at_door" && (
                    <>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <Field label="Largeur totale (mm)">
                                <input type="number" value={totalW} onChange={e => setTotalW(parseFloat(e.target.value) || 0)} className={inputClass} />
                            </Field>
                            <Field label="Hauteur totale (mm)">
                                <input type="number" value={totalH} onChange={e => setTotalH(parseFloat(e.target.value) || 0)} className={inputClass} />
                            </Field>
                            <Field label="Fini intérieur (si différent)">
                                <input value={finishInt} onChange={e => setFinishInt(e.target.value)} className={inputClass}
                                    placeholder="vide = même que extérieur" />
                            </Field>
                        </div>

                        <LengthList label="Meneaux verticaux" rows={verticals} setRows={setVerticals} testid="verticals" />
                        {kind === "flush_glaze" && (
                            <>
                                <LengthList label="Horizontaux Tube à poche (linteau + intermédiaires)"
                                    rows={horizontalsPoche} setRows={setHorizontalsPoche} testid="hpoche" />
                                <LengthList label="Horizontaux Tube escalier (bas de chaque verre)"
                                    rows={horizontalsEscalier} setRows={setHorizontalsEscalier} testid="hesc" />
                            </>
                        )}
                        {kind === "curtain_wall" && (
                            <LengthList label="Meneaux horizontaux Kawneer" rows={horizontalsKawneer} setRows={setHorizontalsKawneer} testid="hkaw" />
                        )}
                        <GlassList glasses={glasses} setGlasses={setGlasses} />

                        <label className="flex items-center gap-2 text-sm font-medium text-[#0c182b]">
                            <input type="checkbox" checked={hasIntegratedDoor}
                                onChange={e => setHasIntegratedDoor(e.target.checked)}
                                data-testid="cuts-template-has-door" />
                            Inclure une porte intégrée (l'élévation devient « mixte »)
                        </label>
                    </>
                )}

                {(kind === "at_door" || hasIntegratedDoor) && (
                    <div className="p-3 bg-[#f3f6fb] border border-[#dde5f0]">
                        <div className="tech-stamp text-[#4b5d7a] mb-2">Spécifications de la porte AT</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <Field label="Série">
                                <select value={series} onChange={e => setSeries(e.target.value)} className={inputClass}>
                                    {SERIES_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                            </Field>
                            <Field label="Largeur battant (mm)">
                                <input type="number" step="0.1" value={leafW}
                                    onChange={e => setLeafW(parseFloat(e.target.value) || 0)}
                                    className={inputClass} data-testid="cuts-template-leaf-w" />
                            </Field>
                            <Field label="Hauteur battant (mm)">
                                <input type="number" step="0.1" value={leafH}
                                    onChange={e => setLeafH(parseFloat(e.target.value) || 0)}
                                    className={inputClass} data-testid="cuts-template-leaf-h" />
                            </Field>
                            <Field label="Verre (mm)">
                                <input type="number" step="0.1" value={glassT}
                                    onChange={e => setGlassT(parseFloat(e.target.value) || 0)}
                                    className={inputClass} />
                            </Field>
                            <Field label="N° porte">
                                <input value={doorNumber} onChange={e => setDoorNumber(e.target.value)} className={inputClass}
                                    placeholder="ex. P-101" />
                            </Field>
                            <Field label="Sens d'ouverture">
                                <select value={handing} onChange={e => setHanding(e.target.value)} className={inputClass}>
                                    {HANDING_OPTIONS.map(h => <option key={h} value={h}>{h || "—"}</option>)}
                                </select>
                            </Field>
                        </div>
                    </div>
                )}

                <div className="p-3 bg-[#fdf2e0] border border-[#e8b87b] text-[11px] text-[#8a4f1f]">
                    💡 Ce gabarit calcule de façon <b>déterministe</b> (zéro IA) tous les profilés
                    avec les bons numéros de pièce (Trifab #450CG005/011, Kawneer #178-001/006/300,
                    #162-310 bris thermique, #027074/027-850 garniture).
                    Pour chaque relance, vous obtiendrez exactement le même résultat.
                </div>
            </div>
        </Modal>
    );
};

const LengthList = ({ label, rows, setRows, testid }) => (
    <div>
        <div className="flex items-center justify-between mb-1">
            <div className="tech-stamp text-[#4b5d7a] text-[11px]">{label}</div>
            <button onClick={() => setRows([...rows, emptyLengthRow()])}
                className="px-2 py-1 border border-[#dde5f0] text-[10px] tech-stamp hover:bg-[#f3f6fb]"
                data-testid={`cuts-template-add-${testid}`}>
                <Plus className="w-3 h-3 inline" /> Ajouter
            </button>
        </div>
        {rows.length === 0 ? (
            <div className="text-[11px] text-[#4b5d7a] italic">Aucune ligne — cliquez « Ajouter ».</div>
        ) : (
            <div className="space-y-1">
                {rows.map((r, i) => (
                    <div key={i} className="flex gap-2 items-center">
                        <input type="number" step="0.1" value={r.length_mm}
                            onChange={e => {
                                const v = [...rows]; v[i] = { ...v[i], length_mm: parseFloat(e.target.value) || 0 };
                                setRows(v);
                            }}
                            placeholder="Longueur (mm)"
                            className="px-2 py-1 border border-[#dde5f0] flex-1 text-sm" />
                        <input type="number" min="1" value={r.qty}
                            onChange={e => {
                                const v = [...rows]; v[i] = { ...v[i], qty: parseInt(e.target.value, 10) || 1 };
                                setRows(v);
                            }}
                            placeholder="Qté"
                            className="px-2 py-1 border border-[#dde5f0] w-16 text-sm text-center" />
                        <button onClick={() => setRows(rows.filter((_, idx) => idx !== i))}
                            className="p-1 text-red-600 hover:bg-red-50">
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    </div>
                ))}
            </div>
        )}
    </div>
);

const GlassList = ({ glasses, setGlasses }) => (
    <div>
        <div className="flex items-center justify-between mb-1">
            <div className="tech-stamp text-[#4b5d7a] text-[11px]">Vitrages (W × H × ép × Qté)</div>
            <button onClick={() => setGlasses([...glasses, emptyGlassRow()])}
                className="px-2 py-1 border border-[#dde5f0] text-[10px] tech-stamp hover:bg-[#f3f6fb]"
                data-testid="cuts-template-add-glass">
                <Plus className="w-3 h-3 inline" /> Ajouter
            </button>
        </div>
        <div className="space-y-1">
            {glasses.map((g, i) => (
                <div key={i} className="flex gap-2 items-center">
                    <input type="number" placeholder="Largeur" value={g.width_mm}
                        onChange={e => { const v = [...glasses]; v[i] = { ...v[i], width_mm: parseFloat(e.target.value) || 0 }; setGlasses(v); }}
                        className="px-2 py-1 border border-[#dde5f0] flex-1 text-sm" />
                    <input type="number" placeholder="Hauteur" value={g.height_mm}
                        onChange={e => { const v = [...glasses]; v[i] = { ...v[i], height_mm: parseFloat(e.target.value) || 0 }; setGlasses(v); }}
                        className="px-2 py-1 border border-[#dde5f0] flex-1 text-sm" />
                    <input type="number" step="0.1" placeholder="Ép." value={g.thickness_mm}
                        onChange={e => { const v = [...glasses]; v[i] = { ...v[i], thickness_mm: parseFloat(e.target.value) || 0 }; setGlasses(v); }}
                        className="px-2 py-1 border border-[#dde5f0] w-20 text-sm text-center" />
                    <input type="number" min="1" placeholder="Qté" value={g.qty}
                        onChange={e => { const v = [...glasses]; v[i] = { ...v[i], qty: parseInt(e.target.value, 10) || 1 }; setGlasses(v); }}
                        className="px-2 py-1 border border-[#dde5f0] w-16 text-sm text-center" />
                    <button onClick={() => setGlasses(glasses.filter((_, idx) => idx !== i))}
                        className="p-1 text-red-600 hover:bg-red-50">
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            ))}
        </div>
    </div>
);
