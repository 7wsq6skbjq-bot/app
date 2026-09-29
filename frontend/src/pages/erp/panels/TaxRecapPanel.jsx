import { useCallback, useEffect, useState } from "react";
import { RefreshCw, FileDown, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { formatCurrency } from "../utils";

const QUARTERS = [
    { q: 1, label: "T1 · jan-mar" },
    { q: 2, label: "T2 · avr-juin" },
    { q: 3, label: "T3 · juil-sep" },
    { q: 4, label: "T4 · oct-déc" },
];

const Block = ({ title, subtitle, blk, testId }) => (
    <div className="border border-[#dde5f0] bg-white p-4" data-testid={testId}>
        <div className="text-[11px] uppercase tracking-wider font-bold text-[#0c182b]">{title}</div>
        <div className="text-xs text-[#4b5d7a] mb-3">{subtitle}</div>
        <div className="grid grid-cols-2 gap-y-1.5 text-sm">
            <span className="text-[#4b5d7a]">Sous-total</span><span className="text-right font-mono">{formatCurrency(blk.subtotal)}</span>
            <span className="text-[#4b5d7a]">TPS (5 %)</span><span className="text-right font-mono">{formatCurrency(blk.tps)}</span>
            <span className="text-[#4b5d7a]">TVQ (9,975 %)</span><span className="text-right font-mono">{formatCurrency(blk.tvq)}</span>
            <span className="font-bold text-[#0c182b] border-t border-[#dde5f0] pt-1">Total</span>
            <span className="text-right font-mono font-bold border-t border-[#dde5f0] pt-1">{formatCurrency(blk.total)}</span>
        </div>
    </div>
);

export const TaxRecapPanel = () => {
    const { http, getToken } = useAuth();
    const now = new Date();
    const [year, setYear] = useState(now.getFullYear());
    const [quarter, setQuarter] = useState(Math.floor(now.getMonth() / 3) + 1);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const { data } = await http.get(`/admin/tax-recap?year=${year}&quarter=${quarter}`);
            setData(data);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally { setLoading(false); }
    }, [http, year, quarter]);
    useEffect(() => { load(); }, [load]);

    const years = data?.available_years?.length ? data.available_years : [now.getFullYear()];

    const previewPdf = () => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/tax-recap/pdf?year=${year}&quarter=${quarter}&token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const net = data?.net || { tps: 0, tvq: 0, total: 0 };
    const netTotal = net.total || 0;
    const netPositive = netTotal >= 0;

    return (
        <div data-testid="tax-recap-panel">
            <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
                <div>
                    <div className="tech-stamp mb-1">Comptabilité · Taxes</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Récap TPS / TVQ</h1>
                    <p className="text-sm text-[#4b5d7a] mt-1">Rapport trimestriel à remettre au comptable.</p>
                </div>
                <div className="flex gap-2 items-center">
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs" data-testid="tax-recap-refresh">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={previewPdf} disabled={!data} data-testid="tax-recap-pdf"
                        className="btn-primary !py-2 !px-4 !text-xs disabled:opacity-40">
                        <FileDown className="w-3.5 h-3.5" /> Aperçu PDF
                    </button>
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 mb-6">
                <select data-testid="tax-recap-year" value={year} onChange={(e) => setYear(Number(e.target.value))}
                    className="px-3 py-2 border border-[#c5d4e7] bg-white text-sm">
                    {years.map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
                <div className="flex gap-1">
                    {QUARTERS.map((qq) => (
                        <button key={qq.q} data-testid={`tax-recap-q${qq.q}`} onClick={() => setQuarter(qq.q)}
                            className={`tech-stamp px-3 py-2 border text-xs ${quarter === qq.q ? "bg-[#0c182b] text-white border-[#0c182b]" : "border-[#dde5f0] text-[#4b5d7a] hover:bg-white"}`}>
                            {qq.label}
                        </button>
                    ))}
                </div>
                {data && <span className="text-sm text-[#4b5d7a] ml-2">{data.period_label} · {data.start_fr} → {data.end_fr}</span>}
            </div>

            {error && <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>}

            {loading ? (
                <div className="py-16 text-center text-[#4b5d7a]"><Loader2 className="w-6 h-6 animate-spin inline" /></div>
            ) : data ? (
                <div className="space-y-6">
                    <div className="grid md:grid-cols-2 gap-4">
                        <Block testId="tax-recap-collected" title={`Taxes perçues — ventes (${data.collected.count})`}
                            subtitle="Factures émises (envoyées + payées) dans la période." blk={data.collected} />
                        <Block testId="tax-recap-paid" title={`Crédits de taxe — achats (${data.paid.count})`}
                            subtitle="Taxes payées sur vos dépenses (CTI / RTI)." blk={data.paid} />
                    </div>

                    <div className="border-2 border-[#0c182b] bg-[#0c182b] text-white p-6" data-testid="tax-recap-net">
                        <div className="text-[11px] uppercase tracking-wider text-[#9fb3d1] mb-3">Net à remettre (perçu − payé)</div>
                        <table className="w-full text-sm">
                            <thead className="text-[#9fb3d1] text-xs uppercase">
                                <tr><th className="text-left py-1"></th><th className="text-right py-1">TPS</th><th className="text-right py-1">TVQ</th><th className="text-right py-1">Total</th></tr>
                            </thead>
                            <tbody className="font-mono">
                                <tr><td className="py-1 text-[#c3d2ea]">Perçues (ventes)</td><td className="text-right">{formatCurrency(data.collected.tps)}</td><td className="text-right">{formatCurrency(data.collected.tvq)}</td><td className="text-right">{formatCurrency(data.collected.tps + data.collected.tvq)}</td></tr>
                                <tr><td className="py-1 text-[#c3d2ea]">− Payées (achats)</td><td className="text-right">{formatCurrency(data.paid.tps)}</td><td className="text-right">{formatCurrency(data.paid.tvq)}</td><td className="text-right">{formatCurrency(data.paid.tps + data.paid.tvq)}</td></tr>
                                <tr className="border-t border-[#2a3d5c]"><td className="py-2 font-bold text-white">= NET</td><td className="text-right font-bold pt-2">{formatCurrency(net.tps)}</td><td className="text-right font-bold pt-2">{formatCurrency(net.tvq)}</td><td className={`text-right font-bold pt-2 ${netPositive ? "text-[#ffb4b4]" : "text-[#4fd1c5]"}`}>{formatCurrency(netTotal)}</td></tr>
                            </tbody>
                        </table>
                        <div className={`mt-4 text-lg font-display font-bold ${netPositive ? "text-[#ffd27f]" : "text-[#4fd1c5]"}`} data-testid="tax-recap-net-label">
                            {netPositive ? "Montant net à remettre" : "Remboursement net attendu"} : {formatCurrency(Math.abs(netTotal))}
                        </div>
                    </div>

                    <p className="text-xs text-[#4b5d7a] italic">
                        À titre indicatif. Basé sur les factures émises et les dépenses enregistrées.
                        Validez avec votre comptable avant toute déclaration à Revenu Québec / ARC.
                    </p>
                </div>
            ) : null}
        </div>
    );
};

export default TaxRecapPanel;
