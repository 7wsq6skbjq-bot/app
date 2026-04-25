export const formatDate = (iso) => {
    try {
        const d = new Date(iso);
        return d.toLocaleString("fr-CA", {
            dateStyle: "medium",
            timeStyle: "short",
        });
    } catch {
        return iso;
    }
};
