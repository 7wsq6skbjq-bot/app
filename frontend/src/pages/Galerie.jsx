import { useEffect } from "react";
import { useParams, Link, Navigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import CtaBanner from "@/components/CtaBanner";

const STOCK = "https://images.unsplash.com/";

// Each category has 8-10 stock photos and a short description.
// Photos are direct Unsplash CDN URLs (free, no auth, stable).
const CATEGORIES = {
    interventions: {
        eyebrow: "Galerie · 01",
        title: "Intervention & Installation",
        intro:
            "Pose, ajustement et installation de quincaillerie commerciale sur portes en acier, en verre ou en bois. Travail propre, alignement au millimètre, finitions sans bavures.",
        photos: [
            { src: `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1400&q=80`, caption: "Pose d'une serrure mortaise sur porte commerciale" },
            { src: `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1400&q=80`, caption: "Poignée et plaque de propreté noir mat" },
            { src: `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1400&q=80`, caption: "Vérification de l'alignement après pose" },
            { src: `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1400&q=80`, caption: "Cylindre haute sécurité prêt à installer" },
            { src: `${STOCK}photo-1586864387634-2f33030dab41?auto=format&fit=crop&w=1400&q=80`, caption: "Quincaillerie sur porte bois — finition châtaignier" },
            { src: `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1400&q=80`, caption: "Système anti-effraction additionnel" },
            { src: `${STOCK}photo-1558002038-1055907df827?auto=format&fit=crop&w=1400&q=80`, caption: "Programmation d'une serrure électronique" },
            { src: `${STOCK}photo-1592924271903-1e4b1a1ae20f?auto=format&fit=crop&w=1400&q=80`, caption: "Test de fonctionnement d'un dispositif de sortie" },
        ],
    },
    chantiers: {
        eyebrow: "Galerie · 02",
        title: "Chantiers réels — Haut de gamme",
        intro:
            "Quelques projets réalisés sur des portes pivot vitrées, des restaurants gastronomiques, des tours à condos et des sièges sociaux. Pré-assemblage en atelier, livraison sans hésitation.",
        photos: [
            { src: "/uploads/glass-door-hardware.jpg", caption: "Porte pivot vitrée — quincaillerie en cours d'installation" },
            { src: `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1400&q=80`, caption: "Poignée luxueuse sur porte de hall" },
            { src: `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1400&q=80`, caption: "Restaurant — ferrure custom finition noire" },
            { src: `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1400&q=80`, caption: "Tour à condos — porte d'entrée pré-installation" },
            { src: `${STOCK}photo-1586864387634-2f33030dab41?auto=format&fit=crop&w=1400&q=80`, caption: "Pré-assemblage en atelier avant livraison" },
            { src: `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1400&q=80`, caption: "Cylindre haut de gamme — restaurant Vieux-Montréal" },
            { src: `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1400&q=80`, caption: "Système de fermeture sur mesure" },
            { src: `${STOCK}photo-1558002038-1055907df827?auto=format&fit=crop&w=1400&q=80`, caption: "Contrôle d'accès intégré sur porte vitrée" },
        ],
    },
    "dispositifs-sortie": {
        eyebrow: "Galerie · 03",
        title: "Dispositifs de sortie",
        intro:
            "Aussi appelés barres antipaniques ou crash bars : ces dispositifs s'ouvrent d'un simple appui pour permettre l'évacuation rapide en cas d'urgence. Indispensables pour la conformité aux codes du bâtiment.",
        photos: [
            { src: `${STOCK}photo-1592924271903-1e4b1a1ae20f?auto=format&fit=crop&w=1400&q=80`, caption: "Dispositif de sortie à barre poussoir" },
            { src: `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1400&q=80`, caption: "Sortie d'urgence en couloir d'école" },
            { src: `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1400&q=80`, caption: "Mécanisme verticale sur porte coupe-feu" },
            { src: `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1400&q=80`, caption: "Test du loquet après ajustement" },
            { src: `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1400&q=80`, caption: "Système de tige verticale (Vertical Rod)" },
            { src: `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1400&q=80`, caption: "Cylindre extérieur sur dispositif de sortie" },
            { src: `${STOCK}photo-1586864387634-2f33030dab41?auto=format&fit=crop&w=1400&q=80`, caption: "Sortie secondaire — finition acier brossé" },
            { src: `${STOCK}photo-1558002038-1055907df827?auto=format&fit=crop&w=1400&q=80`, caption: "Contrôle d'accès couplé à un dispositif de sortie" },
        ],
    },
    "barres-antipaniques": {
        eyebrow: "Galerie · 04",
        title: "Barres antipaniques",
        intro:
            "Installation, ajustement et remplacement de barres antipaniques sur tous types de portes commerciales. On travaille avec Von Duprin, Sargent, Adams Rite, Yale et plus encore — selon ce qui est déjà en place.",
        photos: [
            { src: `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1400&q=80`, caption: "Barre antipanique horizontale — finition acier" },
            { src: `${STOCK}photo-1592924271903-1e4b1a1ae20f?auto=format&fit=crop&w=1400&q=80`, caption: "Barre poussoir — système Concealed Vertical Rod" },
            { src: `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1400&q=80`, caption: "Sortie d'urgence — porte coupe-feu" },
            { src: `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1400&q=80`, caption: "Mécanisme de loquet d'une barre antipanique" },
            { src: `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1400&q=80`, caption: "Tige verticale extérieure (Surface Vertical Rod)" },
            { src: `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1400&q=80`, caption: "Cylindre extérieur pour réentrée contrôlée" },
            { src: `${STOCK}photo-1586864387634-2f33030dab41?auto=format&fit=crop&w=1400&q=80`, caption: "Barre antipanique — finition aluminium anodisé" },
            { src: `${STOCK}photo-1558002038-1055907df827?auto=format&fit=crop&w=1400&q=80`, caption: "Système électrifié pour gestion d'accès" },
        ],
    },
    serrures: {
        eyebrow: "Galerie · 05",
        title: "Serrures commerciales",
        intro:
            "Mortaises, cylindriques, électroniques, à carte, à code. On installe, on remplace, on rénove. On travaille avec toutes les marques majeures et on garde des cylindres maître-clé sur stock pour les dépannages rapides.",
        photos: [
            { src: `${STOCK}photo-1635602739175-bab409a6e94c?auto=format&fit=crop&w=1400&q=80`, caption: "Cylindre haute sécurité — Adams Rite compatible" },
            { src: `${STOCK}photo-1607710533910-d7cdffd9e593?auto=format&fit=crop&w=1400&q=80`, caption: "Poignée et serrure mortaise — finition or brossé" },
            { src: `${STOCK}photo-1583041398200-09b2205f6cf0?auto=format&fit=crop&w=1400&q=80`, caption: "Serrure cylindrique noire mate" },
            { src: `${STOCK}photo-1558002038-1055907df827?auto=format&fit=crop&w=1400&q=80`, caption: "Serrure électronique avec contrôle d'accès mobile" },
            { src: `${STOCK}photo-1586864387634-2f33030dab41?auto=format&fit=crop&w=1400&q=80`, caption: "Serrure mortaise sur porte commerciale en bois" },
            { src: `${STOCK}photo-1538766017398-415434a31a5b?auto=format&fit=crop&w=1400&q=80`, caption: "Plaque de propreté + cylindre extérieur" },
            { src: `${STOCK}photo-1584105154398-99080f81b8ee?auto=format&fit=crop&w=1400&q=80`, caption: "Système de verrouillage multipoint" },
            { src: `${STOCK}photo-1555529902-5261145633bf?auto=format&fit=crop&w=1400&q=80`, caption: "Cadenas commercial inox — issue secondaire" },
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
