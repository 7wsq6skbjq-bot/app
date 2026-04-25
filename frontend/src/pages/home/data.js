// Static content for the Home page — extracted from Home.jsx to keep the page lean.
import {
    AlertTriangle,
    KeyRound,
    Wrench,
    Timer,
    ShieldCheck,
    Ruler,
    CheckCircle2,
} from "lucide-react";

const P = "/generated/portfolio";

// 100 % commercial aluminum door imagery — generated via Nano Banana, single-use.
export const IMG = {
    hero:        `${P}/home-hero.png`,
    hands:       `${P}/home-showcase-tech.png`,
    luxuryGlass: `${P}/home-luxury-glass.png`,
    exitDevice:  `${P}/home-showcase-exit.png`,
    panicBar:    `${P}/home-showcase-panic.png`,
    lockCloseup: `${P}/home-showcase-lock.png`,
    serviceInstall:  `${P}/home-service-installation.png`,
    serviceMachine:  `${P}/home-service-machining.png`,
    serviceRepair:   `${P}/home-service-repair.png`,
    serviceUpgrade:  `${P}/home-service-upgrade.png`,
    serviceConsult:  `${P}/home-showcase-storefront.png`,
    serviceInspect:  "/generated/precision-install.png",
    grid:        `${P}/home-grid-components.png`,
    restaurant:  `${P}/home-client-restaurant.png`,
    school:      `${P}/home-client-school.png`,
    condo:       `${P}/home-client-condo.png`,
    entrance:    `${P}/home-client-office.png`,
};

export const problems = [
    { icon: AlertTriangle, title: "Porte qui ferme mal", desc: "Elle cogne, elle traîne, elle grince. Un problème qui s'aggrave chaque semaine." },
    { icon: KeyRound,      title: "Barre antipanique difficile", desc: "Du personnel qui peine à sortir, des inspections qui tombent à plat." },
    { icon: Wrench,        title: "Serrure mal alignée", desc: "Verrouillage qui force, sécurité compromise, usure prématurée des pièces." },
    { icon: Timer,         title: "Appels de service en boucle", desc: "Des « patchs » temporaires qui reviennent hanter votre budget chaque mois." },
];

export const services = [
    { num: "01", title: "Installation de quincaillerie", desc: "Barres antipaniques, ferme-portes, serrures commerciales, plaques et accessoires. Alignement au millimètre.", img: IMG.serviceInstall },
    { num: "02", title: "Modification & usinage",        desc: "Préparation, perçage et ajustement de vos portes existantes pour accueillir une nouvelle quincaillerie.",   img: IMG.serviceMachine },
    { num: "03", title: "Réparation ciblée",             desc: "On intervient sur une porte qui force, une serrure qui coince, un ferme-porte qui claque. On règle à la source.", img: IMG.serviceRepair },
    { num: "04", title: "Mise à niveau & remplacement",  desc: "Remplacement de pièces usées par des équivalents commerciaux robustes, conformes aux codes du bâtiment.", img: IMG.serviceUpgrade },
    { num: "05", title: "Consultation pour vitreries",   desc: "Accompagnement des vitriers dans le choix et l'achat de la quincaillerie : compatibilité, normes, fournisseurs. Vous vendez la porte, on sécurise la ferrure.", img: IMG.serviceConsult },
    { num: "06", title: "Inspection & rapport d'expertise", desc: "Avant que vous livriez le projet à votre client, on inspecte le travail des sous-traitants en quincaillerie et on remet un rapport d'expertise détaillé.", img: IMG.serviceInspect },
];

export const benefits = [
    { icon: Ruler,        title: "Travail précis",         desc: "Chaque mesure validée, chaque coupe vérifiée. Zéro approximation." },
    { icon: ShieldCheck,  title: "Installation durable",   desc: "On n'applique pas de patch temporaire. On règle le problème à la source." },
    { icon: Timer,        title: "Rapidité d'exécution",   desc: "Planification serrée, intervention ciblée. On respecte vos opérations." },
    { icon: CheckCircle2, title: "Expertise terrain réelle", desc: "Plus de 10 ans sur le chantier, aux côtés de 45 ans de métier transmis." },
];

export const sectors = [
    "Commerces", "Restaurants", "Écoles", "Tours à condos", "Bureaux",
    "Boulangeries", "Épiceries", "Boucheries", "Pharmacies", "Cliniques",
    "Cinémas", "Banques", "Dépanneurs",
];

export const BRAND_STYLE_MAP = {
    italic: "italic",
    condensed: "tracking-tighter",
    wide: "tracking-widest",
    block: "",
};

