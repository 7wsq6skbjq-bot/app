import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import "./print.css";
import { PartyBlock, PrintPageLayout } from "./print-shared";
import { formatDate } from "./utils";

const AdminPrintBol = () => {
    const { id } = useParams();
    const { http } = useAuth();
    const [doc, setDoc] = useState(null);
    const [error, setError] = useState("");

    useEffect(() => {
        (async () => {
            try {
                const { data } = await http.get(`/admin/bills-of-lading/${id}`);
                setDoc(data);
            } catch (e) {
                setError(e?.response?.data?.detail || "Connaissement introuvable");
            }
        })();
    }, [http, id]);

    if (error) return <div className="print-page"><p style={{ color: "red" }}>{error}</p></div>;
    if (!doc) return <div className="print-page">Chargement…</div>;

    const number = `CONN-${String(doc.number).padStart(4, "0")}`;
    return (
        <div data-testid="print-bol">
            <PrintPageLayout title="Connaissement" number={number} statusText={doc.status}>
                <div className="print-grid-2">
                    <PartyBlock label="Expéditeur (Shipper)" party={doc.shipper_snapshot} />
                    <PartyBlock label="Destinataire (Consignee)" party={doc.consignee_snapshot} />
                </div>

                <div className="print-meta">
                    <div><div className="lbl">Numéro</div><div className="val">{number}</div></div>
                    <div><div className="lbl">Date</div><div className="val">{formatDate(doc.date)}</div></div>
                    <div><div className="lbl">Livraison attendue</div><div className="val">{formatDate(doc.expected_delivery)}</div></div>
                    <div><div className="lbl">Transporteur</div><div className="val">{doc.carrier || "—"}</div></div>
                </div>

                <table className="print-items">
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th className="num" style={{ width: "70px" }}>Qté</th>
                            <th style={{ width: "90px" }}>Unité</th>
                            <th className="num" style={{ width: "90px" }}>Poids (kg)</th>
                            <th style={{ width: "130px" }}>Dimensions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {doc.items.map((it, i) => (
                            <tr key={i}>
                                <td>{it.description}</td>
                                <td className="num">{Number(it.quantity).toLocaleString("fr-CA")}</td>
                                <td>{it.unit || "—"}</td>
                                <td className="num">{it.weight_kg ? Number(it.weight_kg).toLocaleString("fr-CA") : "—"}</td>
                                <td>{it.dimensions || "—"}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {doc.total_weight_kg != null && (
                    <div className="print-totals" style={{ width: "40%" }}>
                        <div className="row grand">
                            <span>Poids total</span>
                            <span>{Number(doc.total_weight_kg).toLocaleString("fr-CA")} kg</span>
                        </div>
                    </div>
                )}

                {doc.special_instructions && (
                    <div className="print-notes">
                        <strong>Instructions spéciales :</strong><br />
                        {doc.special_instructions}
                    </div>
                )}

                <div className="print-grid-2" style={{ marginTop: "3rem", gap: "4rem" }}>
                    <div>
                        <div style={{ borderTop: "1px solid #0c182b", paddingTop: "0.5rem", fontSize: "0.75rem", color: "#4b5d7a" }}>
                            Signature de l'expéditeur · Date
                        </div>
                    </div>
                    <div>
                        <div style={{ borderTop: "1px solid #0c182b", paddingTop: "0.5rem", fontSize: "0.75rem", color: "#4b5d7a" }}>
                            Signature du destinataire · Date de réception
                        </div>
                    </div>
                </div>

                <div className="print-footer">
                    <strong>Accord de transport</strong> · La réception de la marchandise atteste de son état apparent satisfaisant. Réserves éventuelles à noter au verso.<br />
                    Contact Portech : info@portech.info
                </div>
            </PrintPageLayout>
        </div>
    );
};

export default AdminPrintBol;
