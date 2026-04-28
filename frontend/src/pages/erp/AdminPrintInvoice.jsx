import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import "./print.css";
import { MetaBlock, PartyBlock, PrintPageLayout } from "./print-shared";
import { formatCurrency, formatDate } from "./utils";

const AdminPrintInvoice = () => {
    const { id } = useParams();
    const { http } = useAuth();
    const [doc, setDoc] = useState(null);
    const [error, setError] = useState("");

    useEffect(() => {
        (async () => {
            try {
                const { data } = await http.get(`/admin/invoices/${id}`);
                setDoc(data);
            } catch (e) {
                setError(e?.response?.data?.detail || "Facture introuvable");
            }
        })();
    }, [http, id]);

    if (error) return <div className="print-page"><p style={{ color: "red" }}>{error}</p></div>;
    if (!doc) return <div className="print-page">Chargement…</div>;

    const number = `FAC-${String(doc.number).padStart(4, "0")}`;
    return (
        <div data-testid="print-invoice">
            <PrintPageLayout title="Facture" number={number} statusText={doc.status}>
                <div className="print-grid-2">
                    <PartyBlock label="Facturé à" party={doc.customer_snapshot} />
                    <div style={{ alignSelf: "start" }}>
                        <div className="print-meta" style={{ gridTemplateColumns: "1fr 1fr" }}>
                            <div><div className="lbl">Numéro</div><div className="val">{number}</div></div>
                            <div><div className="lbl">Date</div><div className="val">{formatDate(doc.date)}</div></div>
                            <div><div className="lbl">Échéance</div><div className="val">{formatDate(doc.due_date)}</div></div>
                            <div><div className="lbl">Statut</div><div className="val">{doc.status}</div></div>
                        </div>
                    </div>
                </div>

                <table className="print-items">
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th className="num" style={{ width: "80px" }}>Qté</th>
                            <th className="num" style={{ width: "120px" }}>Prix unitaire</th>
                            <th className="num" style={{ width: "120px" }}>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {doc.items.map((it, i) => (
                            <tr key={`item-${i}-${it.description || ""}`}>
                                <td>{it.description}</td>
                                <td className="num">{Number(it.quantity).toLocaleString("fr-CA")}</td>
                                <td className="num">{formatCurrency(it.unit_price)}</td>
                                <td className="num">{formatCurrency(it.total)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                <div className="print-totals">
                    <div className="row"><span>Sous-total</span><span>{formatCurrency(doc.subtotal)}</span></div>
                    {doc.taxable && (
                        <>
                            <div className="row"><span>TPS (5 %)</span><span>{formatCurrency(doc.tps)}</span></div>
                            <div className="row"><span>TVQ (9,975 %)</span><span>{formatCurrency(doc.tvq)}</span></div>
                        </>
                    )}
                    <div className="row grand"><span>Total à payer</span><span>{formatCurrency(doc.total)}</span></div>
                </div>

                {doc.notes && (
                    <div className="print-notes">
                        <strong>Notes :</strong><br />
                        {doc.notes}
                    </div>
                )}

                <div className="print-footer">
                    <strong>Modalités de paiement</strong> · Net 30 jours. Intérêts de 1,5 % par mois sur les soldes en souffrance.<br />
                    Merci pour votre confiance. Toute question : info@portech.info
                </div>
            </PrintPageLayout>
        </div>
    );
};

export default AdminPrintInvoice;
