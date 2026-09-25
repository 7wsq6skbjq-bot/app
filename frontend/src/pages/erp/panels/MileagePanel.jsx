/* eslint-disable react-hooks/exhaustive-deps */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Plus, Pencil, Trash2, RefreshCw, FileText, Route, Gauge, DollarSign, MapPin } from "lucide-react";
import { Modal, Field, inputClass } from "../components/Modal";
import { DataCard } from "../../../components/mobile/DataCard";
import { FAB } from "../../../components/mobile/FAB";
import { formatCurrency, formatDate } from "../utils";

const DEFAULT_RATE = 0.73;
const monthKey = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
const fmtKm = (v) => `${(Number(v) || 0).toLocaleString("fr-CA", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} km`;

const emptyTrip = () => ({
    date: new Date().toISOString().slice(0, 10),
    client_id: null,
    client_name: "",
    origin: "",
    destination: "",
    purpose: "",
    odometer_start: "",
    odometer_end: "",
    distance_km: 0,
    rate: DEFAULT_RATE,
    vehicle: "",
    job_number: "",
    notes: "",
});

export const MileagePanel = () => {
    const { http, getToken } = useAuth();
    const [rows, setRows] = useState([]);
    const [summary, setSummary] = useState(null);
    const [customers, setCustomers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [month, setMonth] = useState(monthKey());
    const [filterClient, setFilterClient] = useState("");
    const [editOpen, setEditOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [mode, setMode] = useState("direct"); // "direct" | "odometer"
    const [notice, setNotice] = useState("");
    const [billing, setBilling] = useState(false);

    const flash = (m) => { setNotice(m); setTimeout(() => setNotice(""), 5000); };

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (month) params.set("month", month);
            if (filterClient) params.set("client_id", filterClient);
            const [{ data: list }, { data: sum }, { data: cust }] = await Promise.all([
                http.get(`/admin/mileage?${params}`),
                http.get(`/admin/mileage/summary?month=${month}`),
                http.get("/admin/parties?kind=customer"),
            ]);
            setRows(list || []);
            setSummary(sum);
            setCustomers(cust || []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [month, filterClient]);

    useEffect(() => { load(); }, [load]);

    const computedKm = useMemo(() => {
        if (!editing) return 0;
        if (mode === "odometer") {
            const a = parseFloat(editing.odometer_start) || 0;
            const b = parseFloat(editing.odometer_end) || 0;
            return Math.max(0, Math.round((b - a) * 10) / 10);
        }
        return parseFloat(editing.distance_km) || 0;
    }, [editing, mode]);

    const computedAmount = useMemo(
        () => Math.round(computedKm * (parseFloat(editing?.rate) || DEFAULT_RATE) * 100) / 100,
        [computedKm, editing],
    );

    const openNew = () => { setEditing(emptyTrip()); setMode("direct"); setEditOpen(true); };
    const openEdit = (t) => {
        setEditing({ ...t, odometer_start: t.odometer_start ?? "", odometer_end: t.odometer_end ?? "" });
        setMode(t.odometer_start != null && t.odometer_end != null ? "odometer" : "direct");
        setEditOpen(true);
    };
    const closeEdit = () => { setEditOpen(false); setEditing(null); };

    const onPickClient = (name) => {
        const match = customers.find((c) => c.name === name);
        setEditing((p) => ({ ...p, client_name: name, client_id: match?.id || null }));
    };

    const save = async () => {
        if (!editing.origin?.trim() || !editing.destination?.trim()) {
            alert("Le départ et la destination sont requis.");
            return;
        }
        try {
            const payload = {
                ...editing,
                distance_km: mode === "direct" ? (parseFloat(editing.distance_km) || 0) : 0,
                odometer_start: mode === "odometer" ? (parseFloat(editing.odometer_start) || 0) : null,
                odometer_end: mode === "odometer" ? (parseFloat(editing.odometer_end) || 0) : null,
                rate: parseFloat(editing.rate) || DEFAULT_RATE,
            };
            ["client_id", "client_name", "vehicle", "job_number", "notes", "purpose"].forEach((k) => {
                if (payload[k] === "") payload[k] = null;
            });
            if (editing.id) await http.put(`/admin/mileage/${editing.id}`, payload);
            else await http.post("/admin/mileage", payload);
            closeEdit();
            flash("✅ Trajet enregistré.");
            await load();
        } catch (e) {
            const d = e?.response?.data?.detail;
            alert(Array.isArray(d) ? d.map((x) => x.msg).join(" · ") : (d || "Erreur"));
        }
    };

    const remove = async (t) => {
        if (!window.confirm(`Supprimer le trajet ${t.ref} ?`)) return;
        await http.delete(`/admin/mileage/${t.id}`);
        await load();
    };

    const openPdf = (path) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const sep = path.includes("?") ? "&" : "?";
        const url = `${base}/api/admin${path}${sep}token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };
    const openTripPdf = (t) => openPdf(`/mileage/${t.id}/report.pdf`);
    const openStatementPdf = () => {
        const q = new URLSearchParams({ month });
        if (filterClient) q.set("client_id", filterClient);
        openPdf(`/mileage/report.pdf?${q}`);
    };

    const billTrips = async () => {
        const clientName = customers.find((c) => c.id === filterClient)?.name || "ce client";
        if (!window.confirm(`Créer une facture brouillon (avec TPS/TVQ) pour ${clientName} avec les trajets non facturés de ${month} ?`)) return;
        setBilling(true);
        try {
            const { data } = await http.post(`/admin/mileage/invoice?month=${month}&client_id=${encodeURIComponent(filterClient)}`);
            flash(`✅ Facture brouillon FAC-${String(data.number).padStart(4, "0")} créée (${data.trips} trajet(s), total ${formatCurrency(data.total)}). Vois-la dans l'onglet Factures.`);
            await load();
        } catch (e) {
            const d = e?.response?.data?.detail;
            alert(Array.isArray(d) ? d.map((x) => x.msg).join(" · ") : (d || "Facturation impossible"));
        } finally { setBilling(false); }
    };

    const monthOptions = useMemo(() => {
        const out = [];
        const now = new Date();
        for (let i = 0; i < 12; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            out.push({ value: monthKey(d), label: d.toLocaleDateString("fr-CA", { month: "long", year: "numeric" }) });
        }
        if (month && !out.some((o) => o.value === month)) {
            const [y, m] = month.split("-").map(Number);
            out.push({ value: month, label: new Date(y, (m || 1) - 1, 1).toLocaleDateString("fr-CA", { month: "long", year: "numeric" }) });
            out.sort((a, b) => (a.value < b.value ? 1 : -1));
        }
        return out;
    }, [month]);

    return (
        <div data-testid="mileage-panel" className="space-y-6">
            <div className="hidden md:block">
                <div className="tech-stamp mb-1">Livraisons</div>
                <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Rapport kilométrique</h1>
            </div>

            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                    <SummaryTile icon={Route} label="Trajets du mois" value={summary.count} testid="km-stat-count" />
                    <SummaryTile icon={Gauge} label="Distance totale" value={fmtKm(summary.total_km)} testid="km-stat-km" />
                    <SummaryTile icon={DollarSign} label="Montant total" value={formatCurrency(summary.total_amount)} accent="text-[#0b6b2f]" testid="km-stat-amount" />
                </div>
            )}

            <div className="flex flex-wrap items-center gap-2">
                <select data-testid="km-month-filter" value={month} onChange={(e) => setMonth(e.target.value)} className={inputClass.replace("w-full", "w-auto")}>
                    {monthOptions.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
                <select data-testid="km-client-filter" value={filterClient} onChange={(e) => setFilterClient(e.target.value)} className={inputClass.replace("w-full", "w-auto")}>
                    <option value="">Tous les clients</option>
                    {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <button onClick={openStatementPdf} data-testid="km-statement-pdf" className="btn-secondary !py-2 !px-3 !text-xs" title="Relevé PDF du mois (regroupé)">
                    <FileText className="w-3.5 h-3.5" /> Relevé PDF
                </button>
                {filterClient && (
                    <button onClick={billTrips} data-testid="km-bill" disabled={billing} className="btn-secondary !py-2 !px-3 !text-xs !border-[#0b6b2f] !text-[#0b6b2f]" title="Créer une facture brouillon avec les trajets non facturés de ce client">
                        <DollarSign className="w-3.5 h-3.5" /> {billing ? "..." : "Facturer ce client"}
                    </button>
                )}
                <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                </button>
                <button onClick={openNew} data-testid="km-new" className="hidden md:inline-flex btn-primary !py-2 !px-4 !text-xs ml-auto">
                    <Plus className="w-3.5 h-3.5" /> Nouveau trajet
                </button>
            </div>

            {notice && (
                <div data-testid="km-notice" className="p-3 border border-[#8ec79d] bg-[#e6f4ea] text-[#0b6b2f] text-sm">{notice}</div>
            )}

            {/* MOBILE */}
            <div className="md:hidden space-y-3">
                {!loading && rows.length === 0 && (
                    <div className="p-8 text-center text-[#4b5d7a] text-sm border border-[#dde5f0] bg-white">Aucun trajet ce mois-ci. Appuyez sur + pour ajouter.</div>
                )}
                {rows.map((t) => (
                    <DataCard
                        key={t.id}
                        testid={`km-card-${t.id}`}
                        stamp={`${t.ref} · ${formatDate(t.date)}`}
                        title={`${t.origin || "—"} → ${t.destination || "—"}`}
                        subtitle={t.client_name || t.purpose || "—"}
                        primary={formatCurrency(t.amount)}
                        secondary={`${fmtKm(t.distance_km)} · ${(t.rate || DEFAULT_RATE).toFixed(2)} $/km`}
                        onTap={() => openEdit(t)}
                        actions={[
                            { icon: FileText, label: "PDF", testid: `km-pdf-${t.id}`, onClick: () => openTripPdf(t) },
                        ]}
                    />
                ))}
            </div>

            {/* DESKTOP */}
            <div className="hidden md:block border border-[#dde5f0] bg-white">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                    <div className="col-span-1">Réf</div>
                    <div className="col-span-1">Date</div>
                    <div className="col-span-3">Trajet</div>
                    <div className="col-span-2">Client</div>
                    <div className="col-span-1 text-right">Distance</div>
                    <div className="col-span-1 text-right">Taux</div>
                    <div className="col-span-1 text-right">Montant</div>
                    <div className="col-span-2 text-right">Actions</div>
                </div>
                {!loading && rows.length === 0 && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">Aucun trajet ce mois-ci.</div>
                )}
                <ul>
                    {rows.map((t) => (
                        <li key={t.id} className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb]">
                            <div className="grid grid-cols-12 gap-4 px-6 py-3 items-center text-sm">
                                <div className="col-span-1 font-mono text-xs text-[#2f4f7f]">
                                    {t.ref}
                                    {t.invoiced_number != null && <span className="block mt-0.5 text-[9px] text-[#0b6b2f] font-sans" data-testid={`km-billed-${t.id}`}>Facturé</span>}
                                </div>
                                <div className="col-span-1 text-xs text-[#4b5d7a]">{formatDate(t.date)}</div>
                                <div className="col-span-3">
                                    <button onClick={() => openEdit(t)} className="hover:underline text-left font-medium text-[#0c182b] flex items-center gap-1">
                                        <MapPin className="w-3 h-3 text-[#4b5d7a]" /> {t.origin || "—"} → {t.destination || "—"}
                                    </button>
                                    {t.purpose && <div className="text-xs text-[#4b5d7a] mt-0.5">{t.purpose}</div>}
                                </div>
                                <div className="col-span-2 truncate text-[#0c182b]">{t.client_name || "—"}</div>
                                <div className="col-span-1 text-right text-[#4b5d7a]">{fmtKm(t.distance_km)}</div>
                                <div className="col-span-1 text-right text-[#4b5d7a]">{(t.rate || DEFAULT_RATE).toFixed(2)} $</div>
                                <div className="col-span-1 text-right font-display font-bold">{formatCurrency(t.amount)}</div>
                                <div className="col-span-2 flex justify-end gap-1">
                                    <button onClick={() => openTripPdf(t)} data-testid={`km-pdf-${t.id}`} className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]" title="Rapport PDF">
                                        <FileText className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => openEdit(t)} className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]" aria-label="Modifier">
                                        <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => remove(t)} className="p-2 border border-[#dde5f0] hover:bg-red-50 text-red-600" aria-label="Supprimer">
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>

            {/* By-client breakdown */}
            {summary && summary.by_client.length > 0 && (
                <div className="border border-[#dde5f0] bg-white p-4 md:p-6">
                    <div className="tech-stamp text-[#4b5d7a] mb-3 flex items-center gap-2"><Route className="w-4 h-4" /> Répartition par client</div>
                    <div className="space-y-2">
                        {summary.by_client.map((c) => (
                            <div key={c.client} className="flex justify-between text-sm border-b border-[#f0f3f8] pb-1.5 last:border-0">
                                <span>{c.client}</span>
                                <span className="text-[#4b5d7a]">{fmtKm(c.km)} · <span className="font-display font-bold text-[#0c182b]">{formatCurrency(c.amount)}</span></span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <FAB onClick={openNew} label="Nouveau trajet" testid="km-fab-new" />

            {editing && (
                <Modal
                    open={editOpen}
                    onClose={closeEdit}
                    title={editing.id ? `Modifier ${editing.ref || "le trajet"}` : "Nouveau trajet"}
                    testId="km-modal"
                    footer={
                        <>
                            <button onClick={closeEdit} className="px-4 py-2 border border-[#dde5f0] tech-stamp">Annuler</button>
                            <button data-testid="km-save" onClick={save} className="px-4 py-2 bg-[#0c182b] text-white tech-stamp">Enregistrer</button>
                        </>
                    }
                >
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Date" required>
                            <input type="date" value={editing.date} onChange={(e) => setEditing({ ...editing, date: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Client (optionnel)">
                            <input list="km-clients" value={editing.client_name || ""} placeholder="Nom du client" onChange={(e) => onPickClient(e.target.value)} className={inputClass} />
                            <datalist id="km-clients">
                                {customers.map((c) => <option key={c.id} value={c.name} />)}
                            </datalist>
                        </Field>
                        <Field label="Départ" required>
                            <input value={editing.origin} placeholder="Ex : Atelier Portech, Laval" onChange={(e) => setEditing({ ...editing, origin: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Destination" required>
                            <input value={editing.destination} placeholder="Ex : Chantier, Montréal" onChange={(e) => setEditing({ ...editing, destination: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Motif du déplacement" className="col-span-2">
                            <input value={editing.purpose || ""} placeholder="Ex : Livraison de quincaillerie" onChange={(e) => setEditing({ ...editing, purpose: e.target.value })} className={inputClass} />
                        </Field>

                        {/* Distance mode */}
                        <div className="col-span-2">
                            <div className="tech-stamp text-[#4b5d7a] mb-2">Distance</div>
                            <div className="flex gap-2 mb-3">
                                <button type="button" data-testid="km-mode-direct" onClick={() => setMode("direct")} className={`px-3 py-1.5 border text-xs tech-stamp ${mode === "direct" ? "bg-[#0c182b] text-white border-[#0c182b]" : "border-[#dde5f0] text-[#4b5d7a]"}`}>Km direct</button>
                                <button type="button" data-testid="km-mode-odometer" onClick={() => setMode("odometer")} className={`px-3 py-1.5 border text-xs tech-stamp ${mode === "odometer" ? "bg-[#0c182b] text-white border-[#0c182b]" : "border-[#dde5f0] text-[#4b5d7a]"}`}>Odomètre (début/fin)</button>
                            </div>
                            {mode === "direct" ? (
                                <input type="number" step="0.1" data-testid="km-distance" value={editing.distance_km} onChange={(e) => setEditing({ ...editing, distance_km: e.target.value })} placeholder="Distance en km" className={inputClass} />
                            ) : (
                                <div className="grid grid-cols-2 gap-4">
                                    <input type="number" step="0.1" data-testid="km-odo-start" value={editing.odometer_start} onChange={(e) => setEditing({ ...editing, odometer_start: e.target.value })} placeholder="Odomètre début" className={inputClass} />
                                    <input type="number" step="0.1" data-testid="km-odo-end" value={editing.odometer_end} onChange={(e) => setEditing({ ...editing, odometer_end: e.target.value })} placeholder="Odomètre fin" className={inputClass} />
                                </div>
                            )}
                        </div>

                        <Field label="Taux ($/km)" required>
                            <input type="number" step="0.0001" data-testid="km-rate" value={editing.rate} onChange={(e) => setEditing({ ...editing, rate: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Véhicule (optionnel)">
                            <input value={editing.vehicle || ""} placeholder="Ex : Ford Transit" onChange={(e) => setEditing({ ...editing, vehicle: e.target.value })} className={inputClass} />
                        </Field>
                        <Field label="Nº de job (optionnel)" className="col-span-2">
                            <input value={editing.job_number || ""} placeholder="Ex : JOB-0123" onChange={(e) => setEditing({ ...editing, job_number: e.target.value })} className={inputClass} />
                        </Field>

                        <div className="col-span-2 grid grid-cols-2 gap-4 p-3 bg-[#f3f6fb] border border-[#dde5f0]">
                            <div>
                                <div className="tech-stamp text-[#4b5d7a]">Distance calculée</div>
                                <div className="font-display font-bold text-xl" data-testid="km-computed-distance">{fmtKm(computedKm)}</div>
                            </div>
                            <div className="text-right">
                                <div className="tech-stamp text-[#4b5d7a]">Montant</div>
                                <div className="font-display font-bold text-xl text-[#0b6b2f]" data-testid="km-computed-amount">{formatCurrency(computedAmount)}</div>
                            </div>
                        </div>

                        <Field label="Notes" className="col-span-2">
                            <textarea rows={2} value={editing.notes || ""} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} className={inputClass} />
                        </Field>
                        <div className="col-span-2 p-3 bg-[#fff7e0] border border-[#d4be7a] text-xs text-[#7a5a00]">
                            💡 Taux par défaut 0,73 $/km (allocation ARC / Revenu Québec 2026). Le montant est tout inclus, sans taxes. Vous pouvez ajuster le taux pour chaque trajet.
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
};

const SummaryTile = ({ icon: Icon, label, value, accent, testid }) => (
    <div data-testid={testid} className="bg-white p-4 md:p-6">
        <div className="flex items-center gap-2 mb-2 md:mb-3 tech-stamp">
            <Icon className={`w-4 h-4 ${accent || "text-[#2f4f7f]"}`} />
            <span className="truncate">{label}</span>
        </div>
        <div className={`font-display font-bold text-xl md:text-3xl tracking-tight ${accent || ""}`}>{value}</div>
    </div>
);
