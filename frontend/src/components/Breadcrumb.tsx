interface BreadcrumbProps {
  items: string[];
  onBack?: () => void;
}

export default function Breadcrumb({ items, onBack }: BreadcrumbProps) {
  return (
    <nav className="breadcrumb">
      {onBack && (
        <button className="breadcrumb-back-btn" onClick={onBack}>
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          Back to Home
        </button>
      )}
      <div className="breadcrumb-items">
        {items.map((item, i) => (
          <span key={item} className="breadcrumb-item">
            {i > 0 && <span className="separator"> / </span>}
            <span className={i === items.length - 1 ? "current" : ""}>{item}</span>
          </span>
        ))}
      </div>
    </nav>
  );
}
