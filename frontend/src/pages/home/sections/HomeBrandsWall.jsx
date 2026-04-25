import { Link } from "react-router-dom";
import { brands, BRAND_STYLE_MAP } from "../data";

export const HomeBrandsWall = () => (
    <section
        data-testid="home-brands"
        className="bg-white border-b border-[#dde5f0]"
    >
        <div className="container-portech py-16 md:py-20">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mb-10">
                <div className="lg:col-span-5">
                    <div className="tech-stamp mb-4">Toutes les marques</div>
                    <h2 className="font-display font-bold uppercase tracking-tight text-3xl md:text-4xl leading-[0.95]">
                        On travaille avec
                        <br />
                        <span className="text-[#2f4f7f]">toutes les marques</span>
                        <br />
                        de quincaillerie.
                    </h2>
                </div>
                <div className="lg:col-span-6 lg:col-start-7 pt-2">
                    <p className="text-lg leading-relaxed text-[#4b5d7a]">
                        Pas de fournisseur unique, pas de marque imposée. On
                        installe, ajuste et répare la quincaillerie de tous les
                        manufacturiers commerciaux reconnus — du{" "}
                        <strong className="text-[#0c182b]">haut de gamme</strong>{" "}
                        au standard, peu importe ce qui est déjà sur vos portes.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                {brands.map((b) => (
                    <Link
                        key={b.name}
                        to="/catalogue"
                        data-testid={`brand-${b.slug}`}
                        className="bg-white p-6 md:p-8 flex flex-col items-center justify-center gap-3 min-h-[140px] group hover:bg-[#f3f6fb] transition-colors"
                    >
                        <img
                            src={`/brands/${b.slug}.png`}
                            alt={`Logo ${b.name}`}
                            className="max-h-10 md:max-h-12 w-auto object-contain opacity-80 group-hover:opacity-100 transition-opacity"
                            loading="lazy"
                            onError={(e) => { e.currentTarget.style.display = "none"; }}
                        />
                        <span
                            className={`font-display font-bold uppercase text-sm md:text-base tracking-tight text-[#4b5d7a] group-hover:text-[#0c182b] transition-colors text-center ${BRAND_STYLE_MAP[b.style] || ""}`}
                        >
                            {b.name}
                        </span>
                    </Link>
                ))}
            </div>

            <p className="mt-8 text-sm text-[#4b5d7a] italic">
                * Cliquez sur une marque pour voir notre catalogue de quincaillerie. Liste non exhaustive — on adapte à ce que vous avez, ou on recommande la meilleure option pour votre besoin.
            </p>
        </div>
    </section>
);
