import { Minus } from "lucide-react";
import { sectors } from "../data";

export const HomeSectors = () => (
    <section
        data-testid="home-sectors"
        className="bg-[#f3f6fb] border-y border-[#dde5f0] overflow-hidden"
    >
        <div className="py-6 flex overflow-hidden">
            <div className="marquee-track flex gap-12 whitespace-nowrap pr-12 font-display uppercase text-2xl md:text-3xl font-bold text-[#1e3457] tracking-tight">
                {[...sectors, ...sectors, ...sectors].map((s, i) => (
                    <span key={`${s}-${i}`} className="flex items-center gap-12">
                        {s}
                        <Minus className="w-6 h-6 text-[#97b0d0]" />
                    </span>
                ))}
            </div>
        </div>
    </section>
);
