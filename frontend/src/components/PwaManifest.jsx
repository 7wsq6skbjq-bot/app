import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * Swaps the PWA manifest + iOS app title based on the current route so the
 * user can install TWO distinct home-screen apps from the same origin:
 *   • "/adjointe"  → "Adjointe Portech" (voice assistant, opens /adjointe)
 *   • everything else → "Portech" (full ERP, opens /admin)
 * iOS reads <link rel="manifest"> and the apple-mobile-web-app-title meta at
 * "Add to Home Screen" time, so keeping them in sync with the route fixes the
 * bug where every install became the "Adjointe" app.
 */
export const PwaManifest = () => {
    const { pathname } = useLocation();

    useEffect(() => {
        const isAdjointe = pathname.startsWith("/adjointe");
        const manifestHref = isAdjointe ? "/manifest-adjointe.json" : "/manifest.json";
        const appTitle = isAdjointe ? "Adjointe Portech" : "Portech";

        const link = document.querySelector('link[rel="manifest"]');
        if (link) link.setAttribute("href", manifestHref);

        const meta = document.querySelector('meta[name="apple-mobile-web-app-title"]');
        if (meta) meta.setAttribute("content", appTitle);
    }, [pathname]);

    return null;
};

export default PwaManifest;
