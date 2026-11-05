export interface Item {
    id: string;
    name: string;
    category: string | null;
    tags?: string[] | null;
    description: string | null;
    price_cents: number | null;
    availability: string;
    allergens: string[] | null;
    source_ids: string[];
}

export interface OpeningHours {
    source: "google" | "website" | "merchant" | "unknown";
    days: DayHours[];
    note: string | null;
}

export interface Knowledge {
    business_name: string | null;
    currency: string;
    description: string | null;
    opening_hours_text: string | null;
    opening_hours: OpeningHours | null;
    ordering_enabled: boolean;
    fulfillment_modes: string[];
    items: Item[];
    faq: { question: string; answer: string; source_ids: string[] }[];
    notes: string[];
}

export interface Source { id: string; type: string; url?: string; label?: string; filename?: string }

export interface Job {
    status: "idle" | "collecting" | "extracting" | "ready_for_review" | "failed";
    error?: string | null;
    errors?: string[];
}

export interface CartLine {
    item_id: string; name: string; quantity: number;
    unit_price_cents: number; line_total_cents: number; note: string | null;
}
export interface Cart { lines: CartLine[]; total_cents: number; currency: string }
export interface Order { number: string; status: string; total_cents: number; currency: string }

export interface Slot { open: string; close: string }
export interface DayHours { day: number; slots: Slot[] }
