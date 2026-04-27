import { Field, inputClass } from "./Modal";
import { PROVINCES } from "../utils";

/**
 * PartyForm — shared fields for a customer or supplier.
 * Controlled component: receives `value`, emits `onChange(next)`.
 */
export const PartyForm = ({ value, onChange, hideKind = false, compact = false }) => {
    const set = (k, v) => onChange({ ...value, [k]: v });
    return (
        <div className="space-y-4">
            {!hideKind && (
                <Field label="Type">
                    <select
                        value={value.kind}
                        onChange={(e) => set("kind", e.target.value)}
                        className={inputClass}
                    >
                        <option value="customer">Client</option>
                        <option value="supplier">Fournisseur</option>
                    </select>
                </Field>
            )}
            <Field label="Raison sociale / Nom" required>
                <input
                    type="text"
                    value={value.name || ""}
                    onChange={(e) => set("name", e.target.value)}
                    className={inputClass}
                    data-testid="party-name"
                    required
                />
            </Field>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Personne contact">
                    <input type="text" value={value.contact || ""} onChange={(e) => set("contact", e.target.value)} className={inputClass} />
                </Field>
                <Field label="Courriel">
                    <input type="email" value={value.email || ""} onChange={(e) => set("email", e.target.value)} className={inputClass} />
                </Field>
                <Field label="Téléphone">
                    <input type="tel" value={value.phone || ""} onChange={(e) => set("phone", e.target.value)} className={inputClass} />
                </Field>
                <Field label="Numéro de taxe (NEQ / TPS)">
                    <input type="text" value={value.tax_number || ""} onChange={(e) => set("tax_number", e.target.value)} className={inputClass} />
                </Field>
            </div>
            <Field label="Adresse ligne 1">
                <input type="text" value={value.address_line1 || ""} onChange={(e) => set("address_line1", e.target.value)} className={inputClass} />
            </Field>
            {!compact && (
                <Field label="Adresse ligne 2">
                    <input type="text" value={value.address_line2 || ""} onChange={(e) => set("address_line2", e.target.value)} className={inputClass} />
                </Field>
            )}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Field label="Ville">
                    <input type="text" value={value.city || ""} onChange={(e) => set("city", e.target.value)} className={inputClass} />
                </Field>
                <Field label="Province">
                    <select value={value.province || "QC"} onChange={(e) => set("province", e.target.value)} className={inputClass}>
                        {PROVINCES.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                </Field>
                <Field label="Code postal">
                    <input type="text" value={value.postal_code || ""} onChange={(e) => set("postal_code", e.target.value)} className={inputClass} />
                </Field>
                <Field label="Pays">
                    <input type="text" value={value.country || "Canada"} onChange={(e) => set("country", e.target.value)} className={inputClass} />
                </Field>
            </div>
            {!compact && (
                <Field label="Notes">
                    <textarea rows={2} value={value.notes || ""} onChange={(e) => set("notes", e.target.value)} className={inputClass} />
                </Field>
            )}
        </div>
    );
};
