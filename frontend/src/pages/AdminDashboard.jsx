import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { AdminHeader } from "./admin/AdminHeader";
import { AdminStats } from "./admin/AdminStats";
import { AdminControls } from "./admin/AdminControls";
import { AdminTable } from "./admin/AdminTable";
import { AdminDrawer } from "./admin/AdminDrawer";

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

    useEffect(() => { load(); }, [load]);

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
    const isInitialLoading = loading && submissions.length === 0;
    const isEmpty = !isInitialLoading && filtered.length === 0;

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
            <AdminHeader user={user} onLogout={logout} />

            <main className="container-portech py-10">
                <div className="mb-10">
                    <div className="tech-stamp mb-3">Soumissions entrantes</div>
                    <h1 className="font-display font-bold uppercase text-4xl md:text-5xl tracking-tight leading-[0.95]">
                        Vos leads — en un coup d'œil.
                    </h1>
                </div>

                <AdminStats stats={stats} submissions={submissions} />

                <AdminControls
                    query={query}
                    onQueryChange={setQuery}
                    loading={loading}
                    onRefresh={load}
                />

                {error && (
                    <div
                        data-testid="admin-error"
                        className="mb-6 p-4 border border-red-400 bg-red-50 text-red-800 text-sm"
                    >
                        {error}
                    </div>
                )}

                <AdminTable
                    rows={filtered}
                    isInitialLoading={isInitialLoading}
                    isEmpty={isEmpty}
                    onSelect={setSelectedId}
                />
            </main>

            <AdminDrawer
                submission={selected}
                onClose={() => setSelectedId(null)}
                onDelete={handleDelete}
            />
        </div>
    );
};

export default AdminDashboard;
