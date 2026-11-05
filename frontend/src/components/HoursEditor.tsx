import type { OpeningHours, Slot } from "../types/knowledge";

const LABELS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
const SOURCES: Record<string, string> = {
  google: "Google", website: "Site web", merchant: "Saisi par le commerçant", unknown: "Non renseigné",
};

const emptyWeek = (): OpeningHours => ({
  source: "merchant", days: LABELS.map((_, day) => ({ day, slots: [] })), note: null,
});

interface Props {
  value: OpeningHours | null;
  googleHours?: OpeningHours | null;
  onChange: (v: OpeningHours) => void;
}

export default function HoursEditor({ value, googleHours, onChange }: Props) {
  if (!value || !value.days.length) {
    return (
      <div>
        <p className="error">Horaires introuvables (ni Google, ni le site).</p>
        {googleHours && <button onClick={() => onChange(googleHours)}>Utiliser les horaires Google</button>}
        <button onClick={() => onChange(emptyWeek())}>Saisir les horaires</button>
      </div>
    );
  }

  const slotsOf = (d: number) => value.days.find((x) => x.day === d)?.slots ?? [];
  const setSlots = (d: number, slots: Slot[]) =>
    onChange({
      ...value,
      source: "merchant",
      days: LABELS.map((_, i) => ({ day: i, slots: i === d ? slots : slotsOf(i) })),
    });
  const patch = (d: number, i: number, p: Partial<Slot>) =>
    setSlots(d, slotsOf(d).map((s, idx) => (idx === i ? { ...s, ...p } : s)));

  return (
    <div>
      <p>Source : <span className={value.source === "google" ? "badge ok" : "badge"}>{SOURCES[value.source] ?? value.source}</span></p>
      {LABELS.map((label, d) => {
        const slots = slotsOf(d);
        return (
          <div key={d} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6, flexWrap: "wrap" }}>
            <strong style={{ width: 90 }}>{label}</strong>
            <label>
              <input type="checkbox" checked={slots.length > 0}
                onChange={(e) => setSlots(d, e.target.checked ? [{ open: "09:00", close: "19:00" }] : [])} /> Ouvert
            </label>
            {slots.map((s, i) => (
              <span key={i}>
                <input type="time" value={s.open}
                  onChange={(e) => e.target.value && patch(d, i, { open: e.target.value })} />
                {" – "}
                <input type="time" value={s.close === "24:00" ? "00:00" : s.close}
                  onChange={(e) => e.target.value && patch(d, i, { close: e.target.value === "00:00" ? "24:00" : e.target.value })} />
                <button onClick={() => setSlots(d, slots.filter((_, idx) => idx !== i))}>✕</button>
              </span>
            ))}
            {slots.length > 0 && (
              <button onClick={() => setSlots(d, [...slots, { open: "14:00", close: "19:00" }])}>+ créneau</button>
            )}
          </div>
        );
      })}
      <textarea rows={2} style={{ width: "100%" }} placeholder="Exceptions : jours fériés, congés, horaires d'été…"
        value={value.note ?? ""} onChange={(e) => onChange({ ...value, note: e.target.value || null })} />
      {googleHours && value.source !== "google" && (
        <button onClick={() => onChange(googleHours)}>Réinitialiser avec Google</button>
      )}
    </div>
  );
}