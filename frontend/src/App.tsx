import { useEffect, useState } from "react";
import SearchStep from "./components/SearchStep";
import SourcesStep from "./components/SourcesStep";
import ReviewStep from "./components/ReviewStep";
import ChatPanel from "./components/ChatPanel";

type Step = "search" | "sources" | "review" | "chat";

const STEPS: { id: Step; label: string }[] = [
  { id: "search", label: "Commerce" },
  { id: "sources", label: "Sources" },
  { id: "review", label: "Catalogue" },
  { id: "chat", label: "Agent" },
];

export default function App() {
  const [step, setStep] = useState<Step>("search");
  const [businessId, setBusinessId] = useState("");
  const current = STEPS.findIndex((s) => s.id === step);

  function go(next: Step) {
    window.history.pushState({ step: next }, "");
    setStep(next);
  }

  // le bouton « retour » du navigateur suit les étapes
  useEffect(() => {
    const onPop = (e: PopStateEvent) => {
      const target: Step = e.state?.step ?? "search";
      setStep(target !== "search" && !businessId ? "search" : target);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [businessId]);

  return (
    <main className={step === "chat" || step === "review" ? "page wide" : "page"}>
      <header className="brand">décroche.ai</header>

      <ol className="stepper">
        {STEPS.map((s, i) => {
          const clickable = i < current;
          return (
            <li
              key={s.id}
              className={`step ${i < current ? "done" : ""} ${i === current ? "active" : ""} ${clickable ? "clickable" : ""}`}
              onClick={clickable ? () => go(s.id) : undefined}
              onKeyDown={clickable ? (e) => e.key === "Enter" && go(s.id) : undefined}
              role={clickable ? "button" : undefined}
              tabIndex={clickable ? 0 : undefined}
            >
              <span className="dot">{i < current ? "✓" : i + 1}</span>
              {s.label}
            </li>
          );
        })}
      </ol>

      <section className="panel">
        {step === "search" && (
          <SearchStep onConfirmed={(id) => { setBusinessId(id); go("sources"); }} />
        )}
        {step === "sources" && (
          <SourcesStep businessId={businessId} onReady={() => go("review")} onBack={() => go("search")} />
        )}
        {step === "review" && (
          <ReviewStep businessId={businessId} onApproved={() => go("chat")} onBack={() => go("sources")} />
        )}
        {step === "chat" && <ChatPanel businessId={businessId} onBack={() => go("review")} />}
      </section>
    </main>
  );
}