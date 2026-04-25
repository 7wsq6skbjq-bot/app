import CtaBanner from "@/components/CtaBanner";
import { useSeo } from "@/hooks/use-seo";
import { HomeHero } from "./home/sections/HomeHero";
import { HomeSectors } from "./home/sections/HomeSectors";
import { HomeShowcase } from "./home/sections/HomeShowcase";
import { HomeBrandsWall } from "./home/sections/HomeBrandsWall";
import { HomeProblems } from "./home/sections/HomeProblems";
import { HomeSolution } from "./home/sections/HomeSolution";
import { HomeServices } from "./home/sections/HomeServices";
import { HomeClients } from "./home/sections/HomeClients";
import { HomeWhy } from "./home/sections/HomeWhy";
import { HomeTestimonials } from "./home/sections/HomeTestimonials";

const Home = () => {
    useSeo({
        title: "Portech · Quincaillerie commerciale Grand Montréal | Installation & réparation",
        description:
            "Portech installe, ajuste et répare la quincaillerie de portes commerciales partout dans le Grand Montréal : barres antipaniques, ferme-portes, serrures, gâches électriques. 10+ ans d'expérience.",
    });

    return (
        <div data-testid="page-home">
            <HomeHero />
            <HomeSectors />
            <HomeShowcase />
            <HomeBrandsWall />
            <HomeProblems />
            <HomeSolution />
            <HomeServices />
            <HomeClients />
            <HomeWhy />
            <HomeTestimonials />
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
