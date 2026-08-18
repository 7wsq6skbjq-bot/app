// Shared ERP constants and helpers.
export const TPS_RATE = 0.05;
export const TVQ_RATE = 0.09975;

export const PROVINCES = ["QC", "ON", "NB", "NS", "PE", "NL", "MB", "SK", "AB", "BC", "YT", "NT", "NU"];

export const INVOICE_STATUSES = ["brouillon", "envoyée", "payée", "annulée"];
export const PO_STATUSES = ["brouillon", "envoyée", "reçue", "annulée"];
export const BOL_STATUSES = ["brouillon", "expédié", "livré", "annulé"];
export const QUOTE_STATUSES = ["brouillon", "envoyée", "acceptée", "refusée", "expirée", "annulée"];

export const STATUS_BADGE = {
    brouillon: "bg-[#f3f6fb] text-[#4b5d7a] border-[#c5d4e7]",
    envoyée: "bg-[#eaf1fb] text-[#2f4f7f] border-[#97b0d0]",
    payée: "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
    reçue: "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
    acceptée: "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
    refusée: "bg-[#fbe8e8] text-[#8a1f1f] border-[#e8a5a5]",
    expirée: "bg-[#fff4e0] text-[#925800] border-[#e5ba67]",
    expédié: "bg-[#fff4e0] text-[#925800] border-[#e5ba67]",
    livré: "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
    annulée: "bg-[#fbe8e8] text-[#8a1f1f] border-[#e8a5a5]",
    annulé: "bg-[#fbe8e8] text-[#8a1f1f] border-[#e8a5a5]",
};

