import { X } from "lucide-react";

/** Modal wrapper used by all ERP forms. */
export const Modal = ({ open, onClose, title, testId, children, footer, wide = false }) => {
    if (!open) return null;
    return (
        <div
            data-testid={testId}
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-[100] flex items-start justify-center px-4 py-8 overflow-y-auto"
        >
            <div
                className="absolute inset-0 bg-[#0c182b]/70 backdrop-blur-sm"
                onClick={onClose}
                aria-hidden
            />
            <div className={`relative bg-white border border-[#dde5f0] shadow-2xl w-full ${wide ? "max-w-5xl" : "max-w-2xl"}`}>
                <div className="flex items-center justify-between p-6 border-b border-[#dde5f0] bg-[#0c182b] text-white">
                    <h3 className="font-display font-bold uppercase text-lg tracking-tight">
                        {title}
                    </h3>
                    <button
                        type="button"
                        onClick={onClose}
                        data-testid={`${testId}-close`}
                        aria-label="Fermer"
                        className="w-8 h-8 flex items-center justify-center border border-[#1e3457] hover:bg-white hover:text-[#0c182b] transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
                <div className="p-6">{children}</div>
                {footer && (
                    <div className="p-6 border-t border-[#dde5f0] bg-[#f3f6fb] flex items-center justify-end gap-3">
                        {footer}
                    </div>
                )}
            </div>
        </div>
    );
};

export const Field = ({ label, children, required, className = "" }) => (
    <label className={`block ${className}`}>
        <span className="block tech-stamp mb-1.5">
            {label}
            {required && <span className="text-red-600 ml-1">*</span>}
        </span>
        {children}
    </label>
);

export const inputClass =
    "w-full px-3 py-2 border border-[#c5d4e7] bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] text-sm";
