import Sheet from './Sheet';

export default function AuthSheet({ open, onClose, authUserId, setAuthUserId, userBudget, setUserBudget, onSignIn }) {
  return (
    <Sheet open={open} onClose={onClose} title="Sign in to continue">
      <p className="sheet-note">We keep your city-wise chat history, visited places, and budget for 24 hours.</p>
      <input className="sheet-input" placeholder="User ID (e.g., spartan)" value={authUserId} onChange={(e) => setAuthUserId(e.target.value)} />
      <input className="sheet-input" type="number" placeholder="Budget/day (optional)" value={userBudget} onChange={(e) => setUserBudget(e.target.value)} />
      <div className="sheet-actions">
        <button className="btn-ghost" onClick={onClose}>Later</button>
        <button className="btn-primary" onClick={onSignIn}>Sign in</button>
      </div>
    </Sheet>
  );
}
