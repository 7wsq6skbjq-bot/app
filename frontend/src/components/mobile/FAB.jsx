import { Plus } from "lucide-react";

/**
 * Floating Action Button for primary contextual action on mobile (hidden on md+).
 * Positioned above the MobileTabBar via bottom-[88px].
 */
export const FAB = ({ onClick, label, icon: Icon = Plus, testid }) => (
    <button
        type="button"
        onClick={onClick}
        data-testid={testid}
        aria-label={label}
        className="md:hidden fixed right-5 bottom-[88px] z-40 w-14 h-14 bg-[#0c182b] text-white shadow-xl border-2 border-[#0c182b] active:scale-95 transition-transform flex items-center justify-center"
        style={{ marginBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
        <Icon className="w-6 h-6" strokeWidth={2.5} />
    </button>
);
