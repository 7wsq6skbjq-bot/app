import { Link } from "react-router-dom";
import { ArrowUpRight, MapPin } from "lucide-react";
import { IMG } from "../data";

export const HomeHero = () => (
    <section
        data-testid="home-hero"
        className="relative bg-[#0c182b] text-white overflow-hidden"
    >
        <div
            className="absolute inset-0 bg-cover bg-center opacity-45"
            style={{ backgroundImage: `url(${IMG.hero})` }}
            aria-hidden
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0c182b]/85 via-[#0c182b]/70 to-[#0c182b]" />
        <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />

        <div className="container-portech relative py-24 md:py-36 lg:py-44">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                <div className="lg:col-span-8 reveal">
                    <div className="flex items-center gap-3 tech-stamp text-[#97b0d0] mb-8">
                        <span className="w-8 h-px bg-[#97b0d0]" />
                        Portech · Grand Montréal
                    </div>
                    <h1
                        data-testid="hero-title"
                        className="font-display font-bold uppercase leading-[0.92] tracking-tight text-5xl sm:text-6xl md:text-7xl lg:text-[5.5rem]"
                    >
                        Votre <span className="text-[#97b0d0]">expert</span>
                        <br />
                        en quincaillerie
                        <br />
                        de portes commerciales.
                    </h1>
                    <p className="mt-8 max-w-2xl text-lg md:text-xl text-[#b2c3dd] leading-relaxed">
                        Installation, réparation et modification de
                        quincaillerie pour portes commerciales. On s'occupe des
                        barres antipaniques, ferme-portes, serrures et
                        accessoires — partout dans le Grand Montréal.
                    </p>

                    <div className="mt-10 flex flex-col sm:flex-row gap-4">
                        <Link
                            to="/contact"
                            data-testid="hero-cta-quote"
                            className="btn-primary !bg-white !text-[#0c182b] !border-white hover:!bg-[#97b0d0] hover:!text-[#0c182b] hover:!border-[#97b0d0]"
                        >
                            Demander une soumission
                            <ArrowUpRight className="w-4 h-4" />
                        </Link>
                        <Link
                            to="/services"
                            data-testid="hero-cta-services"
                            className="btn-ghost-dark"
                        >
                            Voir nos services
                        </Link>
                    </div>
                </div>

                <div className="lg:col-span-4 hidden lg:flex flex-col justify-end">
                    <div className="border border-[#1e3457] p-6 bg-[#0c182b]/70 backdrop-blur-sm">
                        <div className="tech-stamp text-[#97b0d0] mb-4">
                            Fiche technique
                        </div>
                        <dl className="space-y-4 text-sm">
                            {[
                                ["Expérience", "10 ans en atelier"],
                                ["Héritage métier", "45 ans transmis"],
                                ["Spécialité", "Installation de quincaillerie"],
                            ].map(([dt, dd], i) => (
                                <div key={dt} className={`flex justify-between ${i < 2 ? "border-b border-[#1e3457] pb-3" : "border-b border-[#1e3457] pb-3"}`}>
                                    <dt className="text-[#b2c3dd]">{dt}</dt>
                                    <dd className="font-display font-bold uppercase">{dd}</dd>
                                </div>
                            ))}
                            <div className="flex justify-between">
                                <dt className="text-[#b2c3dd]">Zone</dt>
                                <dd className="font-display font-bold uppercase flex items-center gap-2">
                                    <MapPin className="w-3.5 h-3.5 text-[#97b0d0]" />
                                    Grand Montréal
                                </dd>
                            </div>
                        </dl>
                    </div>
                </div>
            </div>
        </div>
    </section>
);
