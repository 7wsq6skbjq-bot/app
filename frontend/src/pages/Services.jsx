import { Link } from "react-router-dom";
import {
    ArrowUpRight,
    CheckCircle2,
    Hammer,
    Drill,
    Cog,
    Wrench,
    Lightbulb,
    ClipboardCheck,
} from "lucide-react";
import CtaBanner from "@/components/CtaBanner";
import { useSeo } from "@/hooks/use-seo";

// 100% commercial aluminum door imagery — generated via Nano Banana, single-use.
const P = "/generated/portfolio";
const IMG = {
    hero:        `${P}/services-hero.png`,
    install:     `${P}/services-installation.png`,
    tools:       `${P}/services-machining.png`,
    closer:      `${P}/services-repair.png`,
    lock:        `${P}/services-upgrade.png`,
    luxuryGlass: `${P}/services-inspection.png`,
    grid:        `${P}/services-consultation.png`,
};

const serviceDetails = [
    {
        num: "01",
        icon: Hammer,
        title: "Installation de quincaillerie",
        img: IMG.install,
        summary:
            "Installation complète de quincaillerie commerciale, alignement parfait, fonctionnement optimal dès la mise en service.",
        items: [
            "Barres antipaniques (simples, verticales, rim)",
            "Ferme-portes hydrauliques (au dessus, au sol, concealed)",
            "Serrures commerciales (mortaise, cylindriques, électroniques)",
            "Plaques, poignées, boutons, gâches et accessoires",
            "Alignement et ajustement fin post-installation",
        ],
    },
    {
        num: "02",
        icon: Drill,
        title: "Modification & usinage",
        img: IMG.tools,
        summary:
            "Préparation et modification de portes existantes pour accueillir de la nouvelle quincaillerie. Les portes restent vos portes — on les prépare correctement.",
        items: [
            "Découpe et perçage précis (cisaille, scie, routeur)",
            "Préparation pour serrures mortaises et cylindriques",
            "Modifications pour conformité aux codes du bâtiment",
            "Travail réalisé sur place ou en atelier selon le besoin",
        ],
    },
    {
        num: "03",
        icon: Cog,
        title: "Réparation ciblée",
        img: IMG.closer,
        summary:
            "On intervient sur les problèmes existants. Rapidement, proprement, sans bricolage temporaire.",
        items: [
            "Porte qui ne ferme pas correctement ou qui cogne",
            "Ferme-porte qui claque ou qui relâche",
            "Serrure mal alignée, gâche à repositionner",
            "Barre antipanique qui résiste ou qui déclenche mal",
            "Diagnostic précis avant chaque intervention",
        ],
    },
    {
        num: "04",
        icon: Wrench,
        title: "Mise à niveau & remplacement",
        img: IMG.lock,
        summary:
            "Remplacement de pièces usées ou inadéquates par des équivalents commerciaux robustes, conformes aux codes du bâtiment.",
        items: [
            "Passage de quincaillerie résidentielle vers commerciale",
            "Remplacement de pièces discontinuées ou obsolètes",
            "Mise à niveau sécurité (contrôle d'accès, serrures renforcées)",
            "Pré-assemblage des kits pour un remplacement rapide",
            "Recommandations basées sur votre usage réel",
        ],
    },
    {
        num: "05",
        icon: Lightbulb,
        title: "Consultation pour vitreries",
        img: IMG.grid,
        summary:
            "On agit comme consultant auprès des vitriers : on vous accompagne dans le choix et l'achat de la quincaillerie pour vos projets — résidentiels haut de gamme, commerciaux, institutionnels. Le bon mécanisme du premier coup, sans devinette.",
        items: [
            "Sélection de la quincaillerie selon le type de porte (pivot, battante, coulissante)",
            "Vérification de compatibilité avec le cadre et les profilés",
            "Fournisseurs recommandés et listes de pièces validées",
            "Conformité aux codes du bâtiment du Québec et exigences municipales",
            "Soutien technique pendant l'achat et avant la pose",
            "Idéal pour portes pivots haut de gamme, mortaises multipoints, pièces discontinuées",
        ],
    },
    {
        num: "06",
        icon: ClipboardCheck,
        title: "Inspection & rapport d'expertise",
        img: IMG.luxuryGlass,
        summary:
            "Vous êtes entrepreneur général et vous avez sous-traité l'installation à un vitrier ? Avant de livrer le projet à votre client, on inspecte la quincaillerie posée et on remet un rapport d'expertise détaillé. Vous protégez votre nom, vous évitez les retours de garantie.",
        items: [
            "Inspection complète de chaque porte et de sa quincaillerie",
            "Vérification de l'alignement, des couples de serrage, des jeux et des ajustements",
            "Test de fonctionnement (barre antipanique, ferme-porte, serrure, gâche)",
            "Identification des défauts d'installation ou de pièces non conformes",
            "Rapport d'expertise écrit avec photos, observations et recommandations",
            "Liste précise des correctifs à demander au sous-traitant avant livraison",
        ],
    },
];

