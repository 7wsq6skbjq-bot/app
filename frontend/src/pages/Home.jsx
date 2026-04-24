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
} from "lucide-react";
import CtaBanner from "@/components/CtaBanner";

const HERO_IMG =
    "https://images.unsplash.com/photo-1773291933719-fc02bea5a68f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDR8MHwxfHNlYXJjaHwxfHxjb21tZXJjaWFsJTIwYnVpbGRpbmclMjBlbnRyYW5jZXxlbnwwfHx8fDE3NzcwNTk1Mzd8MA&ixlib=rb-4.1.0&q=85";

const SERVICE_IMG_1 =
    "https://images.unsplash.com/photo-1762431226940-462dec55884d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTF8MHwxfHNlYXJjaHwzfHxtZXRhbCUyMGRvb3IlMjBsb2NrJTIwaGFyZHdhcmV8ZW58MHx8fHwxNzc3MDU5NTI1fDA&ixlib=rb-4.1.0&q=85";

const BEFORE_IMG =
    "https://images.unsplash.com/photo-1763370356214-e4dd692f8697?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTF8MHwxfHNlYXJjaHwyfHxtZXRhbCUyMGRvb3IlMjBsb2NrJTIwaGFyZHdhcmV8ZW58MHx8fHwxNzc3MDU5NTI1fDA&ixlib=rb-4.1.0&q=85";

const AFTER_IMG =
    "https://images.pexels.com/photos/30829651/pexels-photo-30829651.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

const problems = [
    {
        icon: AlertTriangle,
        title: "Porte qui ferme mal",
        desc: "Elle cogne, elle traîne, elle grince. Un problème qui s'aggrave chaque semaine.",
    },
    {
        icon: KeyRound,
        title: "Barre antipaniques difficile",
        desc: "Du personnel qui peine à sortir, des inspections qui tombent à plat.",
    },
    {
        icon: Wrench,
        title: "Serrure mal alignée",
        desc: "Verrouillage qui force, sécurité compromise, usure prématurée des pièces.",
    },
    {
        icon: Timer,
        title: "Appels de service à répétition",
        desc: "Des 'patchs' temporaires qui reviennent hanter votre budget chaque mois.",
    },
];

const services = [
    {
        num: "01",
        title: "Installation de quincaillerie",
        desc: "Barres antipaniques, ferme-portes, serrures commerciales, plaques et accessoires. Alignement au millimètre.",
    },
    {
        num: "02",
        title: "Usinage de portes",
        desc: "Découpe, perçage et modifications précises pour un ajustement parfait. Chaque porte adaptée à son usage exact.",
    },
    {
        num: "03",
        title: "Préparation complète",
        desc: "Achat, modification, installation de la quincaillerie. Portes livrées prêtes à installer, sans surprise.",
    },
    {
        num: "04",
        title: "Ajustement et réparation",
        desc: "Portes qui ne ferment pas, mauvais alignement, pièces mal installées — on corrige rapidement et efficacement.",
    },
];

