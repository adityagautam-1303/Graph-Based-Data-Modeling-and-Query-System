interface BreadcrumbProps {
  items: string[];
}

export default function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="breadcrumb">
      {items.map((item, i) => (
        <span key={item} className="breadcrumb-item">
          {i > 0 && <span className="separator"> / </span>}
          <span className={i === items.length - 1 ? "current" : ""}>{item}</span>
        </span>
      ))}
    </nav>
  );
}
