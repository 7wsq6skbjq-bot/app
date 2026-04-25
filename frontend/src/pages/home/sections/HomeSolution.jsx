import { IMG } from "../data";

export const HomeSolution = () => (
    <section
        data-testid="home-solution"
        className="bg-[#0c182b] text-white border-b border-[#1e3457] relative overflow-hidden"
    >
        <div className="absolute inset-0 bg-blueprint-dark opacity-60 pointer-events-none" />
        <div className="container-portech relative py-24 md:py-32">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
                <div className="lg:col-span-7">
                    <div className="tech-stamp text-[#97b0d0] mb-4">
                        02 — La solution
                    </div>
                    <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl lg:text-6xl leading-[0.95]">
                        La solution
                        <br />
                        <span className="text-[#97b0d0]">Portech</span>.
                    </h2>
                    <div className="mt-8 space-y-5 text-lg md:text-xl text-[#b2c3dd] leading-relaxed max-w-2xl">
                        <p>
                            Chez Portech, on s'occupe de votre quincaillerie de
                            portes commerciales{" "}
                            <strong className="text-white">de A à Z</strong>.
                        </p>
                        <p>On ne fait pas juste installer des pièces.</p>
                        <p>
                            On prépare des portes{" "}
                            <strong className="text-white">
                                prêtes à performer dès le jour 1
                            </strong>
                            .
                        </p>
                    </div>
                </div>

                <div className="lg:col-span-5">
                    <div className="border border-[#1e3457] relative">
                        <img
                            src={IMG.grid}
                            alt="Grille de composants de quincaillerie commerciale"
                            className="w-full h-72 md:h-96 object-cover"
                        />
                        <div className="absolute top-4 left-4 tech-stamp bg-[#0c182b]/85 backdrop-blur border border-[#1e3457] px-3 py-2">
                            Catalogue · Composants
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
);
