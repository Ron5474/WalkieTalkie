import MessageBubble from './MessageBubble';

export default function MessageList({ messages, loading, bottomRef }) {
  return (
    <>
      {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
      {loading && (
        <div className="message">
          <div className="avatar ai">🗺️</div>
          <div className="bubble ai">
            <div className="typing"><div className="dot" /><div className="dot" /><div className="dot" /></div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </>
  );
}
