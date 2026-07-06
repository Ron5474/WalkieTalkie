export default function Sheet({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet-panel" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <h3>{title}</h3>
          <button className="sheet-close" onClick={onClose}>✕</button>
        </div>
        <div className="sheet-body">{children}</div>
      </div>
    </div>
  );
}
