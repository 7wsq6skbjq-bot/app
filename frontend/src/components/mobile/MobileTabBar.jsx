import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
    LayoutDashboard,
    Calendar,
    Users,
    FileText,
    MoreHorizontal,
    Truck,
    Package,
    ShoppingCart,
    Send,
    Wallet,
    Scissors,
    Boxes,
    DoorOpen,
    X,
    Inbox,
} from "lucide-react";

const PRIMARY = [
    { to: "/admin/gestion/tableau-de-bord", label: "Bord",     icon: LayoutDashboard, testid: "mtab-dashboard" },
    { to: "/admin/gestion/calendrier",       label: "RDV",      icon: Calendar,         testid: "mtab-calendar" },
    { to: "/admin/gestion/factures",         label: "Factures", icon: FileText,         testid: "mtab-invoices" },
    { to: "/admin/gestion/depenses",         label: "Dépenses", icon: Wallet,           testid: "mtab-expenses" },
];

const SECONDARY = [
    { to: "/admin",                            label: "Leads (soumissions)", icon: Inbox },
    { to: "/admin/gestion/clients",            label: "Clients",             icon: Users },
    { to: "/admin/gestion/fournisseurs",       label: "Fournisseurs",        icon: Truck },
    { to: "/admin/gestion/produits",           label: "Produits",            icon: Package },
    { to: "/admin/gestion/bons-commande",      label: "Bons de commande",    icon: ShoppingCart },
    { to: "/admin/gestion/connaissements",     label: "Connaissements",      icon: Truck },
    { to: "/admin/gestion/coupes",             label: "Listes de coupe",     icon: Scissors },
    { to: "/admin/gestion/inventaire-alu",      label: "Inventaire alu",      icon: Boxes },
    { to: "/admin/gestion/commandes-at",        label: "Commandes AT",        icon: DoorOpen },
    { to: "/admin/gestion/prospection",        label: "Prospection",         icon: Send },
];

/**
 * Fixed bottom navigation bar for mobile (hidden on md+).
 * Honors iOS safe-area inset so it doesn't collide with the home indicator.
 */
export const MobileTabBar = () => {
    const [moreOpen, setMoreOpen] = useState(false);
    const location = useLocation();
    const isActive = (to) => location.pathname.startsWith(to);

    return (
        <>
            <nav
                data-testid="mobile-tab-bar"
                className="sm:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#0c182b] border-t border-[#1e3457] flex justify-around items-stretch"
                style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
            >
                {PRIMARY.map((t) => {
                    const Icon = t.icon;
                    const active = isActive(t.to);
                    return (
                        <Link
                            key={t.to}
                            to={t.to}
                            data-testid={t.testid}
                            className={`flex-1 flex flex-col items-center justify-center gap-1 py-2.5 min-h-[60px] transition-colors ${
                                active ? "text-white" : "text-[#7c92b7] active:bg-[#1e3457]"
                            }`}
                        >
                            <Icon className={`w-5 h-5 ${active ? "" : ""}`} strokeWidth={active ? 2.5 : 1.8} />
                            <span className="text-[10px] tech-stamp">{t.label}</span>
                        </Link>
                    );
                })}
                <button
                    type="button"
                    data-testid="mtab-more"
                    onClick={() => setMoreOpen(true)}
                    className="flex-1 flex flex-col items-center justify-center gap-1 py-2.5 min-h-[60px] text-[#7c92b7] active:bg-[#1e3457] transition-colors"
                >
                    <MoreHorizontal className="w-5 h-5" strokeWidth={1.8} />
                    <span className="text-[10px] tech-stamp">Plus</span>
                </button>
            </nav>

            {moreOpen && (
                <div
                    data-testid="mtab-more-sheet"
                    className="sm:hidden fixed inset-0 z-[60]"
                    onClick={() => setMoreOpen(false)}
                >
                    <div className="absolute inset-0 bg-[#0c182b]/70 backdrop-blur-sm" />
                    <div
                        className="absolute bottom-0 left-0 right-0 bg-white border-t border-[#dde5f0] animate-in slide-in-from-bottom duration-200"
                        style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between px-5 py-4 border-b border-[#dde5f0]">
                            <h3 className="font-display font-bold uppercase text-lg tracking-tight text-[#0c182b]">Plus</h3>
                            <button
                                onClick={() => setMoreOpen(false)}
                                className="w-9 h-9 flex items-center justify-center text-[#0c182b]"
                                aria-label="Fermer"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <ul>
                            {SECONDARY.map((t) => {
                                const Icon = t.icon;
                                return (
                                    <li key={t.to}>
                                        <Link
                                            to={t.to}
                                            onClick={() => setMoreOpen(false)}
                                            className="flex items-center gap-3 px-5 py-4 border-b border-[#eef2f7] active:bg-[#f3f6fb]"
                                            data-testid={`mtab-secondary-${t.to}`}
                                        >
                                            <Icon className="w-5 h-5 text-[#4b5d7a]" strokeWidth={1.8} />
                                            <span className="text-base text-[#0c182b]">{t.label}</span>
                                        </Link>
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                </div>
            )}
        </>
    );
};
