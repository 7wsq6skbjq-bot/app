import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
    LogOut,
    Mail,
    Phone,
    Tag,
    Trash2,
    RefreshCw,
    Inbox,
    Calendar,
    Search,
    ArrowLeft,
    ExternalLink,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const formatDate = (iso) => {
    try {
        const d = new Date(iso);
        return d.toLocaleString("fr-CA", {
            dateStyle: "medium",
            timeStyle: "short",
        });
    } catch {
        return iso;
    }
};

const AdminDashboard = () => {
    const { logout, http, user } = useAuth();
    const [submissions, setSubmissions] = useState([]);
    const [stats, setStats] = useState({ total: 0, last_30_days: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [query, setQuery] = useState("");
    const [selectedId, setSelectedId] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const [subRes, statsRes] = await Promise.all([
                http.get("/admin/submissions"),
                http.get("/admin/stats"),
            ]);
            setSubmissions(subRes.data || []);
            setStats(statsRes.data || { total: 0, last_30_days: 0 });
        } catch (e) {
            setError(
                e?.response?.data?.detail ||
                    "Impossible de charger les soumissions.",
            );
        } finally {
            setLoading(false);
        }
    }, [http]);

    useEffect(() => {
        load();
    }, [load]);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return submissions;
        return submissions.filter((s) =>
            [s.name, s.email, s.phone, s.message, s.project_type, s.company, s.work_location]
                .filter(Boolean)
                .some((v) => String(v).toLowerCase().includes(q)),
        );
    }, [submissions, query]);

    const selected = submissions.find((s) => s.id === selectedId) || null;

    const handleDelete = async (id) => {
        if (!window.confirm("Supprimer définitivement cette soumission ?")) return;
        try {
            await http.delete(`/admin/submissions/${id}`);
            setSubmissions((prev) => prev.filter((s) => s.id !== id));
            if (selectedId === id) setSelectedId(null);
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec de la suppression");
        }
    };

    return (
        <div
            data-testid="page-admin-dashboard"
            className="min-h-screen bg-[#f3f6fb] text-[#0c182b]"
        >
            {/* HEADER */}
            <header className="bg-[#0c182b] text-white border-b border-[#1e3457]">
                <div className="container-portech flex items-center justify-between h-20">
                    <div className="flex items-center gap-6">
                        <img
                            src="/brand/logo-portech-white.png"
                            alt="Portech"
                            className="h-10 w-auto"
                        />
                        <span className="tech-stamp text-[#97b0d0] hidden md:inline">
                            · Tableau de bord
                        </span>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link
                            to="/"
                            className="tech-stamp text-[#97b0d0] hover:text-white transition-colors inline-flex items-center gap-2"
                            data-testid="admin-link-site"
                        >
                            <ExternalLink className="w-3.5 h-3.5" />
                            Voir le site
                        </Link>
                        <span className="tech-stamp text-[#97b0d0] hidden md:inline">
                            {user?.username}
                        </span>
                        <button
                            onClick={logout}
                            data-testid="admin-logout"
                            className="inline-flex items-center gap-2 border border-[#1e3457] text-[#b2c3dd] hover:bg-white hover:text-[#0c182b] hover:border-white transition-colors px-4 py-2 font-display uppercase text-xs tracking-wider"
                        >
                            <LogOut className="w-3.5 h-3.5" />
                            Déconnexion
                        </button>
                    </div>
                </div>
            </header>

            <main className="container-portech py-10">
                <div className="mb-10">
                    <div className="tech-stamp mb-3">Soumissions entrantes</div>
                    <h1 className="font-display font-bold uppercase text-4xl md:text-5xl tracking-tight leading-[0.95]">
                        Vos leads — en un coup d'œil.
                    </h1>
                </div>

                {/* STATS */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-[#dde5f0] bg-[#dde5f0] mb-10">
                    <div className="bg-white p-6" data-testid="stat-total">
                        <div className="flex items-center gap-3 mb-4">
                            <Inbox className="w-5 h-5 text-[#2f4f7f]" />
                            <span className="tech-stamp">Total</span>
                        </div>
                        <div className="font-display font-bold text-5xl tracking-tight">
                            {stats.total}
                        </div>
                    </div>
                    <div className="bg-white p-6" data-testid="stat-30d">
                        <div className="flex items-center gap-3 mb-4">
                            <Calendar className="w-5 h-5 text-[#2f4f7f]" />
                            <span className="tech-stamp">30 derniers jours</span>
                        </div>
                        <div className="font-display font-bold text-5xl tracking-tight">
                            {stats.last_30_days}
                        </div>
                    </div>
                    <div className="bg-white p-6" data-testid="stat-reachable">
                        <div className="flex items-center gap-3 mb-4">
                            <Mail className="w-5 h-5 text-[#2f4f7f]" />
                            <span className="tech-stamp">Courriel envoyé</span>
                        </div>
                        <div className="font-display font-bold text-5xl tracking-tight">
                            {submissions.filter((s) => s.email_sent).length}
                            <span className="text-[#97b0d0] text-lg ml-2">
                                / {submissions.length}
                            </span>
                        </div>
                    </div>
                </div>

                {/* CONTROLS */}
                <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between mb-6">
                    <div className="relative flex-1 max-w-md">
                        <Search className="w-4 h-4 text-[#97b0d0] absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Rechercher par nom, courriel, message…"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            data-testid="admin-search"
                            className="w-full pl-9 pr-4 py-2.5 border border-[#c5d4e7] bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] text-sm"
                        />
                    </div>
                    <button
                        onClick={load}
                        data-testid="admin-refresh"
                        className="btn-secondary !py-2.5 !px-4 !text-xs self-start"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                        Rafraîchir
                    </button>
                </div>

                {error && (
                    <div
                        data-testid="admin-error"
                        className="mb-6 p-4 border border-red-400 bg-red-50 text-red-800 text-sm"
                    >
                        {error}
                    </div>
                )}

                {/* TABLE */}
                <div className="border border-[#dde5f0] bg-white">
                    <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                        <div className="col-span-3">Nom</div>
                        <div className="col-span-3">Courriel</div>
                        <div className="col-span-2">Téléphone</div>
                        <div className="col-span-2">Type</div>
                        <div className="col-span-2 text-right">Reçu</div>
                    </div>

                    {loading && submissions.length === 0 ? (
                        <div className="p-12 text-center tech-stamp">
                            Chargement…
                        </div>
                    ) : filtered.length === 0 ? (
                        <div
                            data-testid="admin-empty"
                            className="p-12 text-center"
                        >
                            <Inbox className="w-10 h-10 text-[#97b0d0] mx-auto mb-4" />
                            <div className="font-display font-bold uppercase text-xl mb-2">
                                Aucune soumission
                            </div>
                            <p className="text-[#4b5d7a] text-sm">
                                Les nouvelles demandes apparaîtront ici
                                automatiquement.
                            </p>
                        </div>
                    ) : (
                        <ul>
                            {filtered.map((s) => (
                                <li
                                    key={s.id}
                                    data-testid={`admin-submission-${s.id}`}
                                    className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors cursor-pointer"
                                    onClick={() => setSelectedId(s.id)}
                                >
                                    <div className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-4 items-center">
                                        <div className="md:col-span-3">
                                            <div className="font-display font-semibold text-[#0c182b] uppercase text-sm tracking-tight">
                                                {s.name}
                                            </div>
                                        </div>
                                        <div className="md:col-span-3 text-sm text-[#2f4f7f] truncate">
                                            {s.email}
                                        </div>
                                        <div className="md:col-span-2 text-sm text-[#4b5d7a]">
                                            {s.phone}
                                        </div>
                                        <div className="md:col-span-2 text-sm">
                                            {s.project_type ? (
                                                <span className="inline-flex items-center gap-1 tech-stamp px-2 py-1 border border-[#dde5f0] bg-[#f3f6fb]">
                                                    <Tag className="w-3 h-3" />
                                                    {s.project_type}
                                                </span>
                                            ) : (
                                                <span className="text-[#97b0d0]">
                                                    —
                                                </span>
                                            )}
                                        </div>
                                        <div className="md:col-span-2 md:text-right tech-stamp text-[#4b5d7a]">
                                            {formatDate(s.created_at)}
                                        </div>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </main>

            {/* DETAIL DRAWER */}
            {selected && (
                <div
                    data-testid="admin-drawer"
                    className="fixed inset-0 z-50 flex"
                    onClick={() => setSelectedId(null)}
                >
                    <div className="flex-1 bg-black/50" />
                    <aside
                        className="w-full max-w-xl bg-white border-l border-[#dde5f0] overflow-y-auto"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="p-6 border-b border-[#dde5f0] flex items-center justify-between bg-[#0c182b] text-white">
                            <div>
                                <div className="tech-stamp text-[#97b0d0]">
                                    Soumission
                                </div>
                                <div className="font-display font-bold uppercase text-xl tracking-tight mt-1">
                                    {selected.name}
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedId(null)}
                                className="tech-stamp text-[#97b0d0] hover:text-white transition-colors inline-flex items-center gap-2"
                                data-testid="admin-drawer-close"
                            >
                                <ArrowLeft className="w-3.5 h-3.5" />
                                Fermer
                            </button>
                        </div>

                        <div className="p-6 space-y-6">
                            <div>
                                <div className="tech-stamp mb-2">Courriel</div>
                                <a
                                    href={`mailto:${selected.email}`}
                                    className="text-[#2f4f7f] hover:text-[#0c182b] transition-colors inline-flex items-center gap-2"
                                >
                                    <Mail className="w-4 h-4" />
                                    {selected.email}
                                </a>
                            </div>
                            <div>
                                <div className="tech-stamp mb-2">Téléphone</div>
                                <a
                                    href={`tel:${selected.phone}`}
                                    className="text-[#2f4f7f] hover:text-[#0c182b] transition-colors inline-flex items-center gap-2"
                                >
                                    <Phone className="w-4 h-4" />
                                    {selected.phone}
                                </a>
                            </div>
                            {selected.project_type && (
                                <div>
                                    <div className="tech-stamp mb-2">Type</div>
                                    <div className="font-display font-semibold uppercase text-sm tracking-tight">
                                        {selected.project_type}
                                    </div>
                                </div>
                            )}
                            {selected.company && (
                                <div>
                                    <div className="tech-stamp mb-2">Entreprise</div>
                                    <div className="font-display font-semibold uppercase text-sm tracking-tight">
                                        {selected.company}
                                    </div>
                                </div>
                            )}
                            {selected.work_location && (
                                <div>
                                    <div className="tech-stamp mb-2">Lieu des travaux</div>
                                    <div className="text-[#0c182b]">
                                        {selected.work_location}
                                    </div>
                                </div>
                            )}
                            <div>
                                <div className="tech-stamp mb-2">Reçu le</div>
                                <div className="text-[#0c182b]">
                                    {formatDate(selected.created_at)}
                                </div>
                            </div>
                            <div>
                                <div className="tech-stamp mb-2">Message</div>
                                <div className="border border-[#dde5f0] bg-[#f3f6fb] p-4 whitespace-pre-wrap text-[#1e3457] leading-relaxed">
                                    {selected.message}
                                </div>
                            </div>
                            <div>
                                <div className="tech-stamp mb-2">
                                    Notification email
                                </div>
                                <div
                                    className={`font-display font-semibold uppercase text-sm ${
                                        selected.email_sent
                                            ? "text-[#2f4f7f]"
                                            : "text-[#97b0d0]"
                                    }`}
                                >
                                    {selected.email_sent
                                        ? "✓ Envoyée avec succès"
                                        : "— Non envoyée"}
                                </div>
                            </div>

                            <div className="pt-6 border-t border-[#dde5f0] flex flex-col sm:flex-row gap-3">
                                <a
                                    href={`mailto:${selected.email}?subject=Re: Votre demande Portech&body=Bonjour ${encodeURIComponent(
                                        selected.name,
                                    )},%0D%0A%0D%0AMerci pour votre demande.%0D%0A%0D%0A`}
                                    className="btn-primary !py-2.5 !px-4 !text-xs flex-1 justify-center"
                                >
                                    <Mail className="w-3.5 h-3.5" />
                                    Répondre
                                </a>
                                <button
                                    onClick={() => handleDelete(selected.id)}
                                    className="btn-secondary !py-2.5 !px-4 !text-xs !border-red-400 !text-red-600 hover:!bg-red-50 hover:!text-red-700"
                                    data-testid="admin-drawer-delete"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                    Supprimer
                                </button>
                            </div>
                        </div>
                    </aside>
                </div>
            )}
        </div>
    );
};

export default AdminDashboard;
