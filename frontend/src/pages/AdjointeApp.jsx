import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { Send, Loader2, Bot, User, Trash2, Mic, Square, Volume2, VolumeX, LogOut, Smartphone, X, Share, Plus, Sunrise, Calendar, CalendarCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const SUGGESTIONS = [
    "Quelles factures sont impayées et le solde total ?",
    "Quels jobs sont en fabrication ?",
    "Envoie l'état de compte au client qui a le plus gros solde",
    "Envoie une relance pour ma plus vieille soumission",
];
const sessionKey = "portech_adjointe_session";

/** Read a reply aloud using the browser's built-in French voice. */
const speak = (text) => {
    try {
        if (!("speechSynthesis" in window)) return;
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = "fr-CA";
        const voices = window.speechSynthesis.getVoices();
        const fr = voices.find((v) => /fr[-_]?CA/i.test(v.lang)) || voices.find((v) => /^fr/i.test(v.lang));
        if (fr) u.voice = fr;
        u.rate = 1.0;
        window.speechSynthesis.speak(u);
    } catch { /* ignore */ }
};

export default function AdjointeApp() {
    const { http, user, logout } = useAuth();
    const [sessionId, setSessionId] = useState(() => {
        let s = localStorage.getItem(sessionKey);
        if (!s) { s = Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem(sessionKey, s); }
        return s;
    });
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [recording, setRecording] = useState(false);
    const [transcribing, setTranscribing] = useState(false);
    const [speakOn, setSpeakOn] = useState(() => localStorage.getItem("portech_adjointe_speak") === "1");
    const [deferredPrompt, setDeferredPrompt] = useState(null);
    const [showInstall, setShowInstall] = useState(false);
    const [calConnected, setCalConnected] = useState(null);
    const isStandalone = typeof window !== "undefined" && (
        window.matchMedia?.("(display-mode: standalone)").matches || window.navigator.standalone === true);
    const endRef = useRef(null);
    const mediaRef = useRef(null);
    const chunksRef = useRef([]);
    const briefedRef = useRef(false);

    useEffect(() => {
        const onBIP = (e) => { e.preventDefault(); setDeferredPrompt(e); };
        const onInstalled = () => { setDeferredPrompt(null); setShowInstall(false); };
        window.addEventListener("beforeinstallprompt", onBIP);
        window.addEventListener("appinstalled", onInstalled);
        return () => {
            window.removeEventListener("beforeinstallprompt", onBIP);
            window.removeEventListener("appinstalled", onInstalled);
        };
    }, []);

    const handleInstall = async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            try { await deferredPrompt.userChoice; } catch { /* ignore */ }
            setDeferredPrompt(null);
        } else {
            setShowInstall(true); // iOS / unsupported → show manual instructions
        }
    };

    const loadHistory = useCallback(async () => {
        try {
            const { data } = await http.get(`/admin/assistant/history?session_id=${sessionId}`);
            if (data.messages && data.messages.length) setMessages(data.messages);
        } catch { /* silent */ }
    }, [http, sessionId]);
    useEffect(() => { loadHistory(); }, [loadHistory]);
    useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading, transcribing]);
    // Prime voices list (some browsers load async)
    useEffect(() => { if ("speechSynthesis" in window) window.speechSynthesis.getVoices(); }, []);

    const send = async (text) => {
        const msg = (text ?? input).trim();
        if (!msg || loading) return;
        setError(""); setInput("");
        setMessages((m) => [...m, { role: "user", content: msg }]);
        setLoading(true);
        try {
            const { data } = await http.post("/admin/assistant/chat", { message: msg, session_id: sessionId });
            setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
            if (speakOn) speak(data.reply);
        } catch (e) {
            setError(e?.response?.data?.detail || "Échec de la réponse de l'assistante");
        } finally { setLoading(false); }
    };

    const startRecording = async () => {
        setError("");
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mr = new MediaRecorder(stream);
            chunksRef.current = [];
            mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            mr.onstop = async () => {
                stream.getTracks().forEach((t) => t.stop());
                const blob = new Blob(chunksRef.current, { type: "audio/webm" });
                if (blob.size === 0) return;
                setTranscribing(true);
                try {
                    const fd = new FormData();
                    fd.append("file", blob, "dictee.webm");
                    const { data } = await http.post("/admin/assistant/transcribe", fd, {
                        headers: { "Content-Type": "multipart/form-data" },
                    });
                    const t = (data.text || "").trim();
                    if (t) { setInput(""); await send(t); }
                    else setError("Je n'ai rien entendu — réessaie.");
                } catch (e) {
                    setError(e?.response?.data?.detail || "Échec de la transcription");
                } finally { setTranscribing(false); }
            };
            mediaRef.current = mr;
            mr.start();
            setRecording(true);
        } catch {
            setError("Micro inaccessible. Autorise le micro dans les réglages du navigateur.");
        }
    };
    const stopRecording = () => {
        try { mediaRef.current?.stop(); } catch { /* ignore */ }
        setRecording(false);
    };

    const toggleSpeak = () => {
        setSpeakOn((v) => { const nv = !v; localStorage.setItem("portech_adjointe_speak", nv ? "1" : "0"); if (!nv) window.speechSynthesis?.cancel(); return nv; });
    };

    const fetchBriefing = useCallback(async (auto = false) => {
        const todayKey = new Date().toISOString().slice(0, 10);
        if (auto && localStorage.getItem("portech_adjointe_briefing_date") === todayKey) return;
        try {
            const { data } = await http.get("/admin/assistant/briefing");
            localStorage.setItem("portech_adjointe_briefing_date", todayKey);
            setMessages((m) => [...m, { role: "assistant", content: data.text }]);
            speak(data.text);
        } catch { /* silent */ }
    }, [http]);

    // Auto morning briefing once per calendar day when the app opens.
    useEffect(() => {
        if (user && user !== false && !briefedRef.current) {
            briefedRef.current = true;
            const t = setTimeout(() => fetchBriefing(true), 900);
            return () => clearTimeout(t);
        }
    }, [user, fetchBriefing]);

    // Google Calendar status + connect-return handling
    useEffect(() => {
        if (!(user && user !== false)) return;
        http.get("/admin/calendar/status").then(({ data }) => setCalConnected(!!data.connected)).catch(() => {});
        const p = new URLSearchParams(window.location.search).get("calendar");
        if (p === "connected") { setCalConnected(true); setError(""); window.history.replaceState({}, "", "/adjointe"); }
        else if (p === "error") { setError("La connexion à Google Calendar a échoué. Réessaie."); window.history.replaceState({}, "", "/adjointe"); }
    }, [user, http]);

    const connectCalendar = async () => {
        try {
            const { data } = await http.get("/oauth/calendar/login");
            if (data?.authorization_url) window.location.href = data.authorization_url;
        } catch (e) {
            setError(e?.response?.data?.detail || "Google Calendar non configuré.");
        }
    };

    const reset = async () => {
        if (!window.confirm("Effacer cette conversation ?")) return;
        try { await http.delete(`/admin/assistant/history?session_id=${sessionId}`); } catch { /* ignore */ }
        const s = Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem(sessionKey, s); setSessionId(s); setMessages([]);
        window.speechSynthesis?.cancel();
    };

    if (user === null) {
        return (
            <div className="fixed inset-0 flex items-center justify-center bg-[#0c182b] text-[#7f92b3]">
                <Loader2 className="w-6 h-6 animate-spin" />
            </div>
        );
    }
    if (user === false) return <Navigate to="/admin/login?next=/adjointe" replace />;

    return (
        <div className="fixed inset-0 flex flex-col bg-[#0c182b] text-white" data-testid="adjointe-app">
            {/* Header */}
            <header className="flex items-center gap-3 px-4 py-3 bg-[#0c182b] border-b border-[#22314c]" style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}>
                <div className="w-9 h-9 rounded-full bg-[#12233d] flex items-center justify-center shrink-0">
                    <Bot className="w-5 h-5 text-[#4fd1c5]" />
                </div>
                <div className="min-w-0">
                    <div className="font-display font-bold uppercase tracking-wide leading-none">Adjointe Portech</div>
                    <div className="text-[11px] text-[#7f92b3]">Assistante virtuelle {user?.username ? `· ${user.username}` : ""}</div>
                </div>
                <div className="ml-auto flex items-center gap-1">
                    <button onClick={() => fetchBriefing(false)} data-testid="adjointe-briefing-btn" title="Résumé du matin"
                        className="p-2 rounded-full text-[#ffd27f] hover:bg-[#12233d]">
                        <Sunrise className="w-5 h-5" />
                    </button>
                    {!isStandalone && (
                        <button onClick={handleInstall} data-testid="adjointe-install-btn" title="Installer sur mon téléphone"
                            className="p-2 rounded-full text-[#4fd1c5] hover:bg-[#12233d]">
                            <Smartphone className="w-5 h-5" />
                        </button>
                    )}
                    <button onClick={toggleSpeak} data-testid="adjointe-speak-toggle" title={speakOn ? "Voix activée" : "Voix désactivée"}
                        className={`p-2 rounded-full ${speakOn ? "text-[#4fd1c5] bg-[#12233d]" : "text-[#7f92b3]"}`}>
                        {speakOn ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                    </button>
                    <button onClick={reset} data-testid="adjointe-reset" title="Nouvelle conversation" className="p-2 rounded-full text-[#7f92b3] hover:text-white">
                        <Trash2 className="w-5 h-5" />
                    </button>
                    <button onClick={logout} data-testid="adjointe-logout" title="Déconnexion" className="p-2 rounded-full text-[#7f92b3] hover:text-white">
                        <LogOut className="w-5 h-5" />
                    </button>
                </div>
            </header>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3" data-testid="adjointe-messages">
                {messages.length === 0 && !loading && (
                    <div className="text-center py-8 max-w-md mx-auto">
                        <Bot className="w-12 h-12 mx-auto mb-3 text-[#4fd1c5]" />
                        <p className="text-[#c7d3e8] mb-5">Bonjour Cédrick ! Écris ou appuie sur le micro pour me parler.</p>
                        <button onClick={() => fetchBriefing(false)} data-testid="adjointe-briefing-cta"
                            className="mb-4 inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-[#12233d] hover:bg-[#1a2f4f] text-[#ffd27f] text-sm border border-[#2a3d5c]">
                            <Sunrise className="w-4 h-4" /> Mon résumé du matin
                        </button>
                        <div className="grid gap-2">
                            {SUGGESTIONS.map((s, i) => (
                                <button key={i} onClick={() => send(s)} data-testid={`adjointe-suggestion-${i}`}
                                    className="text-sm px-4 py-3 rounded-2xl bg-[#12233d] hover:bg-[#1a2f4f] text-left text-[#dbe6f7] border border-[#22314c]">
                                    {s}
                                </button>
                            ))}
                        </div>
                        {!isStandalone && (
                            <button onClick={handleInstall} data-testid="adjointe-install-cta"
                                className="mt-5 inline-flex items-center gap-2 px-5 py-3 rounded-2xl bg-[#4fd1c5] text-[#07131f] font-semibold text-sm hover:brightness-110">
                                <Smartphone className="w-4 h-4" /> Installer sur mon téléphone
                            </button>
                        )}
                        <div className="mt-3">
                            {calConnected === false && (
                                <button onClick={connectCalendar} data-testid="adjointe-connect-calendar"
                                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-[#12233d] hover:bg-[#1a2f4f] text-[#8fb4ff] text-sm border border-[#2a3d5c]">
                                    <Calendar className="w-4 h-4" /> Connecter Google Calendar
                                </button>
                            )}
                            {calConnected === true && (
                                <span className="inline-flex items-center gap-2 text-[#4fd1c5] text-xs" data-testid="adjointe-calendar-connected">
                                    <CalendarCheck className="w-4 h-4" /> Google Calendar connecté
                                </span>
                            )}
                        </div>
                    </div>
                )}
                {messages.map((m, i) => (
                    <div key={i} className={`flex gap-2 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                        {m.role === "assistant" && <div className="shrink-0 w-8 h-8 rounded-full bg-[#12233d] flex items-center justify-center self-end"><Bot className="w-4 h-4 text-[#4fd1c5]" /></div>}
                        <div className={`max-w-[80%] px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap rounded-2xl ${m.role === "user" ? "bg-[#2f6df0] text-white rounded-br-md" : "bg-[#f4f7fc] text-[#0c182b] rounded-bl-md"}`}>
                            {m.content}
                            {m.role === "assistant" && "speechSynthesis" in window && (
                                <button onClick={() => speak(m.content)} className="ml-2 align-middle text-[#5a76a8] hover:text-[#2f6df0]" title="Lire à voix haute">
                                    <Volume2 className="w-3.5 h-3.5 inline" />
                                </button>
                            )}
                        </div>
                        {m.role === "user" && <div className="shrink-0 w-8 h-8 rounded-full bg-[#2f6df0] flex items-center justify-center self-end"><User className="w-4 h-4 text-white" /></div>}
                    </div>
                ))}
                {(loading || transcribing) && (
                    <div className="flex gap-2 justify-start">
                        <div className="shrink-0 w-8 h-8 rounded-full bg-[#12233d] flex items-center justify-center"><Bot className="w-4 h-4 text-[#4fd1c5]" /></div>
                        <div className="px-4 py-3 bg-[#f4f7fc] rounded-2xl rounded-bl-md flex items-center gap-2 text-[#0c182b] text-sm">
                            <Loader2 className="w-4 h-4 animate-spin" /> {transcribing ? "Transcription…" : "Réflexion…"}
                        </div>
                    </div>
                )}
                <div ref={endRef} />
            </div>

            {error && <div className="mx-4 mb-2 p-2 rounded-lg bg-[#5a1a1a] text-[#ffd4d4] text-xs" data-testid="adjointe-error">{error}</div>}

            {/* Composer */}
            <form onSubmit={(e) => { e.preventDefault(); send(); }}
                className="flex items-end gap-2 px-3 py-3 bg-[#0c182b] border-t border-[#22314c]"
                style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}>
                <button type="button" onClick={recording ? stopRecording : startRecording} disabled={loading || transcribing}
                    data-testid="adjointe-mic"
                    className={`shrink-0 w-12 h-12 rounded-full flex items-center justify-center ${recording ? "bg-red-600 animate-pulse" : "bg-[#12233d] text-[#4fd1c5]"} disabled:opacity-40`}>
                    {recording ? <Square className="w-5 h-5 text-white" /> : <Mic className="w-6 h-6" />}
                </button>
                <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={1} disabled={loading}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                    data-testid="adjointe-input" placeholder={recording ? "Je t'écoute…" : "Écris ou dicte ta question…"}
                    className="flex-1 resize-none rounded-2xl bg-[#f4f7fc] text-[#0c182b] px-4 py-3 text-[15px] focus:outline-none max-h-32" />
                <button type="submit" disabled={loading || !input.trim()} data-testid="adjointe-send"
                    className="shrink-0 w-12 h-12 rounded-full bg-[#2f6df0] flex items-center justify-center disabled:opacity-40">
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                </button>
            </form>

            {showInstall && (
                <div className="fixed inset-0 z-50 bg-black/60 flex items-end sm:items-center justify-center p-0 sm:p-4" data-testid="adjointe-install-modal" onClick={() => setShowInstall(false)}>
                    <div className="w-full sm:max-w-md bg-white text-[#0c182b] rounded-t-3xl sm:rounded-2xl p-6" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <div className="font-display font-bold uppercase text-xl tracking-tight flex items-center gap-2">
                                <Smartphone className="w-5 h-5 text-[#2f6df0]" /> Installer l&apos;app
                            </div>
                            <button onClick={() => setShowInstall(false)} data-testid="adjointe-install-close" className="p-1.5 text-[#5a76a8] hover:text-[#0c182b]">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="space-y-4 text-sm leading-relaxed">
                            <div className="rounded-xl border border-[#dde5f0] p-3">
                                <div className="font-bold mb-1 flex items-center gap-1.5">🍎 iPhone / iPad (Safari)</div>
                                <ol className="list-decimal ml-5 space-y-1 text-[#33455f]">
                                    <li>Touchez l&apos;icône <b>Partager</b> <Share className="w-3.5 h-3.5 inline align-text-bottom" /> en bas de Safari.</li>
                                    <li>Choisissez <b>« Sur l&apos;écran d&apos;accueil »</b> <Plus className="w-3.5 h-3.5 inline align-text-bottom" />.</li>
                                    <li>Touchez <b>Ajouter</b> — l&apos;icône « Adjointe Portech » apparaît sur votre écran.</li>
                                </ol>
                            </div>
                            <div className="rounded-xl border border-[#dde5f0] p-3">
                                <div className="font-bold mb-1 flex items-center gap-1.5">🤖 Android (Chrome)</div>
                                <ol className="list-decimal ml-5 space-y-1 text-[#33455f]">
                                    <li>Touchez le menu <b>⋮</b> en haut à droite de Chrome.</li>
                                    <li>Choisissez <b>« Installer l&apos;application »</b> (ou « Ajouter à l&apos;écran d&apos;accueil »).</li>
                                    <li>Confirmez — l&apos;app s&apos;installe sur votre écran d&apos;accueil.</li>
                                </ol>
                            </div>
                            <p className="text-[#5a76a8] text-xs">Une fois installée, ouvrez « Adjointe Portech » comme n&apos;importe quelle app — vous resterez connecté.</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
