import { useEffect, useState } from "react";
import { NavLink, Link, useLocation } from "react-router-dom";
import { Menu, X, ArrowUpRight } from "lucide-react";

const links = [
    { to: "/", label: "Accueil" },
    { to: "/services", label: "Services" },
    { to: "/a-propos", label: "À propos" },
    { to: "/contact", label: "Contact" },
];

const Navbar = () => {
    const [open, setOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const location = useLocation();

    useEffect(() => {
        setOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 8);
        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, []);

    return (
        <header
            data-testid="site-navbar"
            className={`sticky top-0 z-50 border-b transition-colors duration-200 ${
                scrolled
                    ? "bg-white/90 backdrop-blur-xl border-zinc-200"
                    : "bg-white border-zinc-200"
            }`}
        >
            <div className="container-portech flex items-center justify-between h-16 md:h-20">
                <Link
                    to="/"
                    data-testid="nav-logo"
                    className="flex items-center gap-3 group"
                >
                    <div className="w-9 h-9 bg-zinc-950 text-white flex items-center justify-center font-display font-bold text-lg tracking-tight group-hover:bg-blue-700 transition-colors">
                        P
                    </div>
                    <div className="flex flex-col leading-tight">
                        <span className="font-display text-lg font-bold tracking-tight uppercase">
                            Portech
                        </span>
                        <span className="tech-stamp text-[10px]">
                            QC / Portes commerciales
                        </span>
                    </div>
                </Link>

                <nav className="hidden md:flex items-center gap-8">
                    {links.map((l) => (
                        <NavLink
                            key={l.to}
                            to={l.to}
                            end={l.to === "/"}
                            data-testid={`nav-link-${l.label.toLowerCase().replace(/\s|à|é/g, "")}`}
                            className={({ isActive }) =>
                                `font-display uppercase tracking-wider text-sm font-semibold transition-colors ${
                                    isActive
                                        ? "text-zinc-950"
                                        : "text-zinc-500 hover:text-zinc-950"
                                }`
                            }
                        >
                            {l.label}
                        </NavLink>
                    ))}
                </nav>

                <div className="hidden md:flex items-center gap-3">
                    <Link
                        to="/contact"
                        data-testid="nav-cta-quote"
                        className="btn-primary !py-3 !px-5 !text-sm"
                    >
                        Demander une soumission
                        <ArrowUpRight className="w-4 h-4" />
                    </Link>
                </div>

                <button
                    type="button"
                    data-testid="nav-mobile-toggle"
                    className="md:hidden p-2 border border-zinc-300"
                    onClick={() => setOpen((v) => !v)}
                    aria-label="Menu"
                >
                    {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
            </div>

            {open && (
                <div
                    data-testid="nav-mobile-menu"
                    className="md:hidden border-t border-zinc-200 bg-white"
                >
                    <div className="container-portech py-6 flex flex-col gap-1">
                        {links.map((l) => (
                            <NavLink
                                key={l.to}
                                to={l.to}
                                end={l.to === "/"}
                                data-testid={`mobile-nav-link-${l.label.toLowerCase().replace(/\s|à|é/g, "")}`}
                                className={({ isActive }) =>
                                    `font-display uppercase tracking-wider text-lg font-semibold py-3 border-b border-zinc-100 ${
                                        isActive ? "text-zinc-950" : "text-zinc-600"
                                    }`
                                }
                            >
                                {l.label}
                            </NavLink>
                        ))}
                        <Link
                            to="/contact"
                            data-testid="mobile-nav-cta"
                            className="btn-primary mt-4 justify-center"
                        >
                            Demander une soumission
                            <ArrowUpRight className="w-4 h-4" />
                        </Link>
                    </div>
                </div>
            )}
        </header>
    );
};

export default Navbar;
