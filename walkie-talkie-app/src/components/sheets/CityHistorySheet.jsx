import Sheet from './Sheet';
import { CITIES } from '../../constants';

export default function CityHistorySheet({ open, onClose, chatHistoryItems, selectedCity, onSelectCity }) {
  const items = CITIES.map((city) => {
    const historyItem = chatHistoryItems.find((item) => item.city === city);
    return historyItem || { city, count: 0, preview: 'No messages yet.' };
  });

  return (
    <Sheet open={open} onClose={onClose} title="Cities & History">
      <div className="history-list">
        {items.map((item) => (
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
