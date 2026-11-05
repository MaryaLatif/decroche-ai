import { useEffect, useState } from "react";
import { approve, getBusiness, getDraft, saveDraft } from "../api/onboarding";
import type { Item, Knowledge, OpeningHours } from "../types/knowledge";
import HoursEditor from "./HoursEditor";
import BackButton from "./BackButton";

export default function ReviewStep({ businessId, onApproved, onBack }: { businessId: string; onApproved: () => void; onBack: () => void }) {
    const [kn, setKn] = useState<Knowledge | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [googleHours, setGoogleHours] = useState<OpeningHours | null>(null);

    useEffect(() => {
        getBusiness(businessId).then((d) => setGoogleHours(d.business.google_hours ?? null)).catch(() => { });
    }, [businessId]);

    useEffect(() => { getDraft(businessId).then(setKn).catch((e) => setError(e.message)); }, [businessId]);

    if (!kn) return (
        <>
            <BackButton onClick={onBack} label="Sources" />
            <p className="loading">{error ?? "Chargement…"}</p>
        </>
    );

    const update = (i: number, patch: Partial<Item>) =>
        setKn({ ...kn, items: kn.items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)) });

    async function validate() {
        if (!kn) return;
        setSaving(true); setError(null);
        try {
            await saveDraft(businessId, kn);
            await approve(businessId);
            onApproved();
        } catch (e) { setError((e as Error).message); setSaving(false); }
    }

    async function back() {
        if (!kn) return onBack();
        try {
            await saveDraft(businessId, kn);   // on garde tes corrections
            onBack();
        } catch (e) {
            setError((e as Error).message);    // brouillon invalide : on reste ici
        }
    }

    return (
        <>
            <BackButton onClick={back} label="Sources" />
            <h1>Vérifie ton catalogue</h1>
            <div className="stats">
                <div className="stat"><strong>{kn.items.length}</strong><span>Produits</span></div>
                <div className="stat"><strong>{kn.items.filter((i) => i.price_cents !== null).length}</strong><span>Avec prix</span></div>
                <div className="stat"><strong>{kn.opening_hours?.days.length ? "✓" : "—"}</strong><span>Horaires</span></div>
            </div>
            {kn.notes.map((n, i) => <p key={i} className="note">⚠ {n}</p>)}
            <h2>Horaires d'ouverture</h2>
            <HoursEditor value={kn.opening_hours} googleHours={googleHours}
                onChange={(h) => setKn({ ...kn, opening_hours: h })} />
            <h2>Catalogue</h2>
            <table className="catalog">
                <thead><tr><th>Produit</th><th>Catégorie</th><th>Prix (€)</th><th>Dispo</th><th /></tr></thead>
                <tbody>
                    {kn.items.map((it, i) => (
                        <tr key={it.id || i}>
                            <td><input value={it.name} onChange={(e) => update(i, { name: e.target.value })} /></td>
                            <td><input value={it.category ?? ""} onChange={(e) => update(i, { category: e.target.value || null })} /></td>
                            <td>
                                <input type="number" step="0.01" min="0" style={{ width: 90 }}
                                    value={it.price_cents === null ? "" : it.price_cents / 100}
                                    onChange={(e) => update(i, { price_cents: e.target.value === "" ? null : Math.round(parseFloat(e.target.value) * 100) })} />
                            </td>
                            <td>
                                <select value={it.availability} onChange={(e) => update(i, { availability: e.target.value })}>
                                    <option value="available">Disponible</option>
                                    <option value="unavailable">Indisponible</option>
                                    <option value="unknown">Inconnu</option>
                                </select>
                            </td>
                            <td><button onClick={() => setKn({ ...kn, items: kn.items.filter((_, idx) => idx !== i) })}>✕</button></td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <button onClick={() => setKn({ ...kn, items: [...kn.items, { id: "", name: "Nouveau produit", category: null, description: null, price_cents: null, availability: "available", allergens: null, source_ids: [] }] })}>
                + Ajouter un produit
            </button>
            {error && <p className="error">{error}</p>}
            <div className="actions">
                <button className="primary" onClick={validate} disabled={saving}>Valider et activer l'agent</button>
            </div>
        </>
    );
}