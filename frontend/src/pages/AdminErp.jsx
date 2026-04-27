import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { AdminHeader } from "./admin/AdminHeader";
import { PartiesPanel } from "./erp/panels/PartiesPanel";
import { ProductsPanel } from "./erp/panels/ProductsPanel";
import { InvoicesPanel } from "./erp/panels/InvoicesPanel";
import { PurchaseOrdersPanel } from "./erp/panels/PurchaseOrdersPanel";
import { BolPanel } from "./erp/panels/BolPanel";

const TABS = [
    { slug: "clients",        label: "Clients",         panel: "parties-customer" },
    { slug: "fournisseurs",   label: "Fournisseurs",    panel: "parties-supplier" },
    { slug: "produits",       label: "Produits",        panel: "products" },
    { slug: "factures",       label: "Factures",        panel: "invoices" },
    { slug: "bons-commande",  label: "Bons de commande", panel: "purchase-orders" },
    { slug: "connaissements", label: "Connaissements",  panel: "bills-of-lading" },
];

const AdminErp = () => {
    const { tab } = useParams();
    const navigate = useNavigate();
    const { logout, user } = useAuth();
    const activeSlug = tab || "clients";
    const activeTab = TABS.find((t) => t.slug === activeSlug) || TABS[0];

    useEffect(() => {
        if (!tab) navigate("/admin/gestion/clients", { replace: true });
    }, [tab, navigate]);

    return (
        <div
            data-testid="page-admin-erp"
            className="min-h-screen bg-[#f3f6fb] text-[#0c182b]"
        >
            <AdminHeader user={user} onLogout={logout} />

            {/* Secondary nav */}
            <div className="bg-white border-b border-[#dde5f0]">
                <div className="container-portech flex items-center gap-2 overflow-x-auto py-3">
                    <Link
                        to="/admin"
                        data-testid="erp-nav-leads"
                        className="tech-stamp px-3 py-2 border border-[#dde5f0] text-[#4b5d7a] hover:bg-[#f3f6fb] whitespace-nowrap"
                    >
                        ← Leads (soumissions)
                    </Link>
                    <div className="w-px h-6 bg-[#dde5f0] mx-2" />
                    {TABS.map((t) => (
                        <Link
                            key={t.slug}
                            to={`/admin/gestion/${t.slug}`}
                            data-testid={`erp-tab-${t.slug}`}
                            className={`tech-stamp px-4 py-2 border whitespace-nowrap transition-colors ${
                                t.slug === activeSlug
                                    ? "border-[#0c182b] bg-[#0c182b] text-white"
                                    : "border-[#dde5f0] text-[#4b5d7a] hover:bg-[#f3f6fb]"
                            }`}
                        >
                            {t.label}
                        </Link>
                    ))}
                </div>
            </div>

            <main className="container-portech py-8">
                {activeTab.panel === "parties-customer" && <PartiesPanel kind="customer" />}
                {activeTab.panel === "parties-supplier" && <PartiesPanel kind="supplier" />}
                {activeTab.panel === "products" && <ProductsPanel />}
                {activeTab.panel === "invoices" && <InvoicesPanel />}
                {activeTab.panel === "purchase-orders" && <PurchaseOrdersPanel />}
                {activeTab.panel === "bills-of-lading" && <BolPanel />}
            </main>
        </div>
    );
};

export default AdminErp;
