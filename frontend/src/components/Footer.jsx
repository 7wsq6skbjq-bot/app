import { Link } from "react-router-dom";
import { ArrowUpRight, Mail, MapPin, Clock } from "lucide-react";

const Footer = () => {
    return (
        <footer
            data-testid="site-footer"
            className="relative bg-[#0c182b] text-white border-t border-[#1e3457]"
        >
            <div className="bg-blueprint-dark absolute inset-0 pointer-events-none" />
            <div className="container-portech relative py-16 md:py-20">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-8">
                    <div className="md:col-span-5">
                        <img
                            src="/brand/logo-portech-white.png"
                            alt="Portech"
                            className="h-14 w-auto mb-6"
                        />
                        <p className="text-[#b2c3dd] max-w-md leading-relaxed">
                            Installation, réparation et modification de
                            quincaillerie pour portes commerciales. Un travail
                            précis, rapide et durable — partout dans le Grand
                            Montréal.
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
                        <div className="tech-stamp text-[#6485b4] mb-4">
                            Navigation
                        </div>
                        <ul className="space-y-3 font-display uppercase text-sm tracking-wider">
                            <li>
                                <Link to="/" className="text-[#b2c3dd] hover:text-white transition-colors" data-testid="footer-link-home">
                                    Accueil
                                </Link>
                            </li>
                            <li>
                                <Link to="/services" className="text-[#b2c3dd] hover:text-white transition-colors" data-testid="footer-link-services">
                                    Services
                                </Link>
                            </li>
                            <li>
                                <Link to="/a-propos" className="text-[#b2c3dd] hover:text-white transition-colors" data-testid="footer-link-about">
                                    À propos
                                </Link>
                            </li>
                            <li>
                                <Link to="/contact" className="text-[#b2c3dd] hover:text-white transition-colors" data-testid="footer-link-contact">
                                    Contact
                                </Link>
                            </li>
                        </ul>
                    </div>

                    <div className="md:col-span-4">
                        <div className="tech-stamp text-[#6485b4] mb-4">
                            Coordonnées
                        </div>
                        <ul className="space-y-4 text-sm text-[#b2c3dd]">
                            <li className="flex items-start gap-3">
                                <Mail className="w-4 h-4 mt-1 text-[#97b0d0] flex-shrink-0" />
                                <a
                                    href="mailto:portech.infos@gmail.com"
                                    className="hover:text-white transition-colors"
                                    data-testid="footer-email"
                                >
                                    portech.infos@gmail.com
                                </a>
                            </li>
                            <li className="flex items-start gap-3">
                                <MapPin className="w-4 h-4 mt-1 text-[#97b0d0] flex-shrink-0" />
                                <span data-testid="footer-zone">
                                    Grand Montréal — service sur le terrain
                                </span>
                            </li>
                            <li className="flex items-start gap-3">
                                <Clock className="w-4 h-4 mt-1 text-[#97b0d0] flex-shrink-0" />
                                <span>Lundi — vendredi · Réponse sous 24 h ouvrables</span>
                            </li>
                        </ul>
                    </div>
                </div>

                <div className="mt-16 pt-8 border-t border-[#1e3457] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div className="tech-stamp text-[#6485b4]">
                        © {new Date().getFullYear()} Portech · Tous droits réservés
                    </div>
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                        <Link
                            to="/mentions-legales"
                            data-testid="footer-link-legal"
                            className="tech-stamp text-[#6485b4] hover:text-white transition-colors"
                        >
                            Mentions légales · Confidentialité
                        </Link>
                        <span className="tech-stamp text-[#6485b4]">
                            Rigueur · Précision · Durabilité
                        </span>
                        <Link
                            to="/admin/login"
                            data-testid="footer-admin-link"
                            className="tech-stamp text-[#6485b4] hover:text-white transition-colors"
                        >
                            Admin
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
