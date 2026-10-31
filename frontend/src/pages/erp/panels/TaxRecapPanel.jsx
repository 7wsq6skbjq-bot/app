import { useCallback, useEffect, useState } from "react";
import { RefreshCw, FileDown, Loader2, Mail, Save } from "lucide-react";
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
    const [mode, setMode] = useState("quarter");
    const [rStart, setRStart] = useState(`${now.getFullYear()}-01-01`);
    const [rEnd, setREnd] = useState(new Date().toISOString().slice(0, 10));
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [accountantEmail, setAccountantEmail] = useState("");
    const [savingEmail, setSavingEmail] = useState(false);
    const [sending, setSending] = useState(false);
    const [notice, setNotice] = useState("");

    const flash = (m) => { setNotice(m); setTimeout(() => setNotice(""), 6000); };

    useEffect(() => {
        http.get("/admin/tax-recap/settings")
            .then(({ data }) => setAccountantEmail(data.accountant_email || ""))
            .catch(() => {});
    }, [http]);

    const saveEmail = async () => {
        setSavingEmail(true);
        try {
            await http.put("/admin/tax-recap/settings", { accountant_email: accountantEmail.trim() });
            flash("✅ Courriel du comptable enregistré.");
        } catch (e) {
            setError(e?.response?.data?.detail || "Échec de l'enregistrement");
        } finally { setSavingEmail(false); }
    };

    const sendToAccountant = async () => {
        let to = accountantEmail.trim();
        if (!to) {
            to = window.prompt("Courriel du comptable :", "") || "";
            if (!to.trim()) return;
        }
        setSending(true); setError("");
        try {
            const payload = mode === "range"
                ? { start: rStart, end: rEnd, to_email: to.trim() }
                : { year, quarter, to_email: to.trim() };
            const { data } = await http.post("/admin/tax-recap/send", payload);
            flash(`✅ Récap ${data.period_label} envoyé à ${data.to_email}.`);
        } catch (e) {
            setError(e?.response?.data?.detail || "Échec de l'envoi");
        } finally { setSending(false); }
    };

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const qs = mode === "range"
                ? `start=${rStart}&end=${rEnd}`
                : `year=${year}&quarter=${quarter}`;
            const { data } = await http.get(`/admin/tax-recap?${qs}`);
            setData(data);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally { setLoading(false); }
    }, [http, year, quarter, mode, rStart, rEnd]);
    useEffect(() => { load(); }, [load]);

    const years = data?.available_years?.length ? data.available_years : [now.getFullYear()];

    const previewPdf = () => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const qs = mode === "range"
            ? `start=${rStart}&end=${rEnd}`
            : `year=${year}&quarter=${quarter}`;
        const url = `${base}/api/admin/tax-recap/pdf?${qs}&token=${token}`;
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
                    <button onClick={sendToAccountant} disabled={!data || sending} data-testid="tax-recap-send"
                        className="btn-primary !py-2 !px-4 !text-xs disabled:opacity-40">
                        {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Mail className="w-3.5 h-3.5" />} Envoyer au comptable
                    </button>
                </div>
            </div>

            {notice && <div className="mb-4 p-3 border border-[#8ec79d] bg-[#e6f4ea] text-[#0b6b2f] text-sm" data-testid="tax-recap-notice">{notice}</div>}

            <div className="flex flex-wrap items-center gap-2 mb-4 border border-[#dde5f0] bg-white p-3">
                <span className="text-xs uppercase tracking-wider text-[#4b5d7a] font-bold">Courriel du comptable</span>
                <input type="email" value={accountantEmail} onChange={(e) => setAccountantEmail(e.target.value)}
                    data-testid="tax-recap-accountant-email" placeholder="comptable@exemple.com"
                    className="flex-1 min-w-[220px] px-3 py-2 border border-[#c5d4e7] text-sm" />
                <button onClick={saveEmail} disabled={savingEmail} data-testid="tax-recap-save-email"
                    className="tech-stamp px-3 py-2 bg-[#1f3a5f] text-white text-xs flex items-center gap-1 disabled:opacity-50">
                    <Save className="w-3.5 h-3.5" /> {savingEmail ? "…" : "Enregistrer"}
                </button>
                <span className="text-[11px] text-[#4b5d7a] w-full sm:w-auto">Rappel auto push + courriel au 1er jour de chaque nouveau trimestre.</span>
            </div>

            <div className="flex flex-wrap items-center gap-2 mb-6">
                <div className="flex gap-1 mr-1" data-testid="tax-recap-mode">
                    <button onClick={() => setMode("quarter")} data-testid="tax-recap-mode-quarter"
                        className={`tech-stamp px-3 py-2 border text-xs ${mode === "quarter" ? "bg-[#2f4f7f] text-white border-[#2f4f7f]" : "border-[#dde5f0] text-[#4b5d7a] hover:bg-white"}`}>
                        Trimestre
                    </button>
                    <button onClick={() => setMode("range")} data-testid="tax-recap-mode-range"
                        className={`tech-stamp px-3 py-2 border text-xs ${mode === "range" ? "bg-[#2f4f7f] text-white border-[#2f4f7f]" : "border-[#dde5f0] text-[#4b5d7a] hover:bg-white"}`}>
                        Plage de dates
                    </button>
                </div>

                {mode === "quarter" ? (
                    <>
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
                    </>
                ) : (
                    <div className="flex flex-wrap items-end gap-2">
                        <div>
                            <label className="block text-[10px] uppercase tracking-wider text-[#6485b4] mb-1">Du</label>
                            <input type="date" data-testid="tax-recap-start" value={rStart} onChange={(e) => setRStart(e.target.value)}
                                className="px-3 py-2 border border-[#c5d4e7] bg-white text-sm" />
                        </div>
                        <div>
                            <label className="block text-[10px] uppercase tracking-wider text-[#6485b4] mb-1">Au</label>
                            <input type="date" data-testid="tax-recap-end" value={rEnd} onChange={(e) => setREnd(e.target.value)}
                                className="px-3 py-2 border border-[#c5d4e7] bg-white text-sm" />
                        </div>
                    </div>
                )}
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

                    {data.collected_lines?.length > 0 && (
                        <div className="border border-[#dde5f0] bg-white p-4" data-testid="tax-recap-invoice-detail">
                            <div className="tech-stamp text-[#2f4f7f] mb-3">Détail des factures de vente ({data.collected_lines.length})</div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm min-w-[640px]">
                                    <thead>
                                        <tr className="bg-[#0c182b] text-white tech-stamp text-[10px]">
                                            <th className="text-left px-3 py-2">Date</th>
                                            <th className="text-left px-3 py-2">Nº</th>
                                            <th className="text-left px-3 py-2">Client</th>
                                            <th className="text-right px-3 py-2">Sous-total</th>
                                            <th className="text-right px-3 py-2">TPS</th>
                                            <th className="text-right px-3 py-2">TVQ</th>
                                            <th className="text-right px-3 py-2">Total</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.collected_lines.map((ln, i) => (
                                            <tr key={i} data-testid={`tax-recap-inv-${ln.number}`} className={`border-b border-[#dde5f0] ${ln.non_taxable ? "bg-[#fff4e0]" : "odd:bg-[#f3f6fb]"}`}>
                                                <td className="px-3 py-2">{ln.date}</td>
                                                <td className="px-3 py-2">{ln.number}</td>
                                                <td className="px-3 py-2">
                                                    {ln.customer}
                                                    {ln.non_taxable && <span className="ml-2 text-[10px] uppercase tracking-wider text-[#925800] bg-[#ffe3ab] px-1.5 py-0.5 rounded">Non taxable</span>}
                                                </td>
                                                <td className="px-3 py-2 text-right font-mono">{formatCurrency(ln.subtotal)}</td>
                                                <td className="px-3 py-2 text-right font-mono">{formatCurrency(ln.tps)}</td>
                                                <td className="px-3 py-2 text-right font-mono">{formatCurrency(ln.tvq)}</td>
                                                <td className="px-3 py-2 text-right font-mono font-bold">{formatCurrency(ln.total)}</td>
                                            </tr>
                                        ))}
                                        <tr className="bg-[#eaf1fb] font-bold">
                                            <td className="px-3 py-2" colSpan={3}>TOTAUX</td>
                                            <td className="px-3 py-2 text-right font-mono">{formatCurrency(data.collected.subtotal)}</td>
                                            <td className="px-3 py-2 text-right font-mono">{formatCurrency(data.collected.tps)}</td>
                                            <td className="px-3 py-2 text-right font-mono">{formatCurrency(data.collected.tvq)}</td>
                                            <td className="px-3 py-2 text-right font-mono">{formatCurrency(data.collected.total)}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                            <p className="text-[11px] text-[#6485b4] mt-2">Les lignes surlignées sont des ventes non taxables (TPS/TVQ à 0 $) — incluses au chiffre d'affaires mais pas à la base taxable.</p>
                        </div>
                    )}

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
