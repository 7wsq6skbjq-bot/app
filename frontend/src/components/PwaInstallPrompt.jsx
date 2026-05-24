import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Download, X, Smartphone } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const DISMISS_KEY = "portech_pwa_install_dismissed_at";
const DISMISS_DAYS = 14;

/**
 * Show an install prompt for the admin app on supported devices.
 * - Listens for the `beforeinstallprompt` event (Chrome / Edge / Android)
 * - Shows a custom banner inside /admin only (we don't want to push it to
 *   public visitors of the marketing site)
 * - Falls back to a clear "Add to Home Screen" instruction card on iOS Safari
 *   (which doesn't fire beforeinstallprompt)
 * - Dismissed banners are silenced for 14 days via localStorage
 */
const PwaInstallPrompt = () => {
    const { pathname } = useLocation();
    const { user } = useAuth();
    const [deferred, setDeferred] = useState(null);
    const [showBanner, setShowBanner] = useState(false);
    const [isIosSafari, setIsIosSafari] = useState(false);
    const [installed, setInstalled] = useState(false);

    // Only show the install banner once the user is authenticated as admin.
    // We don't want random visitors of /admin/login installing an app they
    // can't actually use.
    const isAuthenticated = user && user !== false;
    const isAdminRoute = pathname.startsWith("/admin") && isAuthenticated;

    useEffect(() => {
        if (!isAdminRoute) return;
        // Skip if already installed (standalone mode)
        const isStandalone =
            window.matchMedia("(display-mode: standalone)").matches ||
            window.navigator.standalone === true;
        if (isStandalone) {
            setInstalled(true);
            return;
        }

        // Respect a previous dismissal
        try {
            const dismissedAt = window.localStorage.getItem(DISMISS_KEY);
            if (dismissedAt) {
                const elapsedDays = (Date.now() - Number(dismissedAt)) / 86_400_000;
                if (elapsedDays < DISMISS_DAYS) return;
            }
        } catch {
            // localStorage unavailable
        }

        // Detect iOS Safari (no beforeinstallprompt event there)
        const ua = window.navigator.userAgent;
        const iOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
        const isStandaloneIos = window.navigator.standalone === true;
        if (iOS && !isStandaloneIos) {
            setIsIosSafari(true);
            setShowBanner(true);
        }

        const handler = (e) => {
            e.preventDefault();
            setDeferred(e);
            setShowBanner(true);
        };
        window.addEventListener("beforeinstallprompt", handler);

        const installedHandler = () => {
            setInstalled(true);
            setShowBanner(false);
        };
        window.addEventListener("appinstalled", installedHandler);

        return () => {
            window.removeEventListener("beforeinstallprompt", handler);
            window.removeEventListener("appinstalled", installedHandler);
        };
    }, [isAdminRoute]);

    const handleInstall = async () => {
        if (!deferred) return;
        deferred.prompt();
        const { outcome } = await deferred.userChoice;
        setDeferred(null);
        setShowBanner(false);
        if (outcome === "dismissed") {
            try {
                window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
            } catch { /* noop */ }
        }
    };

    const handleDismiss = () => {
        setShowBanner(false);
        try {
            window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
        } catch { /* noop */ }
    };

    if (!isAdminRoute || installed || !showBanner) return null;

    return (
        <div
            data-testid="pwa-install-banner"
            className="fixed bottom-4 right-4 left-4 md:left-auto md:max-w-md z-[60] border border-[#dde5f0] bg-white shadow-2xl"
        >
            <div className="p-4 flex items-start gap-3">
                <div className="w-10 h-10 bg-[#0c182b] flex items-center justify-center flex-shrink-0">
                    <Smartphone className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="font-display font-bold text-sm uppercase tracking-tight mb-1">
                        Installer l'app Portech
                    </div>
                    {isIosSafari ? (
                        <div className="text-xs text-[#4b5d7a] leading-relaxed">
                            Touchez l'icône <b>Partager</b> en bas de Safari, puis
                            <b> « Sur l'écran d'accueil »</b> pour installer Portech.
                        </div>
                    ) : (
                        <div className="text-xs text-[#4b5d7a] leading-relaxed">
                            Ajoutez Portech à votre écran d'accueil pour un accès rapide
                            au tableau de bord, au calendrier et aux factures.
                        </div>
                    )}
                </div>
                <button
                    onClick={handleDismiss}
                    aria-label="Fermer"
                    className="text-[#9eaec5] hover:text-[#0c182b] p-1 -m-1"
                    data-testid="pwa-install-dismiss"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>
            {!isIosSafari && (
                <div className="px-4 pb-4">
                    <button
                        onClick={handleInstall}
                        data-testid="pwa-install-cta"
                        className="btn-primary w-full justify-center !text-xs"
                    >
                        <Download className="w-4 h-4" />
                        Installer maintenant
                    </button>
                </div>
            )}
        </div>
    );
};

export default PwaInstallPrompt;
