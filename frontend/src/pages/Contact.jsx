import { useState } from "react";
import axios from "axios";
import { ArrowUpRight, CheckCircle2, Mail, Phone, MapPin, ShieldCheck } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const initialForm = {
    name: "",
    phone: "",
    email: "",
    project_type: "",
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
    const [form, setForm] = useState(initialForm);
    const [status, setStatus] = useState("idle"); // idle | submitting | success | error
    const [errorMsg, setErrorMsg] = useState("");

    const onChange = (e) => {
        setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
    };

    const onSubmit = async (e) => {
        e.preventDefault();
        setStatus("submitting");
        setErrorMsg("");
        try {
            const payload = { ...form };
            if (!payload.project_type) delete payload.project_type;
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
                typeof detail === "string" ? detail : "Erreur de validation. Vérifiez vos informations.",
            );
        }
    };

    return (
        <div data-testid="page-contact">
            {/* Header */}
            <section
                data-testid="contact-header"
                className="relative bg-zinc-950 text-white border-b border-zinc-900 overflow-hidden"
            >
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                <div className="container-portech relative py-20 md:py-28">
                    <div className="tech-stamp text-blue-400 mb-5">
                        04 / Contact
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-5xl md:text-6xl lg:text-7xl leading-[0.92] max-w-4xl">
                        Contactez-nous.
                    </h1>
                    <p className="mt-6 max-w-2xl text-lg md:text-xl text-zinc-300 leading-relaxed">
                        Vous avez un projet ou un problème avec une porte
                        commerciale ? Écrivez-nous et on vous revient
                        rapidement.
                    </p>
                </div>
            </section>

            {/* Form + Info */}
            <section
                data-testid="contact-main"
                className="bg-white border-b border-zinc-200"
            >
                <div className="container-portech py-16 md:py-24">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14">
                        {/* FORM */}
                        <div className="lg:col-span-7">
                            <div className="border border-zinc-200">
                                <div className="p-6 md:p-8 border-b border-zinc-200 bg-zinc-50">
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
                                        <div className="flex items-start gap-4 p-6 border border-blue-700 bg-blue-50">
                                            <CheckCircle2 className="w-7 h-7 text-blue-700 flex-shrink-0 mt-0.5" />
                                            <div>
                                                <h3 className="font-display font-bold uppercase text-xl tracking-tight mb-2">
                                                    Demande envoyée
                                                </h3>
                                                <p className="text-zinc-700 leading-relaxed">
                                                    Merci ! Votre demande a été
                                                    reçue. On vous revient
                                                    rapidement — habituellement
                                                    sous 24 heures ouvrables.
                                                </p>
                                                <button
                                                    type="button"
                                                    data-testid="contact-send-another"
                                                    onClick={() =>
                                                        setStatus("idle")
                                                    }
                                                    className="mt-6 font-display uppercase text-sm font-semibold tracking-wider text-blue-700 hover:text-blue-900 inline-flex items-center gap-2"
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
                                                <label
                                                    htmlFor="name"
                                                    className="tech-stamp block mb-2"
                                                >
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
                                                    className="w-full border border-zinc-300 px-4 py-3 bg-white text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-colors"
                                                />
                                            </div>
                                            <div>
                                                <label
                                                    htmlFor="phone"
                                                    className="tech-stamp block mb-2"
                                                >
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
                                                    className="w-full border border-zinc-300 px-4 py-3 bg-white text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-colors"
                                                />
                                            </div>
                                        </div>

                                        <div>
                                            <label
                                                htmlFor="email"
                                                className="tech-stamp block mb-2"
                                            >
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
                                                className="w-full border border-zinc-300 px-4 py-3 bg-white text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-colors"
                                            />
                                        </div>

                                        <div>
                                            <label
                                                htmlFor="project_type"
                                                className="tech-stamp block mb-2"
                                            >
                                                Type de projet
                                            </label>
                                            <select
                                                id="project_type"
                                                name="project_type"
                                                value={form.project_type}
                                                onChange={onChange}
                                                data-testid="contact-input-project-type"
                                                className="w-full border border-zinc-300 px-4 py-3 bg-white text-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-colors"
                                            >
                                                <option value="">
                                                    Sélectionner…
                                                </option>
                                                {projectTypes.map((t) => (
                                                    <option key={t} value={t}>
                                                        {t}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>

                                        <div>
                                            <label
                                                htmlFor="message"
                                                className="tech-stamp block mb-2"
                                            >
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
                                                className="w-full border border-zinc-300 px-4 py-3 bg-white text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-colors resize-none"
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
                                            <div className="flex items-center gap-2 tech-stamp text-zinc-500">
                                                <ShieldCheck className="w-4 h-4" />
                                                Vos informations restent
                                                confidentielles
                                            </div>
                                        </div>
                                    </form>
                                )}
                            </div>
                        </div>

                        {/* INFO */}
                        <div className="lg:col-span-5">
                            <div className="border border-zinc-200 bg-zinc-950 text-white relative overflow-hidden">
                                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                                <div className="relative p-8 md:p-10">
                                    <div className="tech-stamp text-blue-400 mb-3">
                                        Coordonnées
                                    </div>
                                    <h2 className="font-display font-bold uppercase text-3xl tracking-tight leading-tight mb-8">
                                        Le plus rapide, c'est par courriel.
                                    </h2>
                                    <ul className="space-y-6">
                                        <li className="flex items-start gap-4">
                                            <div className="w-10 h-10 border border-zinc-700 flex items-center justify-center flex-shrink-0">
                                                <Mail className="w-4 h-4 text-blue-400" />
                                            </div>
                                            <div>
                                                <div className="tech-stamp text-zinc-500 mb-1">
                                                    Courriel
                                                </div>
                                                <a
                                                    href="mailto:info@portech.ca"
                                                    className="font-display font-semibold uppercase text-lg tracking-tight hover:text-blue-400 transition-colors"
                                                    data-testid="contact-info-email"
                                                >
                                                    info@portech.ca
                                                </a>
                                            </div>
                                        </li>
                                        <li className="flex items-start gap-4">
                                            <div className="w-10 h-10 border border-zinc-700 flex items-center justify-center flex-shrink-0">
                                                <Phone className="w-4 h-4 text-blue-400" />
                                            </div>
                                            <div>
                                                <div className="tech-stamp text-zinc-500 mb-1">
                                                    Téléphone
                                                </div>
                                                <span
                                                    className="font-display font-semibold uppercase text-lg tracking-tight"
                                                    data-testid="contact-info-phone"
                                                >
                                                    Communiqué par soumission
                                                </span>
                                            </div>
                                        </li>
                                        <li className="flex items-start gap-4">
                                            <div className="w-10 h-10 border border-zinc-700 flex items-center justify-center flex-shrink-0">
                                                <MapPin className="w-4 h-4 text-blue-400" />
                                            </div>
                                            <div>
                                                <div className="tech-stamp text-zinc-500 mb-1">
                                                    Zone de service
                                                </div>
                                                <span className="font-display font-semibold uppercase text-lg tracking-tight">
                                                    Québec — déplacement sur
                                                    chantier
                                                </span>
                                            </div>
                                        </li>
                                    </ul>

                                    <div className="mt-10 pt-8 border-t border-zinc-800">
                                        <div className="tech-stamp text-zinc-500 mb-3">
                                            Délai de réponse
                                        </div>
                                        <p className="text-zinc-300 leading-relaxed">
                                            Généralement sous{" "}
                                            <strong className="text-white">
                                                24 heures ouvrables
                                            </strong>
                                            . Les urgences de sécurité sont
                                            traitées en priorité.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="mt-6 border border-zinc-200 p-6 bg-zinc-50">
                                <div className="tech-stamp text-blue-700 mb-3">
                                    Ce qu'on vous demande
                                </div>
                                <p className="text-zinc-700 leading-relaxed text-sm">
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
