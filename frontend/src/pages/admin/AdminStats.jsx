import { Inbox, Calendar, Mail } from "lucide-react";

export const AdminStats = ({ stats, submissions }) => (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-[#dde5f0] bg-[#dde5f0] mb-10">
        <div className="bg-white p-6" data-testid="stat-total">
            <div className="flex items-center gap-3 mb-4">
                <Inbox className="w-5 h-5 text-[#2f4f7f]" />
                <span className="tech-stamp">Total</span>
            </div>
            <div className="font-display font-bold text-5xl tracking-tight">
                {stats.total}
            </div>
        </div>
        <div className="bg-white p-6" data-testid="stat-30d">
            <div className="flex items-center gap-3 mb-4">
                <Calendar className="w-5 h-5 text-[#2f4f7f]" />
                <span className="tech-stamp">30 derniers jours</span>
            </div>
            <div className="font-display font-bold text-5xl tracking-tight">
                {stats.last_30_days}
            </div>
        </div>
        <div className="bg-white p-6" data-testid="stat-reachable">
            <div className="flex items-center gap-3 mb-4">
                <Mail className="w-5 h-5 text-[#2f4f7f]" />
                <span className="tech-stamp">Courriel envoyé</span>
            </div>
            <div className="font-display font-bold text-5xl tracking-tight">
                {submissions.filter((s) => s.email_sent).length}
                <span className="text-[#97b0d0] text-lg ml-2">
                    / {submissions.length}
                </span>
            </div>
        </div>
    </div>
);
