import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogIn, ArrowLeft, ShieldCheck } from "lucide-react";
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
            className="min-h-screen bg-[#0c182b] text-white relative overflow-hidden flex flex-col"
        >
            <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
            <div className="container-portech relative py-8 flex items-center justify-between">
                <Link to="/" className="flex items-center gap-3 group">
                    <img
                        src="/brand/logo-portech-white.png"
                        alt="Portech"
                        className="h-10 w-auto"
                    />
                </Link>
                <Link
                    to="/"
                    className="tech-stamp text-[#97b0d0] hover:text-white transition-colors inline-flex items-center gap-2"
                    data-testid="admin-back-home"
                >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    Retour au site
                </Link>
            </div>

            <div className="flex-1 flex items-center justify-center px-6 py-10 relative">
                <div className="w-full max-w-md">
                    <div className="tech-stamp text-[#97b0d0] mb-4">
                        Espace administrateur
                    </div>
                    <h1 className="font-display font-bold uppercase text-4xl md:text-5xl tracking-tight leading-[0.95] mb-8">
                        Connexion
                    </h1>

                    <form
                        onSubmit={onSubmit}
                        data-testid="admin-login-form"
                        className="space-y-5 border border-[#1e3457] bg-[#0c182b]/70 p-8 backdrop-blur-sm"
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
                                className="w-full border border-[#1e3457] bg-[#0c182b] text-white px-4 py-3 placeholder-[#4b5d7a] focus:outline-none focus:ring-2 focus:ring-[#97b0d0] focus:border-[#97b0d0] transition-colors"
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
                                className="w-full border border-[#1e3457] bg-[#0c182b] text-white px-4 py-3 placeholder-[#4b5d7a] focus:outline-none focus:ring-2 focus:ring-[#97b0d0] focus:border-[#97b0d0] transition-colors"
                                placeholder="••••••••"
                            />
                        </div>

                        {error && (
                            <div
                                data-testid="admin-login-error"
                                className="p-3 border border-red-400/40 bg-red-900/30 text-red-200 text-sm"
                            >
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            data-testid="admin-login-submit"
                            disabled={submitting}
                            className="btn-primary !bg-white !text-[#0c182b] !border-white w-full justify-center disabled:opacity-60"
                        >
                            {submitting ? "Connexion…" : "Se connecter"}
                            <LogIn className="w-4 h-4" />
                        </button>

                        <div className="flex items-center gap-2 tech-stamp text-[#4b5d7a] pt-2 border-t border-[#1e3457]">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            Accès sécurisé par JWT
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default AdminLogin;
