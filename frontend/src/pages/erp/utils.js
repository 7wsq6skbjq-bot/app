// Shared ERP constants and helpers.
export const TPS_RATE = 0.05;
export const TVQ_RATE = 0.09975;

export const PROVINCES = ["QC", "ON", "NB", "NS", "PE", "NL", "MB", "SK", "AB", "BC", "YT", "NT", "NU"];

export const INVOICE_STATUSES = ["brouillon", "envoyée", "payée", "annulée"];
export const PO_STATUSES = ["brouillon", "envoyée", "reçue", "annulée"];
export const BOL_STATUSES = ["brouillon", "expédié", "livré", "annulé"];

export const STATUS_BADGE = {
    brouillon: "bg-[#f3f6fb] text-[#4b5d7a] border-[#c5d4e7]",
    envoyée: "bg-[#eaf1fb] text-[#2f4f7f] border-[#97b0d0]",
    payée: "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
    reçue: "bg-[#e6f4ea] text-[#0b6b2f] border-[#8ec79d]",
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
