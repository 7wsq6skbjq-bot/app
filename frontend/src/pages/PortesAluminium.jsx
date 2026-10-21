import { Link } from "react-router-dom";
import {
    ArrowUpRight,
    CheckCircle2,
    ShieldCheck,
    Thermometer,
    Gauge,
    Ruler,
    Layers,
    DoorOpen,
    PanelsTopLeft,
    Palette,
} from "lucide-react";
import CtaBanner from "@/components/CtaBanner";
import { useSeo } from "@/hooks/use-seo";

const A = "/generated/aluminium";

const gammes = [
    {
        num: "01",
        tag: "AT1000",
        title: "Série AT1000 — profil étroit",
        img: `${A}/alu-at1000.webp`,
        desc:
            "Notre porte d'entrée commerciale polyvalente. Profilés d'aluminium étroits qui maximisent le vitrage, pour commerces, bureaux et entrées à trafic standard.",
        points: [
            "Cadre anodisé clair ou fini au choix",
            "Grande surface vitrée, allure moderne",
            "Idéale pour devantures et commerces",
        ],
    },
    {
        num: "02",
        tag: "AT2000",
        title: "Série AT2000 — robuste, fort trafic",
        img: `${A}/alu-at2000.webp`,
        desc:
            "Profilés larges et renforcés pour les entrées à fort achalandage : écoles, institutions, édifices publics. Conçue pour recevoir barre antipanique et ferme-porte lourds.",
        points: [
            "Montants larges et rail inférieur renforcé",
            "Supporte la quincaillerie commerciale lourde",
            "Durabilité maximale, usage intensif",
        ],
    },
    {
        num: "03",
        tag: "ISOLÉES",
        title: "Portes isolées — bris thermique",
        img: `${A}/alu-isolee.webp`,
        desc:
            "Aluminium à rupture de pont thermique avec vitrage thermos double. Réduit les pertes de chaleur et la condensation — parfait pour les entrées chauffées et le climat québécois.",
        points: [
            "Rupture de pont thermique intégrée",
            "Vitrage thermos (double) isolant",
            "Efficacité énergétique accrue",
        ],
    },
    {
        num: "04",
        tag: "SIMPLES & DOUBLES",
        title: "Portes simples et doubles",
        img: `${A}/alu-double.webp`,
        desc:
            "Configuration simple ou double, avec imposte et latéraux vitrés au besoin. Mains MD, MG, MDR ou MGR — on fabrique selon le sens d'ouverture exact de votre ouverture.",
        points: [
            "Simple, double, avec imposte ou latéraux",
            "Mains MD / MG / MDR / MGR",
            "Adaptée à votre ouverture existante",
        ],
    },
    {
        num: "05",
        tag: "SUR MESURE",
        title: "Fabrication sur mesure",
        img: `${A}/alu-surmesure.webp`,
        desc:
            "Dimensions hors norme, ouvertures grand format, configurations particulières : on dessine, on fabrique et on prépare la porte avec sa quincaillerie, prête à être posée.",
        points: [
            "Dimensions et formes sur mesure",
            "Dessins de production fournis",
            "Préparée avec sa quincaillerie",
        ],
    },
];

const avantages = [
    {
        icon: ShieldCheck,
        title: "Sécurité commerciale",
        desc: "Conçue pour recevoir serrures mortaise, barres antipaniques et contrôle d'accès.",
    },
    {
        icon: Thermometer,
        title: "Efficacité énergétique",
        desc: "Options à rupture de pont thermique et vitrage thermos pour le climat d'ici.",
    },
    {
        icon: Gauge,
        title: "Durabilité extrême",
        desc: "L'aluminium ne rouille pas, ne gauchit pas et traverse les années sans entretien lourd.",
    },
    {
        icon: Palette,
        title: "Finis variés",
        desc: "Anodisé clair, bronze, noir mat ou peinture poudre — selon votre image de marque.",
    },
];

