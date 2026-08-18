/** Soumissions (Quotes) — devis client, avec conversion en facture 1-clic. */
import { useState } from "react";
import { FileCheck2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { DocumentPanel } from "./DocumentPanel";
import { PricingCalculator } from "./PricingCalculator";
import { QUOTE_STATUSES, emptyQuote } from "../utils";

/**
 * Wraps the generic DocumentPanel and adds a per-row "Convert to invoice"
 * action available on accepted (or sent) quotes.
 */
export const QuotesPanel = () => {
    const { http } = useAuth();
    const [busy, setBusy] = useState(null);
    const [flash, setFlash] = useState("");

    const convert = async (q) => {
        if (q.converted_invoice_id) {
            window.alert("Cette soumission a déjà été convertie en facture.");
            return;
        }
        if (!window.confirm(
            `Convertir SO-${String(q.number).padStart(4, "0")} en facture ?\n\n`
            + "Une nouvelle facture (brouillon) sera créée avec les mêmes items. "
            + "La soumission passera au statut « acceptée ».",
        )) return;
        setBusy(q.id);
        try {
            const { data } = await http.post(`/admin/quotes/${q.id}/convert-to-invoice`);
            setFlash(`✅ Facture FAC-${String(data.number).padStart(4, "0")} créée. Va dans « Factures » pour la finaliser.`);
        } catch (e) {
            window.alert(e?.response?.data?.detail || "Échec de la conversion.");
        } finally { setBusy(null); }
    };

    return (
        <div>
            {flash && (
                <div className="mb-4 p-3 border border-[#8ec79d] bg-[#e6f4ea] text-[#0b6b2f] text-sm flex items-start justify-between gap-3"
                    data-testid="quote-convert-flash">
                    <span>{flash}</span>
                    <button onClick={() => setFlash("")} className="text-xs underline">Fermer</button>
                </div>
            )}
            <PricingCalculator />
            <DocumentPanel
                title="Soumissions"
                eyebrow="Gestion · Ventes"
                singular="soumission"
                feminineArticle
                kind="quote"
                apiPath="/admin/quotes"
                partyKind="customer"
                partyKey="customer_snapshot"
                printPath={null}
                statuses={QUOTE_STATUSES}
                numberPrefix="SO"
                emptyDoc={emptyQuote}
                csvExportPath="/admin/exports/quotes.csv"
                extraRowActions={(d) => (
                    !d.converted_invoice_id && d.status !== "annulée" && d.status !== "refusée"
                        ? [{
                            icon: FileCheck2,
                            onClick: () => convert(d),
                            title: "Convertir en facture (brouillon)",
                            testid: `quote-convert-${d.id}`,
                            className: "p-2 border border-[#8ec79d] hover:bg-[#e6f4ea] text-[#0b6b2f]",
                            disabled: busy === d.id,
                        }] : []
                )}
            />
        </div>
    );
};

export default QuotesPanel;
