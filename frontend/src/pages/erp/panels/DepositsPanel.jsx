import { useCallback, useEffect, useState } from "react";
import { RefreshCw, FileDown, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { formatCurrency } from "../utils";

export const DepositsPanel = () => {
    const { http, getToken } = useAuth();
    const [rows, setRows] = useState([]);
    const [totalDep, setTotalDep] = useState(0);
    const [totalRemaining, setTotalRemaining] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const { data } = await http.get("/admin/invoices/deposits");
            setRows(data.invoices || []);
            setTotalDep(data.total_deposit || 0);
            setTotalRemaining(data.total_remaining || 0);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally { setLoading(false); }
    }, [http]);
    useEffect(() => { load(); }, [load]);

    const receiptPdf = (id) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/invoices/${id}/deposit-receipt.pdf?token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const num = (n) => `FAC-${String(n).padStart(4, "0")}`;

    return (
        <div data-testid="deposits-panel">
            <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
                <div>
                    <div className="tech-stamp mb-1">Comptes clients</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Suivi des dépôts</h1>
                    <p className="text-sm text-[#4b5d7a] mt-1">Factures avec dépôt reçu et solde restant à encaisser.</p>
                </div>
                <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs" data-testid="deposits-refresh">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                </button>
            </div>

            {error && <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>}

            <div className="grid grid-cols-2 gap-3 mb-6 max-w-lg">
                <div className="border border-[#0c182b] bg-[#0c182b] text-white px-5 py-3">
                    <span className="text-[10px] uppercase tracking-wider text-[#9fb3d1]">Total des dépôts reçus</span>
                    <div className="font-display font-bold text-2xl" data-testid="deposits-total">{formatCurrency(totalDep)}</div>
                </div>
                <div className="border border-[#a31a1a] bg-white px-5 py-3">
                    <span className="text-[10px] uppercase tracking-wider text-[#a31a1a]">Solde restant à encaisser</span>
                    <div className="font-display font-bold text-2xl text-[#a31a1a]" data-testid="deposits-remaining">{formatCurrency(totalRemaining)}</div>
                </div>
            </div>

            <div className="border border-[#dde5f0] bg-white overflow-x-auto">
                <table className="w-full text-sm min-w-[800px]">
                    <thead><tr className="bg-[#f3f6fb] tech-stamp text-left">
                        <th className="px-3 py-2">Facture</th>
                        <th className="px-3 py-2">Client</th>
                        <th className="px-3 py-2">Date</th>
                        <th className="px-3 py-2 text-right">Total</th>
                        <th className="px-3 py-2 text-right">Dépôt reçu</th>
                        <th className="px-3 py-2 text-right">Solde restant</th>
                        <th className="px-3 py-2">Statut</th>
                        <th className="px-3 py-2 text-right">Reçu</th>
                    </tr></thead>
                    <tbody>
                        {!loading && rows.length === 0 && (
                            <tr><td colSpan={8} className="p-10 text-center text-[#4b5d7a]">Aucune facture avec dépôt reçu.</td></tr>
                        )}
                        {rows.map((r) => (
                            <tr key={r.id} data-testid={`deposit-row-${r.id}`} className="border-t border-[#eef2f8] hover:bg-[#f8fafd]">
                                <td className="px-3 py-2 font-mono text-xs text-[#2f4f7f]">{num(r.number)}</td>
                                <td className="px-3 py-2">{r.customer_name}</td>
                                <td className="px-3 py-2 text-xs text-[#4b5d7a]">{r.date}</td>
                                <td className="px-3 py-2 text-right">{formatCurrency(r.total)}</td>
                                <td className="px-3 py-2 text-right text-[#0f6b3a] font-display font-bold">{formatCurrency(r.deposit_amount)} <span className="text-[#93a3bd] text-xs">({r.deposit_pct}%)</span></td>
                                <td className={`px-3 py-2 text-right font-display font-bold ${r.remaining > 0 ? "text-[#a31a1a]" : "text-[#0f6b3a]"}`}>{formatCurrency(r.remaining)}</td>
                                <td className="px-3 py-2"><span className="text-xs uppercase tech-stamp">{r.status}</span></td>
                                <td className="px-3 py-2 text-right">
                                    <button onClick={() => receiptPdf(r.id)} title="Reçu de dépôt PDF"
                                        data-testid={`deposit-receipt-${r.id}`}
                                        className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]">
                                        <FileDown className="w-3.5 h-3.5" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {loading && <div className="p-8 text-center text-[#4b5d7a]"><Loader2 className="w-5 h-5 animate-spin inline" /></div>}
            </div>
        </div>
    );
};

export default DepositsPanel;
