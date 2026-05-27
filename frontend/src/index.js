import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Register the PWA service worker. Unlocks "Add to Home Screen" install
// prompts on Chrome/Edge/Android and provides a minimal offline shell.
// When a NEW service worker is detected (= deploy happened), we dispatch
// a 'portech:sw-update-ready' custom event so the app shell can render
// a "Nouvelle version disponible" banner with a one-click reload button.
if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js")
            .then((reg) => {
                if (!reg) return;
                // Check for an update every 10 min while the PWA is open.
                setInterval(() => reg.update().catch(() => {}), 10 * 60 * 1000);
                const notifyIfWaiting = (worker) => {
                    if (!worker) return;
                    if (worker.state === "installed" && navigator.serviceWorker.controller) {
                        window.dispatchEvent(new CustomEvent("portech:sw-update-ready", {
                            detail: { worker },
                        }));
                    }
                };
                // Already waiting on page load (rare but possible)
                if (reg.waiting) notifyIfWaiting(reg.waiting);
                // New SW being installed → wait for state=installed
                reg.addEventListener("updatefound", () => {
                    const w = reg.installing;
                    if (!w) return;
                    w.addEventListener("statechange", () => notifyIfWaiting(w));
                });
            })
            .catch(() => {
                // Silently ignore — site still works without SW, just no PWA install.
            });
        // When the active SW changes (after skipWaiting), reload once.
        let refreshing = false;
        navigator.serviceWorker.addEventListener("controllerchange", () => {
            if (refreshing) return;
            refreshing = true;
            window.location.reload();
        });
    });
}
