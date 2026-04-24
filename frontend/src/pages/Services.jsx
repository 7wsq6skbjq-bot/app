import { Link } from "react-router-dom";
import {
    ArrowUpRight,
    CheckCircle2,
    PackageOpen,
    Hammer,
    Drill,
    Cog,
} from "lucide-react";
import CtaBanner from "@/components/CtaBanner";

const HERO_IMG =
    "https://images.unsplash.com/photo-1762431226940-462dec55884d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTF8MHwxfHNlYXJjaHwzfHxtZXRhbCUyMGRvb3IlMjBsb2NrJTIwaGFyZHdhcmV8ZW58MHx8fHwxNzc3MDU5NTI1fDA&ixlib=rb-4.1.0&q=85";

const serviceDetails = [
    {
        num: "01",
        icon: Hammer,
        title: "Installation de quincaillerie",
        summary:
            "Installation complète de quincaillerie commerciale, alignement parfait, fonctionnement optimal dès la mise en service.",
        items: [
            "Barres antipaniques (simples, verticales, rim)",
            "Ferme-portes (hydrauliques, au sol, concealed)",
            "Serrures commerciales (mortaise, cylindriques)",
            "Plaques, poignées, boutons, gâches et accessoires",
            "Alignement et ajustement fin post-installation",
        ],
    },
    {
        num: "02",
        icon: Drill,
        title: "Usinage de portes",
        summary:
            "Préparation sur mesure de portes en aluminium. Chaque porte adaptée à son usage exact, sans jeu, sans frottement.",
        items: [
            "Découpe précise (cisaille, scie, routeur)",
            "Perçage millimétrique pour quincaillerie standard",
            "Modifications spécifiques : préparation pour serrures, plaques, verrous",
            "Préparation d'ouvertures pour fenêtres, grilles, hublots",
            "Respect des standards commerciaux et codes du bâtiment",
        ],
    },
    {
        num: "03",
        icon: PackageOpen,
        title: "Préparation complète",
        summary:
            "De l'achat de la porte à la livraison prête à installer — on s'occupe de tout. Aucune surprise sur le chantier.",
        items: [
            "Achat de la porte en aluminium (section standard ou sur mesure)",
            "Modification et usinage en atelier",
            "Installation de la quincaillerie complète",
            "Contrôle qualité avant livraison",
            "Porte livrée prête à être posée — gain de temps immédiat",
        ],
    },
    {
        num: "04",
        icon: Cog,
        title: "Ajustement et réparation",
        summary:
            "On intervient sur les problèmes existants. Rapidement, proprement, sans bricolage temporaire.",
        items: [
            "Porte qui ne ferme pas correctement ou qui cogne",
            "Ferme-porte qui claque ou qui relâche",
            "Serrure mal alignée, gâche à repositionner",
            "Barre antipaniques qui résiste ou qui déclenche mal",
            "Diagnostic précis avant chaque intervention",
        ],
    },
];

const Services = () => {
    return (
        <div data-testid="page-services">
            {/* ============ HEADER ============ */}
            <section
                data-testid="services-header"
                className="relative bg-zinc-950 text-white overflow-hidden border-b border-zinc-900"
            >
                <div
                    className="absolute inset-0 bg-cover bg-center opacity-30"
                    style={{ backgroundImage: `url(${HERO_IMG})` }}
                    aria-hidden
                />
                <div className="absolute inset-0 bg-gradient-to-b from-zinc-950/80 to-zinc-950" />
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />

                <div className="container-portech relative py-24 md:py-32">
                    <div className="tech-stamp text-blue-400 mb-6">
                        02 / Nos services
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-5xl md:text-6xl lg:text-7xl leading-[0.92] max-w-4xl">
                        Services professionnels pour portes commerciales.
                    </h1>
                    <p className="mt-8 max-w-2xl text-lg md:text-xl text-zinc-300 leading-relaxed">
                        Installation, usinage, préparation complète, ajustement
                        et réparation. Chaque projet est traité avec la même
                        rigueur — du premier coup de règle jusqu'à la dernière
                        vis.
                    </p>
                </div>
            </section>

            {/* ============ DETAILED SERVICES ============ */}
            <section
                data-testid="services-details"
                className="bg-white border-b border-zinc-200"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="space-y-px bg-zinc-200 border border-zinc-200">
                        {serviceDetails.map((s, idx) => (
                            <article
                                key={s.num}
                                data-testid={`service-detail-${s.num}`}
                                className="bg-white"
                            >
                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 p-8 md:p-12">
                                    <div className="lg:col-span-4">
                                        <div className="flex items-center gap-4 mb-6">
                                            <div className="w-14 h-14 border border-zinc-300 flex items-center justify-center">
                                                <s.icon className="w-6 h-6 text-blue-700" />
                                            </div>
                                            <span className="tech-stamp text-blue-700">
                                                {s.num}
                                            </span>
                                        </div>
                                        <h2 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-[0.95]">
                                            {s.title}
                                        </h2>
                                    </div>
                                    <div className="lg:col-span-8">
                                        <p className="text-lg text-zinc-700 leading-relaxed mb-8">
                                            {s.summary}
                                        </p>
                                        <ul className="space-y-3">
                                            {s.items.map((it) => (
                                                <li
                                                    key={it}
                                                    className="flex gap-3 text-zinc-800"
                                                >
                                                    <CheckCircle2 className="w-5 h-5 text-blue-700 flex-shrink-0 mt-0.5" />
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

            {/* ============ PROCESS ============ */}
            <section
                data-testid="services-process"
                className="bg-zinc-50 border-b border-zinc-200"
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

                    <div className="grid grid-cols-1 md:grid-cols-4 border-t border-l border-zinc-200">
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
                                className="border-b border-r border-zinc-200 p-8 bg-white"
                            >
                                <div className="tech-stamp text-blue-700 mb-5">
                                    Étape {p.step}
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
                </div>
            </section>

            <CtaBanner
                eyebrow="Prêt à démarrer ?"
                title="Parlez-nous de votre projet."
                description="Quelques minutes pour décrire vos besoins — on revient avec une soumission précise et réaliste."
                buttonLabel="Demander une soumission"
                buttonTo="/contact"
                variant="light"
                testId="services-final-cta"
            />
        </div>
    );
};

export default Services;
