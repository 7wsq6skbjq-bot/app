/** Rapports d'expertise — Field inspection report builder + PDF export.
 *
 *  Cédrick uses this on-site: he selects a client, adds each door he
 *  inspects (dimensions, series, hardware), notes observations/impacts/
 *  recommendation for each, snaps photos from his phone, and hits
 *  "Générer PDF" or "Envoyer". The output is a fully-branded technical
 *  report matching the layout he already uses (5 numbered sections).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    ClipboardList, Plus, Save, Trash2, RefreshCw, Download, Send, Camera,
    ChevronDown, ChevronRight, AlertCircle, CheckCircle2, Loader2, X,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
    REPORT_STATUSES, emptyExpertReport, emptyInspectedDoor, emptyParty,
    formatDate, newKey, stripKeys, todayISO,
} from "../utils";

const fileToBase64 = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => {
        const s = String(reader.result || "");
        const idx = s.indexOf("base64,");
        resolve(idx >= 0 ? s.slice(idx + 7) : s);
    };
    reader.readAsDataURL(file);
});

/**
 * Resize a photo before upload:
 *   - decode via <img>
 *   - draw onto a canvas at max 2000 px on the longest side
 *   - re-encode as JPEG @ quality 0.82
 *
 * This solves 3 pain points:
 *   1) HEIC iPhone photos → become JPEG (universal decoder support)
 *   2) 10-15 MB originals → become 400-900 KB (way under any proxy limit)
 *   3) Portrait / landscape orientation preserved (canvas honors EXIF-baked
 *      orientation once decoded by the browser).
 *
 * If decoding fails (rare — e.g. iOS HEIC on desktop Chrome), we fall back
 * to the original file so nothing is lost.
 */
const resizePhoto = (file) => new Promise((resolve) => {
    // Non-image → pass through untouched
    if (!file.type || !file.type.startsWith("image/")) {
        return resolve(file);
    }
    const url = URL.createObjectURL(file);
    const img = new window.Image();
    const cleanup = () => URL.revokeObjectURL(url);
    img.onerror = () => { cleanup(); resolve(file); };  // fallback → original
    img.onload = () => {
        try {
            const maxSide = 2000;
            let { naturalWidth: w, naturalHeight: h } = img;
            const longest = Math.max(w, h);
            if (longest > maxSide) {
                const ratio = maxSide / longest;
                w = Math.round(w * ratio);
                h = Math.round(h * ratio);
            }
            const canvas = document.createElement("canvas");
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0, w, h);
            canvas.toBlob((blob) => {
                cleanup();
                if (!blob) return resolve(file);
                // Rename to .jpg so backend accepts it (HEIC → JPEG)
                const base = (file.name || "photo").replace(/\.[^.]+$/, "");
                const newFile = new File([blob], `${base}.jpg`, {
                    type: "image/jpeg", lastModified: Date.now(),
                });
                resolve(newFile);
            }, "image/jpeg", 0.82);
        } catch {
            cleanup();
            resolve(file);
        }
    };
    img.src = url;
});

// Editable list of bullet items — used for observations + impacts.
const BulletEditor = ({ label, items, onChange, testidPrefix }) => {
    const set = (i, v) => onChange(items.map((it, idx) => (idx === i ? v : it)));
    const add = () => onChange([...(items || []), ""]);
    const del = (i) => onChange(items.filter((_, idx) => idx !== i));
    return (
        <div>
            <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider">{label}</span>
                <button type="button" onClick={add}
                    className="text-[#1d4ed8] hover:underline text-xs inline-flex items-center gap-1"
                    data-testid={`${testidPrefix}-add`}>
                    <Plus className="w-3 h-3" /> Ajouter un point
                </button>
            </div>
            {(items || []).length === 0 && (
                <div className="text-[11px] italic text-[#4b5d7a] pl-2">
                    Aucun point saisi. Clique « Ajouter un point » pour commencer.
                </div>
            )}
            {(items || []).map((it, i) => (
                <div key={i} className="flex items-center gap-1 mb-1">
                    <span className="text-[#4b5d7a]">•</span>
                    <input type="text" value={it}
                        onChange={(e) => set(i, e.target.value)}
                        placeholder={`Point ${i + 1}`}
                        className="flex-1 px-2 py-1 border border-[#dde5f0] text-sm"
                        data-testid={`${testidPrefix}-${i}`} />
                    <button type="button" onClick={() => del(i)}
                        className="text-[#a31a1a] hover:bg-[#fde7e7] p-1">
                        <X className="w-3 h-3" />
                    </button>
                </div>
            ))}
        </div>
    );
};

