import { ArrowLeft, Mail, Phone, Trash2 } from "lucide-react";
import { formatDate } from "./utils";

export const AdminDrawer = ({ submission, onClose, onDelete }) => {
    if (!submission) return null;
    const s = submission;
    const mailto = `mailto:${s.email}?subject=Re: Votre demande Portech&body=Bonjour ${encodeURIComponent(s.name)},%0D%0A%0D%0AMerci pour votre demande.%0D%0A%0D%0A`;

    return (
        <div
            data-testid="admin-drawer"
            className="fixed inset-0 z-50 flex"
            onClick={onClose}
        >
            <div className="flex-1 bg-black/50" />
            <aside
                className="w-full max-w-xl bg-white border-l border-[#dde5f0] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="p-6 border-b border-[#dde5f0] flex items-center justify-between bg-[#0c182b] text-white">
                    <div>
                        <div className="tech-stamp text-[#97b0d0]">Soumission</div>
                        <div className="font-display font-bold uppercase text-xl tracking-tight mt-1">
                            {s.name}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="tech-stamp text-[#97b0d0] hover:text-white transition-colors inline-flex items-center gap-2"
                        data-testid="admin-drawer-close"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" />
                        Fermer
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    <Field label="Courriel">
                        <a href={`mailto:${s.email}`} className="text-[#2f4f7f] hover:text-[#0c182b] transition-colors inline-flex items-center gap-2">
                            <Mail className="w-4 h-4" />
                            {s.email}
                        </a>
                    </Field>
                    <Field label="Téléphone">
                        <a href={`tel:${s.phone}`} className="text-[#2f4f7f] hover:text-[#0c182b] transition-colors inline-flex items-center gap-2">
                            <Phone className="w-4 h-4" />
                            {s.phone}
                        </a>
                    </Field>
                    {s.project_type && (
                        <Field label="Type">
                            <div className="font-display font-semibold uppercase text-sm tracking-tight">
                                {s.project_type}
                            </div>
                        </Field>
                    )}
                    {s.company && (
                        <Field label="Entreprise">
                            <div className="font-display font-semibold uppercase text-sm tracking-tight">
                                {s.company}
                            </div>
                        </Field>
                    )}
                    {s.work_location && (
                        <Field label="Lieu des travaux">
                            <div className="text-[#0c182b]">{s.work_location}</div>
                        </Field>
                    )}
                    <Field label="Reçu le">
                        <div className="text-[#0c182b]">{formatDate(s.created_at)}</div>
                    </Field>
                    <Field label="Message">
                        <div className="border border-[#dde5f0] bg-[#f3f6fb] p-4 whitespace-pre-wrap text-[#1e3457] leading-relaxed">
                            {s.message}
                        </div>
                    </Field>
                    <Field label="Notification email">
                        <div className={`font-display font-semibold uppercase text-sm ${s.email_sent ? "text-[#2f4f7f]" : "text-[#97b0d0]"}`}>
                            {s.email_sent ? "✓ Envoyée avec succès" : "— Non envoyée"}
                        </div>
                    </Field>

                    <div className="pt-6 border-t border-[#dde5f0] flex flex-col sm:flex-row gap-3">
                        <a href={mailto} className="btn-primary !py-2.5 !px-4 !text-xs flex-1 justify-center">
                            <Mail className="w-3.5 h-3.5" />
                            Répondre
                        </a>
                        <button
                            onClick={() => onDelete(s.id)}
                            className="btn-secondary !py-2.5 !px-4 !text-xs !border-red-400 !text-red-600 hover:!bg-red-50 hover:!text-red-700"
                            data-testid="admin-drawer-delete"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                            Supprimer
                        </button>
                    </div>
                </div>
            </aside>
        </div>
    );
};

const Field = ({ label, children }) => (
    <div>
        <div className="tech-stamp mb-2">{label}</div>
        {children}
    </div>
);
