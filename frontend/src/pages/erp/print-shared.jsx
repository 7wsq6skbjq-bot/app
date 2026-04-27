import { ArrowLeft, Printer } from "lucide-react";
import { Link } from "react-router-dom";

/** Standard print page layout — logo, title, actions bar. */
export const PrintPageLayout = ({ title, number, children, statusText, backTo = "/admin/gestion" }) => (
    <div className="print-page">
        <div className="print-actions">
            <Link
                to={backTo}
                className="btn-secondary !py-2 !px-3 !text-xs"
                data-testid="print-back"
            >
                <ArrowLeft className="w-3.5 h-3.5" />
                Retour
            </Link>
            <button
                type="button"
                onClick={() => window.print()}
                data-testid="print-do"
                className="btn-primary !py-2 !px-3 !text-xs"
            >
                <Printer className="w-3.5 h-3.5" />
                Imprimer / PDF
            </button>
        </div>

        <div className="print-header">
            <div>
                <img
                    src="/brand/logo-portech.png"
                    alt="Portech"
                    className="print-logo"
                />
                <div style={{ marginTop: "0.6rem", fontSize: "0.7rem", color: "#4b5d7a", lineHeight: 1.5 }}>
                    Portech · Grand Montréal (QC)<br />
                    info@portech.info · portech.info
                </div>
            </div>
            <div style={{ textAlign: "right" }}>
                <div className="print-title">
                    {title}
                    {statusText && (
                        <span
                            className="print-status-stamp"
                            style={{
                                color: "#2f4f7f",
                                borderColor: "#97b0d0",
                            }}
                        >
                            {statusText}
                        </span>
                    )}
                </div>
                <div className="print-number">{number}</div>
            </div>
        </div>

        {children}
    </div>
);

export const PartyBlock = ({ label, party }) => (
    <div className="print-party-block">
        <div className="lbl">{label}</div>
        <div className="name">{party?.name || "—"}</div>
        <div className="addr">
            {party?.contact && <>{party.contact}<br /></>}
            {party?.address_line1 && <>{party.address_line1}<br /></>}
            {party?.address_line2 && <>{party.address_line2}<br /></>}
            {(party?.city || party?.province || party?.postal_code) && (
                <>
                    {[party?.city, party?.province, party?.postal_code].filter(Boolean).join(" · ")}
                    <br />
                </>
            )}
            {party?.country && party.country !== "Canada" && <>{party.country}<br /></>}
            {party?.phone && <>Tél. {party.phone}<br /></>}
            {party?.email && <>{party.email}<br /></>}
            {party?.tax_number && <>NEQ/TPS : {party.tax_number}</>}
        </div>
    </div>
);

export const MetaBlock = ({ entries }) => (
    <div className="print-meta">
        {entries.map(([lbl, val], i) => (
            <div key={i}>
                <div className="lbl">{lbl}</div>
                <div className="val">{val || "—"}</div>
            </div>
        ))}
    </div>
);
