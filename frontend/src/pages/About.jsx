import CtaBanner from "@/components/CtaBanner";
import { CheckCircle2, Target, Compass } from "lucide-react";

const FOUNDER_IMG =
    "https://images.unsplash.com/photo-1759847527437-a548715aef7a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjV8MHwxfHNlYXJjaHwzfHxjb25zdHJ1Y3Rpb24lMjB3b3JrZXIlMjBpbmR1c3RyaWFsfGVufDB8fHx8MTc3NzA1OTUzN3ww&ixlib=rb-4.1.0&q=85";

const TEXTURE_IMG =
    "https://images.unsplash.com/photo-1770208741276-dc9e2d235620?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDN8MHwxfHNlYXJjaHwxfHxpbmR1c3RyaWFsJTIwbWV0YWwlMjB0ZXh0dXJlfGVufDB8fHx8MTc3NzA1OTUyNXww&ixlib=rb-4.1.0&q=85";

const storyBlocks = [
    {
        label: "01",
        title: "Sur le terrain, pas dans les livres.",
        paragraphs: [
            "Il y a des parcours qui ne s'inventent pas.",
            "Le mien s'est construit sur le terrain, jour après jour, pendant plus de 10 ans — aux côtés d'un homme qui avait déjà consacré 45 années de sa vie à ce métier.",
            "Un homme de rigueur. Un homme de précision. Un homme qui m'a appris qu'une porte commerciale, ce n'est jamais « juste une porte ».",
        ],
    },
    {
        label: "02",
        title: "Une porte, c'est bien plus qu'une porte.",
        paragraphs: [
            "C'est un point de passage.",
            "Un enjeu de sécurité.",
            "Le premier contact avec vos clients.",
            "J'ai commencé comme tous ceux qui apprennent pour vrai : en bas de l'échelle. Couper des matériaux. Observer. Comprendre.",
        ],
    },
    {
        label: "03",
        title: "Monter, ajuster, installer — répéter.",
        paragraphs: [
            "Puis j'ai avancé. Le montage. Les ajustements précis. Les installations. Les projets. Les équipes.",
            "Chaque étape m'a formé. Chaque défi m'a élevé.",
            "Et à chaque fois, j'ai fait le même choix : dire oui. Oui aux tâches complexes. Oui aux imprévus. Oui aux responsabilités.",
        ],
    },
    {
        label: "04",
        title: "De l'apprentissage à la maîtrise.",
        paragraphs: [
            "Parce que très tôt, j'ai compris une chose : je ne travaillais pas seulement pour gagner ma vie. Je travaillais pour bâtir mon expertise.",
            "Avec le temps, ce qui était un apprentissage est devenu une maîtrise — une compréhension complète du métier : préparation et transformation des portes, installation de quincaillerie spécialisée, ajustement de précision, gestion de projets et coordination.",
            "Une expertise acquise sur le terrain, dans des conditions réelles, là où les erreurs coûtent du temps, de l'argent… et parfois des maux de tête.",
        ],
    },
    {
        label: "05",
        title: "Une page se tourne. Une entreprise naît.",
        paragraphs: [
            "Aujourd'hui, une page se tourne. Celui qui m'a transmis ce savoir prend sa retraite.",
            "Moi, j'ai fait le choix de continuer. Pas en copiant. Mais en reprenant les standards. En élevant les attentes. En construisant quelque chose à mon image.",
            "C'est ainsi qu'est née Portech.",
        ],
    },
];

