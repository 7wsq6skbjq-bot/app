import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import CtaBanner from "@/components/CtaBanner";

// SARGENT (ASSA ABLOY) — vraies photos extraites des PDF catalogues officiels.
const C = "/catalogue";

const CATALOG = [
    {
        slug: "poignees-leviers",
        title: "Poignées & leviers",
        sub: "Lever handles · Push pulls — Sargent Studio Collection",
        photos: [
            `${C}/handle-1.png`,
            `${C}/handle-2.png`,
            `${C}/handle-3.png`,
        ],
    },
    {
        slug: "serrures-cylindres",
        title: "Serrures & cylindres",
        sub: "Mortise locks · Cylinders · Deadbolts — Sargent Degree Key System",
        photos: [
            `${C}/lock-1.png`,
            `${C}/lock-2.png`,
            `${C}/lock-3.png`,
        ],
    },
    {
        slug: "barres-antipaniques",
        title: "Barres antipaniques & dispositifs de sortie",
        sub: "Panic devices · Exit hardware — Sargent 5300 Alarmed Exit Device",
        photos: [
            `${C}/panic-1.png`,
            `${C}/panic-2.png`,
            `${C}/panic-3.png`,
        ],
    },
    {
        slug: "ferme-portes",
        title: "Ferme-portes",
        sub: "Door closers · Surface mount · Concealed — Sargent 2300 / 2409 Fire Guard",
        photos: [
            `${C}/closer-1.png`,
            `${C}/closer-2.png`,
            `${C}/closer-3.png`,
        ],
    },
    {
        slug: "controle-acces",
        title: "Contrôle d'accès & multi-points",
        sub: "Multi-point locks · Auto deadlocking — Sargent FM6100",
        photos: [
            `${C}/access-1.png`,
            `${C}/access-2.png`,
            `${C}/access-3.png`,
        ],
    },
    {
        slug: "charnieres-pivots",
        title: "Charnières & pivots",
        sub: "Hinges · Pivots · Continuous hinges — sur demande",
        comingSoon: true,
        photos: [],
    },
];

const BRAND_TAGS = [
    "Adams Rite", "Von Duprin", "Sargent", "LCN", "Schlage",
    "Yale", "Norton", "dormakaba", "Corbin Russwin", "Best",
    "Hager", "Stanley",
];

const Catalogue = () => {
    const [activeCategory, setActiveCategory] = useState(CATALOG[0].slug);
    useEffect(() => { window.scrollTo(0, 0); }, []);

    const active = CATALOG.find((c) => c.slug === activeCategory);

    return (
        <div data-testid="page-catalogue">
            {/* HEADER */}
            <section className="relative bg-[#0c182b] text-white border-b border-[#1e3457] overflow-hidden">
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                <div className="container-portech relative py-16 md:py-20">
                    <Link
                        to="/"
                        data-testid="catalogue-back-home"
                        className="inline-flex items-center gap-2 tech-stamp text-[#97b0d0] hover:text-white transition-colors mb-6"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Retour à l'accueil
                    </Link>
                    <div className="tech-stamp text-[#97b0d0] mb-4">
                        Catalogue · Quincaillerie commerciale
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95] max-w-4xl">
                        Toutes les marques.
                        <br />
                        <span className="text-[#97b0d0]">Toutes les pièces.</span>
                    </h1>
                    <p className="mt-6 max-w-3xl text-lg text-[#b2c3dd] leading-relaxed">
                        Aperçu de la quincaillerie qu'on installe, ajuste et
                        remplace au quotidien. On travaille avec tous les
                        manufacturiers commerciaux reconnus — pas de fournisseur
                        unique, on s'adapte à ce que vous avez ou ce qui sert
                        votre projet.
                    </p>
                    <div className="mt-8 flex flex-wrap gap-2">
                        {BRAND_TAGS.map((b) => (
                            <span
                                key={b}
                                className="tech-stamp px-3 py-1.5 border border-[#1e3457] bg-[#1e3457]/40 text-[#b2c3dd]"
                            >
                                {b}
                            </span>
                        ))}
                    </div>
                </div>
            </section>

            {/* CATEGORY TABS */}
            <section className="bg-white border-b border-[#dde5f0] sticky top-[var(--navbar-h,64px)] z-20">
                <div className="container-portech py-4 overflow-x-auto">
                    <div className="flex gap-2 min-w-max">
                        {CATALOG.map((c) => (
                            <button
                                key={c.slug}
                                data-testid={`catalogue-tab-${c.slug}`}
                                onClick={() => setActiveCategory(c.slug)}
                                className={`tech-stamp px-4 py-2 border transition-colors whitespace-nowrap ${
                                    activeCategory === c.slug
                                        ? "border-[#0c182b] bg-[#0c182b] text-white"
                                        : "border-[#dde5f0] text-[#1e3457] hover:bg-[#f3f6fb]"
                                }`}
                            >
                                {c.title}
                            </button>
                        ))}
                    </div>
                </div>
            </section>

            {/* CONTENT */}
            <section className="bg-white border-b border-[#dde5f0]">
                <div className="container-portech py-16 md:py-20">
                    <div className="mb-10">
                        <h2 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-tight mb-2">
                            {active.title}
                        </h2>
                        <p className="tech-stamp text-[#4b5d7a]">
                            {active.sub}
                        </p>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                        {active.photos.map((src, idx) => (
                            <figure
                                key={src + idx}
                                data-testid={`catalogue-photo-${active.slug}-${idx}`}
                                className="border border-[#dde5f0] overflow-hidden group bg-white"
                            >
                                <img
                                    src={src}
                                    alt={`${active.title} — fiche ${idx + 1}`}
                                    loading="lazy"
                                    className="w-full h-[420px] object-contain bg-white transition-transform duration-500 group-hover:scale-[1.02]"
                                />
                            </figure>
                        ))}
                    </div>

                    {active.comingSoon && (
                        <div
                            data-testid={`catalogue-coming-soon-${active.slug}`}
                            className="border border-dashed border-[#c5d4e7] bg-[#f3f6fb] p-12 text-center"
                        >
                            <div className="tech-stamp text-[#2f4f7f] mb-3">
                                Catalogue · En construction
                            </div>
                            <h3 className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight mb-4 max-w-2xl mx-auto">
                                Charnières et pivots disponibles sur demande
                            </h3>
                            <p className="text-[#4b5d7a] max-w-xl mx-auto mb-6">
                                On finalise la section catalogue. En attendant, contactez-nous : on identifie la pièce exacte qui vous convient (continue, butt, pivot, à billes, électrifiée).
                            </p>
                            <Link
                                to="/contact"
                                data-testid="catalogue-coming-soon-cta"
                                className="btn-primary"
                            >
                                Demander une pièce
                            </Link>
                        </div>
                    )}
                </div>
            </section>

            <CtaBanner
                eyebrow="Une pièce particulière ?"
                title="Dites-nous ce que vous cherchez, on la trouve."
                description="On a des liens directs avec les manufacturiers commerciaux — incluant les pièces discontinuées."
                buttonLabel="Nous contacter"
                buttonTo="/contact"
                testId="catalogue-cta"
            />
        </div>
    );
};

export default Catalogue;
