import { Link } from "react-router-dom";
import { showcaseTiles } from "../data";

export const HomeShowcase = () => (
    <section
        data-testid="home-showcase"
        className="bg-white border-b border-[#dde5f0]"
    >
        <div className="container-portech py-20 md:py-28">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                {showcaseTiles.map((t) => (
                    <Link
                        key={t.testId}
                        to={t.to}
                        data-testid={t.testId}
                        className={`${t.className} relative overflow-hidden border border-[#dde5f0] group cursor-pointer`}
                    >
                        <img
                            src={t.img}
                            alt={t.alt}
                            className={`w-full h-full ${t.imgClass} object-cover transition-transform duration-500 group-hover:scale-105`}
                        />
                        <div className="absolute top-4 left-4 tech-stamp bg-white/95 border border-[#dde5f0] px-3 py-2">
                            {t.caption}
                        </div>
                        <div className="absolute bottom-4 right-4 bg-[#0c182b] text-white tech-stamp px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            {t.hoverLabel}
                        </div>
                    </Link>
                ))}
            </div>
        </div>
    </section>
);
