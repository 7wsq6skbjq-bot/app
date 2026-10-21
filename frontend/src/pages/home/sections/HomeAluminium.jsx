import { Link } from "react-router-dom";
import { ArrowUpRight, CheckCircle2 } from "lucide-react";

const A = "/generated/aluminium";

const points = [
    "Séries AT1000 & AT2000",
    "Modèles isolés à bris thermique",
    "Simples, doubles & sur mesure",
    "Préparées avec leur quincaillerie",
];

export const HomeAluminium = () => (
    <section
        data-testid="home-aluminium"
        className="bg-[#0c182b] text-white border-b border-[#1e3457] relative overflow-hidden"
    >
        <div className="bg-blueprint-dark absolute inset-0 pointer-events-none" />
        <div className="container-portech relative py-24 md:py-32">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                <div className="lg:col-span-6">
                    <div className="tech-stamp text-[#97b0d0] mb-4">
                        Nouveau — Produit
                    </div>
                    <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95] mb-6">
                        Portes commerciales en aluminium.
                    </h2>
                    <p className="text-lg text-[#b2c3dd] leading-relaxed mb-8 max-w-xl">
                        On ne fait plus que la quincaillerie : on fabrique et
                        fournit maintenant la porte au complet. Robuste, isolée,
                        sur mesure — préparée pour recevoir exactement la bonne
                        quincaillerie.
                    </p>
                    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-10">
                        {points.map((p) => (
                            <li key={p} className="flex gap-3 text-[#dbe5f2]">
                                <CheckCircle2 className="w-5 h-5 text-[#97b0d0] flex-shrink-0 mt-0.5" />
                                <span>{p}</span>
                            </li>
                        ))}
                    </ul>
                    <Link
                        to="/portes-aluminium"
                        data-testid="home-aluminium-cta"
                        className="btn-ghost-dark"
                    >
                        Découvrir nos portes
                        <ArrowUpRight className="w-4 h-4" />
                    </Link>
                </div>
                <div className="lg:col-span-6">
                    <div className="relative overflow-hidden border border-[#1e3457] group">
                        <img
                            src={`${A}/alu-home.png`}
                            alt="Portes commerciales en aluminium Portech"
                            className="w-full h-[380px] object-cover transition-transform duration-500 group-hover:scale-105"
                        />
                    </div>
                </div>
            </div>
        </div>
    </section>
);
