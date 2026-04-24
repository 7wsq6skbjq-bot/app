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

const IMG = {
    hero: "/generated/hero-doors.png",
    panic: "/generated/panic-bar.png",
    closer: "/generated/door-closer.png",
    lock: "/generated/commercial-lock.png",
    hands: "/generated/technician-hands.png",
    tools: "/generated/workshop-tools.png",
    entrance: "/generated/commercial-entrance.png",
    school: "/generated/school-corridor.png",
    before: "/generated/before-problem.png",
    after: "/generated/after-fixed.png",
    condo: "/generated/condo-lobby.png",
    grid: "/generated/hardware-grid.png",
    restaurant: "/generated/restaurant-door.png",
    precision: "/generated/precision-install.png",
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
        img: IMG.panic,
    },
    {
        num: "02",
        title: "Modification & usinage",
        desc: "Préparation, perçage et ajustement de vos portes existantes pour accueillir une nouvelle quincaillerie.",
        img: IMG.tools,
    },
    {
        num: "03",
        title: "Réparation ciblée",
        desc: "On intervient sur une porte qui force, une serrure qui coince, un ferme-porte qui claque. On règle à la source.",
        img: IMG.closer,
    },
    {
        num: "04",
        title: "Mise à niveau & remplacement",
        desc: "Remplacement de pièces usées par des équivalents commerciaux robustes, conformes aux codes du bâtiment.",
        img: IMG.lock,
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
];

const testimonials = [
    {
        quote: "Portech a remplacé nos barres antipaniques en une seule matinée. Nos équipes travaillaient le soir même, sans la moindre interruption.",
        author: "Directeur d'exploitation",
        context: "Chaîne de commerces alimentaires · Grand Montréal",
    },
    {
        quote: "On a fait venir trois soumissions. Portech était la seule à nous expliquer pourquoi nos portes cognaient depuis deux ans. Résolu en une visite.",
        author: "Gestionnaire d'immeuble",
        context: "Tour à condos · 14 étages",
    },
    {
        quote: "Précision au millimètre. La serrure s'enclenche d'un seul doigt, le ferme-porte est silencieux. On aurait dû les appeler dès le début.",
        author: "Directrice d'école primaire",
        context: "Commission scolaire · Laval",
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
                                            Quincaillerie
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
                            <span key={i} className="flex items-center gap-12">
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
                        <div className="md:col-span-5 md:row-span-2 relative overflow-hidden border border-[#dde5f0] group">
                            <img
                                src={IMG.hands}
                                alt="Technicien installant de la quincaillerie sur une porte commerciale"
                                className="w-full h-full min-h-[26rem] object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Intervention · Installation
                            </div>
                        </div>
                        <div className="md:col-span-4 relative overflow-hidden border border-[#dde5f0] group">
                            <img
                                src={IMG.precision}
                                alt="Mesure de précision"
                                className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Mesure · Ajustement
                            </div>
                        </div>
                        <div className="md:col-span-3 relative overflow-hidden border border-[#dde5f0] group">
                            <img
                                src={IMG.tools}
                                alt="Outils de précision"
                                className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Atelier
                            </div>
                        </div>
                        <div className="md:col-span-4 relative overflow-hidden border border-[#dde5f0] group">
                            <img
                                src={IMG.panic}
                                alt="Barre antipanique commerciale"
                                className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Barre antipanique
                            </div>
                        </div>
                        <div className="md:col-span-3 relative overflow-hidden border border-[#dde5f0] group">
                            <img
                                src={IMG.lock}
                                alt="Serrure commerciale"
                                className="w-full h-64 object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                                Serrure
                            </div>
                        </div>
                    </div>
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
                            { img: IMG.school, label: "Écoles & institutions", sub: "Sécurité et conformité codes du bâtiment." },
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

            {/* ============ BEFORE / AFTER ============ */}
            <section
                data-testid="home-before-after"
                className="bg-[#f3f6fb] border-b border-[#dde5f0]"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-14">
                        <div className="lg:col-span-6">
                            <div className="tech-stamp mb-4">06 — Transformation</div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                                Avant / Après.
                            </h2>
                        </div>
                        <div className="lg:col-span-5 lg:col-start-8 pt-2">
                            <p className="text-lg leading-relaxed text-[#4b5d7a]">
                                On transforme des installations problématiques
                                en systèmes fluides, silencieux et fiables.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 border border-[#dde5f0]">
                        <div className="relative border-b md:border-b-0 md:border-r border-[#dde5f0]">
                            <img
                                src={IMG.before}
                                alt="Quincaillerie endommagée, avant intervention Portech"
                                className="w-full h-80 md:h-[30rem] object-cover"
                            />
                            <div className="absolute top-4 left-4 bg-[#b91c1c] text-white tech-stamp px-3 py-2 text-[11px]">
                                Avant · Problème
                            </div>
                            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#0c182b]/85 to-transparent p-6">
                                <h3 className="font-display font-bold uppercase text-xl text-white">
                                    Quincaillerie usée, alignement perdu
                                </h3>
                            </div>
                        </div>
                        <div className="relative">
                            <img
                                src={IMG.after}
                                alt="Installation neuve réalisée par Portech"
                                className="w-full h-80 md:h-[30rem] object-cover"
                            />
                            <div className="absolute top-4 left-4 bg-[#1e3457] text-white tech-stamp px-3 py-2 text-[11px]">
                                Après · Portech
                            </div>
                            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#0c182b]/85 to-transparent p-6">
                                <h3 className="font-display font-bold uppercase text-xl text-white">
                                    Alignement parfait, fermeture silencieuse
                                </h3>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ TESTIMONIALS ============ */}
            <section
                data-testid="home-testimonials"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="mb-14">
                        <div className="tech-stamp mb-4">07 — Retours terrain</div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] max-w-3xl">
                            Ceux qui nous ont fait confiance — et pourquoi ils rappellent.
                        </h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                        {testimonials.map((t, i) => (
                            <figure
                                key={i}
                                data-testid={`testimonial-${i}`}
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
                eyebrow="08 — Passons à l'action"
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
