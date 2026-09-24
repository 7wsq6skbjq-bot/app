import { useCallback, useEffect, useState } from "react";
import { RefreshCw, FileDown, Mail, Loader2, Send } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { formatCurrency } from "../utils";

export const StatementsPanel = () => {
    const { http, getToken } = useAuth();
    const [rows, setRows] = useState([]);
    const [totalBalance, setTotalBalance] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");
    const [busyKey, setBusyKey] = useState("");
    const [sendingAll, setSendingAll] = useState(false);

    const flash = (m) => { setNotice(m); setTimeout(() => setNotice(""), 6000); };

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const { data } = await http.get("/admin/statements/customers");
            setRows(data.customers || []);
            setTotalBalance(data.total_balance || 0);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally { setLoading(false); }
    }, [http]);
    useEffect(() => { load(); }, [load]);

    const previewPdf = (key) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/statements/${encodeURIComponent(key)}/pdf?token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const sendOne = async (row) => {
        let to = row.email;
        if (!to) {
            to = window.prompt(`Aucun courriel enregistré pour ${row.name}. Entrez une adresse :`, "");
            if (!to) return;
        }
        setBusyKey(row.key); setError("");
        try {
            await http.post(`/admin/statements/${encodeURIComponent(row.key)}/send`, { to_email: to });
            flash(`✅ État de compte envoyé à ${to} (${formatCurrency(row.balance)}).`);
        } catch (e) {
            setError(e?.response?.data?.detail || "Échec de l'envoi");
        } finally { setBusyKey(""); }
    };

    const sendAll = async () => {
        if (!window.confirm(`Envoyer l'état de compte à TOUS les clients ayant un solde dû (${rows.length}) ?`)) return;
        setSendingAll(true); setError("");
        try {
            const { data } = await http.post("/admin/statements/send-all");
            flash(`✅ ${data.sent_count} état(s) de compte envoyé(s).`
                + (data.skipped?.length ? ` ${data.skipped.length} ignoré(s) (sans courriel).` : ""));
        } catch (e) {
            setError(e?.response?.data?.detail || "Échec de l'envoi en lot");
        } finally { setSendingAll(false); }
    };

    return (
        <div data-testid="statements-panel">
            <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
                <div>
                    <div className="tech-stamp mb-1">Comptes clients</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight">États de compte</h1>
                    <p className="text-sm text-[#4b5d7a] mt-1">Factures envoyées non payées, regroupées par client.</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={load} className="btn-secondary !py-2 !px-3 !text-xs" data-testid="statements-refresh">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={sendAll} disabled={sendingAll || rows.length === 0}
                        data-testid="statements-send-all"
                        className="btn-primary !py-2 !px-4 !text-xs disabled:opacity-40 disabled:cursor-not-allowed">
                        {sendingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                        Envoyer à tous
                    </button>
                </div>
            </div>

            {notice && <div className="mb-4 p-3 border border-[#8ec79d] bg-[#e6f4ea] text-[#0b6b2f] text-sm" data-testid="statements-notice">{notice}</div>}
            {error && <div className="mb-4 p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>}

            <div className="mb-4 inline-block border border-[#0c182b] bg-[#0c182b] text-white px-5 py-3">
                <span className="text-[10px] uppercase tracking-wider text-[#9fb3d1]">Solde total dû (tous clients)</span>
                <div className="font-display font-bold text-2xl" data-testid="statements-total">{formatCurrency(totalBalance)}</div>
            </div>

            <div className="border border-[#dde5f0] bg-white">
                <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                    <div className="col-span-4">Client</div>
                    <div className="col-span-3">Courriel</div>
                    <div className="col-span-1 text-right">Factures</div>
                    <div className="col-span-2 text-right">Solde dû</div>
                    <div className="col-span-2 text-right">Actions</div>
                </div>
                {rows.length === 0 && !loading && (
                    <div className="p-12 text-center text-[#4b5d7a] text-sm">Aucun client avec un solde dû. 🎉</div>
                )}
                <ul>
                    {rows.map((r) => (
                        <li key={r.key} data-testid={`statement-row-${r.key}`}
                            className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors">
                            <div className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-3 items-center">
                                <div className="col-span-4 font-display font-semibold uppercase text-sm tracking-tight">{r.name}</div>
                                <div className="col-span-3 text-sm text-[#4b5d7a] truncate">{r.email || <span className="text-red-500">— aucun —</span>}</div>
                                <div className="col-span-1 text-sm text-right">{r.invoice_count}</div>
                                <div className="col-span-2 text-sm text-right font-display font-bold">{formatCurrency(r.balance)}</div>
                                <div className="col-span-2 flex justify-end gap-1">
                                    <button onClick={() => previewPdf(r.key)} title="Aperçu PDF"
                                        data-testid={`statement-pdf-${r.key}`}
                                        className="p-2 border border-[#dde5f0] hover:bg-[#eaf1fb] text-[#2f4f7f]">
                                        <FileDown className="w-3.5 h-3.5" />
                                    </button>
                                    <button onClick={() => sendOne(r)} disabled={busyKey === r.key} title="Envoyer par courriel"
                                        data-testid={`statement-send-${r.key}`}
                                        className="p-2 border border-[#8ec79d] hover:bg-[#e6f4ea] text-[#0b6b2f] disabled:opacity-40">
                                        {busyKey === r.key ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Mail className="w-3.5 h-3.5" />}
                                    </button>
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default StatementsPanel;
