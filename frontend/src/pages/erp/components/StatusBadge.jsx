import { STATUS_BADGE, STATUS_DOT } from "../utils";

/** Shared ERP status pill — colored dot + label, blueprint styling. */
export const StatusBadge = ({ status, className = "", testId }) => (
    <span
        data-testid={testId}
        className={`inline-flex items-center gap-1.5 tech-stamp px-2 py-1 border ${STATUS_BADGE[status] || "border-[#dde5f0]"} ${className}`}
    >
        <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status] || "bg-[#8aa0bd]"}`} />
        {status}
    </span>
);

export default StatusBadge;
