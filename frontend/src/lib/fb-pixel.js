/**
 * Thin wrapper around the global Facebook Pixel `fbq()` function.
 * Safe to call even if the pixel script hasn't loaded yet (ad-blockers,
 * preview deploys, slow networks) — calls become no-ops in those cases.
 *
 * Standard events we fire:
 *   - PageView     → initial page load (already in index.html)
 *   - Lead         → contact form submitted
 *   - Contact      → phone click (tel: link tapped) / email click
 *   - ViewContent  → catalogue page viewed (helps build the audience)
 */
const safeFbq = (...args) => {
    try {
        if (typeof window !== "undefined" && typeof window.fbq === "function") {
            window.fbq(...args);
        }
    } catch {
        // ad-blocker stripped fbq — silently ignore
    }
};

export const trackLead = (data = {}) => safeFbq("track", "Lead", data);
export const trackContact = (data = {}) => safeFbq("track", "Contact", data);
export const trackViewContent = (data = {}) => safeFbq("track", "ViewContent", data);
export const trackCustom = (name, data = {}) => safeFbq("trackCustom", name, data);
