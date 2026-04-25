import { Link } from "react-router-dom";
import { ExternalLink, LogOut } from "lucide-react";

export const AdminHeader = ({ user, onLogout }) => (
    <header className="bg-[#0c182b] text-white border-b border-[#1e3457]">
        <div className="container-portech flex items-center justify-between h-20">
            <div className="flex items-center gap-6">
                <img
                    src="/brand/logo-portech-white.png"
                    alt="Portech"
                    className="h-10 w-auto"
                />
                <span className="tech-stamp text-[#97b0d0] hidden md:inline">
                    · Tableau de bord
                </span>
            </div>
            <div className="flex items-center gap-4">
                <Link
                    to="/"
                    className="tech-stamp text-[#97b0d0] hover:text-white transition-colors inline-flex items-center gap-2"
                    data-testid="admin-link-site"
                >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Voir le site
                </Link>
                <span className="tech-stamp text-[#97b0d0] hidden md:inline">
                    {user?.username}
                </span>
                <button
                    onClick={onLogout}
                    data-testid="admin-logout"
                    className="inline-flex items-center gap-2 border border-[#1e3457] text-[#b2c3dd] hover:bg-white hover:text-[#0c182b] hover:border-white transition-colors px-4 py-2 font-display uppercase text-xs tracking-wider"
                >
                    <LogOut className="w-3.5 h-3.5" />
                    Déconnexion
                </button>
            </div>
        </div>
    </header>
);