const Services = () => {
    useSeo({
        title: "Services · Installation, entretien, réparation et remplacement de quincaillerie de porte commerciale | Portech",
        description:
            "Services Portech : installation, entretien, réparation et remplacement de quincaillerie de porte commerciale. Barres antipaniques, ferme-portes, serrures mortaise, dispositifs de sortie. Grand Montréal, Laval, Rive-Sud et Rive-Nord.",
        canonical: "https://portech.info/services",
    });
    return (
        <div data-testid="page-services">
            {/* ============ HEADER ============ */}
            <section
                data-testid="services-header"
                className="relative bg-[#0c182b] text-white overflow-hidden border-b border-[#1e3457]"
            >
                <div
                    className="absolute inset-0 bg-cover bg-center opacity-35"
                    style={{ backgroundImage: `url(${IMG.hero})` }}
                    aria-hidden
                />
                <div className="absolute inset-0 bg-gradient-to-b from-[#0c182b]/85 to-[#0c182b]" />
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />

                <div className="container-portech relative py-24 md:py-32">
                    <div className="tech-stamp text-[#97b0d0] mb-6">
                        02 / Nos services
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-5xl md:text-6xl lg:text-7xl leading-[0.92] max-w-4xl">
                        La quincaillerie commerciale, c'est notre spécialité.
                    </h1>
                    <p className="mt-8 max-w-2xl text-lg md:text-xl text-[#b2c3dd] leading-relaxed">
                        Installation, modification, réparation et mise à
                        niveau. Chaque projet est traité avec la même rigueur —
                        du premier coup de règle jusqu'à la dernière vis.
                    </p>
                    <div className="mt-8 flex flex-wrap gap-3">
                        {[
                            "Barres antipaniques",
                            "Ferme-portes",
                            "Serrures commerciales",
                            "Plaques & poignées",
                            "Accessoires",
                            "Consultation vitreries",
                            "Inspection & expertise",
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

            {/* ============ DETAILED SERVICES ============ */}
            <section
                data-testid="services-details"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="space-y-px bg-[#dde5f0] border border-[#dde5f0]">
                        {serviceDetails.map((s, idx) => (
                            <article
                                key={s.num}
                                data-testid={`service-detail-${s.num}`}
                                className="bg-white"
                            >
                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 p-8 md:p-12">
                                    <div className="lg:col-span-5">
                                        <div className="flex items-center gap-4 mb-6">
                                            <div className="w-14 h-14 border border-[#c5d4e7] flex items-center justify-center">
                                                <s.icon className="w-6 h-6 text-[#2f4f7f]" />
                                            </div>
                                            <span className="tech-stamp text-[#2f4f7f]">
                                                {s.num}
                                            </span>
                                        </div>
                                        <h2 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-[0.95] mb-6">
                                            {s.title}
                                        </h2>
                                        <div className="relative overflow-hidden border border-[#dde5f0]">
                                            <img
                                                src={s.img}
                                                alt={s.title}
                                                className="w-full h-64 object-cover"
                                            />
                                        </div>
                                    </div>
                                    <div className="lg:col-span-7">
                                        <p className="text-lg text-[#1e3457] leading-relaxed mb-8">
                                            {s.summary}
                                        </p>
                                        <ul className="space-y-3">
                                            {s.items.map((it) => (
                                                <li
                                                    key={it}
                                                    className="flex gap-3 text-[#1e3457]"
                                                >
                                                    <CheckCircle2 className="w-5 h-5 text-[#2f4f7f] flex-shrink-0 mt-0.5" />
                                                    <span>{it}</span>
                                                </li>
                                            ))}
                                        </ul>
                                        {idx === serviceDetails.length - 1 && (
                                            <Link
                                                to="/contact"
                                                data-testid={`service-cta-${s.num}`}
                                                className="btn-primary mt-10"
                                            >
                                                Discuter de votre projet
                                                <ArrowUpRight className="w-4 h-4" />
                                            </Link>
                                        )}
                                    </div>
                                </div>
                            </article>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============ NOTE — doors vs hardware ============ */}
            <section
                data-testid="services-scope"
                className="bg-[#f3f6fb] border-b border-[#dde5f0]"
            >
                <div className="container-portech py-16 md:py-20">
                    <div className="border border-[#dde5f0] bg-white p-8 md:p-10 grid grid-cols-1 lg:grid-cols-12 gap-8">
                        <div className="lg:col-span-4">
                            <div className="tech-stamp mb-3 text-[#2f4f7f]">
                                Notre périmètre
                            </div>
                            <h3 className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight leading-tight">
                                La quincaillerie — c'est tout ce qu'on fait.
                            </h3>
                        </div>
                        <div className="lg:col-span-8 text-[#4b5d7a] leading-relaxed space-y-4">
                            <p>
                                On <strong className="text-[#0c182b]">n'installe pas de portes</strong> —
                                c'est le travail des vitriers. Ce qu'on fait,
                                c'est tout ce qui{" "}
                                <em>vit sur</em> la porte : barres antipaniques,
                                ferme-portes, serrures, plaques, poignées,
                                gâches, accessoires.
                            </p>
                            <p>
                                Au besoin, on peut <strong className="text-[#0c182b]">fournir la porte</strong>{" "}
                                (en aluminium, section standard ou sur mesure)
                                et la préparer avec sa quincaillerie, prête à
                                être installée par votre vitrier ou votre
                                entrepreneur. Mais la{" "}
                                <strong className="text-[#0c182b]">pose finale de la porte</strong>{" "}
                                elle-même reste du ressort du vitrier.
                            </p>
                            <p>
                                Résultat : vous avez{" "}
                                <strong className="text-[#0c182b]">un seul interlocuteur</strong>{" "}
                                pour toute la quincaillerie, et un travail réalisé par
                                un spécialiste — pas un généraliste qui
                                « touche un peu à tout ».
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ PROCESS ============ */}
            <section
                data-testid="services-process"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="mb-14">
                        <div className="tech-stamp mb-4">
                            Méthode — Processus standard
                        </div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] max-w-3xl">
                            Comment on travaille — étape par étape.
                        </h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 border-t border-l border-[#dde5f0]">
                        {[
                            {
                                step: "A",
                                title: "Évaluation",
                                desc: "On mesure, on écoute, on identifie le vrai problème — pas le symptôme.",
                            },
                            {
                                step: "B",
                                title: "Soumission claire",
                                desc: "Prix détaillé, délais précis, options expliquées. Pas de frais cachés.",
                            },
                            {
                                step: "C",
                                title: "Exécution rigoureuse",
                                desc: "Préparation en atelier, installation propre, respect de vos opérations.",
                            },
                            {
                                step: "D",
                                title: "Validation",
                                desc: "Test de fonctionnement sur place. On livre seulement quand c'est parfait.",
                            },
                        ].map((p) => (
                            <div
                                key={p.step}
                                data-testid={`process-step-${p.step}`}
                                className="border-b border-r border-[#dde5f0] p-8 bg-[#f3f6fb]"
                            >
                                <div className="tech-stamp text-[#2f4f7f] mb-5">
                                    Étape {p.step}
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
                </div>
            </section>

            <CtaBanner
                eyebrow="Prêt à démarrer ?"
                title="Parlez-nous de votre projet."
                description="Quelques minutes pour décrire vos besoins — on revient avec une soumission précise et réaliste, partout dans le Grand Montréal."
                buttonLabel="Demander une soumission"
                buttonTo="/contact"
                variant="light"
                testId="services-final-cta"
            />
        </div>
    );
};

export default Services;
