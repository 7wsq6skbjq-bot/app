/** Composer — write any free-form branded email from the ERP.
 *
 *  Replaces opening Gmail when Cédrick wants to:
 *    - Send a quick note to a client / supplier with the Portech header banner
 *    - Attach photos taken on a job site, a quote PDF, a shop drawing, etc.
 *    - Keep an audit trail (every send is logged in `erp_email_log`)
 *
 *  Reply-to is the Gmail inbox, so replies arrive in the right place.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    Send, Paperclip, X, AlertCircle, CheckCircle2, Mail, Loader2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const MAX_TOTAL_MB = 20;

const emptyForm = () => ({
    to_email: "",
    cc_email: "",
    subject: "",
    message: "",
    party_id: "",
    party_name: "",
});

// Convert File -> base64 (without data:URL prefix) using FileReader.
const fileToBase64 = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => {
        const result = String(reader.result || "");
        const idx = result.indexOf("base64,");
        resolve(idx >= 0 ? result.slice(idx + 7) : result);
    };
    reader.readAsDataURL(file);
});

const fmtBytes = (n) => {
    if (n < 1024) return `${n} o`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} ko`;
    return `${(n / 1024 / 1024).toFixed(2)} Mo`;
};

const fmtDate = (iso) => {
    if (!iso) return "";
    try {
        const d = new Date(iso);
        return d.toLocaleString("fr-CA", {
            year: "numeric", month: "2-digit", day: "2-digit",
            hour: "2-digit", minute: "2-digit",
        });
    } catch { return iso; }
};

export const ComposeEmailPanel = () => {
    const { http } = useAuth();
    const [form, setForm] = useState(emptyForm);
    const [attachments, setAttachments] = useState([]);   // [{file, b64, name, size, type}]
    const [parties, setParties] = useState([]);
    const [partyQuery, setPartyQuery] = useState("");
    const [showPartySuggest, setShowPartySuggest] = useState(false);
    const [sending, setSending] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");
    const [log, setLog] = useState([]);
    const fileInputRef = useRef(null);

    // ─── Load parties (clients + suppliers) for autocomplete ───
    const loadParties = useCallback(async () => {
        try {
            const { data } = await http.get("/admin/parties");
            setParties((prev) => (Array.isArray(data) ? data : prev));
        } catch (_) { /* non-blocking */ }
    }, [http]);

    const loadLog = useCallback(async () => {
        try {
            const { data } = await http.get("/admin/compose-email/log?limit=30");
            setLog((prev) => (Array.isArray(data) ? data : prev));
        } catch (_) { /* non-blocking */ }
    }, [http]);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [p, l] = await Promise.all([
                    http.get("/admin/parties"),
                    http.get("/admin/compose-email/log?limit=30"),
                ]);
                if (!cancelled) {
                    setParties(Array.isArray(p.data) ? p.data : []);
                    setLog(Array.isArray(l.data) ? l.data : []);
                }
            } catch {
                /* silent — user can hit Rafraîchir */
            }
        })();
        return () => { cancelled = true; };
    }, [http]);

    // ─── Recipient autocomplete suggestions ────────────────────
    const suggestions = useMemo(() => {
        const q = (partyQuery || form.to_email || "").trim().toLowerCase();
        if (!q || q.length < 2) return [];
        return parties.filter((p) => {
            return (
                (p.name || "").toLowerCase().includes(q) ||
                (p.email || "").toLowerCase().includes(q) ||
                (p.contact_name || "").toLowerCase().includes(q)
            ) && p.email;
        }).slice(0, 6);
    }, [partyQuery, form.to_email, parties]);

    const pickParty = (p) => {
        setForm((f) => ({
            ...f,
            to_email: p.email || "",
            party_id: p.id || "",
            party_name: p.name || "",
        }));
        setPartyQuery(p.name || p.email || "");
        setShowPartySuggest(false);
    };

    // ─── Attachments ───────────────────────────────────────────
    const totalBytes = attachments.reduce((s, a) => s + a.size, 0);
    const overLimit = totalBytes > MAX_TOTAL_MB * 1024 * 1024;

    const addFiles = async (fileList) => {
        const files = Array.from(fileList || []);
        if (!files.length) return;
        setErrorMsg("");
        const next = [...attachments];
        for (const f of files) {
            try {
                const b64 = await fileToBase64(f);
                next.push({
                    name: f.name, size: f.size, type: f.type || "application/octet-stream",
                    b64,
                });
            } catch (e) {
                setErrorMsg(`Impossible de lire « ${f.name} ».`);
            }
        }
        setAttachments(next);
    };

    const removeAttachment = (idx) => {
        setAttachments((a) => a.filter((_, i) => i !== idx));
    };

    // ─── Send ──────────────────────────────────────────────────
    const canSend = form.to_email && form.subject.trim() && form.message.trim() && !overLimit;

    const send = async () => {
        if (!canSend) return;
        setSending(true);
        setErrorMsg("");
        setSuccessMsg("");
        try {
            const payload = {
                to_email: form.to_email.trim(),
                subject: form.subject.trim(),
                message: form.message,
                attachments: attachments.map((a) => ({
                    filename: a.name,
                    content_base64: a.b64,
                    content_type: a.type,
                })),
            };
            if (form.cc_email && form.cc_email.trim()) payload.cc_email = form.cc_email.trim();
            if (form.party_id) payload.party_id = form.party_id;
            if (form.party_name) payload.party_name = form.party_name;

            const { data } = await http.post("/admin/compose-email", payload);
            setSuccessMsg(`Courriel envoyé à ${payload.to_email}.`);
            // Reset form but keep recipient if the user wants to send a follow-up
            setForm({ ...emptyForm(), to_email: payload.to_email });
            setAttachments([]);
            await loadLog();
            window.scrollTo({ top: 0, behavior: "smooth" });
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Échec de l'envoi du courriel.");
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <Mail className="w-6 h-6 text-[#0c182b]" />
                <h2 className="text-xl font-bold text-[#0c182b]">Composer un courriel</h2>
                <span className="text-xs text-[#4b5d7a]">
                    En-tête et pied de page Portech ajoutés automatiquement.
                </span>
            </div>

            {errorMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#fde7e7] border border-[#e89a9a] text-[#a31a1a] text-sm"
                    data-testid="compose-error">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{errorMsg}</div>
                    <button onClick={() => setErrorMsg("")} className="text-[#a31a1a] hover:underline text-xs">Fermer</button>
                </div>
            )}
            {successMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#e6f7ee] border border-[#86c9a4] text-[#0f6b3a] text-sm"
                    data-testid="compose-success">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{successMsg}</div>
                    <button onClick={() => setSuccessMsg("")} className="text-[#0f6b3a] hover:underline text-xs">Fermer</button>
                </div>
            )}

            {/* ─── Compose form ─────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-4">
                {/* To */}
                <div className="relative">
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        À · Destinataire
                    </label>
                    <input
                        type="email"
                        data-testid="compose-to"
                        value={form.to_email}
                        onChange={(e) => {
                            setForm((f) => ({ ...f, to_email: e.target.value, party_id: "", party_name: "" }));
                            setPartyQuery(e.target.value);
                            setShowPartySuggest(true);
                        }}
                        onFocus={() => setShowPartySuggest(true)}
                        onBlur={() => setTimeout(() => setShowPartySuggest(false), 200)}
                        placeholder="client@exemple.com  ou taper le nom du client/fournisseur"
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]"
                        autoComplete="off"
                    />
                    {showPartySuggest && suggestions.length > 0 && (
                        <div className="absolute z-10 left-0 right-0 top-full mt-0.5 bg-white border border-[#dde5f0] shadow-lg max-h-64 overflow-y-auto"
                            data-testid="compose-suggestions">
                            {suggestions.map((p) => (
                                <button
                                    key={p.id}
                                    type="button"
                                    onMouseDown={(e) => e.preventDefault()}
                                    onClick={() => pickParty(p)}
                                    className="w-full text-left px-3 py-2 hover:bg-[#f3f6fb] border-b border-[#f3f6fb] last:border-0 text-sm"
                                    data-testid={`compose-suggest-${p.id}`}>
                                    <div className="font-bold text-[#0c182b]">{p.name}</div>
                                    <div className="text-xs text-[#4b5d7a]">
                                        {p.email}{p.contact_name ? ` · ${p.contact_name}` : ""}
                                        {p.kind ? ` · ${p.kind === "supplier" ? "Fournisseur" : "Client"}` : ""}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                    {form.party_name && (
                        <div className="text-[10px] text-[#0f6b3a] mt-1">
                            ✓ Lié à : <b>{form.party_name}</b>
                        </div>
                    )}
                </div>

                {/* CC */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Cc (optionnel)
                    </label>
                    <input
                        type="email"
                        data-testid="compose-cc"
                        value={form.cc_email}
                        onChange={(e) => setForm((f) => ({ ...f, cc_email: e.target.value }))}
                        placeholder="copie@exemple.com"
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]"
                    />
                </div>

                {/* Subject */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Sujet
                    </label>
                    <input
                        type="text"
                        data-testid="compose-subject"
                        value={form.subject}
                        onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
                        placeholder="Ex : Suivi commande BC-0123"
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b]"
                    />
                </div>

                {/* Message */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Message
                    </label>
                    <textarea
                        data-testid="compose-message"
                        value={form.message}
                        onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
                        placeholder="Bonjour,&#10;&#10;Voici un suivi pour…&#10;&#10;Cordialement"
                        rows={10}
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm focus:outline-none focus:border-[#0c182b] font-mono"
                    />
                    <div className="text-[10px] text-[#4b5d7a] mt-1">
                        Les sauts de ligne et les paragraphes seront conservés à la réception.
                    </div>
                </div>

                {/* Attachments */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Pièces jointes ({fmtBytes(totalBytes)} / {MAX_TOTAL_MB} Mo max)
                    </label>
                    <div
                        onDragOver={(e) => { e.preventDefault(); }}
                        onDrop={(e) => { e.preventDefault(); addFiles(e.dataTransfer.files); }}
                        className="border-2 border-dashed border-[#dde5f0] p-3 text-center"
                        data-testid="compose-dropzone"
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            className="hidden"
                            onChange={(e) => addFiles(e.target.files)}
                            data-testid="compose-file-input"
                        />
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-[#dde5f0] hover:border-[#0c182b] text-sm"
                            data-testid="compose-add-attachment"
                        >
                            <Paperclip className="w-4 h-4" /> Ajouter des fichiers
                        </button>
                        <div className="text-[10px] text-[#4b5d7a] mt-1.5">
                            …ou glisse-dépose ici (PDF, images, etc.)
                        </div>
                    </div>
                    {attachments.length > 0 && (
                        <ul className="mt-2 space-y-1" data-testid="compose-attachments">
                            {attachments.map((a, i) => (
                                <li key={i} className="flex items-center gap-2 px-2 py-1 bg-[#f7f9fc] border border-[#dde5f0] text-sm">
                                    <Paperclip className="w-3.5 h-3.5 text-[#4b5d7a]" />
                                    <span className="flex-1 truncate text-[#0c182b]">{a.name}</span>
                                    <span className="text-[10px] text-[#4b5d7a]">{fmtBytes(a.size)}</span>
                                    <button
                                        onClick={() => removeAttachment(i)}
                                        className="text-[#a31a1a] hover:bg-[#fde7e7] p-0.5"
                                        data-testid={`compose-remove-attachment-${i}`}>
                                        <X className="w-3.5 h-3.5" />
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                    {overLimit && (
                        <div className="mt-2 text-[11px] text-[#a31a1a]">
                            ⚠ Limite de {MAX_TOTAL_MB} Mo dépassée — retire des fichiers ou réduis leur taille.
                        </div>
                    )}
                </div>

                {/* Send */}
                <div className="flex items-center gap-3 pt-2 border-t border-[#dde5f0]">
                    <button
                        onClick={send}
                        disabled={!canSend || sending}
                        data-testid="compose-send"
                        className="btn-primary !py-2 !px-5 !text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {sending
                            ? <><Loader2 className="w-4 h-4 animate-spin" /> Envoi…</>
                            : <><Send className="w-4 h-4" /> Envoyer</>}
                    </button>
                    <span className="text-[10px] text-[#4b5d7a]">
                        Expéditeur : <b>info@portech.info</b> · Réponses redirigées vers <b>portech.infos@gmail.com</b>
                    </span>
                </div>
            </div>

            {/* ─── Sent log ──────────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">Courriels envoyés (historique)</h3>
                    <button onClick={loadLog} className="text-xs text-[#1d4ed8] hover:underline">
                        Rafraîchir
                    </button>
                </div>
                {log.length === 0 ? (
                    <div className="text-sm italic text-[#4b5d7a]">Aucun courriel envoyé pour l&apos;instant.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm" data-testid="compose-log-table">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                                <tr>
                                    <th className="text-left px-2 py-1.5">Date</th>
                                    <th className="text-left px-2 py-1.5">Destinataire</th>
                                    <th className="text-left px-2 py-1.5">Sujet</th>
                                    <th className="text-left px-2 py-1.5 hidden sm:table-cell">PJ</th>
                                    <th className="text-left px-2 py-1.5">Statut</th>
                                </tr>
                            </thead>
                            <tbody>
                                {log.map((row) => (
                                    <tr key={row.id} className="border-b border-[#f3f6fb] hover:bg-[#f7f9fc]">
                                        <td className="px-2 py-1.5 text-[11px] text-[#4b5d7a] whitespace-nowrap">
                                            {fmtDate(row.sent_at)}
                                        </td>
                                        <td className="px-2 py-1.5">
                                            <div className="text-[#0c182b]">{row.to_email}</div>
                                            {row.party_name && (
                                                <div className="text-[10px] text-[#4b5d7a]">{row.party_name}</div>
                                            )}
                                        </td>
                                        <td className="px-2 py-1.5 text-[#0c182b]">{row.subject}</td>
                                        <td className="px-2 py-1.5 hidden sm:table-cell text-[11px] text-[#4b5d7a]">
                                            {row.attachment_filenames?.length || 0}
                                        </td>
                                        <td className="px-2 py-1.5">
                                            {row.status === "sent" ? (
                                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#0f6b3a]">
                                                    <CheckCircle2 className="w-3 h-3" /> Envoyé
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#a31a1a]">
                                                    <AlertCircle className="w-3 h-3" /> Échec
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ComposeEmailPanel;
