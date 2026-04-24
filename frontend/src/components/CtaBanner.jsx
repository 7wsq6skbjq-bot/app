import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

const CtaBanner = ({
    eyebrow = "Passons à l'action",
    title = "Besoin d'une porte qui fonctionne vraiment ?",
    description = "Arrêtez de perdre du temps avec des ajustements temporaires. Faites faire le travail correctement dès le départ.",
    buttonLabel = "Demander une soumission",
    buttonTo = "/contact",
    variant = "dark",
    testId = "cta-banner",
}) => {
    const isDark = variant === "dark";

    return (
        <section
            data-testid={testId}
            className={`relative overflow-hidden border-t ${
                isDark
                    ? "bg-zinc-950 text-white border-zinc-900"
                    : "bg-zinc-50 text-zinc-950 border-zinc-200"
            }`}
        >
            <div
                className={`absolute inset-0 pointer-events-none ${
                    isDark ? "bg-blueprint-dark" : "bg-blueprint"
                }`}
            />
            <div className="container-portech relative py-20 md:py-28">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-end">
                    <div className="lg:col-span-8">
                        <div
                            className={`tech-stamp mb-5 ${
                                isDark ? "text-zinc-400" : "text-zinc-500"
                            }`}
                        >
                            {eyebrow}
                        </div>
                        <h2 className="font-display font-bold uppercase tracking-tight text-4xl sm:text-5xl lg:text-6xl leading-[0.95] max-w-3xl">
                            {title}
                        </h2>
                        <p
                            className={`mt-6 max-w-xl text-base md:text-lg leading-relaxed ${
                                isDark ? "text-zinc-400" : "text-zinc-600"
                            }`}
                        >
                            {description}
                        </p>
                    </div>
                    <div className="lg:col-span-4 flex lg:justify-end">
                        <Link
                            to={buttonTo}
                            data-testid={`${testId}-button`}
                            className={
                                isDark ? "btn-ghost-dark" : "btn-primary"
                            }
                        >
                            {buttonLabel}
                            <ArrowUpRight className="w-4 h-4" />
                        </Link>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default CtaBanner;
