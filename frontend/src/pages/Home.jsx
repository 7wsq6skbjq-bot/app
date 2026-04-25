import { Link } from "react-router-dom";
import {
    ArrowUpRight,
    AlertTriangle,
    KeyRound,
    Wrench,
    Timer,
    ShieldCheck,
    Ruler,
    CheckCircle2,
    Quote,
    Minus,
    MapPin,
} from "lucide-react";
import CtaBanner from "@/components/CtaBanner";

// 100% commercial aluminum door imagery — generated via Nano Banana.
// Each image is used in EXACTLY ONE place across the entire site.
const P = "/generated/portfolio";
const IMG = {
    // Hero
    hero:        `${P}/home-hero.png`,
    // Showcase tiles (5 unique)
    hands:       `${P}/home-showcase-tech.png`,        // Intervention · Installation
    luxuryGlass: `${P}/home-luxury-glass.png`,         // Chantier réel · Haut de gamme
    exitDevice:  `${P}/home-showcase-exit.png`,        // Dispositif de sortie
    panicBar:    `${P}/home-showcase-panic.png`,       // Barre antipanique
    lockCloseup: `${P}/home-showcase-lock.png`,        // Serrure
    // Services tiles (6 unique — different from showcase)
    serviceInstall:  `${P}/home-service-installation.png`,
    serviceMachine:  `${P}/home-service-machining.png`,
    serviceRepair:   `${P}/home-service-repair.png`,
    serviceUpgrade:  `${P}/home-service-upgrade.png`,
    serviceConsult:  `${P}/home-showcase-storefront.png`,   // catalogue/consult
    serviceInspect:  "/generated/precision-install.png",   // existing — caliper precision shot
    // Solution grid (single use)
    grid:        `${P}/home-grid-components.png`,
    // Clients (4 unique)
    restaurant:  `${P}/home-client-restaurant.png`,
    school:      `${P}/home-client-school.png`,
    condo:       `${P}/home-client-condo.png`,
    entrance:    `${P}/home-client-office.png`,
};

const problems = [
    {
        icon: AlertTriangle,
        title: "Porte qui ferme mal",
        desc: "Elle cogne, elle traîne, elle grince. Un problème qui s'aggrave chaque semaine.",
    },
    {
        icon: KeyRound,
        title: "Barre antipanique difficile",
        desc: "Du personnel qui peine à sortir, des inspections qui tombent à plat.",
    },
    {
        icon: Wrench,
        title: "Serrure mal alignée",
        desc: "Verrouillage qui force, sécurité compromise, usure prématurée des pièces.",
    },
    {
        icon: Timer,
        title: "Appels de service en boucle",
        desc: "Des « patchs » temporaires qui reviennent hanter votre budget chaque mois.",
    },
];

const services = [
    {
        num: "01",
        title: "Installation de quincaillerie",
        desc: "Barres antipaniques, ferme-portes, serrures commerciales, plaques et accessoires. Alignement au millimètre.",
        img: IMG.serviceInstall,
    },
    {
        num: "02",
        title: "Modification & usinage",
        desc: "Préparation, perçage et ajustement de vos portes existantes pour accueillir une nouvelle quincaillerie.",
        img: IMG.serviceMachine,
    },
    {
        num: "03",
        title: "Réparation ciblée",
        desc: "On intervient sur une porte qui force, une serrure qui coince, un ferme-porte qui claque. On règle à la source.",
        img: IMG.serviceRepair,
    },
    {
        num: "04",
        title: "Mise à niveau & remplacement",
        desc: "Remplacement de pièces usées par des équivalents commerciaux robustes, conformes aux codes du bâtiment.",
        img: IMG.serviceUpgrade,
    },
    {
        num: "05",
        title: "Consultation pour vitreries",
        desc: "Accompagnement des vitriers dans le choix et l'achat de la quincaillerie : compatibilité, normes, fournisseurs. Vous vendez la porte, on sécurise la ferrure.",
        img: IMG.serviceConsult,
    },
    {
        num: "06",
        title: "Inspection & rapport d'expertise",
        desc: "Avant que vous livriez le projet à votre client, on inspecte le travail des sous-traitants en quincaillerie et on remet un rapport d'expertise détaillé.",
        img: IMG.serviceInspect,
    },
];