// One collapsible door card.
const DoorCard = ({ door, index, onChange, onRemove, canDelete, reportId, photos, onUploadPhotos, onDeletePhoto, onCaptionSaved, http }) => {
    const [expanded, setExpanded] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({ done: 0, total: 0, failed: [] });
    const fileRef = useRef(null);

    const set = (k, v) => onChange({ ...door, [k]: v });

    // Sequential per-file upload:
    //   * resize each photo to max 2000 px JPEG (fixes HEIC + 10 MB iPhone)
    //   * upload ONE at a time (bypasses proxy body-size limits)
    //   * a bad photo doesn't kill the batch
    //   * UI shows "Photo X sur N"
    const handleFiles = async (fileList) => {
        const files = Array.from(fileList || []);
        if (!files.length) return;
        setUploading(true);
        setUploadProgress({ done: 0, total: files.length, failed: [] });
        const failed = [];
        for (let i = 0; i < files.length; i++) {
            const original = files[i];
            try {
                const resized = await resizePhoto(original);
                const b64 = await fileToBase64(resized);
                await onUploadPhotos([{
                    filename: resized.name || `photo-${Date.now()}.jpg`,
                    content_base64: b64,
                    caption: "",
                    door_index: index,
                }]);
            } catch (e) {
                failed.push(original.name || `photo ${i + 1}`);
            }
            setUploadProgress({ done: i + 1, total: files.length, failed: [...failed] });
        }
        setUploading(false);
        if (fileRef.current) fileRef.current.value = "";
        if (failed.length) {
            window.alert(
                `${files.length - failed.length} photo(s) ajoutée(s).\n\n`
                + `Échec pour :\n- ${failed.join("\n- ")}\n\n`
                + "Réessaie individuellement les photos en échec.",
            );
        }
        // Reset progress a bit later so the user sees "13/13"
        setTimeout(() => setUploadProgress({ done: 0, total: 0, failed: [] }), 1500);
    };

    return (
        <div className="border border-[#dde5f0] bg-white mb-3" data-testid={`door-card-${index}`}>
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 bg-[#f3f6fb] border-b border-[#dde5f0]">
                <button type="button" onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-2 text-[#0c182b] font-bold text-sm">
                    {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    Porte {index + 1} · <span className="font-mono">{door.tag || "sans tag"}</span>
                    {door.location && <span className="text-[#4b5d7a] font-normal">— {door.location}</span>}
                </button>
                <button type="button" onClick={onRemove}
                    disabled={!canDelete}
                    className="text-[#a31a1a] hover:bg-[#fde7e7] p-1 disabled:opacity-30 disabled:cursor-not-allowed"
                    data-testid={`door-remove-${index}`}>
                    <Trash2 className="w-3.5 h-3.5" />
                </button>
            </div>

            {expanded && (
                <div className="p-3 space-y-3">
                    {/* Identification */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <input type="text" placeholder="Tag / n° (ex. P-101)"
                            value={door.tag} onChange={(e) => set("tag", e.target.value)}
                            data-testid={`door-tag-${index}`}
                            className="px-3 py-2 border border-[#dde5f0] text-sm font-mono" />
                        <input type="text" placeholder="Emplacement (ex. Entrée principale)"
                            value={door.location} onChange={(e) => set("location", e.target.value)}
                            className="px-3 py-2 border border-[#dde5f0] text-sm" />
                    </div>

                    {/* Specs */}
                    <details className="border border-[#dde5f0]">
                        <summary className="px-3 py-2 bg-[#f7f9fc] cursor-pointer text-sm font-bold text-[#0c182b]">
                            Description technique
                        </summary>
                        <div className="p-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <input type="text" placeholder="Série (AT1000, Kawneer 190…)"
                                value={door.series} onChange={(e) => set("series", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="text" placeholder="Modèle / description"
                                value={door.model} onChange={(e) => set("model", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="number" placeholder="Largeur (mm)"
                                value={door.width_mm ?? ""}
                                onChange={(e) => set("width_mm", e.target.value === "" ? null : Number(e.target.value))}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="number" placeholder="Hauteur (mm)"
                                value={door.height_mm ?? ""}
                                onChange={(e) => set("height_mm", e.target.value === "" ? null : Number(e.target.value))}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="text" placeholder="Finition (anodisé clair, noir…)"
                                value={door.finish} onChange={(e) => set("finish", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="text" placeholder="Configuration (simple, double…)"
                                value={door.configuration} onChange={(e) => set("configuration", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="text" placeholder="Pentures"
                                value={door.hinges} onChange={(e) => set("hinges", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="text" placeholder="Serrure"
                                value={door.lock} onChange={(e) => set("lock", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="text" placeholder="Gâche électrique"
                                value={door.electric_strike} onChange={(e) => set("electric_strike", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="text" placeholder="Seuil"
                                value={door.threshold} onChange={(e) => set("threshold", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm" />
                            <input type="text" placeholder="Trim / Moulure"
                                value={door.trim} onChange={(e) => set("trim", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm sm:col-span-2" />
                            <textarea rows={2} placeholder="Notes libres sur cette porte"
                                value={door.other_specs} onChange={(e) => set("other_specs", e.target.value)}
                                className="px-3 py-2 border border-[#dde5f0] text-sm sm:col-span-2" />
                        </div>
                    </details>

                    {/* Deficiencies */}
                    <div className="space-y-3 border-t border-[#dde5f0] pt-3">
                        <BulletEditor
                            label="Observations"
                            items={door.observations}
                            onChange={(v) => set("observations", v)}
                            testidPrefix={`door-${index}-obs`}
                        />
                        <BulletEditor
                            label="Impacts"
                            items={door.impacts}
                            onChange={(v) => set("impacts", v)}
                            testidPrefix={`door-${index}-imp`}
                        />
                        <div>
                            <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                                Recommandation
                            </label>
                            <textarea rows={2} value={door.recommendation}
                                onChange={(e) => set("recommendation", e.target.value)}
                                placeholder='Ex : Remplacer les vis par des ancrages 2" et sceller le pourtour.'
                                className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                        </div>
                    </div>

                    {/* Photos */}
                    <div className="border-t border-[#dde5f0] pt-3">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider">
                                Photos ({photos.length})
                            </span>
                            <input ref={fileRef} type="file" accept="image/*" multiple capture="environment"
                                className="hidden"
                                onChange={(e) => handleFiles(e.target.files)}
                                data-testid={`door-photo-input-${index}`} />
                            <button type="button" onClick={() => fileRef.current?.click()}
                                disabled={!reportId || uploading}
                                className="btn-secondary !py-1.5 !px-2.5 !text-xs disabled:opacity-40"
                                data-testid={`door-photo-add-${index}`}>
                                {uploading
                                    ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        {uploadProgress.total > 0
                                            ? `Photo ${uploadProgress.done} / ${uploadProgress.total}…`
                                            : "Upload…"}
                                      </>
                                    : <><Camera className="w-3.5 h-3.5" /> Ajouter photos</>}
                            </button>
                        </div>
                        {!reportId && (
                            <div className="text-[11px] italic text-[#4b5d7a] px-2">
                                Enregistre d&apos;abord le rapport pour pouvoir ajouter des photos.
                            </div>
                        )}
                        {photos.length > 0 && (
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {photos.map((p) => (
                                    <PhotoThumb key={p.id} photo={p} reportId={reportId}
                                        http={http} onDelete={() => onDeletePhoto(p.id)}
                                        onCaptionSaved={onCaptionSaved} />
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

// Photo thumbnail with delete button + editable caption/note.
const PhotoThumb = ({ photo, reportId, http, onDelete, onCaptionSaved }) => {
    const [src, setSrc] = useState("");
    const [captionDraft, setCaptionDraft] = useState(photo.caption || "");
    const [savingCap, setSavingCap] = useState(false);
    // Track the last value we successfully persisted so we know if the
    // draft has diverged (avoids showing a "Save" button when the user
    // didn't actually edit).
    const [savedCaption, setSavedCaption] = useState(photo.caption || "");

    useEffect(() => {
        let objUrl = null;
        (async () => {
            try {
                const resp = await http.get(
                    `/admin/expert-reports/${reportId}/photos/${photo.filename}`,
                    { responseType: "blob" },
                );
                objUrl = URL.createObjectURL(resp.data);
                setSrc(objUrl);
            } catch { /* silent */ }
        })();
        return () => { if (objUrl) URL.revokeObjectURL(objUrl); };
    }, [http, reportId, photo.filename]);

    const dirty = captionDraft !== savedCaption;

    const saveCaption = async () => {
        setSavingCap(true);
        try {
            await http.patch(
                `/admin/expert-reports/${reportId}/photos/${photo.id}`,
                { caption: captionDraft },
            );
            setSavedCaption(captionDraft);
            if (onCaptionSaved) onCaptionSaved();
        } catch (e) {
            alert(e?.response?.data?.detail || "Échec de la sauvegarde de la note.");
        } finally { setSavingCap(false); }
    };

    return (
        <div className="relative border border-[#dde5f0] bg-[#f7f9fc]"
            data-testid={`photo-thumb-${photo.id}`}>
            {src ? (
                <img src={src} alt={savedCaption || "photo"} className="w-full h-24 object-cover" />
            ) : (
                <div className="w-full h-24 flex items-center justify-center text-[#4b5d7a] text-[10px]">Chargement…</div>
            )}
            <button type="button" onClick={onDelete}
                className="absolute top-1 right-1 bg-white/90 text-[#a31a1a] p-1 hover:bg-white"
                title="Supprimer">
                <X className="w-3 h-3" />
            </button>
            {/* Editable caption / reference note */}
            <div className="p-1 border-t border-[#dde5f0] bg-white">
                <input
                    type="text"
                    value={captionDraft}
                    onChange={(e) => setCaptionDraft(e.target.value)}
                    placeholder='Ex: "Réf. #1" ou "Voir photo 3"'
                    data-testid={`photo-caption-${photo.id}`}
                    className="w-full px-1.5 py-1 border border-[#dde5f0] text-[10px] focus:outline-none focus:border-[#0c182b]"
                    maxLength={500}
                />
                {dirty && (
                    <button type="button" onClick={saveCaption}
                        disabled={savingCap}
                        data-testid={`photo-caption-save-${photo.id}`}
                        className="mt-1 w-full text-[9px] py-0.5 bg-[#0c182b] text-white hover:bg-[#1a2b4a] tech-stamp disabled:opacity-50">
                        {savingCap ? "…" : "Enregistrer la note"}
                    </button>
                )}
            </div>
        </div>
    );
};

export const ExpertReportsPanel = () => {
    const { http, getToken } = useAuth();
    const [list, setList] = useState([]);
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [form, setForm] = useState(emptyExpertReport());
    const [editingId, setEditingId] = useState(null);
    const [photos, setPhotos] = useState([]);
    const [busy, setBusy] = useState(false);
    const [sending, setSending] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");
    const topRef = useRef(null);

    // ─── Initial load ─────────────────────────────────────────
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [r, c] = await Promise.all([
                    http.get("/admin/expert-reports"),
                    http.get("/admin/parties?kind=customer"),
                ]);
                if (!cancelled) {
                    setList(Array.isArray(r.data) ? r.data : []);
                    setClients(Array.isArray(c.data) ? c.data : []);
                    setLoading(false);
                }
            } catch (e) {
                if (!cancelled) {
                    setErrorMsg(e?.response?.data?.detail || "Erreur de chargement.");
                    setLoading(false);
                }
            }
        })();
        return () => { cancelled = true; };
    }, [http]);

    const reload = useCallback(async () => {
        try {
            const { data } = await http.get("/admin/expert-reports");
            setList(Array.isArray(data) ? data : []);
        } catch { /* silent */ }
    }, [http]);

    // ─── Helpers ──────────────────────────────────────────────
    const newReport = () => {
        setForm(emptyExpertReport());
        setEditingId(null);
        setPhotos([]);
        setSuccessMsg("");
        setErrorMsg("");
        topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    const openEdit = (r) => {
        setForm({
            ...r,
            doors: (r.doors || []).map((d) => ({ ...d, _key: newKey() })),
        });
        setEditingId(r.id);
        setPhotos(r.photos || []);
        setSuccessMsg("");
        setErrorMsg("");
        topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    const updateDoor = (idx, next) => {
        setForm((f) => {
            const doors = [...f.doors];
            doors[idx] = next;
            return { ...f, doors };
        });
    };
    const addDoor = () => setForm((f) => ({ ...f, doors: [...f.doors, emptyInspectedDoor()] }));
    const removeDoor = (idx) => setForm((f) => ({
        ...f, doors: f.doors.filter((_, i) => i !== idx),
    }));

    const clientAutocomplete = useMemo(() => {
        const q = (form.client_snapshot?.name || "").trim().toLowerCase();
        if (!q || q.length < 2) return [];
        return clients.filter((p) =>
            (p.name || "").toLowerCase().includes(q) ||
            (p.email || "").toLowerCase().includes(q),
        ).slice(0, 5);
    }, [form.client_snapshot, clients]);

    const pickClient = (p) => {
        setForm((f) => ({ ...f, client_snapshot: { ...emptyParty("customer"), ...p } }));
    };

    // ─── Save / delete ────────────────────────────────────────
    const save = async () => {
        if (!form.client_snapshot?.name) {
            setErrorMsg("Le nom du client est requis.");
            return;
        }
        if (!form.project_name) {
            setErrorMsg("Le nom du projet est requis.");
            return;
        }
        setBusy(true);
        setErrorMsg("");
        try {
            const payload = {
                client_snapshot: form.client_snapshot,
                project_name: form.project_name,
                project_address: form.project_address || "",
                project_city: form.project_city || "",
                inspection_date: form.inspection_date || todayISO(),
                inspector_name: form.inspector_name || "Cédrick Pimparé",
                inspector_title: form.inspector_title || "Expert Portes Commerciales – Portech",
                mandated_by: form.mandated_by || "",
                purpose: form.purpose || "",
                doors: stripKeys(form.doors),
                risks: form.risks || "",
                conclusion: form.conclusion || "",
                status: form.status || "brouillon",
            };
            const url = editingId ? `/admin/expert-reports/${editingId}` : "/admin/expert-reports";
            const method = editingId ? "put" : "post";
            const { data } = await http[method](url, payload);
            setEditingId(data.id);
            setForm({ ...data, doors: (data.doors || []).map((d) => ({ ...d, _key: newKey() })) });
            setPhotos(data.photos || []);
            setSuccessMsg(editingId
                ? `Rapport RAP-${String(data.number).padStart(4, "0")} mis à jour.`
                : `Rapport RAP-${String(data.number).padStart(4, "0")} créé. Tu peux maintenant ajouter des photos.`);
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'enregistrement.");
        } finally { setBusy(false); }
    };

    const removeReport = async (id) => {
        if (!window.confirm("Supprimer ce rapport et toutes ses photos ?")) return;
        try {
            await http.delete(`/admin/expert-reports/${id}`);
            if (editingId === id) newReport();
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur de suppression.");
        }
    };

    // ─── Photo upload / delete ────────────────────────────────
    const uploadPhotos = async (items) => {
        if (!editingId) return;
        try {
            const { data } = await http.post(
                `/admin/expert-reports/${editingId}/photos`, { photos: items },
            );
            setPhotos(data.photos || []);
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur lors de l'ajout des photos.");
        }
    };
    const deletePhoto = async (photoId) => {
        if (!editingId) return;
        try {
            const { data } = await http.delete(
                `/admin/expert-reports/${editingId}/photos/${photoId}`,
            );
            setPhotos(data.photos || []);
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur de suppression.");
        }
    };

    // Refetch the current report to pull updated photo captions.
    const refetchPhotos = async () => {
        if (!editingId) return;
        try {
            const { data } = await http.get(`/admin/expert-reports/${editingId}`);
            setPhotos(data.photos || []);
        } catch { /* silent */ }
    };

    const photosForDoor = (idx) => photos.filter((p) => p.door_index === idx);

    // ─── PDF & email ──────────────────────────────────────────
    const downloadPdf = (id) => {
        const base = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");
        const token = encodeURIComponent(getToken() || "");
        const url = `${base}/api/admin/expert-reports/${id}/pdf?token=${token}`;
        const isMobile = /iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
        if (isMobile) window.location.href = url; else window.open(url, "_blank");
    };

    const sendEmail = async (report) => {
        const defaultEmail = report.client_snapshot?.email || "";
        const to = window.prompt(
            `Envoyer RAP-${String(report.number).padStart(4, "0")} à quelle adresse ?`,
            defaultEmail,
        );
        if (!to) return;
        setSending(true);
        try {
            await http.post(`/admin/expert-reports/${report.id}/send-email`, { to_email: to });
            setSuccessMsg(`Rapport envoyé à ${to}.`);
            await reload();
        } catch (e) {
            setErrorMsg(e?.response?.data?.detail || "Erreur d'envoi.");
        } finally { setSending(false); }
    };

    // ──────────────────────────────────────────────────────────
    return (
        <div className="space-y-6" ref={topRef}>
            <div className="flex items-center gap-3 flex-wrap">
                <ClipboardList className="w-6 h-6 text-[#0c182b]" />
                <h2 className="text-xl font-bold text-[#0c182b]">Rapports d&apos;expertise</h2>
                <span className="text-xs text-[#4b5d7a]">
                    Inspection sur chantier · portes, déficiences, photos → PDF brandé prêt à envoyer.
                </span>
                <button onClick={newReport} className="ml-auto btn-secondary !py-1.5 !px-3 !text-xs"
                    data-testid="report-new">
                    <Plus className="w-3.5 h-3.5" /> Nouveau
                </button>
            </div>

            {errorMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#fde7e7] border border-[#e89a9a] text-[#a31a1a] text-sm"
                    data-testid="report-error">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{errorMsg}</div>
                    <button onClick={() => setErrorMsg("")} className="text-[#a31a1a] hover:underline text-xs">Fermer</button>
                </div>
            )}
            {successMsg && (
                <div className="flex items-start gap-2 px-3 py-2 bg-[#e6f7ee] border border-[#86c9a4] text-[#0f6b3a] text-sm"
                    data-testid="report-success">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">{successMsg}</div>
                    <button onClick={() => setSuccessMsg("")} className="text-[#0f6b3a] hover:underline text-xs">Fermer</button>
                </div>
            )}

            {/* ─── Form ─────────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4 space-y-4">
                <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">
                        {editingId ? `Modifier RAP-${String(form.number || "").padStart(4, "0")}` : "Nouveau rapport"}
                    </h3>
                    <select value={form.status || "brouillon"}
                        onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                        className="ml-auto px-2 py-1 border border-[#dde5f0] text-xs bg-white">
                        {REPORT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                </div>

                {/* Client */}
                <div className="relative">
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        Client
                    </label>
                    <input type="text" value={form.client_snapshot?.name || ""}
                        onChange={(e) => setForm((f) => ({
                            ...f, client_snapshot: { ...f.client_snapshot, name: e.target.value },
                        }))}
                        placeholder="Nom du client — commence à taper pour autocompléter"
                        data-testid="report-client-name"
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                    {clientAutocomplete.length > 0 && form.client_snapshot?.name && (
                        <div className="mt-1 border border-[#dde5f0] bg-white">
                            {clientAutocomplete.map((p) => (
                                <button key={p.id} type="button"
                                    onClick={() => pickClient(p)}
                                    className="w-full text-left px-3 py-1.5 hover:bg-[#f3f6fb] border-b border-[#f3f6fb] last:border-0 text-sm">
                                    <div className="text-[#0c182b]">{p.name}</div>
                                    <div className="text-[10px] text-[#4b5d7a]">{p.email || "—"}</div>
                                </button>
                            ))}
                        </div>
                    )}
                    <input type="email" placeholder="Courriel du client"
                        value={form.client_snapshot?.email || ""}
                        onChange={(e) => setForm((f) => ({
                            ...f, client_snapshot: { ...f.client_snapshot, email: e.target.value },
                        }))}
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm mt-1" />
                </div>

                {/* Project */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <input type="text" placeholder="Nom du projet (ex : 750 Peel)"
                        value={form.project_name}
                        onChange={(e) => setForm((f) => ({ ...f, project_name: e.target.value }))}
                        data-testid="report-project-name"
                        className="px-3 py-2 border border-[#dde5f0] text-sm" />
                    <input type="text" placeholder="Ville (ex : Montréal)"
                        value={form.project_city}
                        onChange={(e) => setForm((f) => ({ ...f, project_city: e.target.value }))}
                        className="px-3 py-2 border border-[#dde5f0] text-sm" />
                    <input type="text" placeholder="Adresse du projet"
                        value={form.project_address}
                        onChange={(e) => setForm((f) => ({ ...f, project_address: e.target.value }))}
                        className="px-3 py-2 border border-[#dde5f0] text-sm sm:col-span-2" />
                    <input type="date" value={form.inspection_date}
                        onChange={(e) => setForm((f) => ({ ...f, inspection_date: e.target.value }))}
                        data-testid="report-inspection-date"
                        className="px-3 py-2 border border-[#dde5f0] text-sm" />
                    <input type="text" placeholder="Mandaté par (Ex: Marc Tremblay – VERRE SELECT)"
                        value={form.mandated_by}
                        onChange={(e) => setForm((f) => ({ ...f, mandated_by: e.target.value }))}
                        className="px-3 py-2 border border-[#dde5f0] text-sm" />
                </div>

                {/* Purpose */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        1. Objet du rapport
                    </label>
                    <textarea rows={3} value={form.purpose}
                        onChange={(e) => setForm((f) => ({ ...f, purpose: e.target.value }))}
                        placeholder="Documenter les déficiences observées lors de l'inspection…&#10;&#10;Zones inspectées : …"
                        data-testid="report-purpose"
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                </div>

                {/* Doors */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <label className="text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider">
                            2 & 3. Portes inspectées ({form.doors.length})
                        </label>
                        <button type="button" onClick={addDoor}
                            className="text-[#1d4ed8] hover:underline text-xs inline-flex items-center gap-1"
                            data-testid="report-add-door">
                            <Plus className="w-3 h-3" /> Ajouter une porte
                        </button>
                    </div>
                    {form.doors.map((d, i) => (
                        <DoorCard
                            key={d._key || i}
                            door={d}
                            index={i}
                            onChange={(next) => updateDoor(i, next)}
                            onRemove={() => removeDoor(i)}
                            canDelete={form.doors.length > 1}
                            reportId={editingId}
                            photos={photosForDoor(i)}
                            onUploadPhotos={uploadPhotos}
                            onDeletePhoto={deletePhoto}
                            onCaptionSaved={refetchPhotos}
                            http={http}
                        />
                    ))}
                </div>

                {/* Risks */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        4. Risques et responsabilités potentielles
                    </label>
                    <textarea rows={3} value={form.risks}
                        onChange={(e) => setForm((f) => ({ ...f, risks: e.target.value }))}
                        placeholder="Ces déficiences, si non corrigées, peuvent entraîner…"
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                </div>

                {/* Conclusion */}
                <div>
                    <label className="block text-[10px] uppercase text-[#4b5d7a] font-bold tracking-wider mb-1">
                        5. Conclusion
                    </label>
                    <textarea rows={3} value={form.conclusion}
                        onChange={(e) => setForm((f) => ({ ...f, conclusion: e.target.value }))}
                        placeholder="L'inspection révèle…"
                        className="w-full px-3 py-2 border border-[#dde5f0] text-sm" />
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-[#dde5f0]">
                    <button onClick={save} disabled={busy} data-testid="report-save"
                        className="btn-primary !py-2 !px-4 !text-sm">
                        {busy
                            ? <><Loader2 className="w-4 h-4 animate-spin" /> Enregistrement…</>
                            : <><Save className="w-4 h-4" /> {editingId ? "Mettre à jour" : "Enregistrer"}</>}
                    </button>
                    {editingId && (
                        <>
                            <button onClick={() => downloadPdf(editingId)}
                                className="btn-secondary !py-2 !px-3 !text-sm"
                                data-testid="report-download-pdf">
                                <Download className="w-4 h-4" /> Télécharger PDF
                            </button>
                            <button onClick={() => sendEmail({ ...form, id: editingId })}
                                disabled={sending}
                                className="btn-secondary !py-2 !px-3 !text-sm"
                                data-testid="report-send-email">
                                <Send className="w-4 h-4" />
                                {sending ? "Envoi…" : "Envoyer par courriel"}
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* ─── List ──────────────────────────────────────── */}
            <div className="bg-white border border-[#dde5f0] p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="tech-stamp text-[#0c182b] font-bold">Rapports</h3>
                    <button onClick={reload} className="text-xs text-[#1d4ed8] hover:underline inline-flex items-center gap-1">
                        <RefreshCw className="w-3 h-3" /> Rafraîchir
                    </button>
                </div>
                {loading ? (
                    <div className="text-sm italic text-[#4b5d7a]">Chargement…</div>
                ) : list.length === 0 ? (
                    <div className="text-sm italic text-[#4b5d7a]">Aucun rapport pour l&apos;instant.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm" data-testid="report-list">
                            <thead className="text-[10px] uppercase text-[#4b5d7a] border-b border-[#dde5f0]">
                                <tr>
                                    <th className="text-left px-2 py-1.5">N°</th>
                                    <th className="text-left px-2 py-1.5">Client / Projet</th>
                                    <th className="text-left px-2 py-1.5">Date</th>
                                    <th className="text-center px-2 py-1.5 hidden sm:table-cell">Portes</th>
                                    <th className="text-center px-2 py-1.5 hidden sm:table-cell">Photos</th>
                                    <th className="text-left px-2 py-1.5">Statut</th>
                                    <th className="px-2 py-1.5"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {list.map((r) => (
                                    <tr key={r.id} className="border-b border-[#f3f6fb] hover:bg-[#f7f9fc]">
                                        <td className="px-2 py-1.5 font-mono text-[#0c182b]">
                                            RAP-{String(r.number).padStart(4, "0")}
                                        </td>
                                        <td className="px-2 py-1.5">
                                            <div className="text-[#0c182b]">{r.client_snapshot?.name}</div>
                                            <div className="text-[10px] text-[#4b5d7a]">{r.project_name}</div>
                                        </td>
                                        <td className="px-2 py-1.5 text-[11px] text-[#4b5d7a] whitespace-nowrap">
                                            {formatDate(r.inspection_date)}
                                        </td>
                                        <td className="px-2 py-1.5 text-center hidden sm:table-cell">{(r.doors || []).length}</td>
                                        <td className="px-2 py-1.5 text-center hidden sm:table-cell">{(r.photos || []).length}</td>
                                        <td className="px-2 py-1.5">
                                            <span className="tech-stamp px-2 py-0.5 text-[10px] border border-[#dde5f0] bg-[#f3f6fb]">
                                                {r.status}
                                            </span>
                                        </td>
                                        <td className="px-2 py-1.5 text-right whitespace-nowrap">
                                            <button onClick={() => openEdit(r)}
                                                className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Ouvrir">
                                                <ClipboardList className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => downloadPdf(r.id)}
                                                className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Télécharger PDF">
                                                <Download className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => sendEmail(r)}
                                                className="p-1 hover:bg-[#f3f6fb] text-[#0c182b]" title="Envoyer">
                                                <Send className="w-3.5 h-3.5" />
                                            </button>
                                            <button onClick={() => removeReport(r.id)}
                                                className="p-1 hover:bg-[#fde7e7] text-[#a31a1a]" title="Supprimer">
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
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

export default ExpertReportsPanel;
