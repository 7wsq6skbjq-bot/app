import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { services } from "../data";

export const HomeServices = () => (
    <section
        data-testid="home-services"
        className="bg-white border-b border-[#dde5f0]"
    >
        <div className="container-portech py-24 md:py-32">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-14">
                <div>
                    <div className="tech-stamp mb-4">03 — Nos services</div>
                    <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95]">
                        Nos services
                    </h2>
                </div>
                <Link
                    to="/services"
                    data-testid="services-see-all"
                    className="btn-secondary self-start md:self-auto"
                >
                    Voir tous les services
                    <ArrowUpRight className="w-4 h-4" />
                </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 border-t border-l border-[#dde5f0]">
                {services.map((s) => (
                    <div
                        key={s.num}
                        data-testid={`service-card-${s.num}`}
                        className="border-b border-r border-[#dde5f0] group hover:bg-[#f3f6fb] transition-colors overflow-hidden"
                    >
                        <div className="relative h-56 overflow-hidden border-b border-[#dde5f0]">
                            <img
                                src={s.img}
                                alt={s.title}
                                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                        </div>
                        <div className="p-8">
                            <div className="flex items-start justify-between mb-4">
                                <span className="tech-stamp text-[#2f4f7f]">{s.num}</span>
                                <ArrowUpRight className="w-5 h-5 text-[#97b0d0] group-hover:text-[#1e3457] transition-colors" />
                            </div>
                            <h3 className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight mb-4">
                                {s.title}
                            </h3>
                            <p className="text-[#4b5d7a] leading-relaxed">{s.desc}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    </section>
);