const benefits = [
    {
        icon: Ruler,
        title: "Travail précis",
        desc: "Chaque mesure validée, chaque coupe vérifiée. Zéro approximation.",
    },
    {
        icon: ShieldCheck,
        title: "Installation durable",
        desc: "On n'applique pas de patch temporaire. On règle le problème à la source.",
    },
    {
        icon: Timer,
        title: "Rapidité d'exécution",
        desc: "Planification serrée, intervention ciblée. On respecte vos opérations.",
    },
    {
        icon: CheckCircle2,
        title: "Expertise terrain réelle",
        desc: "Plus de 10 ans sur le chantier, aux côtés de 45 ans de métier transmis.",
    },
];

const sectors = [
    "Commerces",
    "Restaurants",
    "Écoles",
    "Tours à condos",
    "Bureaux",
    "Boulangeries",
    "Épiceries",
    "Boucheries",
    "Pharmacies",
    "Cliniques",
    "Cinémas",
    "Banques",
    "Dépanneurs",
];

const BRAND_STYLE_MAP = {
    italic: "italic",
    condensed: "tracking-tighter",
    wide: "tracking-widest",
    block: "",
};

const brands = [
    { name: "Adams Rite", style: "italic" },
    { name: "Von Duprin", style: "condensed" },
    { name: "Sargent", style: "wide" },
    { name: "LCN", style: "block" },
    { name: "Schlage", style: "italic" },
    { name: "Yale", style: "block" },
    { name: "Norton", style: "wide" },
    { name: "dormakaba", style: "condensed" },
    { name: "Corbin Russwin", style: "italic" },
    { name: "Best", style: "block" },
    { name: "Hager", style: "wide" },
    { name: "Stanley", style: "condensed" },
];

const testimonials = [
    {
        quote: "Trois portes coupe-feu coincées au sous-sol, on n'arrivait plus à les fermer correctement depuis l'été. Cédrick est venu, a démonté les ferme-portes, ajusté les pivots. Tout fonctionne. Première fois en 2 ans qu'on n'a pas un appel par semaine pour les portes.",
        author: "Mario L.",
        context: "Concierge en chef · Tour de bureaux Côte-de-Liesse",
    },
    {
        quote: "30 étages, condos haut de gamme rue Peel. On avait 2 vitriers en place pour le verre, mais la quincaillerie sur les portes pivot du lobby c'est lui qui a fait la job. Pré-assemblé en atelier, posé en une journée, alignement nickel.",
        author: "Patrick D.",
        context: "Surintendant · Tour à condos · Rue Peel, Montréal",
    },
    {
        quote: "Notre barre antipanique de la sortie d'urgence côté ruelle s'enclenchait pas. Inspection des pompiers dans 5 jours, on stressait. Cédrick est passé le lendemain matin, ajustement, nettoyage du loquet. On a passé l'inspection sans correctif.",
        author: "Marie-Pier T.",
        context: "Gérante · Pharmacie · Plateau Mont-Royal",
    },
    {
        quote: "On gère 14 écoles primaires. Quand un cylindre brise ou qu'une serrure de classe se grippe, faut que ça se règle vite. Avec Portech on appelle, et c'est fait dans la semaine, parfois la journée. Pas de drame, pas de devis en 4 pages.",
        author: "Sylvain B.",
        context: "Coordonnateur entretien · Centre de services scolaire de Laval",
    },
    {
        quote: "Restaurant, portes pivots sur mesure, le client avait dépensé une fortune. Quatre vitriers ont reculé sur la quincaillerie. Cédrick a accepté, a fait le préassemblage chez lui, livré une fermeture parfaite. Aucune marque sur le cadre. Je l'appelle pour le prochain projet, c'est sûr.",
        author: "Jean-François M.",
        context: "Designer-architecte · Restaurant gastronomique · Vieux-Montréal",
    },
    {
        quote: "Cinéma 8 salles, ouverture en 2 semaines, 12 portes coupe-feu et 2 sorties d'urgence à régler. Cédrick est venu un dimanche, a tout aligné, vérifié la conformité. On a passé l'inspection lundi sans une remarque. Sauveur.",
        author: "Daniel R.",
        context: "Chargé de projet · Complexe cinématographique · Brossard",
    },
];

