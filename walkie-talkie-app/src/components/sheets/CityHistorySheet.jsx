import Sheet from './Sheet';

export default function CityHistorySheet({ open, onClose, chatHistoryItems, selectedCity, onSelectCity }) {
  return (
    <Sheet open={open} onClose={onClose} title="Cities & History">
      <div className="history-list">
        {chatHistoryItems.map((item) => (
          <button key={item.city}
            className={`history-item ${item.city === selectedCity ? 'active' : ''}`}
            onClick={() => onSelectCity(item.city)}>
            <div className="history-city">{item.city}</div>
            <div className="history-meta">{item.count} message{item.count === 1 ? '' : 's'}</div>
            <div className="history-preview">{item.preview || 'No messages yet.'}</div>
          </button>
        ))}
      </div>
    </Sheet>
  );
}
