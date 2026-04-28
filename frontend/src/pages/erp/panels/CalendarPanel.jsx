/* eslint-disable react-hooks/exhaustive-deps */
import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2, RefreshCw, ChevronLeft, ChevronRight, MapPin, FileText } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Modal } from "../components/Modal";

const STATUS_BADGE = {
    "prévu": "bg-[#eaf1fb] text-[#1d3557] border-[#9bb6d8]",
    "fait": "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
    "annulé": "bg-[#fbe8e8] text-[#8a1f1f] border-[#e8a5a5]",
};

const STATUS_OPTS = ["prévu", "fait", "annulé"];

const pad2 = (n) => String(n).padStart(2, "0");

/** Returns YYYY-MM-DD for a Date object using local time. */
const toDateOnly = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;

/** Build the 6×7 grid of Date objects for a given month, starting Sunday. */
const buildMonthGrid = (year, month) => {
    const first = new Date(year, month, 1);
    const startOffset = first.getDay(); // 0 = Sunday
    const start = new Date(year, month, 1 - startOffset);
    return Array.from({ length: 42 }, (_, i) => {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        return d;
    });
};

const MONTHS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];
const DAYS_FR = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"];

const emptyForm = () => {
    const now = new Date();
    const start = `${toDateOnly(now)}T09:00`;
    return {
        title: "",
        start,
        end: "",
        party_id: null,
        party_name: "",
        location: "",
        notes: "",
        status: "prévu",
    };
};

