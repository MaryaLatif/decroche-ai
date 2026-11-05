import { useCallback, useEffect, useRef, useState } from "react";
import { addText, addUrl, collectStatus, getBusiness, startCollect, uploadDocument } from "../api/onboarding";
import type { Job, Source } from "../types/knowledge";
import BackButton from "./BackButton";

interface Props { businessId: string; onReady: () => void; onBack: () => void }

export default function SourcesStep({ businessId, onReady, onBack }: Props) {
  const [sources, setSources] = useState<Source[]>([]);
  const [job, setJob] = useState<Job>({ status: "idle" });
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const readyRef = useRef(onReady);
  readyRef.current = onReady;

  const refresh = useCallback(async () => {
    const data = await getBusiness(businessId);
    setSources(data.sources);
    setJob(data.job);
    return data;
  }, [businessId]);

  const poll = useCallback(() => {
    window.clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try {
        const j = await collectStatus(businessId);
        setJob(j);
        if (j.status === "ready_for_review") { window.clearInterval(timer.current); readyRef.current(); }
        if (j.status === "failed") window.clearInterval(timer.current);
      } catch {
        window.clearInterval(timer.current);
      }
    }, 2000);
  }, [businessId]);

  useEffect(() => {
    refresh()
      .then((d) => { if (d.job.status === "collecting" || d.job.status === "extracting") poll(); })
      .catch((e) => setError(e.message));
    return () => window.clearInterval(timer.current);
  }, [refresh, poll]);

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try { await action(); await refresh(); } catch (e) { setError((e as Error).message); }
  }

  async function collect() {
    setError(null);
    try {
      setJob(await startCollect(businessId));
      poll();
    } catch (e) { setError((e as Error).message); }
  }

  const busy = job.status === "collecting" || job.status === "extracting";

  return (
    <>
      <BackButton onClick={onBack} label="Changer de commerce" />
      <h1>Sources d'information</h1>

      <ul>
        {sources.map((s) => (
          <li key={s.id}>{s.type} — {s.url ?? s.filename ?? s.label}</li>
        ))}
      </ul>

      <div className="search-grid" style={{ gridTemplateColumns: "1fr auto" }}>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://… (site, page menu, PDF)" />
        <button onClick={() => run(async () => { await addUrl(businessId, url); setUrl(""); })}>Ajouter</button>
      </div>

      <p>
        <input type="file" accept=".pdf,.txt,.md"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) run(() => uploadDocument(businessId, f)); e.target.value = ""; }} />
      </p>

      <textarea rows={5} style={{ width: "100%" }} value={text} onChange={(e) => setText(e.target.value)} placeholder="Ou colle ton menu ici" />
      <button disabled={text.trim().length < 3} onClick={() => run(async () => { await addText(businessId, text.trim()); setText(""); })}>
        Ajouter le texte
      </button>

      {error && <p className="error">{error}</p>}
      {job.status === "failed" && <p className="error">Échec : {job.error}</p>}
      {busy && <p className="loading">{job.status === "collecting" ? "Collecte en cours…" : "Analyse par Claude…"}</p>}
      {job.errors?.map((e, i) => <p key={i} className="note">⚠ {e}</p>)}

      {job.status === "ready_for_review" && (
        <p className="note">
          Un catalogue a déjà été préparé. Relancer la collecte le remplacera, avec tes corrections.{" "}
          <button type="button" onClick={onReady}>Revoir le catalogue</button>
        </p>
      )}

      <div className="actions">
        <button className="primary" disabled={busy || !sources.length} onClick={collect}>
          {job.status === "ready_for_review" ? "Relancer la collecte" : "Collecter les informations"}
        </button>
      </div>
    </>
  );
}