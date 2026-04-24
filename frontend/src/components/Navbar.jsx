import { useEffect, useState } from "react";
import { NavLink, Link, useLocation } from "react-router-dom";
import { Menu, X, ArrowUpRight } from "lucide-react";

const links = [
    { to: "/", label: "Accueil", slug: "accueil" },
    { to: "/services", label: "Services", slug: "services" },
    { to: "/a-propos", label: "À propos", slug: "apropos" },
    { to: "/contact", label: "Contact", slug: "contact" },
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
                    ? "bg-white/95 backdrop-blur-xl border-[#dde5f0]"
                    : "bg-white border-[#dde5f0]"
            }`}
        >
            <div className="container-portech flex items-center justify-between h-20 md:h-24">
                <Link
                    to="/"
                    data-testid="nav-logo"
                    className="flex items-center group"
                >
                    <img
                        src="/brand/logo-portech.png"
                        alt="Portech — quincaillerie de portes commerciales"
                        className="h-12 md:h-16 w-auto"
                    />
                </Link>

                <nav className="hidden md:flex items-center gap-10">
                    {links.map((l) => (
                        <NavLink
                            key={l.to}
                            to={l.to}
                            end={l.to === "/"}
                            data-testid={`nav-link-${l.slug}`}
                            className={({ isActive }) =>
                                `font-display uppercase tracking-wider text-sm font-semibold transition-colors ${
                                    isActive
                                        ? "text-[#162842]"
                                        : "text-[#4b5d7a] hover:text-[#162842]"
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
                    className="md:hidden p-2 border border-[#dde5f0]"
                    onClick={() => setOpen((v) => !v)}
                    aria-label="Menu"
                >
                    {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
            </div>

            {open && (
                <div
                    data-testid="nav-mobile-menu"
                    className="md:hidden border-t border-[#dde5f0] bg-white"
                >
                    <div className="container-portech py-6 flex flex-col gap-1">
                        {links.map((l) => (
                            <NavLink
                                key={l.to}
                                to={l.to}
                                end={l.to === "/"}
                                data-testid={`mobile-nav-link-${l.slug}`}
                                className={({ isActive }) =>
                                    `font-display uppercase tracking-wider text-lg font-semibold py-3 border-b border-[#eef2f8] ${
                                        isActive ? "text-[#162842]" : "text-[#4b5d7a]"
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
