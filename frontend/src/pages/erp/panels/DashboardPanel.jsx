import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
    Banknote, FileText, Hourglass, Calendar, Users,
    Truck, ShoppingCart, Inbox, AlertCircle,
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
            <div className="mb-8">
                <div className="tech-stamp mb-1">Vue d'ensemble</div>
                <h1 className="font-display font-bold uppercase text-3xl tracking-tight">Tableau de bord financier</h1>
            </div>

            {/* KPI tiles */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#dde5f0] border border-[#dde5f0] mb-8">
                <KpiTile icon={Banknote}  label="Revenus du mois"   value={formatCurrency(kpi.revenue_this_month)} accent="text-[#0b6b2f]" testid="kpi-revenue" />
                <KpiTile icon={Hourglass} label="En attente paiement" value={formatCurrency(kpi.outstanding_total)} accent="text-[#925800]" testid="kpi-outstanding" />
                <KpiTile icon={FileText}  label="Total facturé"      value={formatCurrency(kpi.invoiced_total)} testid="kpi-invoiced" />
                <KpiTile icon={Calendar}  label="Factures · payées"  value={`${kpi.invoices_count} (${formatCurrency(kpi.paid_total)})`} testid="kpi-paid" />
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

const KpiTile = ({ icon: Icon, label, value, accent, testid }) => (
    <div data-testid={testid} className="bg-white p-6">
        <div className="flex items-center gap-3 mb-3 tech-stamp">
            <Icon className={`w-4 h-4 ${accent || "text-[#2f4f7f]"}`} />
            {label}
        </div>
        <div className={`font-display font-bold text-2xl md:text-3xl tracking-tight ${accent || ""}`}>
            {value}
        </div>
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
