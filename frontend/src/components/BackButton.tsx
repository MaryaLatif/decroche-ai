export default function BackButton({ onClick, label = "Retour" }: { onClick: () => void; label?: string }) {
    return (
      <button type="button" className="back-btn" onClick={onClick}>
        ← {label}
      </button>
    );
  }