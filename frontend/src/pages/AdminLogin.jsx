import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogIn, ArrowLeft, ShieldCheck, MapPin, Mail } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const AdminLogin = () => {
    const { login, user, error } = useAuth();
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (user && user !== false) navigate("/admin", { replace: true });
    }, [user, navigate]);

    const onSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        const ok = await login(username, password);
        setSubmitting(false);
        if (ok) navigate("/admin", { replace: true });
    };

    return (
        <div
            data-testid="page-admin-login"
            className="min-h-screen bg-white flex flex-col lg:flex-row"
        >
            {/* LEFT — dark brand panel */}
            <aside className="relative lg:w-[42%] bg-[#0c182b] text-white overflow-hidden flex flex-col">
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                <div className="relative p-8 md:p-10 flex items-center justify-between">
                    <Link to="/" className="flex items-center gap-3">
                        <img
                            src="/brand/logo-portech-white.png"
                            alt="Portech"
                            className="h-10 w-auto"
                        />
                    </Link>
                    <Link
                        to="/"
                        data-testid="admin-back-home"
                        className="tech-stamp text-[#97b0d0] hover:text-white transition-colors inline-flex items-center gap-2 lg:hidden"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" />
                        Retour
                    </Link>
                </div>

                <div className="relative flex-1 p-8 md:p-14 flex flex-col justify-center">
                    <div className="tech-stamp text-[#97b0d0] mb-5">
                        Espace administrateur
                    </div>
                    <h1 className="font-display font-bold uppercase text-4xl md:text-5xl lg:text-6xl tracking-tight leading-[0.95] mb-6">
                        Gérez vos
                        <br />
                        <span className="text-[#97b0d0]">soumissions</span>
                        <br />
                        en un clic.
                    </h1>
                    <p className="text-[#b2c3dd] leading-relaxed max-w-sm">
                        Consultez les nouveaux leads, répondez directement par
                        courriel, et gardez un œil sur les statistiques — tout
                        depuis un seul tableau de bord.
                    </p>

                    <ul className="mt-10 space-y-4 text-sm text-[#b2c3dd] max-w-sm">
                        <li className="flex items-center gap-3">
                            <div className="w-8 h-8 border border-[#1e3457] flex items-center justify-center flex-shrink-0">
                                <Mail className="w-3.5 h-3.5 text-[#97b0d0]" />
                            </div>
                            Notifications automatiques sur chaque soumission
                        </li>
                        <li className="flex items-center gap-3">
                            <div className="w-8 h-8 border border-[#1e3457] flex items-center justify-center flex-shrink-0">
                                <MapPin className="w-3.5 h-3.5 text-[#97b0d0]" />
                            </div>
                            Grand Montréal — un seul interlocuteur
                        </li>
                        <li className="flex items-center gap-3">
                            <div className="w-8 h-8 border border-[#1e3457] flex items-center justify-center flex-shrink-0">
                                <ShieldCheck className="w-3.5 h-3.5 text-[#97b0d0]" />
                            </div>
                            Accès sécurisé par JWT + cookies httpOnly
                        </li>
                    </ul>
                </div>

                <div className="relative p-8 md:p-10 tech-stamp text-[#4b5d7a] border-t border-[#1e3457]">
                    © {new Date().getFullYear()} Portech · Espace privé
                </div>
            </aside>

            {/* RIGHT — white form panel */}
            <section className="flex-1 flex flex-col bg-white">
                <div className="hidden lg:flex items-center justify-end p-8 md:p-10">
                    <Link
                        to="/"
                        data-testid="admin-back-home-desktop"
                        className="tech-stamp text-[#4b5d7a] hover:text-[#0c182b] transition-colors inline-flex items-center gap-2"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" />
                        Retour au site
                    </Link>
                </div>

                <div className="flex-1 flex items-center justify-center px-6 py-10 md:py-16">
                    <div className="w-full max-w-md">
                        <div className="tech-stamp mb-3">01 — Connexion</div>
                        <h2 className="font-display font-bold uppercase text-4xl md:text-5xl tracking-tight leading-[0.95] text-[#0c182b]">
                            Bon retour.
                        </h2>
                        <p className="mt-4 text-[#4b5d7a] leading-relaxed">
                            Entrez vos identifiants pour accéder à votre
                            tableau de bord.
                        </p>

                        <form
                            onSubmit={onSubmit}
                            data-testid="admin-login-form"
                            className="mt-10 space-y-5"
                        >
                            <div>
                                <label
                                    htmlFor="username"
                                    className="tech-stamp block mb-2"
                                >
                                    Identifiant
                                </label>
                                <input
                                    id="username"
                                    type="text"
                                    required
                                    autoComplete="username"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    data-testid="admin-login-username"
                                    className="w-full border border-[#c5d4e7] bg-white text-[#0c182b] px-4 py-3.5 placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors"
                                    placeholder="PortechAdmin"
                                />
                            </div>
                            <div>
                                <label
                                    htmlFor="password"
                                    className="tech-stamp block mb-2"
                                >
                                    Mot de passe
                                </label>
                                <input
                                    id="password"
                                    type="password"
                                    required
                                    autoComplete="current-password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    data-testid="admin-login-password"
                                    className="w-full border border-[#c5d4e7] bg-white text-[#0c182b] px-4 py-3.5 placeholder-[#97b0d0] focus:outline-none focus:ring-2 focus:ring-[#2f4f7f] focus:border-[#2f4f7f] transition-colors"
                                    placeholder="••••••••"
                                />
                            </div>

                            {error && (
                                <div
                                    data-testid="admin-login-error"
                                    className="p-3 border border-red-400 bg-red-50 text-red-800 text-sm"
                                >
                                    {error}
                                </div>
                            )}

                            <button
                                type="submit"
                                data-testid="admin-login-submit"
                                disabled={submitting}
                                className="btn-primary w-full justify-center disabled:opacity-60"
                            >
                                {submitting ? "Connexion…" : "Se connecter"}
                                <LogIn className="w-4 h-4" />
                            </button>

                            <div className="flex items-center gap-2 tech-stamp text-[#4b5d7a] pt-4 border-t border-[#dde5f0]">
                                <ShieldCheck className="w-3.5 h-3.5 text-[#2f4f7f]" />
                                Accès sécurisé par JWT
                            </div>
                        </form>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default AdminLogin;
