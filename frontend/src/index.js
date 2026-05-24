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

// Register the PWA service worker. This unlocks "Add to Home Screen" install
// prompts on Chrome/Edge/Android and provides a minimal offline shell.
if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js").catch(() => {
            // Silently ignore — site still works without SW, just no PWA install.
        });
    });
}
