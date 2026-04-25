import { benefits } from "../data";

export const HomeWhy = () => (
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
                        Parce qu'une quincaillerie bien posée, c'est une porte
                        qu'on oublie. Voici ce qui distingue une intervention
                        Portech — sur chaque chantier, sans exception.
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
);
