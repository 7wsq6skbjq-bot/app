import { Link } from "react-router-dom";
import { ArrowUpRight, Mail, Phone, MapPin } from "lucide-react";

const Footer = () => {
    return (
        <footer
            data-testid="site-footer"
            className="relative bg-zinc-950 text-white border-t border-zinc-800"
        >
            <div className="bg-blueprint-dark absolute inset-0 pointer-events-none" />
            <div className="container-portech relative py-16 md:py-20">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-8">
                    <div className="md:col-span-5">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 bg-white text-zinc-950 flex items-center justify-center font-display font-bold text-xl">
                                P
                            </div>
                            <span className="font-display text-2xl font-bold uppercase tracking-tight">
                                Portech
                            </span>
                        </div>
                        <p className="text-zinc-400 max-w-md leading-relaxed">
                            Installation et préparation de quincaillerie
                            professionnelle pour portes commerciales. Un travail
                            précis, rapide et durable.
                        </p>

                        <Link
                            to="/contact"
                            data-testid="footer-cta-quote"
                            className="btn-ghost-dark mt-8"
                        >
                            Demander une soumission
                            <ArrowUpRight className="w-4 h-4" />
                        </Link>
                    </div>

                    <div className="md:col-span-3">
                        <div className="tech-stamp text-zinc-500 mb-4">
                            Navigation
                        </div>
                        <ul className="space-y-3 font-display uppercase text-sm tracking-wider">
                            <li>
                                <Link
                                    to="/"
                                    className="text-zinc-300 hover:text-white transition-colors"
                                    data-testid="footer-link-home"
                                >
                                    Accueil
                                </Link>
                            </li>
                            <li>
                                <Link
                                    to="/services"
                                    className="text-zinc-300 hover:text-white transition-colors"
                                    data-testid="footer-link-services"
                                >
                                    Services
                                </Link>
                            </li>
                            <li>
                                <Link
                                    to="/a-propos"
                                    className="text-zinc-300 hover:text-white transition-colors"
                                    data-testid="footer-link-about"
                                >
                                    À propos
                                </Link>
                            </li>
                            <li>
                                <Link
                                    to="/contact"
                                    className="text-zinc-300 hover:text-white transition-colors"
                                    data-testid="footer-link-contact"
                                >
                                    Contact
                                </Link>
                            </li>
                        </ul>
                    </div>

                    <div className="md:col-span-4">
                        <div className="tech-stamp text-zinc-500 mb-4">
                            Coordonnées
                        </div>
                        <ul className="space-y-4 text-sm text-zinc-300">
                            <li className="flex items-start gap-3">
                                <Phone className="w-4 h-4 mt-1 text-blue-400 flex-shrink-0" />
                                <a
                                    href="tel:+15140000000"
                                    className="hover:text-white transition-colors"
                                    data-testid="footer-phone"
                                >
                                    Sur demande — par soumission
                                </a>
                            </li>
                            <li className="flex items-start gap-3">
                                <Mail className="w-4 h-4 mt-1 text-blue-400 flex-shrink-0" />
                                <a
                                    href="mailto:info@portech.ca"
                                    className="hover:text-white transition-colors"
                                    data-testid="footer-email"
                                >
                                    info@portech.ca
                                </a>
                            </li>
                            <li className="flex items-start gap-3">
                                <MapPin className="w-4 h-4 mt-1 text-blue-400 flex-shrink-0" />
                                <span>Québec — service sur le terrain</span>
                            </li>
                        </ul>
                    </div>
                </div>

                <div className="mt-16 pt-8 border-t border-zinc-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div className="tech-stamp text-zinc-500">
                        © {new Date().getFullYear()} Portech · Tous droits
                        réservés
                    </div>
                    <div className="tech-stamp text-zinc-500">
                        Rigueur · Précision · Durabilité
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