const About = () => {
    return (
        <div data-testid="page-about">
            {/* ============ HEADER ============ */}
            <section
                data-testid="about-header"
                className="relative bg-zinc-950 text-white overflow-hidden border-b border-zinc-900"
            >
                <div
                    className="absolute inset-0 bg-cover bg-center opacity-25"
                    style={{ backgroundImage: `url(${TEXTURE_IMG})` }}
                    aria-hidden
                />
                <div className="absolute inset-0 bg-gradient-to-b from-zinc-950/80 to-zinc-950" />
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />

                <div className="container-portech relative py-24 md:py-32">
                    <div className="tech-stamp text-blue-400 mb-6">
                        03 / À propos
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-5xl md:text-6xl lg:text-7xl leading-[0.92] max-w-4xl">
                        Une entreprise bâtie sur{" "}
                        <span className="text-blue-400">10 ans</span> de
                        chantier et <span className="text-blue-400">45 ans</span>{" "}
                        de métier transmis.
                    </h1>
                    <p className="mt-8 max-w-2xl text-lg md:text-xl text-zinc-300 leading-relaxed">
                        Portech est une entreprise spécialisée dans la
                        quincaillerie de portes commerciales. Notre mission est
                        simple : offrir des installations fiables, précises et
                        durables.
                    </p>
                </div>
            </section>

            {/* ============ STORY ============ */}
            <section
                data-testid="about-story"
                className="bg-white border-b border-zinc-200"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-14">
                        <div className="lg:col-span-5">
                            <div className="sticky top-28">
                                <div className="border border-zinc-200 relative">
                                    <img
                                        src={FOUNDER_IMG}
                                        alt="Fondateur de Portech dans son atelier"
                                        className="w-full h-[28rem] md:h-[32rem] object-cover grayscale"
                                    />
                                    <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-zinc-200 px-3 py-2">
                                        Fondateur · Portech
                                    </div>
                                </div>
                                <div className="mt-6 p-6 border border-zinc-200 bg-zinc-50">
                                    <div className="tech-stamp text-blue-700 mb-3">
                                        Philosophie
                                    </div>
                                    <p className="font-display font-bold uppercase text-lg tracking-tight leading-tight">
                                        « Peu importe le client, le besoin
                                        reste le même : chaque porte doit
                                        fonctionner parfaitement. »
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="lg:col-span-7">
                            <div className="tech-stamp mb-4">
                                Notre histoire
                            </div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] mb-10">
                                Un parcours qui ne s'invente pas.
                            </h2>

                            <div className="space-y-12">
                                {storyBlocks.map((b) => (
                                    <div
                                        key={b.label}
                                        data-testid={`story-block-${b.label}`}
                                        className="pl-6 border-l border-zinc-200 hover:border-blue-600 transition-colors"
                                    >
                                        <div className="tech-stamp text-blue-700 mb-3">
                                            Chapitre {b.label}
                                        </div>
                                        <h3 className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight leading-tight mb-5">
                                            {b.title}
                                        </h3>
                                        <div className="space-y-4 text-zinc-700 leading-relaxed">
                                            {b.paragraphs.map((p, i) => (
                                                <p key={i}>{p}</p>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ MISSION & VISION ============ */}
            <section
                data-testid="about-mission-vision"
                className="bg-zinc-50 border-b border-zinc-200"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="grid grid-cols-1 md:grid-cols-2 border border-zinc-200">
                        <div
                            data-testid="mission-block"
                            className="p-10 md:p-14 border-b md:border-b-0 md:border-r border-zinc-200 bg-white"
                        >
                            <Target className="w-8 h-8 text-blue-700 mb-6" />
                            <div className="tech-stamp mb-4">Mission</div>
                            <h3 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-[1] mb-6">
                                Offrir des installations fiables, précises et
                                durables.
                            </h3>
                            <p className="text-zinc-700 leading-relaxed">
                                On sait qu'une porte mal installée devient
                                rapidement un problème. C'est pourquoi chaque
                                projet est réalisé avec rigueur — même les plus
                                petits.
                            </p>
                        </div>
                        <div
                            data-testid="vision-block"
                            className="p-10 md:p-14 bg-zinc-950 text-white relative overflow-hidden"
                        >
                            <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                            <Compass className="w-8 h-8 text-blue-400 mb-6 relative" />
                            <div className="tech-stamp text-zinc-400 mb-4 relative">
                                Vision
                            </div>
                            <h3 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-[1] mb-6 relative">
                                Devenir la référence des portes commerciales au
                                Québec.
                            </h3>
                            <p className="text-zinc-300 leading-relaxed relative">
                                Offrir un service constant, professionnel, et
                                tellement fiable qu'on en parle entre
                                gestionnaires d'immeubles, directeurs d'école
                                et propriétaires de commerce.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============ WHY US ============ */}
            <section
                data-testid="about-why"
                className="bg-white border-b border-zinc-200"
            >
                <div className="container-portech py-20 md:py-28">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                        <div className="lg:col-span-5">
                            <div className="tech-stamp mb-4">Pourquoi nous</div>
                            <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95]">
                                On ne fait pas du
                                <br />
                                <span className="text-blue-700">« vite fait ».</span>
                            </h2>
                        </div>
                        <div className="lg:col-span-7">
                            <ul className="space-y-5">
                                {[
                                    "Chaque porte est bien ajustée",
                                    "Chaque porte est solide",
                                    "Chaque porte est fonctionnelle dès le départ",
                                    "Chaque intervention respecte vos opérations",
                                    "Chaque projet est documenté — rien n'est laissé au hasard",
                                ].map((line) => (
                                    <li
                                        key={line}
                                        className="flex gap-4 items-start pb-5 border-b border-zinc-200"
                                    >
                                        <CheckCircle2 className="w-6 h-6 text-blue-700 flex-shrink-0 mt-0.5" />
                                        <span className="text-lg md:text-xl font-display font-semibold uppercase tracking-tight text-zinc-900">
                                            {line}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            <CtaBanner
                eyebrow="Faisons connaissance"
                title="Donnez à vos portes le travail qu'elles méritent."
                description="Un entrepreneur, une école, une tour à condos, une boulangerie — peu importe le client, chaque porte doit fonctionner parfaitement."
                buttonLabel="Demander une soumission"
                buttonTo="/contact"
                variant="dark"
                testId="about-final-cta"
            />
        </div>
    );
};

export default About;
