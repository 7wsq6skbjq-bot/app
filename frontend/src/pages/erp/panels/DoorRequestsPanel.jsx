import { useCallback, useEffect, useState } from "react";
import { RefreshCw, DoorOpen, Phone, Mail, MapPin } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const fmtDate = (iso) => {
    try {
        return new Date(iso).toLocaleDateString("fr-CA", {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    } catch {
        return iso || "—";
    }
};

const dims = (r) => {
    if (!r.door_width && !r.door_height) return "—";
    return `${r.door_width || "?"} × ${r.door_height || "?"}`;
};

export const DoorRequestsPanel = () => {
    const { http } = useAuth();
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const load = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const { data } = await http.get("/admin/door-requests");
            setRows(Array.isArray(data) ? data : []);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally {
            setLoading(false);
        }
    }, [http]);
    useEffect(() => {
        load();
    }, [load]);

    return (
        <div data-testid="door-requests-panel">
            <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
                <div>
                    <div className="tech-stamp mb-1">Portes en aluminium</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight flex items-center gap-2">
                        <DoorOpen className="w-6 h-6 text-[#2f4f7f]" />
                        Demandes de porte
                    </h1>
                    <p className="text-sm text-[#4b5d7a] mt-1">
                        Demandes reçues du site avec gamme, dimensions et quantité.
                    </p>
                </div>
                <button
                    onClick={load}
                    className="btn-secondary !py-2 !px-3 !text-xs"
                    data-testid="door-requests-refresh"
                >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                </button>
            </div>

            {error && (
                <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">
                    {error}
                </div>
            )}

            <div className="mb-4 inline-block border border-[#0c182b] bg-[#0c182b] text-white px-5 py-3">
                <span className="text-[10px] uppercase tracking-wider text-[#9fb3d1]">
                    Demandes de porte reçues
                </span>
                <div className="font-display font-bold text-2xl" data-testid="door-requests-count">
                    {rows.length}
                </div>
            </div>

            <div className="border border-[#dde5f0] bg-white overflow-x-auto">
                <div className="hidden lg:grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp min-w-[900px]">
                    <div className="col-span-2">Date</div>
                    <div className="col-span-3">Client</div>
                    <div className="col-span-2">Gamme</div>
                    <div className="col-span-1">Config.</div>
                    <div className="col-span-1 text-right pr-4">Qté</div>
                    <div className="col-span-2">Dimensions (L × H)</div>
                    <div className="col-span-1">Fini</div>
                </div>

                {rows.length === 0 && !loading && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">
                        Aucune demande de porte pour le moment.
                    </div>
                )}

                <ul className="min-w-[900px] lg:min-w-0">
                    {rows.map((r) => (
                        <li
                            key={r.id}
                            data-testid={`door-request-row-${r.id}`}
                            className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors"
                        >
                            <div className="grid grid-cols-1 lg:grid-cols-12 gap-2 lg:gap-4 px-6 py-4 lg:items-center">
                                <div className="lg:col-span-2 text-sm text-[#4b5d7a]">
                                    {fmtDate(r.created_at)}
                                </div>
                                <div className="lg:col-span-3">
                                    <div className="font-display font-semibold uppercase text-sm tracking-tight">
                                        {r.name}
                                    </div>
                                    <div className="text-xs text-[#4b5d7a] mt-1 space-y-0.5">
                                        <a
                                            href={`tel:${r.phone}`}
                                            className="flex items-center gap-1 hover:text-[#2f4f7f]"
                                        >
                                            <Phone className="w-3 h-3" /> {r.phone}
                                        </a>
                                        <a
                                            href={`mailto:${r.email}`}
                                            className="flex items-center gap-1 hover:text-[#2f4f7f] truncate"
                                        >
                                            <Mail className="w-3 h-3 flex-shrink-0" /> {r.email}
                                        </a>
                                        {r.work_location && (
                                            <span className="flex items-center gap-1 text-[#6485b4]">
                                                <MapPin className="w-3 h-3 flex-shrink-0" />
                                                {r.work_location}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="lg:col-span-2 text-sm">
                                    <span className="lg:hidden tech-stamp text-[#6485b4] mr-2">Gamme :</span>
                                    {r.door_gamme || "—"}
                                </div>
                                <div className="lg:col-span-1 text-sm">
                                    <span className="lg:hidden tech-stamp text-[#6485b4] mr-2">Config. :</span>
                                    {r.door_config || "—"}
                                </div>
                                <div className="lg:col-span-1 text-sm lg:text-right lg:pr-4 font-display font-bold">
                                    <span className="lg:hidden tech-stamp text-[#6485b4] mr-2">Qté :</span>
                                    {r.door_qty || "—"}
                                </div>
                                <div className="lg:col-span-2 text-sm">
                                    <span className="lg:hidden tech-stamp text-[#6485b4] mr-2">Dimensions :</span>
                                    {dims(r)}
                                </div>
                                <div className="lg:col-span-1 text-sm">
                                    <span className="lg:hidden tech-stamp text-[#6485b4] mr-2">Fini :</span>
                                    {r.door_finish || "—"}
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default DoorRequestsPanel;