export const brands = [
    { name: "Adams Rite",     slug: "adams-rite",     style: "italic" },
    { name: "Von Duprin",     slug: "von-duprin",     style: "condensed" },
    { name: "Sargent",        slug: "sargent",        style: "wide" },
    { name: "LCN",            slug: "lcn",            style: "block" },
    { name: "Schlage",        slug: "schlage",        style: "italic" },
    { name: "Yale",           slug: "yale",           style: "block" },
    { name: "Norton",         slug: "norton",         style: "wide" },
    { name: "dormakaba",      slug: "dormakaba",      style: "condensed" },
    { name: "Corbin Russwin", slug: "corbin-russwin", style: "italic" },
    { name: "Best",           slug: "best",           style: "block" },
    { name: "Hager",          slug: "hager",          style: "wide" },
    { name: "Stanley",        slug: "stanley",        style: "condensed" },
];

export const testimonials = [
    { quote: "Trois portes coupe-feu coincées au sous-sol, on n'arrivait plus à les fermer correctement depuis l'été. Cédrick est venu, a démonté les ferme-portes, ajusté les pivots. Tout fonctionne. Première fois en 2 ans qu'on n'a pas un appel par semaine pour les portes.", author: "Mario L.", context: "Concierge en chef · Tour de bureaux Côte-de-Liesse" },
    { quote: "30 étages, condos haut de gamme rue Peel. On avait 2 vitriers en place pour le verre, mais la quincaillerie sur les portes pivot du lobby c'est lui qui a fait la job. Pré-assemblé en atelier, posé en une journée, alignement nickel.", author: "Patrick D.", context: "Surintendant · Tour à condos · Rue Peel, Montréal" },
    { quote: "Notre barre antipanique de la sortie d'urgence côté ruelle s'enclenchait pas. Inspection des pompiers dans 5 jours, on stressait. Cédrick est passé le lendemain matin, ajustement, nettoyage du loquet. On a passé l'inspection sans correctif.", author: "Marie-Pier T.", context: "Gérante · Pharmacie · Plateau Mont-Royal" },
    { quote: "On gère 14 écoles primaires. Quand un cylindre brise ou qu'une serrure de classe se grippe, faut que ça se règle vite. Avec Portech on appelle, et c'est fait dans la semaine, parfois la journée. Pas de drame, pas de devis en 4 pages.", author: "Sylvain B.", context: "Coordonnateur entretien · Centre de services scolaire de Laval" },
    { quote: "Restaurant, portes pivots sur mesure, le client avait dépensé une fortune. Quatre vitriers ont reculé sur la quincaillerie. Cédrick a accepté, a fait le préassemblage chez lui, livré une fermeture parfaite. Aucune marque sur le cadre. Je l'appelle pour le prochain projet, c'est sûr.", author: "Jean-François M.", context: "Designer-architecte · Restaurant gastronomique · Vieux-Montréal" },
    { quote: "Cinéma 8 salles, ouverture en 2 semaines, 12 portes coupe-feu et 2 sorties d'urgence à régler. Cédrick est venu un dimanche, a tout aligné, vérifié la conformité. On a passé l'inspection lundi sans une remarque. Sauveur.", author: "Daniel R.", context: "Chargé de projet · Complexe cinématographique · Brossard" },
];

export const showcaseTiles = [
    { to: "/galerie/interventions",       testId: "showcase-interventions", img: IMG.hands,       caption: "Intervention · Installation",     hoverLabel: "Voir la galerie →", className: "md:col-span-5 md:row-span-2", imgClass: "min-h-[26rem]", alt: "Technicien installant de la quincaillerie sur une porte commerciale" },
    { to: "/galerie/chantiers",           testId: "showcase-chantiers",     img: IMG.luxuryGlass, caption: "Chantier réel · Haut de gamme",   hoverLabel: "Voir la galerie →", className: "md:col-span-4", imgClass: "h-64", alt: "Installation de quincaillerie sur porte pivot vitrée haut de gamme" },
    { to: "/galerie/dispositifs-sortie",  testId: "showcase-exit-device",   img: IMG.exitDevice,  caption: "Dispositif de sortie",            hoverLabel: "Voir →",            className: "md:col-span-3", imgClass: "h-64", alt: "Dispositif de sortie sur porte commerciale" },
    { to: "/galerie/barres-antipaniques", testId: "showcase-panic-bar",     img: IMG.panicBar,    caption: "Barre antipanique",               hoverLabel: "Voir →",            className: "md:col-span-4", imgClass: "h-64", alt: "Barre antipanique commerciale" },
    { to: "/galerie/serrures",            testId: "showcase-lock",          img: IMG.lockCloseup, caption: "Serrure",                         hoverLabel: "Voir →",            className: "md:col-span-3", imgClass: "h-64", alt: "Serrure commerciale" },
];

export const clientTypes = [
    { img: IMG.restaurant, label: "Restaurants & commerces", sub: "Horaires serrés, zéro arrêt toléré." },
    { img: IMG.school,     label: "Écoles & institutions",   sub: "Sécurité et conformité aux codes du bâtiment." },
    { img: IMG.condo,      label: "Tours à condos",          sub: "Portes lourdes, trafic constant, fini haut de gamme." },
    { img: IMG.entrance,   label: "Bureaux & commerces",     sub: "Image professionnelle, fonctionnement silencieux." },
];
