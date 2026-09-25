import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
    Banknote, FileText, Hourglass, Calendar, Users,
    Truck, ShoppingCart, Inbox, AlertCircle, TrendingUp, TrendingDown, Wallet, Route,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { formatCurrency, formatDate, STATUS_BADGE } from "../utils";

export const DashboardPanel = () => {
    const { http } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const load = useCallback(async () => {
        setLoading(true); setError("");
        try {
            const { data: d } = await http.get("/admin/dashboard");
            setData(d);
        } catch (e) {
            setError(e?.response?.data?.detail || "Erreur de chargement");
        } finally {
            setLoading(false);
        }
    }, [http]);

    useEffect(() => { load(); }, [load]);

    if (loading && !data) return <div className="p-12 text-center tech-stamp">Chargement…</div>;
    if (error) return <div className="p-4 border border-red-400 bg-red-50 text-red-800 text-sm">{error}</div>;
    if (!data) return null;

    const { kpi, monthly_revenue, top_customers, outstanding_invoices } = data;
    const maxMonthly = Math.max(1, ...monthly_revenue.map((m) => m.total));

    return (
        <div data-testid="dashboard-panel">
            <div className="hidden md:block mb-8">
                <div className="tech-stamp mb-1">Vue d'ensemble</div>
                <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Tableau de bord financier</h1>
            </div>

            {/* Mobile hero KPI — full width revenue */}
            <div className="md:hidden mb-4 bg-[#0c182b] text-white p-5">
                <div className="tech-stamp text-[#9bb6d8] mb-2 flex items-center gap-2">
                    <Banknote className="w-4 h-4" /> Revenus du mois
                </div>
                <div className="font-display font-black text-4xl tracking-tight text-[#7bd1a0]">
                    {formatCurrency(kpi.revenue_this_month)}
                </div>
                <div className="text-xs text-[#9bb6d8] mt-2">{kpi.invoices_count} factures payées · {formatCurrency(kpi.paid_total)} encaissés</div>
                {/* Profit net mini-bar */}
                <div className="mt-4 pt-4 border-t border-[#1e3457] flex items-center justify-between">
                    <div>
                        <div className="tech-stamp text-[#9bb6d8] flex items-center gap-1">
                            {(kpi.profit_this_month || 0) >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />} Profit net
                        </div>
                        <div className={`font-display font-bold text-2xl ${(kpi.profit_this_month || 0) >= 0 ? "text-[#7bd1a0]" : "text-[#ff8a8a]"}`}>
                            {formatCurrency(kpi.profit_this_month || 0)}
                        </div>
                    </div>
                    <div className="text-right">
                        <div className="tech-stamp text-[#9bb6d8]">Dépenses</div>
                        <div className="font-display font-bold text-lg text-[#ffcc7b]">{formatCurrency(kpi.expenses_this_month || 0)}</div>
                    </div>
                </div>
            </div>

            {/* KPI tiles */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#dde5f0] border border-[#dde5f0] mb-6 md:mb-8">
                <KpiTile icon={Banknote}  label="Revenus du mois"   value={formatCurrency(kpi.revenue_this_month)} accent="text-[#0b6b2f]" testid="kpi-revenue" hideMobile />
                <KpiTile icon={Wallet}    label="Dépenses du mois"  value={formatCurrency(kpi.expenses_this_month || 0)} accent="text-[#925800]" testid="kpi-expenses" hideMobile />
                <KpiTile
                    icon={(kpi.profit_this_month || 0) >= 0 ? TrendingUp : TrendingDown}
                    label="Profit net"
                    value={formatCurrency(kpi.profit_this_month || 0)}
                    accent={(kpi.profit_this_month || 0) >= 0 ? "text-[#0b6b2f]" : "text-[#8a1f1f]"}
                    testid="kpi-profit"
                    hideMobile
                />
                <KpiTile icon={Hourglass} label="En attente"         value={formatCurrency(kpi.outstanding_total)} accent="text-[#925800]" testid="kpi-outstanding" />
                <KpiTile icon={FileText}  label="Total facturé"      value={formatCurrency(kpi.invoiced_total)} testid="kpi-invoiced" />
                <KpiTile icon={Calendar}  label="Payées"             value={`${kpi.invoices_count}`} sub={formatCurrency(kpi.paid_total)} testid="kpi-paid" />
                <KpiTile icon={Wallet}    label="TPS récupérable"    value={formatCurrency(kpi.tps_recoverable_month || 0)} sub="ce mois" accent="text-[#0b6b2f]" testid="kpi-tps" />
                <KpiTile icon={Wallet}    label="TVQ récupérable"    value={formatCurrency(kpi.tvq_recoverable_month || 0)} sub="ce mois" accent="text-[#0b6b2f]" testid="kpi-tvq" />
                <KpiTile icon={Route}     label="Kilométrage du mois" value={formatCurrency(kpi.mileage_amount_month || 0)} sub={`${(kpi.mileage_km_month || 0).toLocaleString("fr-CA", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} km · ${kpi.mileage_count_month || 0} trajet(s)`} accent="text-[#2f4f7f]" testid="kpi-mileage" />
            </div>

            {/* Sub-counts */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[#dde5f0] border border-[#dde5f0] mb-8">
                <MiniTile icon={Users}        label="Clients"         value={kpi.customers_count} to="/admin/gestion/clients" />
                <MiniTile icon={Truck}        label="Fournisseurs"    value={kpi.suppliers_count} to="/admin/gestion/fournisseurs" />
                <MiniTile icon={ShoppingCart} label="Produits"        value={kpi.products_count}  to="/admin/gestion/produits" />
                <MiniTile icon={Inbox}        label="Bons commande"   value={kpi.po_count}        to="/admin/gestion/bons-commande" />
                <MiniTile icon={Truck}        label="Connaissements"  value={kpi.bol_count}       to="/admin/gestion/connaissements" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 6-month revenue trend */}
                <div className="lg:col-span-2 border border-[#dde5f0] bg-white p-6">
                    <div className="flex items-center justify-between mb-5">
                        <div className="tech-stamp">Revenus encaissés · 6 derniers mois</div>
                        <div className="tech-stamp text-[#4b5d7a]">Factures payées</div>
                    </div>
                    <div className="grid grid-cols-6 gap-3 h-44 items-end">
                        {monthly_revenue.map((m) => (
                            <div key={m.month} className="flex flex-col items-center gap-2">
                                <div
                                    className="w-full bg-[#2f4f7f] hover:bg-[#0c182b] transition-colors"
                                    style={{ height: `${(m.total / maxMonthly) * 100}%`, minHeight: "2px" }}
                                    title={`${m.label}: ${formatCurrency(m.total)}`}
                                />
                                <div className="tech-stamp text-[10px] text-[#4b5d7a]">{m.label}</div>
                                <div className="text-xs font-display font-bold">{m.total > 0 ? formatCurrency(m.total) : "—"}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Top customers */}
                <div className="border border-[#dde5f0] bg-white p-6">
                    <div className="tech-stamp mb-5">Top clients · facturé</div>
                    {top_customers.length === 0 && <div className="text-sm text-[#4b5d7a]">Aucune donnée pour l'instant.</div>}
                    <ul className="space-y-3">
                        {top_customers.map((c, i) => (
                            <li key={c.name} className="flex items-baseline justify-between gap-3 border-b border-[#dde5f0] last:border-b-0 pb-2 last:pb-0">
                                <div className="flex items-baseline gap-2 min-w-0">
                                    <span className="tech-stamp text-[#97b0d0] flex-none">{(i + 1).toString().padStart(2, "0")}</span>
                                    <span className="font-display font-semibold uppercase text-sm tracking-tight truncate">{c.name}</span>
                                </div>
                                <span className="font-display font-bold text-sm flex-none">{formatCurrency(c.total)}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Outstanding invoices */}
            <div className="mt-8 border border-[#dde5f0] bg-white">
                <div className="px-6 py-4 border-b border-[#dde5f0] bg-[#f9fbfd] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-[#925800]" />
                        <h3 className="font-display font-bold uppercase text-sm tracking-tight">
                            Factures en attente de paiement ({outstanding_invoices.length})
                        </h3>
                    </div>
                    <Link to="/admin/gestion/factures" className="tech-stamp text-[#2f4f7f] hover:underline">
                        Voir toutes →
                    </Link>
                </div>
                {outstanding_invoices.length === 0 ? (
                    <div className="p-8 text-center text-sm text-[#4b5d7a]">
                        Aucune facture en attente — tout est à jour.
                    </div>
                ) : (
                    <ul>
                        {outstanding_invoices.map((i) => (
                            <li key={i.id} className="border-b border-[#dde5f0] last:border-b-0">
                                <div className="grid grid-cols-1 md:grid-cols-12 gap-2 px-6 py-3 items-center">
                                    <div className="md:col-span-2 font-display font-bold text-sm">FAC-{String(i.number).padStart(4, "0")}</div>
                                    <div className="md:col-span-4 text-sm truncate">{i.customer || "—"}</div>
                                    <div className="md:col-span-2 text-xs text-[#4b5d7a]">{formatDate(i.date)}</div>
                                    <div className="md:col-span-1">
                                        <span className={`tech-stamp px-2 py-1 border ${STATUS_BADGE[i.status] || ""}`}>{i.status}</span>
                                    </div>
                                    <div className="md:col-span-3 text-right font-display font-bold text-sm">{formatCurrency(i.total)}</div>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
};

const KpiTile = ({ icon: Icon, label, value, sub, accent, testid, hideMobile = false }) => (
    <div data-testid={testid} className={`bg-white p-4 md:p-6 ${hideMobile ? "hidden md:block" : ""}`}>
        <div className="flex items-center gap-2 mb-2 md:mb-3 tech-stamp">
            <Icon className={`w-4 h-4 ${accent || "text-[#2f4f7f]"}`} />
            <span className="truncate">{label}</span>
        </div>
        <div className={`font-display font-bold text-xl md:text-3xl tracking-tight ${accent || ""}`}>
            {value}
        </div>
        {sub && <div className="text-xs text-[#4b5d7a] mt-1 truncate">{sub}</div>}
    </div>
);

const MiniTile = ({ icon: Icon, label, value, to }) => (
    <Link to={to} className="bg-white p-5 hover:bg-[#f3f6fb] transition-colors group">
        <div className="flex items-center gap-2 tech-stamp text-[#4b5d7a] mb-2">
            <Icon className="w-3.5 h-3.5 text-[#2f4f7f]" />
            {label}
        </div>
        <div className="font-display font-bold text-2xl tracking-tight group-hover:text-[#2f4f7f]">
            {value}
        </div>
    </Link>
);
