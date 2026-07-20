export default function TopBar({ selectedCity, onOpenCityHistory, onOpenSettings }) {
  return (
    <header className="topbar">
      <div className="logo-mark">🗺️</div>
      <div className="brand-wrap">
        <div className="brand">WalkieTalkie</div>
        <div className="tagline">Local Intel · Budget Travel</div>
      </div>
      <button className="city-chip" onClick={onOpenCityHistory}>{selectedCity} ▾</button>
      <button className="icon-btn" title="Settings" onClick={onOpenSettings}>⚙️</button>
    </header>
  );
}
