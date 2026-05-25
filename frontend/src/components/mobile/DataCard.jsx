import { ChevronRight } from "lucide-react";

/**
 * Universal stacked card for mobile lists (replaces table rows).
 * Layout:
 *   [Tech-stamp ID]                                       [Status badge]
 *   [Main title — large]
 *   [Subtitle — muted]
 *   [Footer row: amount / date + quick action icons → arrow]
 *
 * Tap anywhere on the body opens the detail/edit. Quick actions on the right
 * stop propagation so they don't trigger the main tap.
 */
export const DataCard = ({
    stamp,
    title,
    subtitle,
    badge,        // { label, className }
    extraBadge,   // optional second badge under the first
    primary,      // main right-aligned value (amount or date)
    secondary,    // small line under primary
    actions,      // optional list of { icon, onClick, label, color }
    onTap,
    testid,
}) => {
    return (
        <div
            data-testid={testid}
            onClick={onTap}
            className="bg-white border border-[#dde5f0] active:bg-[#f3f6fb] transition-colors p-4"
        >
            <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    {stamp && <div className="tech-stamp text-[#4b5d7a] mb-1">{stamp}</div>}
                    <div className="font-semibold text-[#0c182b] text-base leading-snug truncate">{title}</div>
                    {subtitle && <div className="text-sm text-[#4b5d7a] truncate mt-0.5">{subtitle}</div>}
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                    {badge && (
                        <span className={`tech-stamp px-2 py-1 border whitespace-nowrap text-[10px] ${badge.className}`}>
                            {badge.label}
                        </span>
                    )}
                    {extraBadge && (
                        <span className={`tech-stamp px-2 py-1 border whitespace-nowrap text-[10px] ${extraBadge.className}`}>
                            {extraBadge.label}
                        </span>
                    )}
                </div>
            </div>
            {(primary || actions?.length || onTap) && (
                <div className="flex items-end justify-between mt-3 pt-3 border-t border-[#eef2f7] gap-2">
                    <div>
                        {primary && <div className="font-display font-bold text-lg text-[#0c182b] leading-none">{primary}</div>}
                        {secondary && <div className="text-xs text-[#4b5d7a] mt-1">{secondary}</div>}
                    </div>
                    <div className="flex items-center gap-1.5">
                        {actions?.map((a, i) => {
                            const Icon = a.icon;
                            return (
                                <button
                                    key={i}
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); a.onClick(); }}
                                    data-testid={a.testid}
                                    aria-label={a.label}
                                    className={`w-10 h-10 flex items-center justify-center border ${a.color || "border-[#dde5f0] text-[#2f4f7f] active:bg-[#eaf1fb]"}`}
                                >
                                    <Icon className="w-4 h-4" />
                                </button>
                            );
                        })}
                        {onTap && <ChevronRight className="w-5 h-5 text-[#97b0d0]" />}
                    </div>
                </div>
            )}
        </div>
    );
};