const configs = [
    {
        icon: DoorOpen,
        label: "Mains d'ouverture",
        value: "MD · MG · MDR · MGR",
    },
    {
        icon: Layers,
        label: "Vitrage",
        value: "Simple ou thermos (double)",
    },
    {
        icon: PanelsTopLeft,
        label: "Configurations",
        value: "Simple · double · imposte · latéraux",
    },
    {
        icon: Ruler,
        label: "Dimensions",
        value: "Standard ou sur mesure",
    },
];

const PortesAluminium = () => {
    useSeo({
        title: "Portes commerciales en aluminium · Fabrication sur mesure AT1000, AT2000 & isolées | Portech",
        description:
            "Portech fabrique et fournit des portes commerciales en aluminium : séries AT1000, AT2000, portes isolées à bris thermique, simples et doubles, sur mesure. Préparées avec leur quincaillerie. Grand Montréal, Laval, Rive-Sud et Rive-Nord.",
        canonical: "https://portech.info/portes-aluminium",
    });

    return (
        <div data-testid="page-portes-aluminium">
            {/* ============ HERO ============ */}
            <section
                data-testid="alu-hero"
                className="relative bg-[#0c182b] text-white overflow-hidden border-b border-[#1e3457]"
            >
                <div
                    className="absolute inset-0 bg-cover bg-center opacity-60"
                    style={{ backgroundImage: `url(${A}/alu-hero.webp)` }}
                    aria-hidden
                />
                <div className="absolute inset-0 bg-gradient-to-b from-[#0c182b]/70 via-[#0c182b]/75 to-[#0c182b]/95" />
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />

                <div className="container-portech relative py-24 md:py-36">
                    <div className="tech-stamp text-[#97b0d0] mb-6">
                        Produit — Portes en aluminium
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-5xl md:text-6xl lg:text-7xl leading-[0.92] max-w-4xl">
                        Portes commerciales en aluminium — fabriquées pour durer.
                    </h1>
                    <p className="mt-8 max-w-2xl text-lg md:text-xl text-[#b2c3dd] leading-relaxed">
                        On ne fait pas qu'installer la quincaillerie : on fournit
                        maintenant la porte au complet. Séries AT1000 et AT2000,
                        modèles isolés, simples ou doubles, standard ou sur
                        mesure — préparés avec leur quincaillerie, prêts à être
                        posés.
                    </p>
                    <div className="mt-10 flex flex-wrap gap-4">
                        <Link
                            to="/contact?produit=aluminium"
                            data-testid="alu-hero-cta"
                            className="btn-ghost-dark"
                        >
                            Demander une soumission
                            <ArrowUpRight className="w-4 h-4" />
                        </Link>
                        <a
                            href="#gammes"
                            data-testid="alu-hero-gammes"
                            className="inline-flex items-center gap-2 font-display font-bold uppercase tracking-tight text-sm text-white/90 hover:text-white border border-[#1e3457] px-6 py-4 transition-colors"
                        >
                            Voir les gammes
                        </a>
                    </div>
                    <div className="mt-10 flex flex-wrap gap-3">
                        {[
                            "AT1000",
                            "AT2000",
                            "Isolées / bris thermique",
                            "Simples & doubles",
                            "Sur mesure",
                        ].map((chip) => (
                            <span
                                key={chip}
                                className="tech-stamp px-4 py-2 border border-[#1e3457] text-[#b2c3dd]"
                            >
                                {chip}
                            </span>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ INTRO / VALUE ============ */}
            <section
                data-testid="alu-intro"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-20 md:py-28 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                    <div className="lg:col-span-6">
                        <div className="tech-stamp mb-4 text-[#2f4f7f]">
                            Pourquoi l'aluminium
                        </div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] mb-6">
                            La porte idéale pour le commercial.
                        </h2>
                        <p className="text-lg text-[#1e3457] leading-relaxed mb-5">
                            L'aluminium est le matériau de référence pour les
                            entrées commerciales : léger, rigide, insensible à la
                            corrosion et taillé pour recevoir la quincaillerie
                            lourde. Il traverse les hivers sans gauchir ni
                            rouiller.
                        </p>
                        <p className="text-[#4b5d7a] leading-relaxed">
                            Comme c'est aussi notre spécialité côté quincaillerie,
                            on vous livre un ensemble cohérent : la bonne porte,
                            préparée pour la bonne serrure, le bon ferme-porte et
                            la bonne barre antipanique — du premier coup.
                        </p>
                    </div>
                    <div className="lg:col-span-6">
                        <div className="relative overflow-hidden border border-[#dde5f0]">
                            <img loading="lazy" decoding="async"
                                src={`${A}/alu-gal1.webp`}
                                alt="Portes commerciales en aluminium installées à l'entrée d'un commerce"
                                className="w-full h-80 object-cover"
                            />
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ GAMMES ============ */}
            <section
                id="gammes"
                data-testid="alu-gammes"
                className="bg-[#f3f6fb] border-b border-[#dde5f0] scroll-mt-24"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="mb-14">
                        <div className="tech-stamp mb-4">Nos gammes</div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] max-w-3xl">
                            Une porte pour chaque type d'ouverture.
                        </h2>
                    </div>

                    <div className="space-y-px bg-[#dde5f0] border border-[#dde5f0]">
                        {gammes.map((g, idx) => (
                            <article
                                key={g.num}
                                data-testid={`alu-gamme-${g.tag.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-")}`}
                                className="bg-white"
                            >
                                <div
                                    className={`grid grid-cols-1 lg:grid-cols-12 gap-10 p-8 md:p-12 ${
                                        idx % 2 === 1 ? "lg:[direction:rtl]" : ""
                                    }`}
                                >
                                    <div className="lg:col-span-5 lg:[direction:ltr]">
                                        <div className="relative overflow-hidden border border-[#dde5f0] bg-[#f3f6fb]">
                                            <img loading="lazy" decoding="async"
                                                src={g.img}
                                                alt={g.title}
                                                loading="lazy"
                                                className="w-full h-72 object-cover"
                                            />
                                            <div className="absolute top-4 left-4 tech-stamp bg-[#0c182b] text-white px-3 py-2">
                                                {g.tag}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="lg:col-span-7 lg:[direction:ltr]">
                                        <span className="tech-stamp text-[#2f4f7f]">
                                            {g.num}
                                        </span>
                                        <h3 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-[0.95] mt-3 mb-5">
                                            {g.title}
                                        </h3>
                                        <p className="text-lg text-[#1e3457] leading-relaxed mb-6">
                                            {g.desc}
                                        </p>
                                        <ul className="space-y-3">
                                            {g.points.map((p) => (
                                                <li
                                                    key={p}
                                                    className="flex gap-3 text-[#1e3457]"
                                                >
                                                    <CheckCircle2 className="w-5 h-5 text-[#2f4f7f] flex-shrink-0 mt-0.5" />
                                                    <span>{p}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </article>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ AVANTAGES ============ */}
            <section
                data-testid="alu-avantages"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="mb-14">
                        <div className="tech-stamp mb-4">Avantages</div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] max-w-3xl">
                            Pourquoi choisir nos portes.
                        </h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-t border-l border-[#dde5f0]">
                        {avantages.map((a) => (
                            <div
                                key={a.title}
                                data-testid={`alu-avantage-${a.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                                className="border-b border-r border-[#dde5f0] p-8 bg-white hover:bg-[#f3f6fb] transition-colors"
                            >
                                <div className="w-14 h-14 border border-[#c5d4e7] flex items-center justify-center mb-6">
                                    <a.icon className="w-6 h-6 text-[#2f4f7f]" />
                                </div>
                                <h3 className="font-display font-bold uppercase text-xl tracking-tight mb-3">
                                    {a.title}
                                </h3>
                                <p className="text-[#4b5d7a] text-sm leading-relaxed">
                                    {a.desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ CONFIGURATIONS ============ */}
            <section
                data-testid="alu-configurations"
                className="bg-[#0c182b] text-white border-b border-[#1e3457] relative overflow-hidden"
            >
                <div className="bg-blueprint-dark absolute inset-0 pointer-events-none" />
                <div className="container-portech relative py-20 md:py-28">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                        <div className="lg:col-span-5">
                            <div className="tech-stamp text-[#97b0d0] mb-4">
                                Configurations & finis
                            </div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] mb-6">
                                On fabrique selon votre ouverture.
                            </h2>
                            <p className="text-[#b2c3dd] leading-relaxed mb-10">
                                Chaque porte est fabriquée selon le sens
                                d'ouverture, le vitrage et le fini que vous
                                choisissez. On fournit même les dessins de
                                production pour approbation avant la fabrication.
                            </p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-[#1e3457] border border-[#1e3457]">
                                {configs.map((c) => (
                                    <div
                                        key={c.label}
                                        data-testid={`alu-config-${c.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                                        className="bg-[#0c182b] p-6"
                                    >
                                        <c.icon className="w-6 h-6 text-[#97b0d0] mb-4" />
                                        <div className="tech-stamp text-[#6485b4] mb-2">
                                            {c.label}
                                        </div>
                                        <div className="font-display font-bold uppercase tracking-tight text-base">
                                            {c.value}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="lg:col-span-7">
                            <div className="relative overflow-hidden border border-[#1e3457]">
                                <img loading="lazy" decoding="async"
                                    src={`${A}/alu-finis.webp`}
                                    alt="Échantillons de finis d'aluminium : anodisé clair, bronze, noir mat et blanc"
                                    loading="lazy"
                                    className="w-full h-80 object-cover"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ GALERIE ============ */}
            <section
                data-testid="alu-galerie"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="mb-14">
                        <div className="tech-stamp mb-4">Réalisations</div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] max-w-3xl">
                            Des portes qui s'intègrent partout.
                        </h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                        <div className="md:col-span-7 relative overflow-hidden border border-[#dde5f0] group">
                            <img loading="lazy" decoding="async"
                                src={`${A}/alu-gal2.webp`}
                                alt="Porte commerciale en aluminium robuste à l'entrée d'un bâtiment"
                                loading="lazy"
                                className="w-full h-full min-h-[280px] object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                        </div>
                        <div className="md:col-span-5 relative overflow-hidden border border-[#dde5f0] group">
                            <img loading="lazy" decoding="async"
                                src={`${A}/alu-cta.webp`}
                                alt="Porte isolée en aluminium à bris thermique"
                                loading="lazy"
                                className="w-full h-full min-h-[280px] object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ NOTE — prête à poser ============ */}
            <section
                data-testid="alu-scope"
                className="bg-[#f3f6fb] border-b border-[#dde5f0]"
            >
                <div className="container-portech py-16 md:py-20">
                    <div className="border border-[#dde5f0] bg-white p-8 md:p-10 grid grid-cols-1 lg:grid-cols-12 gap-8">
                        <div className="lg:col-span-4">
                            <div className="tech-stamp mb-3 text-[#2f4f7f]">
                                Comment ça marche
                            </div>
                            <h3 className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight leading-tight">
                                La porte, prête à poser.
                            </h3>
                        </div>
                        <div className="lg:col-span-8 text-[#4b5d7a] leading-relaxed space-y-4">
                            <p>
                                On <strong className="text-[#0c182b]">fabrique et fournit la porte</strong>{" "}
                                en aluminium — standard ou sur mesure — et on la
                                prépare avec toute sa quincaillerie montée ou
                                prête à monter.
                            </p>
                            <p>
                                La <strong className="text-[#0c182b]">pose finale</strong>{" "}
                                dans l'ouverture peut être faite par votre
                                vitrier ou votre entrepreneur ; vous bénéficiez
                                d'un <strong className="text-[#0c182b]">seul interlocuteur</strong>{" "}
                                pour la porte et sa quincaillerie, et d'un travail
                                fait par un spécialiste.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            <CtaBanner
                eyebrow="Un projet de portes ?"
                title="Demandez votre soumission dès aujourd'hui."
                description="Décrivez votre ouverture, votre usage et vos besoins — on revient avec une soumission précise pour vos portes en aluminium, partout dans le Grand Montréal."
                buttonLabel="Demander une soumission"
                buttonTo="/contact?produit=aluminium"
                variant="dark"
                testId="alu-final-cta"
            />
        </div>
    );
};

export default PortesAluminium;
