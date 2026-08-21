/** Soumissions (Quotes) — devis client, avec conversion en facture 1-clic. */
import { useEffect, useState } from "react";
import { FileCheck2, DraftingCompass, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { DocumentPanel } from "./DocumentPanel";
import { PricingCalculator } from "./PricingCalculator";
import { Modal } from "../components/Modal";
import { QUOTE_STATUSES, emptyQuote } from "../utils";

// ── Modale de sélection des dessins Adams Rite ───────────────
const DrawingsModal = ({ http, quote, onClose, onSaved }) => {
    const [list, setList] = useState(null);
    const [sel, setSel] = useState(new Set(quote.drawing_pages || []));
    const [q, setQ] = useState("");
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        http.get("/admin/adams-rite/drawings")
            .then(({ data }) => setList(data.drawings))
            .catch(() => setList([]));
    }, [http]);

    const toggle = (page) => {
        setSel((prev) => {
            const n = new Set(prev);
            n.has(page) ? n.delete(page) : n.add(page);
            return n;
        });
    };
    const save = async () => {
        setSaving(true);
        try {
            await http.patch(`/admin/quotes/${quote.id}/drawings`, { pages: [...sel] });
            onSaved([...sel].sort((a, b) => a - b));
        } finally { setSaving(false); }
    };

    const filtered = (list || []).filter((d) =>
        d.label.toLowerCase().includes(q.trim().toLowerCase()));

    return (
        <Modal open onClose={onClose} title={`Dessins de quincaillerie · SO-${String(quote.number).padStart(4, "0")}`} testId="quote-drawings-modal" wide
            footer={<div className="flex justify-between items-center gap-2">
                <span className="text-xs text-[#4b5d7a]">{sel.size} dessin(s) — annexé(s) automatiquement au PDF</span>
                <button data-testid="quote-drawings-save" onClick={save} disabled={saving} className="tech-stamp px-4 py-2 bg-[#0c182b] text-white flex items-center gap-1">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <DraftingCompass className="w-4 h-4" />} Enregistrer</button>
            </div>}>
            <input data-testid="quote-drawings-search" className="w-full px-3 py-2 border border-[#dde5f0] text-sm mb-3" placeholder="Rechercher une série (ex. 3600, MS1850, 8800)…" value={q} onChange={(e) => setQ(e.target.value)} />
            {list === null ? (
                <div className="py-10 text-center text-[#4b5d7a]"><Loader2 className="w-5 h-5 animate-spin inline" /></div>
            ) : (
                <div className="max-h-[55vh] overflow-y-auto divide-y divide-[#eef2f8]">
                    {filtered.map((d) => (
                        <label key={d.page} data-testid={`quote-drawing-${d.page}`} className="flex items-center gap-3 px-2 py-2 cursor-pointer hover:bg-[#f3f6fb]">
                            <input type="checkbox" checked={sel.has(d.page)} onChange={() => toggle(d.page)} className="w-4 h-4" />
                            <span className="text-sm text-[#0c182b] flex-1">{d.label}</span>
                            <span className="text-xs text-[#9aa8bd]">p. {d.page}</span>
                        </label>
                    ))}
                    {filtered.length === 0 && <div className="text-sm text-[#9aa8bd] py-6 text-center">Aucun dessin trouvé.</div>}
                </div>
            )}
        </Modal>
    );
};

/**
 * Wraps the generic DocumentPanel and adds a per-row "Convert to invoice"
 * action available on accepted (or sent) quotes.
 */
export const QuotesPanel = () => {
    const { http } = useAuth();
    const [busy, setBusy] = useState(null);
    const [flash, setFlash] = useState("");
    const [drawings, setDrawings] = useState(null); // quote being edited

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
                extraRowActions={(d) => ([
                    {
                        icon: DraftingCompass,
                        onClick: () => setDrawings(d),
                        title: "Joindre des dessins Adams Rite au PDF",
                        testid: `quote-drawings-btn-${d.id}`,
                        className: `p-2 border ${d.drawing_pages?.length ? "border-[#2f4f7f] bg-[#eaf1fb] text-[#2f4f7f]" : "border-[#dde5f0] hover:bg-[#f3f6fb] text-[#4b5d7a]"}`,
                    },
                    ...(!d.converted_invoice_id && d.status !== "annulée" && d.status !== "refusée"
                        ? [{
                            icon: FileCheck2,
                            onClick: () => convert(d),
                            title: "Convertir en facture (brouillon)",
                            testid: `quote-convert-${d.id}`,
                            className: "p-2 border border-[#8ec79d] hover:bg-[#e6f4ea] text-[#0b6b2f]",
                            disabled: busy === d.id,
                        }] : []),
                ])}
            />
            {drawings && (
                <DrawingsModal http={http} quote={drawings} onClose={() => setDrawings(null)}
                    onSaved={(pages) => {
                        setDrawings(null);
                        setFlash(`✅ ${pages.length} dessin(s) joint(s) à SO-${String(drawings.number).padStart(4, "0")}. Ils apparaîtront dans le PDF.`);
                    }} />
            )}
        </div>
    );
};

export default QuotesPanel;