const benefits = [
    {
        icon: Ruler,
        title: "Travail précis et professionnel",
        desc: "Chaque mesure validée. Chaque coupe vérifiée. Zéro approximation.",
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
];

const testimonials = [
    {
        quote: "Portech a remplacé nos barres antipaniques en une seule matinée. Nos équipes travaillaient le soir même, sans la moindre interruption.",
        author: "Directeur d'exploitation",
        context: "Chaîne de commerces alimentaires · Région de Québec",
    },
    {
        quote: "On a fait venir trois soumissions. Portech était la seule à nous expliquer pourquoi nos portes cognaient depuis deux ans. Résolu en une visite.",
        author: "Gestionnaire d'immeuble",
        context: "Tour à condos · 14 étages",
    },
    {
        quote: "Précision au millimètre. La serrure s'enclenche d'un seul doigt, le ferme-porte est silencieux. On aurait dû les appeler dès le début.",
        author: "Directrice d'école primaire",
        context: "Commission scolaire",
    },
];

const Home = () => {
    return (
        <div data-testid="page-home">
            {/* ============ HERO ============ */}
            <section
                data-testid="home-hero"
                className="relative bg-zinc-950 text-white overflow-hidden"
            >
                <div
                    className="absolute inset-0 bg-cover bg-center opacity-40"
                    style={{ backgroundImage: `url(${HERO_IMG})` }}
                    aria-hidden
                />
                <div className="absolute inset-0 bg-gradient-to-b from-zinc-950/80 via-zinc-950/70 to-zinc-950" />
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />

                <div className="container-portech relative py-24 md:py-36 lg:py-44">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                        <div className="lg:col-span-8 reveal">
                            <div className="flex items-center gap-3 tech-stamp text-zinc-300 mb-8">
                                <span className="w-8 h-px bg-blue-400" />
                                Portech · Installations commerciales QC
                            </div>
                            <h1
                                data-testid="hero-title"
                                className="font-display font-bold uppercase leading-[0.92] tracking-tight text-5xl sm:text-6xl md:text-7xl lg:text-[5.5rem]"
                            >
                                Des portes
                                <br />
                                commerciales
                                <br />
                                <span className="text-blue-400">fiables.</span>{" "}
                                Sans compromis.
                            </h1>
                            <p className="mt-8 max-w-2xl text-lg md:text-xl text-zinc-300 leading-relaxed">
                                Installation et préparation de quincaillerie
                                professionnelle pour commerces, écoles et
                                immeubles. Un travail précis, rapide et
                                durable.
                            </p>

                            <div className="mt-10 flex flex-col sm:flex-row gap-4">
                                <Link
                                    to="/contact"
                                    data-testid="hero-cta-quote"
                                    className="btn-primary !bg-white !text-zinc-950 !border-white hover:!bg-blue-500 hover:!text-white hover:!border-blue-500"
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
                            <div className="border border-zinc-800 p-6 bg-zinc-950/60 backdrop-blur-sm">
                                <div className="tech-stamp text-blue-400 mb-4">
                                    Fiche technique
                                </div>
                                <dl className="space-y-4 text-sm">
                                    <div className="flex justify-between border-b border-zinc-800 pb-3">
                                        <dt className="text-zinc-400">
                                            Expérience
                                        </dt>
                                        <dd className="font-display font-bold uppercase">
                                            10+ ans terrain
                                        </dd>
                                    </div>
                                    <div className="flex justify-between border-b border-zinc-800 pb-3">
                                        <dt className="text-zinc-400">
                                            Héritage métier
                                        </dt>
                                        <dd className="font-display font-bold uppercase">
                                            45 ans transmis
                                        </dd>
                                    </div>
                                    <div className="flex justify-between border-b border-zinc-800 pb-3">
                                        <dt className="text-zinc-400">
                                            Secteurs
                                        </dt>
                                        <dd className="font-display font-bold uppercase">
                                            Commerce · Éducation · Résidentiel
                                        </dd>
                                    </div>
                                    <div className="flex justify-between">
                                        <dt className="text-zinc-400">
                                            Zone de service
                                        </dt>
                                        <dd className="font-display font-bold uppercase">
                                            Québec
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
                className="bg-zinc-100 border-y border-zinc-200 overflow-hidden"
            >
                <div className="py-6 flex overflow-hidden">
                    <div className="marquee-track flex gap-12 whitespace-nowrap pr-12 font-display uppercase text-2xl md:text-3xl font-bold text-zinc-800 tracking-tight">
                        {[...sectors, ...sectors, ...sectors].map((s, i) => (
                            <span key={i} className="flex items-center gap-12">
                                {s}
                                <Minus className="w-6 h-6 text-zinc-400" />
                            </span>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ PROBLEMS ============ */}
            <section
                data-testid="home-problems"
                className="bg-white border-b border-zinc-200"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-16">
                        <div className="lg:col-span-5">
                            <div className="tech-stamp mb-4">
                                01 — Le constat
                            </div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                                Vos portes
                                <br />
                                vous causent
                                <br />
                                des <span className="text-blue-700">problèmes ?</span>
                            </h2>
                        </div>
                        <div className="lg:col-span-6 lg:col-start-7 pt-2">
                            <p className="text-lg leading-relaxed text-zinc-600">
                                Une porte commerciale défectueuse, c'est une
                                perte de temps, d'argent… et parfois un{" "}
                                <span className="text-zinc-950 font-semibold">
                                    risque de sécurité
                                </span>
                                . Voici ce qu'on entend — presque chaque
                                semaine.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-t border-l border-zinc-200">
                        {problems.map((p) => (
                            <div
                                key={p.title}
                                data-testid={`problem-${p.title.toLowerCase().replace(/\s/g, "-")}`}
                                className="border-b border-r border-zinc-200 p-8 hover:bg-zinc-50 transition-colors group"
                            >
                                <div className="w-11 h-11 border border-zinc-300 flex items-center justify-center mb-6 group-hover:border-blue-600 group-hover:text-blue-700 transition-colors">
                                    <p.icon className="w-5 h-5" />
                                </div>
                                <h3 className="font-display font-bold uppercase text-xl tracking-tight mb-3">
                                    {p.title}
                                </h3>
                                <p className="text-zinc-600 text-sm leading-relaxed">
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
                className="bg-zinc-950 text-white border-b border-zinc-900 relative overflow-hidden"
            >
                <div className="absolute inset-0 bg-blueprint-dark opacity-60 pointer-events-none" />
                <div className="container-portech relative py-24 md:py-32">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
                        <div className="lg:col-span-7">
                            <div className="tech-stamp text-zinc-400 mb-4">
                                02 — La solution
                            </div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                                La solution
                                <br />
                                <span className="text-blue-400">Portech</span>.
                            </h2>
                            <div className="mt-8 space-y-5 text-lg md:text-xl text-zinc-300 leading-relaxed max-w-2xl">
                                <p>
                                    Chez Portech, on s'occupe de vos portes
                                    commerciales de <strong className="text-white">A à Z</strong>.
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
                            <div className="border border-zinc-800 relative">
                                <img
                                    src={SERVICE_IMG_1}
                                    alt="Quincaillerie de porte métallique commerciale"
                                    className="w-full h-72 md:h-96 object-cover grayscale"
                                />
                                <div className="absolute top-4 left-4 tech-stamp bg-zinc-950/80 backdrop-blur border border-zinc-800 px-3 py-2">
                                    Spec · 03-A / Serrure commerciale
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ SERVICES GRID ============ */}
            <section
                data-testid="home-services"
                className="bg-white border-b border-zinc-200"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-14">
                        <div>
                            <div className="tech-stamp mb-4">
                                03 — Nos services
                            </div>
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

                    <div className="grid grid-cols-1 md:grid-cols-2 border-t border-l border-zinc-200">
                        {services.map((s) => (
                            <div
                                key={s.num}
                                data-testid={`service-card-${s.num}`}
                                className="border-b border-r border-zinc-200 p-10 flex flex-col group hover:bg-zinc-50 transition-colors"
                            >
                                <div className="flex items-start justify-between mb-6">
                                    <span className="tech-stamp text-blue-700">
                                        {s.num}
                                    </span>
                                    <ArrowUpRight className="w-5 h-5 text-zinc-400 group-hover:text-blue-700 transition-colors" />
                                </div>
                                <h3 className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight mb-4">
                                    {s.title}
                                </h3>
                                <p className="text-zinc-600 leading-relaxed">
                                    {s.desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ WHY PORTECH ============ */}
            <section
                data-testid="home-why"
                className="bg-zinc-50 border-b border-zinc-200"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-16">
                        <div className="lg:col-span-5">
                            <div className="tech-stamp mb-4">
                                04 — Pourquoi nous
                            </div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                                Pourquoi choisir
                                <br />
                                <span className="text-blue-700">Portech</span> ?
                            </h2>
                        </div>
                        <div className="lg:col-span-6 lg:col-start-7 pt-2">
                            <p className="text-lg leading-relaxed text-zinc-600">
                                Parce qu'une porte bien faite, c'est une porte
                                qu'on oublie. Voici ce qui distingue une
                                installation Portech — sur chaque chantier,
                                sans exception.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-zinc-200 border border-zinc-200">
                        {benefits.map((b) => (
                            <div
                                key={b.title}
                                data-testid={`benefit-${b.title.toLowerCase().replace(/\s/g, "-")}`}
                                className="bg-white p-8 flex flex-col"
                            >
                                <b.icon className="w-7 h-7 text-blue-700 mb-6" />
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-3">
                                    {b.title}
                                </h3>
                                <p className="text-zinc-600 text-sm leading-relaxed">
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
                className="bg-white border-b border-zinc-200"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-14">
                        <div className="lg:col-span-6">
                            <div className="tech-stamp mb-4">
                                05 — Transformation
                            </div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                                Avant / Après.
                            </h2>
                        </div>
                        <div className="lg:col-span-5 lg:col-start-8 pt-2">
                            <p className="text-lg leading-relaxed text-zinc-600">
                                On transforme des installations problématiques
                                en systèmes fluides, silencieux et fiables.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 border border-zinc-200">
                        <div className="relative border-b md:border-b-0 md:border-r border-zinc-200">
                            <img
                                src={BEFORE_IMG}
                                alt="Porte commerciale avec installation problématique"
                                className="w-full h-80 md:h-[30rem] object-cover grayscale"
                            />
                            <div className="absolute top-4 left-4 bg-red-600 text-white tech-stamp px-3 py-2 text-[11px]">
                                Avant · Problème
                            </div>
                            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-zinc-950/80 to-transparent p-6">
                                <h3 className="font-display font-bold uppercase text-xl text-white">
                                    Porte qui force, quincaillerie usée
                                </h3>
                            </div>
                        </div>
                        <div className="relative">
                            <img
                                src={AFTER_IMG}
                                alt="Porte commerciale réalisée par Portech"
                                className="w-full h-80 md:h-[30rem] object-cover"
                            />
                            <div className="absolute top-4 left-4 bg-blue-700 text-white tech-stamp px-3 py-2 text-[11px]">
                                Après · Portech
                            </div>
                            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-zinc-950/80 to-transparent p-6">
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
                className="bg-zinc-50 border-b border-zinc-200"
            >
                <div className="container-portech py-24 md:py-32">
                    <div className="mb-14">
                        <div className="tech-stamp mb-4">
                            06 — Retours terrain
                        </div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] max-w-3xl">
                            Ceux qui nous ont fait confiance — et pourquoi ils
                            rappellent.
                        </h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-zinc-200 border border-zinc-200">
                        {testimonials.map((t, i) => (
                            <figure
                                key={i}
                                data-testid={`testimonial-${i}`}
                                className="bg-white p-8 md:p-10 flex flex-col"
                            >
                                <Quote className="w-8 h-8 text-blue-700 mb-6" />
                                <blockquote className="text-zinc-800 leading-relaxed text-base md:text-lg mb-8 flex-1">
                                    {t.quote}
                                </blockquote>
                                <figcaption className="pt-6 border-t border-zinc-200">
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
                description="Arrêtez de perdre du temps avec des ajustements temporaires. Faites faire le travail correctement dès le départ."
                buttonLabel="Demander une soumission"
                buttonTo="/contact"
                variant="dark"
                testId="home-final-cta"
            />
        </div>
    );
};

export default Home;
