import { Quote } from "lucide-react";
import { testimonials } from "../data";

export const HomeTestimonials = () => (
    <section
        data-testid="home-testimonials"
        className="bg-[#f3f6fb] border-b border-[#dde5f0]"
    >
        <div className="container-portech py-24 md:py-32">
            <div className="mb-14">
                <div className="tech-stamp mb-4">06 — Retours terrain</div>
                <h2 className="font-display font-bold uppercase tracking-tight text-4xl md:text-5xl leading-[0.95] max-w-3xl">
                    Ceux qui nous ont fait confiance — et pourquoi ils rappellent.
                </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-[#dde5f0] border border-[#dde5f0]">
                {testimonials.map((t) => (
                    <figure
                        key={`${t.author}-${t.context}`}
                        data-testid={`testimonial-${t.context.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}
                        className="bg-white p-8 md:p-10 flex flex-col"
                    >
                        <Quote className="w-8 h-8 text-[#2f4f7f] mb-6" />
                        <blockquote className="text-[#1e3457] leading-relaxed text-base md:text-lg mb-8 flex-1">
                            {t.quote}
                        </blockquote>
                        <figcaption className="pt-6 border-t border-[#dde5f0]">
                            <div className="font-display font-bold uppercase text-sm tracking-wider">
                                {t.author}
                            </div>
                            <div className="tech-stamp mt-1">{t.context}</div>
                        </figcaption>
                    </figure>
                ))}
            </div>
        </div>
    </section>
);
