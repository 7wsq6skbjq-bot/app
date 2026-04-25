import { Inbox, Tag } from "lucide-react";
import { formatDate } from "./utils";

export const AdminTable = ({ rows, isInitialLoading, isEmpty, onSelect }) => {
    let body;
    if (isInitialLoading) {
        body = <div className="p-12 text-center tech-stamp">Chargement…</div>;
    } else if (isEmpty) {
        body = (
            <div data-testid="admin-empty" className="p-12 text-center">
                <Inbox className="w-10 h-10 text-[#97b0d0] mx-auto mb-4" />
                <div className="font-display font-bold uppercase text-xl mb-2">
                    Aucune soumission
                </div>
                <p className="text-[#4b5d7a] text-sm">
                    Les nouvelles demandes apparaîtront ici automatiquement.
                </p>
            </div>
        );
    } else {
        body = (
            <ul>
                {rows.map((s) => (
                    <li
                        key={s.id}
                        data-testid={`admin-submission-${s.id}`}
                        className="border-b border-[#dde5f0] last:border-b-0 hover:bg-[#f3f6fb] transition-colors cursor-pointer"
                        onClick={() => onSelect(s.id)}
                    >
                        <div className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-4 items-center">
                            <div className="md:col-span-3">
                                <div className="font-display font-semibold text-[#0c182b] uppercase text-sm tracking-tight">
                                    {s.name}
                                </div>
                            </div>
                            <div className="md:col-span-3 text-sm text-[#2f4f7f] truncate">
                                {s.email}
                            </div>
                            <div className="md:col-span-2 text-sm text-[#4b5d7a]">
                                {s.phone}
                            </div>
                            <div className="md:col-span-2 text-sm">
                                {s.project_type ? (
                                    <span className="inline-flex items-center gap-1 tech-stamp px-2 py-1 border border-[#dde5f0] bg-[#f3f6fb]">
                                        <Tag className="w-3 h-3" />
                                        {s.project_type}
                                    </span>
                                ) : (
                                    <span className="text-[#97b0d0]">—</span>
                                )}
                            </div>
                            <div className="md:col-span-2 md:text-right tech-stamp text-[#4b5d7a]">
                                {formatDate(s.created_at)}
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
        );
    }

    return (
        <div className="border border-[#dde5f0] bg-white">
            <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#dde5f0] bg-[#f3f6fb] tech-stamp">
                <div className="col-span-3">Nom</div>
                <div className="col-span-3">Courriel</div>
                <div className="col-span-2">Téléphone</div>
                <div className="col-span-2">Type</div>
                <div className="col-span-2 text-right">Reçu</div>
            </div>
            {body}
        </div>
    );
};
