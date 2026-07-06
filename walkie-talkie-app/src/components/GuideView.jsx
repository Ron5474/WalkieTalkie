import { suggestedPrompts } from '../constants';
import MessageList from './MessageList';

export default function GuideView({ messages, loading, bottomRef, onSuggestion }) {
  const isEmpty = messages.length === 0;
  return (
    <div className="chat-area">
      {isEmpty ? (
        <div className="welcome">
          <h1>Explore Like a Local</h1>
          <p>I know the spots that don't show up on travel blogs — the century-old tea stall, the mural with a story, the $4 meal that locals swear by.</p>
          <div className="suggestions">
            {suggestedPrompts.map((p, i) => (
              <button key={i} className="suggestion-btn" onClick={() => onSuggestion(p.text)}>
                <span className="suggestion-icon">{p.icon}</span>
                <span>{p.text}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <MessageList messages={messages} loading={loading} bottomRef={bottomRef} />
      )}
    </div>
  );
}
