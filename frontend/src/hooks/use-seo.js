import { useEffect } from "react";

/**
 * Lightweight SEO hook — sets document.title and meta description / og tags.
 * No external dependency. Call once at the top of each page component.
 */
export function useSeo({ title, description, canonical } = {}) {
    useEffect(() => {
        if (title) document.title = title;

        const upsertMeta = (key, attrName, value) => {
            if (!value) return;
            let el = document.head.querySelector(`meta[${key}="${attrName}"]`);
            if (!el) {
                el = document.createElement("meta");
                el.setAttribute(key, attrName);
                document.head.appendChild(el);
            }
            el.setAttribute("content", value);
        };

        upsertMeta("name", "description", description);
        upsertMeta("property", "og:title", title);
        upsertMeta("property", "og:description", description);

        if (canonical) {
            let link = document.head.querySelector('link[rel="canonical"]');
            if (!link) {
                link = document.createElement("link");
                link.setAttribute("rel", "canonical");
                document.head.appendChild(link);
            }
            link.setAttribute("href", canonical);
        }
    }, [title, description, canonical]);
}