export const formatCurrency = (n) => {
    const v = Number(n || 0);
    return new Intl.NumberFormat("fr-CA", {
        style: "currency",
        currency: "CAD",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(v);
};

export const formatDate = (iso) => {
    if (!iso) return "—";
    try {
        return new Date(iso).toLocaleDateString("fr-CA", {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
    } catch {
        return iso;
    }
};

export const todayISO = () => new Date().toISOString().slice(0, 10);

// Stable unique client-side key for form array items (so React doesn't
// lose state when items are added/removed/reordered). Stripped before
// POST/PUT payloads are sent to the backend.
let _keyCounter = 0;
export const newKey = () => {
    _keyCounter += 1;
    return `k-${Date.now()}-${_keyCounter}`;
};

/** Strip client-only _key field from a list of items before sending to API. */
export const stripKeys = (items) =>
    (items || []).map(({ _key, ...rest }) => rest); // eslint-disable-line no-unused-vars

// Empty templates
export const emptyParty = (kind = "customer") => ({
    kind,
    name: "",
    contact: "",
    email: "",
    phone: "",
    address_line1: "",
    address_line2: "",
    city: "",
    province: "QC",
    postal_code: "",
    country: "Canada",
    tax_number: "",
    notes: "",
});

export const emptyLineItem = () => ({
    _key: newKey(),
    description: "",
    quantity: 1,
    unit_price: 0,
    product_id: null,
});

export const emptyInvoice = () => ({
    customer_id: null,
    customer_snapshot: emptyParty("customer"),
    date: todayISO(),
    due_date: "",
    items: [emptyLineItem()],
    taxable: true,
    notes: "",
    status: "brouillon",
});

// Default valid_until = today + 30 days
const _plusDays = (n) => {
    const d = new Date();
    d.setDate(d.getDate() + n);
    return d.toISOString().slice(0, 10);
};

export const emptyQuote = () => ({
    customer_id: null,
    customer_snapshot: emptyParty("customer"),
    date: todayISO(),
    valid_until: _plusDays(30),
    items: [emptyLineItem()],
    taxable: true,
    notes: "",
    status: "brouillon",
});

export const emptyPO = () => ({
    supplier_id: null,
    supplier_snapshot: emptyParty("supplier"),
    date: todayISO(),
    expected_delivery: "",
    items: [emptyLineItem()],
    taxable: true,
    notes: "",
    status: "brouillon",
});

export const emptyBolItem = () => ({
    _key: newKey(),
    description: "",
    quantity: 1,
    unit: "unité",
    weight_kg: "",
    dimensions: "",
});

export const emptyBOL = () => ({
    shipper_snapshot: { ...emptyParty("customer"), name: "Portech" },
    consignee_snapshot: emptyParty("customer"),
    carrier: "",
    date: todayISO(),
    expected_delivery: "",
    items: [emptyBolItem()],
    total_weight_kg: "",
    special_instructions: "",
    status: "brouillon",
});

export const PAYMENT_METHODS = [
    "Virement bancaire (EFT)",
    "Chèque",
    "Carte de crédit",
    "Comptant",
    "Virement Interac",
    "Autre",
];

export const emptyPaymentNoticeItem = () => ({
    _key: newKey(),
    invoice_number: "",
    description: "",
    amount: 0,
});

export const emptyPaymentNotice = () => ({
    supplier_id: null,
    supplier_snapshot: emptyParty("supplier"),
    date: todayISO(),
    payment_date: todayISO(),
    payment_method: "Virement bancaire (EFT)",
    reference_number: "",
    items: [emptyPaymentNoticeItem()],
    notes: "",
});


// ─── Mosquito screens (Moustiquaires) ──────────────────────
export const MOSQUITO_SCREEN_STATUSES = [
    "brouillon", "envoyé", "en fabrication", "reçu", "fabriqué", "annulé",
];

export const MOSQUITO_FRAME_COLORS = [
    "Blanc", "Noir", "Bronze", "Brun commercial", "Naturel (anodisé)", "Sur mesure",
];

export const MOSQUITO_MESH_TYPES = [
    "Fibre de verre standard",
    "Anti-pollen (No-see-um)",
    "Anti-chat renforcée",
    "Solaire (Solar Screen)",
    "Aluminium",
    "Sur mesure",
];

export const MOSQUITO_ATTACHMENT_TYPES = [
    "Accroches (clips)",
    "Rails coulissants",
    "À visser",
    "Magnétique",
    "Sur cadre existant",
    "Sur mesure",
];

export const emptyMosquitoScreenItem = () => ({
    _key: newKey(),
    name: "",
    width_mm: 0,
    height_mm: 0,
    qty: 1,
    frame_color: "Blanc",
    mesh_type: "Fibre de verre standard",
    attachment_type: "Accroches (clips)",
    notes: "",
});

export const emptyMosquitoScreen = () => ({
    mode: "interne",
    supplier_id: null,
    supplier_snapshot: emptyParty("supplier"),
    customer_name: "",
    project_ref: "",
    project_address: "",
    date: todayISO(),
    needed_by: "",
    status: "brouillon",
    items: [emptyMosquitoScreenItem()],
    notes: "",
});


// ─── Production drawings (Dessins de production) ───────────
export const PRODUCTION_SERIES = ["AT1000", "ATi1000", "AT2000", "ATi2000"];
export const PRODUCTION_CONFIGS = [
    { v: "simple", lbl: "Porte simple" },
    { v: "pair", lbl: "Paire de portes" },
];
export const PRODUCTION_STATUSES = [
    "brouillon", "en production", "en hold", "produit", "annulé",
];
export const PRODUCTION_MENTIONS = [
    "Pour approbation", "Pour demande de prix", "Pour production",
];
export const PRODUCTION_FINISHES = [
    "Anodisé clair", "Noir", "Bronze", "Dark Bronze", "Champagne",
    "Mill finish", "Sur mesure",
];
export const HINGE_TYPES = [
    { v: "butt45", lbl: "Charnière 4½\" (paumelles)" },
    { v: "continue", lbl: "Charnière continue" },
    { v: "none", lbl: "Aucune / autre" },
];
export const INSTALL_PARTIES = ["Portech", "A.T. Fabrication"];
export const HANDING_OPTIONS = [
    { v: "MG", lbl: "MG — Main gauche" },
    { v: "MD", lbl: "MD — Main droite" },
    { v: "MGR", lbl: "MGR — Main gauche renversée" },
    { v: "MDR", lbl: "MDR — Main droite renversée" },
];

export const emptyHardwareLine = () => ({
    _key: newKey(),
    qty: "1",
    description: "",
    part_number: "",
    note: "",
    unit_price: 0,
    on_active: false,
    on_inactive: false,
});

export const emptyProductionDoor = () => ({
    _key: newKey(),
    tag: "",
    series: "AT1000",
    config: "simple",
    opening_width_in: 36,
    opening_height_in: 84,
    qty: 1,
    handing: "MD",
    active_leaf: "right",
    leaf_active_width_in: 0,
    leaf_inactive_width_in: 0,
    fab_width_in: 0,
    fab_height_in: 0,
    handle_height_in: 34.5,
    handle_length_in: 9,
    handle_both: false,
    lock_height_in: 40,
    panic_bar: false,
    panic_height_in: 40,
    no_hardware: false,
    show_handle: true,
    show_lock: true,
    lever: false,
    lever_height_in: 40,
    push_paddle: false,
    paddle_height_in: 40,
    protection_plate: false,
    plate_height_in: 40,
    flush_bolt: false,
    door_closer: false,
    closer_leaf: "active",
    astragal: false,
    handle_leaf: "active",
    lock_leaf: "active",
    lever_leaf: "active",
    paddle_leaf: "active",
    plate_leaf: "active",
    panic_leaf: "active",
    flush_leaf: "inactive",
    undercut_mm: 17.5,
    finish_ext: "Anodisé clair",
    finish_int: "Anodisé clair",
    glass: "VT6 · 6mm trempé clair",
    glass_type: "6mm",
    hinges: "",
    hinge_type: "butt45",
    scale_note: "1:30",
    hardware: [emptyHardwareLine()],
    notes: "",
});

export const emptyProductionPlan = () => ({
    project_name: "",
    project_number: "",
    production_name: "",
    production_note: "",
    revision: "no00",
    mention: "Pour production",
    date: todayISO(),
    client_name: "",
    client_address: "",
    client_contact: "",
    client_phone: "",
    machining_by: "A.T. Fabrication",
    installer: "Portech",
    fab_auto: true,
    fab_allowance_in: 0,
    include_plan_details: true,
    include_section_details: true,
    include_anchors: true,
    show_costs: false,
    status: "brouillon",
    doors: [emptyProductionDoor()],
    notes: "",
});



// ─── Expert reports (Rapports d'expertise) ─────────────────
export const REPORT_STATUSES = ["brouillon", "finalisé", "envoyé", "archivé"];

export const emptyInspectedDoor = () => ({
    _key: newKey(),
    tag: "",
    location: "",
    series: "",
    model: "",
    width_mm: null,
    height_mm: null,
    finish: "",
    configuration: "",
    hinges: "",
    lock: "",
    electric_strike: "",
    threshold: "",
    trim: "",
    other_specs: "",
    observations: [],
    impacts: [],
    recommendation: "",
});

export const emptyExpertReport = () => ({
    client_snapshot: emptyParty("customer"),
    project_name: "",
    project_address: "",
    project_city: "",
    inspection_date: todayISO(),
    inspector_name: "Cédrick Pimparé",
    inspector_title: "Expert Portes Commerciales – Portech",
    mandated_by: "",
    purpose: "",
    doors: [emptyInspectedDoor()],
    risks: "",
    conclusion: "",
    status: "brouillon",
});


export const computeTotals = (items, taxable = true) => {
    const subtotal = items.reduce(
        (s, it) => s + Number(it.quantity || 0) * Number(it.unit_price || 0),
        0,
    );
    const tps = taxable ? subtotal * TPS_RATE : 0;
    const tvq = taxable ? subtotal * TVQ_RATE : 0;
    return {
        subtotal: Math.round(subtotal * 100) / 100,
        tps: Math.round(tps * 100) / 100,
        tvq: Math.round(tvq * 100) / 100,
        total: Math.round((subtotal + tps + tvq) * 100) / 100,
    };
};

/**
 * Compute the visual overdue state of an invoice (null if not applicable).
 * Returns { label, tone } with tone: 'red' (overdue, no reminder yet),
 * 'orange' (J+7 reminder sent), 'red-firm' (J+30 reminder sent).
 */
export const overdueState = (invoice) => {
    if (!invoice || invoice.status !== "envoyée" || !invoice.due_date) return null;
    const due = new Date(invoice.due_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const daysPast = Math.floor((today - due) / 86_400_000);
    if (daysPast < 1) return null;
    const level = Number(invoice.reminder_level_sent || 0);
    if (level === 30) return { label: `Rappelé J+30 · ${daysPast}j retard`, tone: "red-firm" };
    if (level === 7) return { label: `Rappelé J+7 · ${daysPast}j retard`, tone: "orange" };
    return { label: `En retard · ${daysPast}j`, tone: "red" };
};

export const OVERDUE_BADGE = {
    red: "bg-[#fbe8e8] text-[#8a1f1f] border-[#e8a5a5]",
    orange: "bg-[#fff4e0] text-[#925800] border-[#e5ba67]",
    "red-firm": "bg-[#8a1f1f] text-white border-[#8a1f1f]",
};
