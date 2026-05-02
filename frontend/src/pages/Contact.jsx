import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import {
    ArrowUpRight,
    CheckCircle2,
    Mail,
    MapPin,
    ShieldCheck,
    Clock,
} from "lucide-react";
import { useSeo } from "@/hooks/use-seo";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const initialForm = {
    name: "",
    company: "",
    phone: "",
    email: "",
    project_type: "",
    work_location: "",
    message: "",
};

const projectTypes = [
    "Commerce / Boutique",
    "Restaurant",
    "École",
    "Tour à condos",
    "Bureau",
    "Réparation / Ajustement",
    "Autre",
];

const Contact = () => {
    const location = useLocation();
    const [form, setForm] = useState(initialForm);
    const [status, setStatus] = useState("idle");
    const [errorMsg, setErrorMsg] = useState("");

    useSeo({
        title: "Contact · Demander une soumission — Quincaillerie de porte commerciale | Portech",
        description:
            "Contactez Portech pour une soumission gratuite : installation, entretien, réparation ou remplacement de quincaillerie de porte commerciale. Grand Montréal, Laval, Rive-Sud et Rive-Nord. Réponse sous 24 h ouvrables.",
        canonical: "https://portech.info/contact",
    });

    // Pre-fill message when arriving from a Catalogue PDF download
    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const categorie = params.get("categorie");
        if (categorie) {
            setForm((f) => ({
                ...f,
                message: f.message ||
                    `Bonjour, je viens de télécharger votre fiche « ${categorie} » et j'aimerais discuter d'un projet. `,
            }));
        }
    }, [location.search]);

    const onChange = (e) =>
        setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

    const onSubmit = async (e) => {
        e.preventDefault();
        setStatus("submitting");
        setErrorMsg("");
        try {
            const payload = { ...form };
            if (!payload.project_type) delete payload.project_type;
            if (!payload.company) delete payload.company;
            await axios.post(`${API}/contact`, payload);
            setStatus("success");
            setForm(initialForm);
        } catch (err) {
            setStatus("error");
            const detail =
                err?.response?.data?.detail?.[0]?.msg ||
                err?.response?.data?.detail ||
                "Une erreur est survenue. Veuillez réessayer.";
            setErrorMsg(
                typeof detail === "string"
                    ? detail
                    : "Erreur de validation. Vérifiez vos informations.",
            );
        }
    };

    return (
        <div data-testid="page-contact">
            {/* Header */}
            <section
                data-testid="contact-header"
                className="relative bg-[#0c182b] text-white border-b border-[#1e3457] overflow-hidden"
            >
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                <div className="container-portech relative py-20 md:py-28">
                    <div className="tech-stamp text-[#97b0d0] mb-5">
                        04 / Contact
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-5xl md:text-6xl lg:text-7xl leading-[0.92] max-w-4xl">
                        Contactez-nous.
                    </h1>
                    <p className="mt-6 max-w-2xl text-lg md:text-xl text-[#b2c3dd] leading-relaxed">
                        Vous avez un projet ou un problème avec une porte
                        commerciale ? Écrivez-nous et on vous revient
                        rapidement — partout dans le Grand Montréal.
                    </p>
                </div>
            </section>

            {/* Form + Info */}
            <section
                data-testid="contact-main"
                className="bg-white border-b border-[#dde5f0]"
            >
                <div className="container-portech py-16 md:py-24">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14">
                        {/* FORM */}
                        <div className="lg:col-span-7">
                            <div className="border border-[#dde5f0]">
                                <div className="p-6 md:p-8 border-b border-[#dde5f0] bg-[#f3f6fb]">
                                    <div className="tech-stamp mb-2">
                                        Formulaire · Soumission
                                    </div>
                                    <h2 className="font-display font-bold uppercase text-2xl md:text-3xl tracking-tight">
                                        Envoyez votre demande
                                    </h2>
                                </div>

                                {status === "success" ? (
                                    <div
                                        data-testid="contact-success"
                                        className="p-8 md:p-10"
                                    >
                                        <div className="flex items-start gap-4 p-6 border border-[#1e3457] bg-[#f3f6fb]">
                                            <CheckCircle2 className="w-7 h-7 text-[#2f4f7f] flex-shrink-0 mt-0.5" />
                                            <div>
                                                <h3 className="font-display font-bold uppercase text-xl tracking-tight mb-2">
                                                    Demande envoyée
                                                </h3>
                                                <p className="text-[#1e3457] leading-relaxed">
                                                    Merci ! Votre demande a été
                                                    reçue. On vous revient
                                                    rapidement — habituellement
                                                    sous 24 heures ouvrables.
                                                </p>
                                                <button
                                                    type="button"
                                                    data-testid="contact-send-another"
                                                    onClick={() => setStatus("idle")}
                                                    className="mt-6 font-display uppercase text-sm font-semibold tracking-wider text-[#2f4f7f] hover:text-[#162842] inline-flex items-center gap-2"
                                                >
                                                    Envoyer une autre demande
                                                    <ArrowUpRight className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <form
                                        data-testid="contact-form"
                                        onSubmit={onSubmit}
                                        className="p-6 md:p-8 space-y-6"
                                        noValidate
                                    >
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                            <div>
                                                <label htmlFor="name" className="tech-stamp block mb-2">
                                                    Nom *
                                                </label>
                                                <input
                                                    id="name"
                                                    name="name"
                                                    type="text"
                                                    required
                                                    value={form.name}
                                                    onChange={onChange}
                                                    data-testid="contact-input-name"
                                                    placeholder="Prénom Nom"
                                                    className="w-full border border-[#c5d4e7] px-4 py-3 bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors"
                                                />
                                            </div>
                                            <div>
                                                <label htmlFor="phone" className="tech-stamp block mb-2">
                                                    Téléphone *
                                                </label>
                                                <input
                                                    id="phone"
                                                    name="phone"
                                                    type="tel"
                                                    required
                                                    value={form.phone}
                                                    onChange={onChange}
                                                    data-testid="contact-input-phone"
                                                    placeholder="(514) 000-0000"
                                                    className="w-full border border-[#c5d4e7] px-4 py-3 bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors"
                                                />
                                            </div>
                                        </div>

                                        <div>
                                            <label htmlFor="email" className="tech-stamp block mb-2">
                                                Courriel *
                                            </label>
                                            <input
                                                id="email"
                                                name="email"
                                                type="email"
                                                required
                                                value={form.email}
                                                onChange={onChange}
                                                data-testid="contact-input-email"
                                                placeholder="vous@entreprise.com"
                                                className="w-full border border-[#c5d4e7] px-4 py-3 bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors"
                                            />
                                        </div>

                                        <div>
                                            <label htmlFor="company" className="tech-stamp block mb-2">
                                                Entreprise <span className="text-[#97b0d0] normal-case font-normal">(facultatif)</span>
                                            </label>
                                            <input
                                                id="company"
                                                name="company"
                                                type="text"
                                                value={form.company}
                                                onChange={onChange}
                                                data-testid="contact-input-company"
                                                placeholder="Nom de votre entreprise"
                                                className="w-full border border-[#c5d4e7] px-4 py-3 bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors"
                                            />
                                        </div>

                                        <div>
                                            <label htmlFor="work_location" className="tech-stamp block mb-2">
                                                Lieu des travaux *
                                            </label>
                                            <input
                                                id="work_location"
                                                name="work_location"
                                                type="text"
                                                required
                                                value={form.work_location}
                                                onChange={onChange}
                                                data-testid="contact-input-work-location"
                                                placeholder="Adresse ou ville (ex. : 123 rue Saint-Denis, Montréal)"
                                                className="w-full border border-[#c5d4e7] px-4 py-3 bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors"
                                            />
                                        </div>

                                        <div>
                                            <label htmlFor="project_type" className="tech-stamp block mb-2">
                                                Type de projet
                                            </label>
                                            <select
                                                id="project_type"
                                                name="project_type"
                                                value={form.project_type}
                                                onChange={onChange}
                                                data-testid="contact-input-project-type"
                                                className="w-full border border-[#c5d4e7] px-4 py-3 bg-white text-[#0c182b] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors"
                                            >
                                                <option value="">Sélectionner…</option>
                                                {projectTypes.map((t) => (
                                                    <option key={t} value={t}>
                                                        {t}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>

                                        <div>
                                            <label htmlFor="message" className="tech-stamp block mb-2">
                                                Message *
                                            </label>
                                            <textarea
                                                id="message"
                                                name="message"
                                                required
                                                rows={5}
                                                value={form.message}
                                                onChange={onChange}
                                                data-testid="contact-input-message"
                                                placeholder="Décrivez votre besoin : type de porte, nombre d'ouvertures, quincaillerie recherchée, délai…"
                                                className="w-full border border-[#c5d4e7] px-4 py-3 bg-white text-[#0c182b] placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors resize-none"
                                            />
                                        </div>

                                        {status === "error" && (
                                            <div
                                                data-testid="contact-error"
                                                className="p-4 border border-red-400 bg-red-50 text-red-800 text-sm"
                                            >
                                                {errorMsg}
                                            </div>
                                        )}

                                        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 pt-2">
                                            <button
                                                type="submit"
                                                data-testid="contact-submit"
                                                disabled={status === "submitting"}
                                                className="btn-primary disabled:opacity-60 disabled:cursor-not-allowed"
                                            >
                                                {status === "submitting"
                                                    ? "Envoi en cours…"
                                                    : "Envoyer ma demande"}
                                                <ArrowUpRight className="w-4 h-4" />
                                            </button>
                                            <div className="flex items-center gap-2 tech-stamp text-[#4b5d7a]">
                                                <ShieldCheck className="w-4 h-4" />
                                                Vos informations restent confidentielles
                                            </div>
                                        </div>
                                    </form>
                                )}
                            </div>
                        </div>

                        {/* INFO */}
                        <div className="lg:col-span-5">
                            <div className="border border-[#dde5f0] bg-[#0c182b] text-white relative overflow-hidden">
                                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                                <div className="relative p-8 md:p-10">
                                    <div className="tech-stamp text-[#97b0d0] mb-3">
                                        Coordonnées
                                    </div>
                                    <h2 className="font-display font-bold uppercase text-3xl tracking-tight leading-tight mb-8">
                                        Le plus rapide, c'est par courriel.
                                    </h2>
                                    <ul className="space-y-6">
                                        <li className="flex items-start gap-4">
                                            <div className="w-10 h-10 border border-[#1e3457] flex items-center justify-center flex-shrink-0">
                                                <Mail className="w-4 h-4 text-[#97b0d0]" />
                                            </div>
                                            <div>
                                                <div className="tech-stamp text-[#97b0d0] mb-1">
                                                    Courriel
                                                </div>
                                                <a
                                                    href="mailto:portech.infos@gmail.com"
                                                    className="font-display font-semibold uppercase text-lg tracking-tight hover:text-[#97b0d0] transition-colors"
                                                    data-testid="contact-info-email"
                                                >
                                                    portech.infos@gmail.com
                                                </a>
                                            </div>
                                        </li>
                                        <li className="flex items-start gap-4">
                                            <div className="w-10 h-10 border border-[#1e3457] flex items-center justify-center flex-shrink-0">
                                                <MapPin className="w-4 h-4 text-[#97b0d0]" />
                                            </div>
                                            <div>
                                                <div className="tech-stamp text-[#97b0d0] mb-1">
                                                    Zone de service
                                                </div>
                                                <span
                                                    className="font-display font-semibold uppercase text-lg tracking-tight"
                                                    data-testid="contact-info-zone"
                                                >
                                                    Grand Montréal
                                                </span>
                                            </div>
                                        </li>
                                        <li className="flex items-start gap-4">
                                            <div className="w-10 h-10 border border-[#1e3457] flex items-center justify-center flex-shrink-0">
                                                <Clock className="w-4 h-4 text-[#97b0d0]" />
                                            </div>
                                            <div>
                                                <div className="tech-stamp text-[#97b0d0] mb-1">
                                                    Délai de réponse
                                                </div>
                                                <span className="font-display font-semibold uppercase text-lg tracking-tight">
                                                    Sous 24 h ouvrables
                                                </span>
                                            </div>
                                        </li>
                                    </ul>

                                    <div className="mt-10 pt-8 border-t border-[#1e3457]">
                                        <div className="tech-stamp text-[#97b0d0] mb-3">
                                            Bon à savoir
                                        </div>
                                        <p className="text-[#b2c3dd] leading-relaxed">
                                            Les urgences de sécurité (barres
                                            antipaniques HS, portes qui ne
                                            verrouillent plus) sont traitées en{" "}
                                            <strong className="text-white">priorité</strong>.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="mt-6 border border-[#dde5f0] p-6 bg-[#f3f6fb]">
                                <div className="tech-stamp text-[#2f4f7f] mb-3">
                                    Ce qu'on vous demande
                                </div>
                                <p className="text-[#1e3457] leading-relaxed text-sm">
                                    Plus vous êtes précis, plus la soumission
                                    est juste : type de porte, nombre
                                    d'ouvertures, quincaillerie existante,
                                    contraintes d'horaire, photos si possible.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default Contact;
