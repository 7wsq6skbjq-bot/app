import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { problems } from "../data";

export const HomeProblems = () => (
    <section
        data-testid="home-problems"
        className="bg-[#f3f6fb] border-b border-[#dde5f0]"
    >
        <div className="container-portech py-24 md:py-32">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-16">
                <div className="lg:col-span-5">
                    <div className="tech-stamp mb-4">01 — Le constat</div>
                    <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                        Vos portes
                        <br />
                        vous causent
                        <br />
                        des <span className="text-[#2f4f7f]">problèmes ?</span>
                    </h2>
                </div>
                <div className="lg:col-span-6 lg:col-start-7 pt-2">
                    <p className="text-lg leading-relaxed text-[#4b5d7a]">
                        Une quincaillerie défectueuse, c'est une perte de
                        temps, d'argent… et parfois un{" "}
                        <span className="text-[#0c182b] font-semibold">
                            risque de sécurité
                        </span>
                        . Voici ce qu'on entend — presque chaque semaine.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-t border-l border-[#dde5f0] bg-white">
                {problems.map((p) => (
                    <div
                        key={p.title}
                        data-testid={`problem-${p.title.toLowerCase().replace(/\s/g, "-")}`}
                        className="border-b border-r border-[#dde5f0] p-8 hover:bg-[#f3f6fb] transition-colors group"
                    >
                        <div className="w-11 h-11 border border-[#c5d4e7] flex items-center justify-center mb-6 group-hover:border-[#1e3457] group-hover:text-[#1e3457] transition-colors">
                            <p.icon className="w-5 h-5" />
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
);
