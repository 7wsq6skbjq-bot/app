import { useCallback, useEffect, useRef, useState } from "react";
import { Send, Loader2, Bot, User, Trash2, Sparkles } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const SUGGESTIONS = [
    "Quelles factures sont impayées et quel est le solde total ?",
    "Quels jobs sont en fabrication en ce moment ?",
    "Quelles soumissions attendent une réponse ?",
    "Rédige un courriel de relance pour ma plus vieille facture impayée",
];

const sessionKey = "portech_assistant_session";

export const AssistantPanel = () => {
    const { http } = useAuth();
    const [sessionId, setSessionId] = useState(() => {
        let s = localStorage.getItem(sessionKey);
        if (!s) { s = Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem(sessionKey, s); }
        return s;
    });
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const endRef = useRef(null);

    const loadHistory = useCallback(async () => {
        try {
            const { data } = await http.get(`/admin/assistant/history?session_id=${sessionId}`);
            setMessages(data.messages || []);
        } catch { /* silent */ }
    }, [http, sessionId]);
    useEffect(() => { loadHistory(); }, [loadHistory]);

    useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

    const send = async (text) => {
        const msg = (text ?? input).trim();
        if (!msg || loading) return;
        setError(""); setInput("");
        setMessages((m) => [...m, { role: "user", content: msg }]);
        setLoading(true);
        try {
            const { data } = await http.post("/admin/assistant/chat", { message: msg, session_id: sessionId });
            setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
        } catch (e) {
            setError(e?.response?.data?.detail || "Échec de la réponse de l'assistante");
        } finally { setLoading(false); }
    };

    const reset = async () => {
        if (!window.confirm("Effacer cette conversation ?")) return;
        try { await http.delete(`/admin/assistant/history?session_id=${sessionId}`); } catch { /* ignore */ }
        const s = Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem(sessionKey, s); setSessionId(s); setMessages([]);
    };

    return (
        <div data-testid="assistant-panel" className="flex flex-col h-[calc(100vh-190px)]">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <div>
                    <div className="tech-stamp mb-1">Adjointe virtuelle</div>
                    <h1 className="font-display font-bold uppercase text-3xl tracking-tight flex items-center gap-2">
                        <Sparkles className="w-6 h-6 text-[#4fd1c5]" /> Assistante IA
                    </h1>
                    <p className="text-sm text-[#4b5d7a] mt-1">Pose des questions sur tes jobs, soumissions et factures — en français.</p>
                </div>
                <button onClick={reset} data-testid="assistant-reset" className="btn-secondary !py-2 !px-3 !text-xs">
                    <Trash2 className="w-3.5 h-3.5" /> Nouvelle conversation
                </button>
            </div>

            <div className="flex-1 overflow-y-auto border border-[#dde5f0] bg-[#f7f9fc] p-4 space-y-4" data-testid="assistant-messages">
                {messages.length === 0 && !loading && (
                    <div className="text-center text-[#4b5d7a] py-8">
                        <Bot className="w-10 h-10 mx-auto mb-3 text-[#2f4f7f]" />
                        <p className="text-sm mb-4">Bonjour Cédrick ! Comment puis-je t'aider aujourd'hui ?</p>
                        <div className="flex flex-wrap gap-2 justify-center max-w-2xl mx-auto">
                            {SUGGESTIONS.map((s, i) => (
                                <button key={i} onClick={() => send(s)} data-testid={`assistant-suggestion-${i}`}
                                    className="text-xs px-3 py-2 border border-[#dde5f0] bg-white hover:bg-[#eaf1fb] text-[#2f4f7f] text-left">
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
                {messages.map((m, i) => (
                    <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                        {m.role === "assistant" && <div className="shrink-0 w-8 h-8 rounded-full bg-[#0c182b] flex items-center justify-center"><Bot className="w-4 h-4 text-[#4fd1c5]" /></div>}
                        <div className={`max-w-[75%] px-4 py-2.5 text-sm whitespace-pre-wrap ${m.role === "user" ? "bg-[#0c182b] text-white" : "bg-white border border-[#dde5f0] text-[#0c182b]"}`}>
                            {m.content}
                        </div>
                        {m.role === "user" && <div className="shrink-0 w-8 h-8 rounded-full bg-[#2f4f7f] flex items-center justify-center"><User className="w-4 h-4 text-white" /></div>}
                    </div>
                ))}
                {loading && (
                    <div className="flex gap-3 justify-start">
                        <div className="shrink-0 w-8 h-8 rounded-full bg-[#0c182b] flex items-center justify-center"><Bot className="w-4 h-4 text-[#4fd1c5]" /></div>
                        <div className="px-4 py-2.5 bg-white border border-[#dde5f0]"><Loader2 className="w-4 h-4 animate-spin text-[#2f4f7f]" /></div>
                    </div>
                )}
                <div ref={endRef} />
            </div>

            {error && <div className="mt-2 p-2 border border-red-400 bg-red-50 text-red-800 text-xs">{error}</div>}

            <form onSubmit={(e) => { e.preventDefault(); send(); }} className="mt-3 flex gap-2">
                <input value={input} onChange={(e) => setInput(e.target.value)} disabled={loading}
                    data-testid="assistant-input" placeholder="Écris ta question ici…"
                    className="flex-1 border border-[#dde5f0] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#2f4f7f]" />
                <button type="submit" disabled={loading || !input.trim()} data-testid="assistant-send"
                    className="btn-primary !px-5 disabled:opacity-40">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
            </form>
        </div>
    );
};

export default AssistantPanel;
