import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { AdminHeader } from "./admin/AdminHeader";
import { PartiesPanel } from "./erp/panels/PartiesPanel";
import { ProductsPanel } from "./erp/panels/ProductsPanel";
import { InvoicesPanel } from "./erp/panels/InvoicesPanel";
import { QuotesPanel } from "./erp/panels/QuotesPanel";
import { ExpertReportsPanel } from "./erp/panels/ExpertReportsPanel";
import { PurchaseOrdersPanel } from "./erp/panels/PurchaseOrdersPanel";
import { BolPanel } from "./erp/panels/BolPanel";
import { CalendarPanel } from "./erp/panels/CalendarPanel";
import { DashboardPanel } from "./erp/panels/DashboardPanel";
import { ProspectionPanel } from "./erp/panels/ProspectionPanel";
import { ExpensesPanel } from "./erp/panels/ExpensesPanel";
import { CutListPanel } from "./erp/panels/CutListPanel";
import { FabricationPanel } from "./erp/panels/FabricationPanel";
import { InventoryPanel } from "./erp/panels/InventoryPanel";
import { ATOrdersPanel } from "./erp/panels/ATOrdersPanel";
import { PaymentNoticesPanel } from "./erp/panels/PaymentNoticesPanel";
import { ComposeEmailPanel } from "./erp/panels/ComposeEmailPanel";
import { JobsPanel } from "./erp/panels/JobsPanel";
import { CatalogPanel } from "./erp/panels/CatalogPanel";
import { StatementsPanel } from "./erp/panels/StatementsPanel";
import { AssistantPanel } from "./erp/panels/AssistantPanel";
import { MileagePanel } from "./erp/panels/MileagePanel";
import { MasterCostsPanel } from "./erp/panels/MasterCostsPanel";
import { TaxRecapPanel } from "./erp/panels/TaxRecapPanel";
import { MobileTabBar } from "../components/mobile/MobileTabBar";

const TABS = [
    { slug: "tableau-de-bord", label: "Tableau de bord", panel: "dashboard" },
    { slug: "suivi-jobs",      label: "Suivi des jobs",  panel: "jobs" },
    { slug: "assistante-ia",   label: "Assistante IA",   panel: "assistant" },
    { slug: "calendrier",      label: "Calendrier",      panel: "calendar" },
    { slug: "clients",         label: "Clients",         panel: "parties-customer" },
    { slug: "fournisseurs",    label: "Fournisseurs",    panel: "parties-supplier" },
    { slug: "produits",        label: "Produits",        panel: "products" },
    { slug: "catalogue-quincaillerie", label: "Catalogue quincaillerie", panel: "catalog" },
    { slug: "soumissions",     label: "Soumissions",     panel: "quotes" },
    { slug: "factures",        label: "Factures",        panel: "invoices" },
    { slug: "etats-de-compte", label: "États de compte", panel: "statements" },
    { slug: "bons-commande",   label: "Bons de commande", panel: "purchase-orders" },
    { slug: "connaissements",  label: "Connaissements",  panel: "bills-of-lading" },
    { slug: "depenses",        label: "Dépenses",        panel: "expenses" },
    { slug: "recap-taxes",     label: "Récap TPS/TVQ",   panel: "tax-recap" },
    { slug: "kilometrage",     label: "Rapport kilométrique", panel: "mileage" },
    { slug: "couts-master",    label: "Coûts Master",     panel: "master" },
    { slug: "fabrication",     label: "Fabrication",     panel: "fabrication" },
    { slug: "inventaire-alu",  label: "Inventaire alu",  panel: "inventory" },
    { slug: "commandes-at",    label: "Commandes AT",    panel: "at-orders" },
    { slug: "rapports",         label: "Rapports d'expertise", panel: "expert-reports" },
    { slug: "avis-paiement",   label: "Avis de paiement", panel: "payment-notices" },
    { slug: "courriel",         label: "Composer courriel", panel: "compose-email" },
    { slug: "prospection",     label: "Prospection",     panel: "prospection" },
];

const AdminErp = () => {
    const { tab } = useParams();
    const navigate = useNavigate();
    const { logout, user } = useAuth();
    const activeSlug = tab || "tableau-de-bord";
    const activeTab = TABS.find((t) => t.slug === activeSlug) || TABS[0];

    useEffect(() => {
        if (!tab) navigate("/admin/gestion/tableau-de-bord", { replace: true });
        // Legacy URL support — /coupes → /fabrication
        if (tab === "coupes") navigate("/admin/gestion/fabrication", { replace: true });
    }, [tab, navigate]);

    return (
        <div
            data-testid="page-admin-erp"
            className="min-h-screen bg-[#f3f6fb] text-[#0c182b] pb-[80px] sm:pb-0"
        >
            <AdminHeader user={user} onLogout={logout} />

            {/* Secondary nav — desktop / PWA Windows / tablet (sm+) */}
            <div className="hidden sm:block bg-white border-b border-[#dde5f0]">
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
                            className={`tech-stamp px-3 py-2 border whitespace-nowrap transition-colors ${
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

            {/* Phone-only current section title bar (< sm) */}
            <div className="sm:hidden bg-white border-b border-[#dde5f0] px-4 py-3">
                <div className="tech-stamp text-[#4b5d7a]">Gestion</div>
                <div className="font-display font-bold uppercase text-xl tracking-tight text-[#0c182b]">{activeTab.label}</div>
            </div>

            <main className="container-portech py-4 md:py-8 px-3 md:px-6">
                {activeTab.panel === "dashboard" && <DashboardPanel />}
                {activeTab.panel === "jobs" && <JobsPanel />}
                {activeTab.panel === "assistant" && <AssistantPanel />}
                {activeTab.panel === "calendar" && <CalendarPanel />}
                {activeTab.panel === "parties-customer" && <PartiesPanel kind="customer" />}
                {activeTab.panel === "parties-supplier" && <PartiesPanel kind="supplier" />}
                {activeTab.panel === "products" && <ProductsPanel />}
                {activeTab.panel === "catalog" && <CatalogPanel />}
                {activeTab.panel === "invoices" && <InvoicesPanel />}
                {activeTab.panel === "statements" && <StatementsPanel />}
                {activeTab.panel === "quotes" && <QuotesPanel />}
                {activeTab.panel === "purchase-orders" && <PurchaseOrdersPanel />}
                {activeTab.panel === "bills-of-lading" && <BolPanel />}
                {activeTab.panel === "expenses" && <ExpensesPanel />}
                {activeTab.panel === "tax-recap" && <TaxRecapPanel />}
                {activeTab.panel === "mileage" && <MileagePanel />}
                {activeTab.panel === "master" && <MasterCostsPanel />}
                {activeTab.panel === "cuts" && <CutListPanel />}
                {activeTab.panel === "fabrication" && <FabricationPanel />}
                {activeTab.panel === "inventory" && <InventoryPanel />}
                {activeTab.panel === "at-orders" && <ATOrdersPanel />}
                {activeTab.panel === "expert-reports" && <ExpertReportsPanel />}
                {activeTab.panel === "payment-notices" && <PaymentNoticesPanel />}
                {activeTab.panel === "compose-email" && <ComposeEmailPanel />}
                {activeTab.panel === "prospection" && <ProspectionPanel />}
            </main>

            <MobileTabBar />
        </div>
    );
};

export default AdminErp;
