import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, ArrowUpRight, X } from "lucide-react";
import CtaBanner from "@/components/CtaBanner";

// Vraies photos extraites des PDF catalogues officiels (Sargent, Hager, Von Duprin).
const C = "/catalogue";
const PDF = "/catalogue/pdf";

const CATALOG = [
    {
        slug: "poignees-leviers",
        title: "Poignées & leviers",
        sub: "Lever handles · Push pulls — Sargent Studio Collection",
        photos: [`${C}/handle-1.png`, `${C}/handle-2.png`, `${C}/handle-3.png`],
        pdf: { href: `${PDF}/sargent-studio-collection.pdf`, label: "Sargent · Studio Collection (45 MB)" },
    },
    {
        slug: "serrures-cylindres",
        title: "Serrures & cylindres",
        sub: "Mortise locks · Cylinders · Deadbolts — Sargent Degree Key System",
        photos: [`${C}/lock-1.png`, `${C}/lock-2.png`, `${C}/lock-3.png`],
        pdf: { href: `${PDF}/sargent-degree-key-system.pdf`, label: "Sargent · Degree Key System (5 MB)" },
    },
    {
        slug: "barres-antipaniques",
        title: "Barres antipaniques & dispositifs de sortie",
        sub: "Panic devices · Exit hardware — Sargent 5300 Alarmed Exit Device",
        photos: [`${C}/panic-1.png`, `${C}/panic-2.png`, `${C}/panic-3.png`],
        pdf: { href: `${PDF}/sargent-5300-alarmed-exit.pdf`, label: "Sargent · 5300 Series Alarmed Exit (2 MB)" },
    },
    {
        slug: "ferme-portes",
        title: "Ferme-portes",
        sub: "Door closers · Surface mount · Concealed — Sargent 2300 / 2409 Fire Guard",
        photos: [`${C}/closer-1.png`, `${C}/closer-2.png`, `${C}/closer-3.png`],
        pdf: { href: `${PDF}/sargent-2300-2409-fire-guard.pdf`, label: "Sargent · 2300 / 2409 Fire Guard (4 MB)" },
    },
    {
        slug: "controle-acces",
        title: "Contrôle d'accès",
        sub: "Electric strikes · Electrified locks — Von Duprin Electrical Security",
        photos: [`${C}/access-1.png`, `${C}/access-2.png`, `${C}/access-3.png`],
        pdf: { href: `${PDF}/von-duprin-electrical-security.pdf`, label: "Von Duprin · Electrical Security (7 MB)" },
    },
    {
        slug: "charnieres-pivots",
        title: "Charnières & pivots",
        sub: "Hinges · Pivots · Continuous hinges — Hager Commercial Hinges",
        photos: [`${C}/hinge-1.png`, `${C}/hinge-2.png`, `${C}/hinge-3.png`],
        pdf: { href: `${PDF}/hager-commercial-hinges.pdf`, label: "Hager · Commercial Hinges (1 MB)" },
    },
];

const BRAND_TAGS = [
    "Adams Rite", "Von Duprin", "Sargent", "LCN", "Schlage",
    "Yale", "Norton", "dormakaba", "Corbin Russwin", "Best",
    "Hager", "Stanley",
];

const Catalogue = () => {
    const [activeCategory, setActiveCategory] = useState(CATALOG[0].slug);
    const [leadModal, setLeadModal] = useState(null); // null | category object
    useEffect(() => { window.scrollTo(0, 0); }, []);

    const active = CATALOG.find((c) => c.slug === activeCategory);

    // Trigger PDF download AND open the lead-capture modal
    const handlePdfDownload = (cat) => {
        // Trigger download programmatically
        const a = document.createElement("a");
        a.href = cat.pdf.href;
        a.download = cat.pdf.href.split("/").pop();
        document.body.appendChild(a);
        a.click();
        a.remove();
        // Open modal
        setLeadModal(cat);
    };

    // Close on Escape
    useEffect(() => {
        if (!leadModal) return;
        const onKey = (e) => { if (e.key === "Escape") setLeadModal(null); };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [leadModal]);

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
                    <div className="mb-10 flex flex-col md:flex-row md:items-end md:justify-between gap-6">
                        <div>
                            <h2 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-tight mb-2">
                                {active.title}
                            </h2>
                            <p className="tech-stamp text-[#4b5d7a]">
                                {active.sub}
                            </p>
                        </div>
                        {active.pdf && (
                            <button
                                type="button"
                                onClick={() => handlePdfDownload(active)}
                                data-testid={`catalogue-pdf-${active.slug}`}
                                className="btn-secondary self-start md:self-auto whitespace-nowrap"
                            >
                                <Download className="w-4 h-4" />
                                Télécharger la fiche PDF
                            </button>
                        )}
                    </div>
                    {active.pdf && (
                        <p className="-mt-6 mb-10 text-xs text-[#4b5d7a]">
                            Source : {active.pdf.label}
                        </p>
                    )}

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

            {/* ============ LEAD-CAPTURE MODAL (triggered after PDF download) ============ */}
            {leadModal && (
                <div
                    data-testid="catalogue-lead-modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="lead-modal-title"
                    className="fixed inset-0 z-[100] flex items-center justify-center px-4 animate-in fade-in duration-200"
                >
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-[#0c182b]/70 backdrop-blur-sm"
                        onClick={() => setLeadModal(null)}
                        aria-hidden
                    />
                    {/* Card */}
                    <div className="relative bg-white border border-[#dde5f0] shadow-2xl max-w-lg w-full p-8 md:p-10">
                        <button
                            type="button"
                            onClick={() => setLeadModal(null)}
                            data-testid="lead-modal-close"
                            aria-label="Fermer"
                            className="absolute top-4 right-4 w-9 h-9 flex items-center justify-center border border-[#dde5f0] hover:bg-[#f3f6fb] transition-colors"
                        >
                            <X className="w-4 h-4 text-[#0c182b]" />
                        </button>

                        <div className="tech-stamp text-[#2f4f7f] mb-4">
                            Téléchargement démarré · {leadModal.title}
                        </div>
                        <h3
                            id="lead-modal-title"
                            className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight leading-[1.05] mb-4"
                        >
                            Vous étudiez un projet&nbsp;?
                        </h3>
                        <p className="text-[#4b5d7a] leading-relaxed mb-6">
                            Pendant que vous parcourez la fiche, on peut déjà
                            préparer votre soumission. Décrivez-nous votre besoin
                            en {leadModal.title.toLowerCase()} — on revient sous{" "}
                            <strong className="text-[#0c182b]">24 h</strong>{" "}
                            avec un prix précis et des recommandations honnêtes.
                        </p>

                        <div className="flex flex-col sm:flex-row gap-3">
                            <Link
                                to={`/contact?categorie=${encodeURIComponent(leadModal.title)}`}
                                onClick={() => setLeadModal(null)}
                                data-testid="lead-modal-cta"
                                className="btn-primary"
                            >
                                Demander une soumission
                                <ArrowUpRight className="w-4 h-4" />
                            </Link>
                            <button
                                type="button"
                                onClick={() => setLeadModal(null)}
                                data-testid="lead-modal-dismiss"
                                className="btn-secondary"
                            >
                                Plus tard
                            </button>
                        </div>

                        <p className="mt-6 text-xs text-[#4b5d7a] italic">
                            Soumission gratuite · Aucun engagement · Grand Montréal
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Catalogue;
