import { DocumentPanel } from "./DocumentPanel";
import { INVOICE_STATUSES, emptyInvoice } from "../utils";

export const InvoicesPanel = () => (
    <DocumentPanel
        title="Factures"
        eyebrow="Gestion · Ventes"
        singular="facture"
        feminineArticle
        kind="invoice"
        apiPath="/admin/invoices"
        partyKind="customer"
        partyKey="customer_snapshot"
        printPath="/admin/imprimer/facture"
        statuses={INVOICE_STATUSES}
        numberPrefix="FAC"
        emptyDoc={emptyInvoice}
    />
);
