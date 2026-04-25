import { Search, RefreshCw } from "lucide-react";

export const AdminControls = ({ query, onQueryChange, loading, onRefresh }) => (
    <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between mb-6">
        <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-[#97b0d0] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
                type="text"
                placeholder="Rechercher par nom, courriel, message…"
                value={query}
                onChange={(e) => onQueryChange(e.target.value)}
                data-testid="admin-search"
                className="w-full pl-9 pr-4 py-2.5 border border-[#c5d4e7] bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] text-sm"
            />
        </div>
        <button
            onClick={onRefresh}
            data-testid="admin-refresh"
            className="btn-secondary !py-2.5 !px-4 !text-xs self-start"
        >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Rafraîchir
        </button>
    </div>
);