const Home = () => {
    return (
        <div data-testid="page-home">
            {/* ============ HERO ============ */}
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
                                quincaillerie pour portes commerciales. On
                                s'occupe des barres antipaniques, ferme-portes,
                                serrures et accessoires — partout dans le Grand
                                Montréal.
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
                                    <div className="flex justify-between border-b border-[#1e3457] pb-3">
                                        <dt className="text-[#b2c3dd]">
                                            Expérience
                                        </dt>
                                        <dd className="font-display font-bold uppercase">
                                            10+ ans terrain
                                        </dd>
                                    </div>
                                    <div className="flex justify-between border-b border-[#1e3457] pb-3">
                                        <dt className="text-[#b2c3dd]">
                                            Héritage métier
                                        </dt>
                                        <dd className="font-display font-bold uppercase">
                                            45 ans transmis
                                        </dd>
                                    </div>
                                    <div className="flex justify-between border-b border-[#1e3457] pb-3">
                                        <dt className="text-[#b2c3dd]">
                                            Spécialité
                                        </dt>
                                        <dd className="font-display font-bold uppercase">
                                            Installation de quincaillerie
                                        </dd>
                                    </div>
                                    <div className="flex justify-between">
                                        <dt className="text-[#b2c3dd]">
                                            Zone
                                        </dt>
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

            {/* ============ MARQUEE SECTORS ============ */}
            <section
                data-testid="home-sectors"
                className="bg-[#f3f6fb] border-y border-[#dde5f0] overflow-hidden"
            >
                <div className="py-6 flex overflow-hidden">
                    <div className="marquee-track flex gap-12 whitespace-nowrap pr-12 font-display uppercase text-2xl md:text-3xl font-bold text-[#1e3457] tracking-tight">
                        {[...sectors, ...sectors, ...sectors].map((s, i) => (
                            <span key={`${s}-${i}`} className="flex items-center gap-12">
                                {s}
                                <Minus className="w-6 h-6 text-[#97b0d0]" />
                            </span>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ IMAGE SHOWCASE (3-col asymmetric) ============ */}
            <section
                data-testid="home-showcase"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                        <Link
                            to="/galerie/interventions"
                            data-testid="showcase-interventions"
                            className="md:col-span-5 md:row-span-2 relative overflow-hidden border border-[#dde5f0] group cursor-pointer"
                        >
                            <img
                                src={IMG.hands}
                                alt="Technicien installant de la quincaillerie sur une porte commerciale"
                                className="w-full h-full min-h-[26rem] object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Intervention · Installation
                            </div>
                            <div className="absolute bottom-4 right-4 bg-[#0c182b] text-white tech-stamp px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                Voir la galerie →
                            </div>
                        </Link>
                        <Link
                            to="/galerie/chantiers"
                            data-testid="showcase-chantiers"
                            className="md:col-span-4 relative overflow-hidden border border-[#dde5f0] group cursor-pointer"
                        >
                            <img
                                src={IMG.luxuryGlass}
                                alt="Installation de quincaillerie sur porte pivot vitrée haut de gamme"
                                className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Chantier réel · Haut de gamme
                            </div>
                            <div className="absolute bottom-4 right-4 bg-[#0c182b] text-white tech-stamp px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                Voir la galerie →
                            </div>
                        </Link>
                        <Link
                            to="/galerie/dispositifs-sortie"
                            data-testid="showcase-exit-device"
                            className="md:col-span-3 relative overflow-hidden border border-[#dde5f0] group cursor-pointer"
                        >
                            <img
                                src={IMG.exitDevice}
                                alt="Dispositif de sortie sur porte commerciale"
                                className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Dispositif de sortie
                            </div>
                            <div className="absolute bottom-4 right-4 bg-[#0c182b] text-white tech-stamp px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                Voir →
                            </div>
                        </Link>
                        <Link
                            to="/galerie/barres-antipaniques"
                            data-testid="showcase-panic-bar"
                            className="md:col-span-4 relative overflow-hidden border border-[#dde5f0] group cursor-pointer"
                        >
                            <img
                                src={IMG.panicBar}
                                alt="Barre antipanique commerciale"
                                className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Barre antipanique
                            </div>
                            <div className="absolute bottom-4 right-4 bg-[#0c182b] text-white tech-stamp px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                Voir →
                            </div>
                        </Link>
                        <Link
                            to="/galerie/serrures"
                            data-testid="showcase-lock"
                            className="md:col-span-3 relative overflow-hidden border border-[#dde5f0] group cursor-pointer"
                        >
                            <img
                                src={IMG.lockCloseup}
                                alt="Serrure commerciale"
                                className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Serrure
                            </div>
                            <div className="absolute bottom-4 right-4 bg-[#0c182b] text-white tech-stamp px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                Voir →
                            </div>
                        </Link>
                    </div>
                </div>
            </section>

            {/* ============ BRANDS WALL ============ */}
            <section
                data-testid="home-brands"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-16 md:py-20">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-10">
                        <div className="lg:col-span-5">
                            <div className="tech-stamp mb-4">
                                Toutes les marques
                            </div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-3xl md:text-4xl leading-[0.95]">
                                On travaille avec
                                <br />
                                <span className="text-[#2f4f7f]">toutes les marques</span>
                                <br />
                                de quincaillerie.
                            </h2>
                        </div>
                        <div className="lg:col-span-6 lg:col-start-7 pt-2">
                            <p className="text-lg leading-relaxed text-[#4b5d7a]">
                                Pas de fournisseur unique, pas de marque
                                imposée. On installe, ajuste et répare la
                                quincaillerie de tous les manufacturiers
                                commerciaux reconnus — du{" "}
                                <strong className="text-[#0c182b]">haut de gamme</strong>{" "}
                                au standard, peu importe ce qui est déjà sur
                                vos portes.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                        {brands.map((b) => (
                            <Link
                                key={b.name}
                                to="/catalogue"
                                data-testid={`brand-${b.name.toLowerCase().replace(/\s+/g, "-")}`}
                                className="bg-white p-6 md:p-8 flex items-center justify-center min-h-[110px] group hover:bg-[#f3f6fb] transition-colors"
                            >
                                <span
                                    className={`font-display font-bold uppercase text-lg md:text-xl tracking-tight text-[#0c182b] group-hover:text-[#2f4f7f] transition-colors text-center ${BRAND_STYLE_MAP[b.style] || ""}`}
                                >
                                    {b.name}
                                </span>
                            </Link>
                        ))}
                    </div>

                    <p className="mt-8 text-sm text-[#4b5d7a] italic">
                        * Cliquez sur une marque pour voir notre catalogue de quincaillerie. Liste non exhaustive — on adapte à ce que vous avez, ou on recommande la meilleure option pour votre besoin.
                    </p>
                </div>
            </section>

            {/* ============ PROBLEMS ============ */}
            <section
                data-testid="home-problems"
                className="bg-[#f3f6fb] border-b border-[#dde5f0]"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-16">
                        <div className="lg:col-span-5">
                            <div className="tech-stamp mb-4">01 — Le constat</div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                                Vos portes
                                <br />
                                vous causent
                                <br />
                                des <span className="text-[#2f4f7f]">problèmes ?</span>
                            </h2>
                        </div>
                        <div className="lg:col-span-6 lg:col-start-7 pt-2">
                            <p className="text-lg leading-relaxed text-[#4b5d7a]">
                                Une quincaillerie défectueuse, c'est une perte
                                de temps, d'argent… et parfois un{" "}
                                <span className="text-[#0c182b] font-semibold">
                                    risque de sécurité
                                </span>
                                . Voici ce qu'on entend — presque chaque
                                semaine.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-t border-l border-[#dde5f0] bg-white">
                        {problems.map((p) => (
                            <div
                                key={p.title}
                                data-testid={`problem-${p.title.toLowerCase().replace(/\s/g, "-")}`}
                                className="border-b border-r border-[#dde5f0] p-8 hover:bg-[#f3f6fb] transition-colors group"
                            >
                                <div className="w-11 h-11 border border-[#c5d4e7] flex items-center justify-center mb-6 group-hover:border-[#1e3457] group-hover:text-[#1e3457] transition-colors">
                                    <p.icon className="w-5 h-5" />
                                </div>
                                <h3 className="font-display font-bold uppercase text-xl tracking-tight mb-3">
                                    {p.title}
                                </h3>
                                <p className="text-[#4b5d7a] text-sm leading-relaxed">
                                    {p.desc}
                                </p>
                            </div>
                        ))}
                    </div>

                    <div className="mt-12">
                        <Link
                            to="/contact"
                            data-testid="problems-cta"
                            className="btn-primary"
                        >
                            On règle ça rapidement
                            <ArrowUpRight className="w-4 h-4" />
                        </Link>
                    </div>
                </div>
            </section>

            {/* ============ SOLUTION ============ */}
            <section
                data-testid="home-solution"
                className="bg-[#0c182b] text-white border-b border-[#1e3457] relative overflow-hidden"
            >
                <div className="absolute inset-0 bg-blueprint-dark opacity-60 pointer-events-none" />
                <div className="container-portech relative py-24 md:py-32">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
                        <div className="lg:col-span-7">
                            <div className="tech-stamp text-[#97b0d0] mb-4">
                                02 — La solution
                            </div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                                La solution
                                <br />
                                <span className="text-[#97b0d0]">Portech</span>.
                            </h2>
                            <div className="mt-8 space-y-5 text-lg md:text-xl text-[#b2c3dd] leading-relaxed max-w-2xl">
                                <p>
                                    Chez Portech, on s'occupe de votre
                                    quincaillerie de portes commerciales{" "}
                                    <strong className="text-white">de A à Z</strong>.
                                </p>
                                <p>
                                    On ne fait pas juste installer des pièces.
                                </p>
                                <p>
                                    On prépare des portes{" "}
                                    <strong className="text-white">
                                        prêtes à performer dès le jour 1
                                    </strong>
                                    .
                                </p>
                            </div>
                        </div>

                        <div className="lg:col-span-5">
                            <div className="border border-[#1e3457] relative">
                                <img
                                    src={IMG.grid}
                                    alt="Grille de composants de quincaillerie commerciale"
                                    className="w-full h-72 md:h-96 object-cover"
                                />
                                <div className="absolute top-4 left-4 tech-stamp bg-[#0c182b]/85 backdrop-blur border border-[#1e3457] px-3 py-2">
                                    Catalogue · Composants
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ SERVICES GRID ============ */}
            <section
                data-testid="home-services"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-14">
                        <div>
                            <div className="tech-stamp mb-4">03 — Nos services</div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95]">
                                Nos services
                            </h2>
                        </div>
                        <Link
                            to="/services"
                            data-testid="services-see-all"
                            className="btn-secondary self-start md:self-auto"
                        >
                            Voir tous les services
                            <ArrowUpRight className="w-4 h-4" />
                        </Link>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 border-t border-l border-[#dde5f0]">
                        {services.map((s) => (
                            <div
                                key={s.num}
                                data-testid={`service-card-${s.num}`}
                                className="border-b border-r border-[#dde5f0] group hover:bg-[#f3f6fb] transition-colors overflow-hidden"
                            >
                                <div className="relative h-56 overflow-hidden border-b border-[#dde5f0]">
                                    <img
                                        src={s.img}
                                        alt={s.title}
                                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                                    />
                                </div>
                                <div className="p-8">
                                    <div className="flex items-start justify-between mb-4">
                                        <span className="tech-stamp text-[#2f4f7f]">
                                            {s.num}
                                        </span>
                                        <ArrowUpRight className="w-5 h-5 text-[#97b0d0] group-hover:text-[#1e3457] transition-colors" />
                                    </div>
                                    <h3 className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight mb-4">
                                        {s.title}
                                    </h3>
                                    <p className="text-[#4b5d7a] leading-relaxed">
                                        {s.desc}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ CLIENT TYPES (with images) ============ */}
            <section
                data-testid="home-clients"
                className="bg-[#f3f6fb] border-b border-[#dde5f0]"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="mb-14 max-w-3xl">
                        <div className="tech-stamp mb-4">04 — Nos clients</div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95]">
                            Là où la quincaillerie doit tenir, on est là.
                        </h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[
                            { img: IMG.restaurant, label: "Restaurants & commerces", sub: "Horaires serrés, zéro arrêt toléré." },
                            { img: IMG.school, label: "Écoles & institutions", sub: "Sécurité et conformité aux codes du bâtiment." },
                            { img: IMG.condo, label: "Tours à condos", sub: "Portes lourdes, trafic constant, fini haut de gamme." },
                            { img: IMG.entrance, label: "Bureaux & commerces", sub: "Image professionnelle, fonctionnement silencieux." },
                        ].map((c) => (
                            <div
                                key={c.label}
                                className="group border border-[#dde5f0] bg-white overflow-hidden"
                            >
                                <div className="relative h-56 overflow-hidden">
                                    <img
                                        src={c.img}
                                        alt={c.label}
                                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                                    />
                                </div>
                                <div className="p-6">
                                    <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2">
                                        {c.label}
                                    </h3>
                                    <p className="text-[#4b5d7a] text-sm leading-relaxed">
                                        {c.sub}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ WHY PORTECH ============ */}
            <section
                data-testid="home-why"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-16">
                        <div className="lg:col-span-5">
                            <div className="tech-stamp mb-4">05 — Pourquoi nous</div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                                Pourquoi choisir
                                <br />
                                <span className="text-[#2f4f7f]">Portech</span> ?
                            </h2>
                        </div>
                        <div className="lg:col-span-6 lg:col-start-7 pt-2">
                            <p className="text-lg leading-relaxed text-[#4b5d7a]">
                                Parce qu'une quincaillerie bien posée, c'est
                                une porte qu'on oublie. Voici ce qui distingue
                                une intervention Portech — sur chaque chantier,
                                sans exception.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                        {benefits.map((b) => (
                            <div
                                key={b.title}
                                data-testid={`benefit-${b.title.toLowerCase().replace(/\s/g, "-")}`}
                                className="bg-white p-8 flex flex-col"
                            >
                                <b.icon className="w-7 h-7 text-[#2f4f7f] mb-6" />
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-3">
                                    {b.title}
                                </h3>
                                <p className="text-[#4b5d7a] text-sm leading-relaxed">
                                    {b.desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ TESTIMONIALS ============ */}
            <section
                data-testid="home-testimonials"
                className="bg-[#f3f6fb] border-b border-[#dde5f0]"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="mb-14">
                        <div className="tech-stamp mb-4">06 — Retours terrain</div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] max-w-3xl">
                            Ceux qui nous ont fait confiance — et pourquoi ils rappellent.
                        </h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                        {testimonials.map((t) => (
                            <figure
                                key={`${t.author}-${t.context}`}
                                data-testid={`testimonial-${t.context.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}
                                className="bg-white p-8 md:p-10 flex flex-col"
                            >
                                <Quote className="w-8 h-8 text-[#2f4f7f] mb-6" />
                                <blockquote className="text-[#1e3457] leading-relaxed text-base md:text-lg mb-8 flex-1">
                                    {t.quote}
                                </blockquote>
                                <figcaption className="pt-6 border-t border-[#dde5f0]">
                                    <div className="font-display font-bold uppercase text-sm tracking-wider">
                                        {t.author}
                                    </div>
                                    <div className="tech-stamp mt-1">
                                        {t.context}
                                    </div>
                                </figcaption>
                            </figure>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ FINAL CTA ============ */}
            <CtaBanner
                eyebrow="07 — Passons à l'action"
                title="Besoin d'une porte qui fonctionne vraiment ?"
                description="Arrêtez de perdre du temps avec des ajustements temporaires. Faites faire le travail correctement dès le départ — Grand Montréal."
                buttonLabel="Demander une soumission"
                buttonTo="/contact"
                variant="dark"
                testId="home-final-cta"
            />
        </div>
    );
};

export default Home;
