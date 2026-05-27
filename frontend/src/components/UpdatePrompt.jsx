import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

/**
 * Listens for the 'portech:sw-update-ready' custom event (fired in index.js
 * when a new Service Worker version finishes installing) and shows a fixed
 * banner at the top of the screen with a one-click "Recharger" button.
 *
 * Clicking the button postMessages SKIP_WAITING to the new worker — the SW
 * then calls self.skipWaiting() and the controllerchange listener in
 * index.js triggers a full page reload, replacing the stale shell.
 *
 * No-op when no update is pending. Safe to mount globally in App.jsx.
 */
export const UpdatePrompt = () => {
    const [waitingWorker, setWaitingWorker] = useState(null);

    useEffect(() => {
        const handler = (e) => setWaitingWorker(e.detail?.worker || null);
        window.addEventListener("portech:sw-update-ready", handler);
        return () => window.removeEventListener("portech:sw-update-ready", handler);
    }, []);

    if (!waitingWorker) return null;

    const reload = () => {
        try {
            waitingWorker.postMessage({ type: "SKIP_WAITING" });
        } catch {
            // Fallback: hard reload directly
            window.location.reload();
        }
    };

    return (
        <div
            data-testid="sw-update-banner"
            className="fixed top-0 left-0 right-0 z-[100] bg-[#0b6b2f] text-white shadow-lg"
            style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}
        >
            <div className="container-portech flex items-center justify-between gap-3 py-2 px-4">
                <div className="flex items-center gap-2 text-sm">
                    <RefreshCw className="w-4 h-4 flex-shrink-0" />
                    <span><b>Nouvelle version disponible.</b> Rechargez pour appliquer les dernières corrections.</span>
                </div>
                <button
                    onClick={reload}
                    data-testid="sw-update-reload"
                    className="tech-stamp px-3 py-1.5 bg-white text-[#0b6b2f] hover:bg-[#e6f4ea] whitespace-nowrap font-bold"
                >
                    Recharger
                </button>
            </div>
        </div>
    );
};
