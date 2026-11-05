import { useState } from "react";
import type { FormEvent } from "react";
import { searchBusinesses } from "../api/business";
import { confirmBusiness } from "../api/onboarding";
import type { BusinessSearchResult } from "../types/business";

export default function SearchStep({ onConfirmed }: { onConfirmed: (id: string, name: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<BusinessSearchResult[]>([]);
  const [picked, setPicked] = useState<BusinessSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search(e: FormEvent) {
    e.preventDefault();
    setError(null); setPicked(null); setLoading(true);
    try {
      const data = await searchBusinesses(query);
      setResults(data.results);
      if (!data.results.length) setError("Aucun commerce trouvé.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function confirm() {
    if (!picked) return;
    setLoading(true); setError(null);
    try {
      const { business_id } = await confirmBusiness(picked.place_id);
      onConfirmed(business_id, picked.name ?? "");
    } catch (err) {
      setError((err as Error).message);
      setLoading(false);
    }
  }

  return (
    <>
      <h1>Active ton agent</h1>
      <form className="search-form" onSubmit={search}>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Nom du commerce + ville" required minLength={3} />
        <button disabled={loading}>{loading ? "…" : "Rechercher"}</button>
      </form>
      {error && <p className="error">{error}</p>}

      {picked ? (
        <div className="details-card">
          <h3>Est-ce bien votre établissement ?</h3>
          <p><strong>{picked.name}</strong><br />{picked.address}</p>
          <div className="actions">
            <button onClick={() => setPicked(null)}>Choisir un autre</button>
            <button className="primary" onClick={confirm} disabled={loading}>Valider</button>
          </div>
        </div>
      ) : (
        results.map((b) => (
          <button key={b.place_id} className="business-card" onClick={() => setPicked(b)}>
            <div><h3>{b.name}</h3><p>{b.address}</p></div>
            <span className="badge">{b.category ?? "Commerce"}</span>
          </button>
        ))
      )}
    </>
  );
}