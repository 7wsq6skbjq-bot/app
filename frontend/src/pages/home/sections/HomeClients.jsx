import { clientTypes } from "../data";

export const HomeClients = () => (
    <section
        data-testid="home-clients"
        className="bg-[#f3f6fb] border-b border-[#dde5f0]"
    >
        <div className="container-portech py-24 md:py-32">
            <div className="mb-14 max-w-3xl">
                <div className="tech-stamp mb-4">04 — Nos clients</div>
                <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95]">
                    Là où la quincaillerie doit tenir, on est là.
                </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {clientTypes.map((c) => (
                    <div
                        key={c.label}
                        className="group border border-[#dde5f0] bg-white overflow-hidden"
                    >
                        <div className="relative h-56 overflow-hidden">
                            <img
                                src={c.img}
                                alt={c.label}
                                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                        </div>
                        <div className="p-6">
                            <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2">
                                {c.label}
                            </h3>
                            <p className="text-[#4b5d7a] text-sm leading-relaxed">
                                {c.sub}
                            </p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    </section>
);