export const CalendarPanel = () => {
    const { http } = useAuth();
    const today = new Date();
    const [cursor, setCursor] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
    const [appts, setAppts] = useState([]);
    const [parties, setParties] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(emptyForm());

    const monthDays = useMemo(
        () => buildMonthGrid(cursor.getFullYear(), cursor.getMonth()),
        [cursor],
    );

    const load = async () => {
        try {
            setLoading(true);
            // Load whole month's appointments (slight overlap to fill the grid)
            const start = monthDays[0];
            const end = monthDays[monthDays.length - 1];
            const startISO = `${toDateOnly(start)}T00:00`;
            const endISO = `${toDateOnly(end)}T23:59`;
            const [a, p] = await Promise.all([
                http.get(`/admin/appointments?start_from=${startISO}&start_to=${endISO}`),
                http.get("/admin/parties"),
            ]);
            setAppts(a.data || []);
            setParties(p.data || []);
            setError("");
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, [cursor]);

    // Group appointments by date string for fast cell lookup
    const byDay = useMemo(() => {
        const map = {};
        for (const a of appts) {
            const k = (a.start || "").slice(0, 10);
            (map[k] = map[k] || []).push(a);
        }
        // Sort each day by start time
        Object.values(map).forEach((arr) => arr.sort((x, y) => (x.start || "").localeCompare(y.start || "")));
        return map;
    }, [appts]);

    const openNew = (preselectDate) => {
        setEditing(null);
        const f = emptyForm();
        if (preselectDate) {
            f.start = `${toDateOnly(preselectDate)}T09:00`;
        }
        setForm(f);
        setModalOpen(true);
    };

    const openEdit = (a) => {
        setEditing(a);
        setForm({
            title: a.title || "",
            start: a.start || "",
            end: a.end || "",
            party_id: a.party_id || null,
            party_name: a.party_name || "",
            location: a.location || "",
            notes: a.notes || "",
            status: a.status || "prévu",
        });
        setModalOpen(true);
    };

    const save = async () => {
        try {
            if (!form.title.trim()) {
                setError("Le titre est requis");
                return;
            }
            if (!form.start) {
                setError("La date/heure de début est requise");
                return;
            }
            const payload = {
                ...form,
                end: form.end || null,
                party_id: form.party_id || null,
                party_name: form.party_name || null,
                location: form.location || null,
                notes: form.notes || null,
            };
            if (editing) {
                await http.put(`/admin/appointments/${editing.id}`, payload);
            } else {
                await http.post("/admin/appointments", payload);
            }
            setModalOpen(false);
            await load();
        } catch (e) {
            setError(e?.response?.data?.detail || "Échec de l'enregistrement");
        }
    };

    const remove = async (a) => {
        if (!window.confirm(`Supprimer le rendez-vous « ${a.title} » ?`)) return;
        try {
            await http.delete(`/admin/appointments/${a.id}`);
            await load();
        } catch (e) {
            setError(e?.response?.data?.detail || "Échec");
        }
    };

    const goPrev = () => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1));
    const goNext = () => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1));
    const goToday = () => {
        const t = new Date();
        setCursor(new Date(t.getFullYear(), t.getMonth(), 1));
    };

    const todayKey = toDateOnly(today);
    const inMonth = (d) => d.getMonth() === cursor.getMonth();

    // Upcoming appointments list (next 5 starting today)
    const upcoming = useMemo(() => {
        const now = new Date().toISOString().slice(0, 16);
        return [...appts]
            .filter((a) => a.status !== "annulé" && (a.start || "") >= now.slice(0, 10))
            .sort((x, y) => (x.start || "").localeCompare(y.start || ""))
            .slice(0, 5);
    }, [appts]);

    return (
        <div data-testid="erp-panel-calendar" className="space-y-6">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <div className="tech-stamp text-[#4b5d7a] mb-2">Gestion · Calendrier</div>
                    <h1 className="font-display text-3xl md:text-4xl font-black tracking-tight">
                        {MONTHS_FR[cursor.getMonth()]} {cursor.getFullYear()}
                    </h1>
                </div>
                <div className="flex gap-2">
                    <button onClick={goPrev} data-testid="cal-prev" className="btn-secondary !py-2 !px-3 !text-xs">
                        <ChevronLeft className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={goToday} data-testid="cal-today" className="btn-secondary !py-2 !px-3 !text-xs">
                        Aujourd'hui
                    </button>
                    <button onClick={goNext} data-testid="cal-next" className="btn-secondary !py-2 !px-3 !text-xs">
                        <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={() => openNew()} data-testid="erp-new-appointment" className="btn-primary !py-2 !px-4 !text-xs">
                        <Plus className="w-3.5 h-3.5" />
                        Nouveau rendez-vous
                    </button>
                </div>
            </div>

            {error && <div className="p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>}

            {/* Calendar grid */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <div className="lg:col-span-3 border border-[#dde5f0] bg-white">
                    {/* Day headers */}
                    <div className="grid grid-cols-7 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp text-center">
                        {DAYS_FR.map((d) => (
                            <div key={d} className="py-2 border-r border-[#dde5f0] last:border-r-0">{d}</div>
                        ))}
                    </div>
                    {/* Days */}
                    <div className="grid grid-cols-7">
                        {monthDays.map((d) => {
                            const key = toDateOnly(d);
                            const events = byDay[key] || [];
                            const isToday = key === todayKey;
                            const dim = !inMonth(d);
                            return (
                                <div
                                    key={key}
                                    onClick={() => openNew(d)}
                                    data-testid={`cal-cell-${key}`}
                                    className={`min-h-[110px] border-r border-b border-[#dde5f0] last:border-r-0 p-2 cursor-pointer transition-colors hover:bg-[#f7faff] ${
                                        dim ? "bg-[#fafbfd] text-[#9eaec5]" : ""
                                    }`}
                                >
                                    <div className={`flex items-center justify-between mb-1 ${isToday ? "font-bold" : ""}`}>
                                        <span className={`text-xs ${isToday ? "bg-[#0c182b] text-white px-1.5 py-0.5" : ""}`}>
                                            {d.getDate()}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        {events.slice(0, 3).map((a) => (
                                            <div
                                                key={a.id}
                                                onClick={(e) => { e.stopPropagation(); openEdit(a); }}
                                                className={`tech-stamp px-1.5 py-1 border truncate text-[10px] ${STATUS_BADGE[a.status] || "border-[#dde5f0]"}`}
                                                title={`${a.start.slice(11, 16)} · ${a.title}${a.party_name ? " · " + a.party_name : ""}`}
                                            >
                                                {a.start.slice(11, 16)} {a.title}
                                            </div>
                                        ))}
                                        {events.length > 3 && (
                                            <div className="text-[10px] text-[#4b5d7a] tech-stamp">+{events.length - 3} autre(s)</div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Upcoming sidebar */}
                <div className="border border-[#dde5f0] bg-white p-4">
                    <div className="tech-stamp text-[#4b5d7a] mb-3">Rendez-vous à venir</div>
                    {upcoming.length === 0 && (
                        <div className="text-sm text-[#4b5d7a] py-6 text-center">Aucun RDV à venir.</div>
                    )}
                    <ul className="space-y-3">
                        {upcoming.map((a) => (
                            <li key={a.id} className="border border-[#dde5f0] p-3 hover:bg-[#f7faff] cursor-pointer" onClick={() => openEdit(a)}>
                                <div className="flex items-center justify-between mb-1">
                                    <div className="font-display font-bold text-sm">{a.title}</div>
                                    <span className={`tech-stamp px-2 py-0.5 border text-[10px] ${STATUS_BADGE[a.status] || "border-[#dde5f0]"}`}>
                                        {a.status}
                                    </span>
                                </div>
                                <div className="text-xs text-[#4b5d7a]">
                                    {new Date(a.start).toLocaleDateString("fr-CA", { day: "numeric", month: "long", year: "numeric" })}
                                    {" · "}
                                    {a.start.slice(11, 16)}
                                </div>
                                {a.party_name && <div className="text-xs text-[#4b5d7a] mt-1">👤 {a.party_name}</div>}
                                {a.location && <div className="text-xs text-[#4b5d7a]">📍 {a.location}</div>}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Edit/Create modal */}
            <Modal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                title={editing ? `Modifier — ${editing.title}` : "Nouveau rendez-vous"}
                footer={(
                    <>
                        <button onClick={() => setModalOpen(false)} className="btn-secondary">Annuler</button>
                        <button onClick={save} data-testid="appointment-save" className="btn-primary">
                            {editing ? "Enregistrer" : "Créer"}
                        </button>
                        {editing && (
                            <button onClick={() => { remove(editing); setModalOpen(false); }} className="btn-secondary !text-red-600 !border-red-300">
                                <Trash2 className="w-4 h-4" /> Supprimer
                            </button>
                        )}
                    </>
                )}
            >
                <div className="space-y-4">
                    <div>
                        <label className="tech-stamp block mb-1">Titre *</label>
                        <input
                            type="text"
                            value={form.title}
                            onChange={(e) => setForm({ ...form, title: e.target.value })}
                            data-testid="appointment-title"
                            className="w-full px-3 py-2 bg-white border border-[#dde5f0] focus:border-[#0c182b] focus:outline-none"
                            placeholder="Visite chantier École Mont-Royal"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="tech-stamp block mb-1">Début *</label>
                            <input
                                type="datetime-local"
                                value={form.start.slice(0, 16)}
                                onChange={(e) => setForm({ ...form, start: e.target.value })}
                                data-testid="appointment-start"
                                className="w-full px-3 py-2 bg-white border border-[#dde5f0] focus:border-[#0c182b] focus:outline-none"
                            />
                        </div>
                        <div>
                            <label className="tech-stamp block mb-1">Fin (optionnel)</label>
                            <input
                                type="datetime-local"
                                value={(form.end || "").slice(0, 16)}
                                onChange={(e) => setForm({ ...form, end: e.target.value })}
                                className="w-full px-3 py-2 bg-white border border-[#dde5f0] focus:border-[#0c182b] focus:outline-none"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="tech-stamp block mb-1">Client / contact (optionnel)</label>
                        <select
                            value={form.party_id || ""}
                            onChange={(e) => {
                                const id = e.target.value || null;
                                const party = parties.find((p) => p.id === id);
                                setForm({ ...form, party_id: id, party_name: party?.name || "" });
                            }}
                            className="w-full px-3 py-2 bg-white border border-[#dde5f0] focus:border-[#0c182b] focus:outline-none"
                        >
                            <option value="">— Aucun —</option>
                            {parties.map((p) => (
                                <option key={p.id} value={p.id}>{p.name} ({p.kind === "customer" ? "client" : "fournisseur"})</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="tech-stamp block mb-1"><MapPin className="inline w-3 h-3" /> Lieu / adresse</label>
                        <input
                            type="text"
                            value={form.location}
                            onChange={(e) => setForm({ ...form, location: e.target.value })}
                            className="w-full px-3 py-2 bg-white border border-[#dde5f0] focus:border-[#0c182b] focus:outline-none"
                            placeholder="123 rue Sainte-Catherine, Montréal"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="tech-stamp block mb-1">Statut</label>
                            <select
                                value={form.status}
                                onChange={(e) => setForm({ ...form, status: e.target.value })}
                                className="w-full px-3 py-2 bg-white border border-[#dde5f0] focus:border-[#0c182b] focus:outline-none"
                            >
                                {STATUS_OPTS.map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="tech-stamp block mb-1"><FileText className="inline w-3 h-3" /> Notes</label>
                        <textarea
                            value={form.notes}
                            onChange={(e) => setForm({ ...form, notes: e.target.value })}
                            rows={3}
                            className="w-full px-3 py-2 bg-white border border-[#dde5f0] focus:border-[#0c182b] focus:outline-none"
                            placeholder="Mesures portes 7'x3', barre antipanique à valider…"
                        />
                    </div>
                </div>
            </Modal>
        </div>
    );
};
