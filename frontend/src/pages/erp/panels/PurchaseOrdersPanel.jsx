import { DocumentPanel } from "./DocumentPanel";
import { PO_STATUSES, emptyPO } from "../utils";

export const PurchaseOrdersPanel = () => (
    <DocumentPanel
        title="Bons de commande"
        eyebrow="Gestion · Achats"
        singular="bon de commande"
        kind="purchase-order"
        apiPath="/admin/purchase-orders"
        partyKind="supplier"
        partyKey="supplier_snapshot"
        printPath="/admin/imprimer/bon-commande"
        statuses={PO_STATUSES}
        numberPrefix="BC"
        emptyDoc={emptyPO}
    />
);
