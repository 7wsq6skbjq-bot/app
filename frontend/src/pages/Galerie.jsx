import { useEffect } from "react";
import { useParams, Link, Navigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import CtaBanner from "@/components/CtaBanner";

const P = "/generated/portfolio";

// 100% commercial aluminum door imagery — generated via Nano Banana.
// Each photo is single-use across the entire site.
const CATEGORIES = {
    interventions: {
        eyebrow: "Galerie · 01",
        title: "Intervention & Installation",
        intro:
            "Pose, ajustement et installation de quincaillerie commerciale sur portes en aluminium, en acier ou en verre. Travail propre, alignement au millimètre, finitions sans bavures.",
        photos: [
            { src: `${P}/gal-interv-1.png`, caption: "Pose d'une poignée à levier sur porte commerciale en aluminium" },
            { src: `${P}/gal-interv-2.png`, caption: "Ajustement d'un ferme-porte hydraulique de surface" },
            { src: `${P}/gal-interv-3.png`, caption: "Installation d'une charnière continue à pignons sur porte aluminium" },
            { src: `${P}/gal-interv-4.png`, caption: "Pose d'un cylindre haute sécurité dans une serrure mortaise" },
        ],
    },
    chantiers: {
        eyebrow: "Galerie · 02",
        title: "Chantiers réels — Haut de gamme",
        intro:
            "Quelques projets réalisés sur des portes pivot vitrées, des restaurants gastronomiques, des tours à condos et des sièges sociaux. Pré-assemblage en atelier, livraison sans hésitation.",
        photos: [
            { src: "/uploads/glass-door-hardware.jpg", caption: "Porte pivot vitrée — quincaillerie en cours d'installation" },
            { src: `${P}/gal-chantier-1.png`, caption: "Boutique haut de gamme — porte pivot en verre frameless" },
            { src: `${P}/gal-chantier-2.png`, caption: "Pré-assemblage en atelier — kit complet prêt à poser" },
            { src: `${P}/gal-chantier-3.png`, caption: "Restaurant gastronomique — finition noire avec poignées laiton" },
            { src: `${P}/gal-chantier-4.png`, caption: "Tour à bureaux — devanture aluminium anodisé en lobby" },
        ],
    },
    "dispositifs-sortie": {
        eyebrow: "Galerie · 03",
        title: "Dispositifs de sortie",
        intro:
            "Aussi appelés barres antipaniques ou crash bars : ces dispositifs s'ouvrent d'un simple appui pour permettre l'évacuation rapide en cas d'urgence. Indispensables pour la conformité aux codes du bâtiment.",
        photos: [
            { src: `${P}/gal-exit-1.png`, caption: "Dispositif de sortie rim chromé — porte aluminium simple" },
            { src: `${P}/gal-exit-2.png`, caption: "Tige verticale dissimulée — issue d'auditorium scolaire" },
            { src: `${P}/gal-exit-3.png`, caption: "Tige verticale en surface — corridor d'hôpital" },
            { src: `${P}/gal-exit-4.png`, caption: "Dispositif touchpad chromé — gros plan" },
        ],
    },
    "barres-antipaniques": {
        eyebrow: "Galerie · 04",
        title: "Barres antipaniques",
        intro:
            "Installation, ajustement et remplacement de barres antipaniques sur tous types de portes commerciales. On travaille avec Von Duprin, Sargent, Adams Rite, Yale et plus encore — selon ce qui est déjà en place.",
        photos: [
            { src: `${P}/gal-panic-1.png`, caption: "Barre horizontale fini noir — sortie arrière commerce de détail" },
            { src: `${P}/gal-panic-2.png`, caption: "Barre acier brossé avec dogging — sortie d'urgence cinéma" },
            { src: `${P}/gal-panic-3.png`, caption: "Barre aluminium anodisé — pharmacie" },
            { src: `${P}/gal-panic-4.png`, caption: "Barre électrifiée avec REX — zone sécurisée" },
        ],
    },
    serrures: {
        eyebrow: "Galerie · 05",
        title: "Serrures commerciales",
        intro:
            "Mortaises, cylindriques, électroniques, à carte, à code. On installe, on remplace, on rénove. On travaille avec toutes les marques majeures et on garde des cylindres maître-clé sur stock pour les dépannages rapides.",
        photos: [
            { src: `${P}/gal-lock-1.png`, caption: "Boîtier mortaise inox partiellement exposé — porte aluminium" },
            { src: `${P}/gal-lock-2.png`, caption: "Levier cylindrique fini noir mat — porte de bureau" },
            { src: `${P}/gal-lock-3.png`, caption: "Mortaise électronique à carte — salle sécurisée" },
            { src: `${P}/gal-lock-4.png`, caption: "Mortaise storeroom — entrepôt commercial" },
        ],
    },
};

const Galerie = () => {
    const { category } = useParams();
    const data = CATEGORIES[category];

    useEffect(() => {
        window.scrollTo(0, 0);
    }, [category]);

    if (!data) return <Navigate to="/" replace />;

    return (
        <div data-testid={`page-galerie-${category}`}>
            {/* HEADER */}
            <section className="relative bg-[#0c182b] text-white border-b border-[#1e3457] overflow-hidden">
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                <div className="container-portech relative py-16 md:py-20">
                    <Link
                        to="/"
                        data-testid="galerie-back-home"
                        className="inline-flex items-center gap-2 tech-stamp text-[#97b0d0] hover:text-white transition-colors mb-6"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Retour à l'accueil
                    </Link>
                    <div className="tech-stamp text-[#97b0d0] mb-4">
                        {data.eyebrow}
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95] max-w-4xl">
                        {data.title}
                    </h1>
                    <p className="mt-6 max-w-3xl text-lg text-[#b2c3dd] leading-relaxed">
                        {data.intro}
                    </p>
                </div>
            </section>

            {/* GRID */}
            <section className="bg-white border-b border-[#dde5f0]">
                <div className="container-portech py-16 md:py-24">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {data.photos.map((p) => (
                            <figure
                                key={p.src}
                                className="border border-[#dde5f0] overflow-hidden group"
                            >
                                <div className="overflow-hidden">
                                    <img
                                        src={p.src}
                                        alt={p.caption}
                                        loading="lazy"
                                        className="w-full h-72 object-cover transition-transform duration-500 group-hover:scale-105"
                                    />
                                </div>
                                <figcaption className="p-4 bg-white text-sm text-[#1e3457] leading-snug border-t border-[#dde5f0]">
                                    {p.caption}
                                </figcaption>
                            </figure>
                        ))}
                    </div>
                </div>
            </section>

            <CtaBanner
                eyebrow="Un projet similaire ?"
                title={`Parlons de votre besoin en ${data.title.toLowerCase()}.`}
                description="Soumission gratuite, visite sur place, recommandations honnêtes."
                buttonLabel="Demander une soumission"
                buttonTo="/contact"
                testId="galerie-cta"
            />
        </div>
    );
};

export default Galerie;
