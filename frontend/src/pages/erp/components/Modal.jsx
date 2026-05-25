import { X } from "lucide-react";

/** Modal wrapper used by all ERP forms. Mobile-optimized: full-screen sheet on small screens, centered modal on md+. */
export const Modal = ({ open, onClose, title, testId, children, footer, wide = false }) => {
    if (!open) return null;
    return (
        <div
            data-testid={testId}
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-[100] flex items-stretch md:items-start md:justify-center md:px-4 md:py-8 md:overflow-y-auto"
        >
            <div
                className="absolute inset-0 bg-[#0c182b]/70 backdrop-blur-sm"
                onClick={onClose}
                aria-hidden
            />
            <div className={`relative bg-white border-0 md:border md:border-[#dde5f0] shadow-2xl w-full h-full md:h-auto flex flex-col md:block ${wide ? "md:max-w-5xl" : "md:max-w-2xl"}`}>
                <div className="flex items-center justify-between p-4 md:p-6 border-b border-[#dde5f0] bg-[#0c182b] text-white shrink-0" style={{ paddingTop: "max(env(safe-area-inset-top, 0px), 1rem)" }}>
                    <h3 className="font-display font-bold uppercase text-base md:text-lg tracking-tight pr-3 truncate">
                        {title}
                    </h3>
                    <button
                        type="button"
                        onClick={onClose}
                        data-testid={`${testId}-close`}
                        aria-label="Fermer"
                        className="w-10 h-10 md:w-8 md:h-8 shrink-0 flex items-center justify-center border border-[#1e3457] hover:bg-white hover:text-[#0c182b] transition-colors"
                    >
                        <X className="w-5 h-5 md:w-4 md:h-4" />
                    </button>
                </div>
                <div className="p-4 md:p-6 overflow-y-auto flex-1 md:flex-none">{children}</div>
                {footer && (
                    <div
                        className="p-4 md:p-6 border-t border-[#dde5f0] bg-[#f3f6fb] flex items-center justify-end gap-3 shrink-0 sticky md:static bottom-0"
                        style={{ paddingBottom: "max(env(safe-area-inset-bottom, 0px), 1rem)" }}
                    >
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
    "w-full px-3 py-2.5 md:py-2 min-h-[44px] md:min-h-0 border border-[#c5d4e7] bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] text-base md:text-sm";
