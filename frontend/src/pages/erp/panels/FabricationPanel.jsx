/** Fabrication tab wrapper — hosts two sub-panels :
 *   1. Listes de coupe (existing CutListPanel)
 *   2. Moustiquaires (new MosquitoScreensPanel)
 *
 *  The sub-tab selection is persisted in localStorage so a returning user
 *  lands back where they were.
 */
import { useState } from "react";
import { Scissors, Bug, DraftingCompass } from "lucide-react";
import { CutListPanel } from "./CutListPanel";
import { MosquitoScreensPanel } from "./MosquitoScreensPanel";
import { ProductionPlansPanel } from "./ProductionPlansPanel";

const STORAGE_KEY = "portech.fabrication.subTab";

const SUB_TABS = [
    { id: "cuts",       label: "Listes de coupe", icon: Scissors },
    { id: "mosquito",   label: "Moustiquaires",   icon: Bug },
    { id: "plans",      label: "Dessin de production de porte", icon: DraftingCompass },
];

export const FabricationPanel = () => {
    const [active, setActive] = useState(() => {
        if (typeof window === "undefined") return "cuts";
        const saved = window.localStorage.getItem(STORAGE_KEY);
        return SUB_TABS.some((t) => t.id === saved) ? saved : "cuts";
    });

    const switchTo = (id) => {
        setActive(id);
        try { window.localStorage.setItem(STORAGE_KEY, id); } catch (_) { /* ignore */ }
    };

    return (
        <div data-testid="fabrication-panel" className="space-y-4">
            {/* Sub-tabs */}
            <div className="flex flex-wrap gap-2 bg-white border border-[#dde5f0] p-2"
                 data-testid="fabrication-subtabs">
                {SUB_TABS.map((t) => {
                    const Icon = t.icon;
                    const isActive = active === t.id;
                    return (
                        <button
                            key={t.id}
                            type="button"
                            onClick={() => switchTo(t.id)}
                            data-testid={`fabrication-subtab-${t.id}`}
                            className={`inline-flex items-center gap-2 px-4 py-2 border text-sm font-bold uppercase tracking-wider transition-colors ${
                                isActive
                                    ? "bg-[#0c182b] text-white border-[#0c182b]"
                                    : "bg-white text-[#4b5d7a] border-[#dde5f0] hover:bg-[#f3f6fb]"
                            }`}
                        >
                            <Icon className="w-4 h-4" />
                            {t.label}
                        </button>
                    );
                })}
            </div>

            {active === "cuts" && <CutListPanel />}
            {active === "mosquito" && <MosquitoScreensPanel />}
            {active === "plans" && <ProductionPlansPanel />}
        </div>
    );
};

export default FabricationPanel;
