import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import CtaBanner from "@/components/CtaBanner";

const STOCK = "https://images.unsplash.com/";

// Catalogue catégorisé. Chaque catégorie a 6-8 photos.
const CATALOG = [
    {
        slug: "poignees-leviers",
        title: "Poignées & leviers",
        sub: "Lever handles · Push pulls",
        photos: [
            `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1586864387634-2f33030dab41?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1532550256335-c281a64ac9f6?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1200&q=80`,
        ],
    },
    {
        slug: "serrures-cylindres",
        title: "Serrures & cylindres",
        sub: "Mortise locks · Cylinders · Deadbolts",
        photos: [
            `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1555529902-5261145633bf?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1585914641050-fa9883c4e21c?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1586661615438-349a276d098b?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1677951570313-b0750351c461?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1558002038-1055907df827?auto=format&fit=crop&w=1200&q=80`,
        ],
    },
    {
        slug: "barres-antipaniques",
        title: "Barres antipaniques & dispositifs de sortie",
        sub: "Panic devices · Exit hardware",
        photos: [
            `${STOCK}photo-1592924271903-1e4b1a1ae20f?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1200&q=80`,
        ],
    },
    {
        slug: "ferme-portes",
        title: "Ferme-portes",
        sub: "Door closers · Surface mount · Concealed",
        photos: [
            `${STOCK}photo-1586864387634-2f33030dab41?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1592924271903-1e4b1a1ae20f?auto=format&fit=crop&w=1200&q=80`,
        ],
    },
    {
        slug: "controle-acces",
        title: "Contrôle d'accès",
        sub: "Electronic locks · Card readers · Keypads",
        photos: [
            `${STOCK}photo-1558002038-1055907df827?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1586864387634-2f33030dab41?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1200&q=80`,
        ],
    },
    {
        slug: "charnieres-pivots",
        title: "Charnières & pivots",
        sub: "Hinges · Pivots · Continuous hinges",
        photos: [
            `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1532550256335-c281a64ac9f6?auto=format&fit=crop&w=1200&q=80`,
            `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1200&q=80`,
        ],
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
                                className="border border-[#dde5f0] overflow-hidden group"
                            >
                                <img
                                    src={src}
                                    alt={`${active.title} — pièce ${idx + 1}`}
                                    loading="lazy"
                                    className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                                />
                            </figure>
                        ))}
                    </div>
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
