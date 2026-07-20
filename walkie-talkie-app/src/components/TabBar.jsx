const TABS = [
  { id: 'guide', label: 'Guide', icon: '🗺️' },
  { id: 'trip', label: 'Trip', icon: '🧭' },
  { id: 'walk', label: 'Walk', icon: '🚶' },
];

export default function TabBar({ activeTab, setActiveTab }) {
  return (
    <nav className="tabbar">
      {TABS.map((t) => (
        <button key={t.id}
          className={`tab ${activeTab === t.id ? 'active' : ''}`}
          onClick={() => setActiveTab(t.id)}>
          <span className="tab-icon">{t.icon}</span>
          <span className="tab-label">{t.label}</span>
        </button>
      ))}
    </nav>
  );
}
