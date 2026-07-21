import { useState } from 'react';

export default function LoginScreen({ onLogin, onRegister }) {
  const [mode, setMode] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [budget, setBudget] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError('');
    const u = username.trim();
    if (!u) { setError('Username is required.'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setBusy(true);
    try {
      const budgetNum = parseInt(budget, 10);
      const res = mode === 'login'
        ? await onLogin(u, password)
        : await onRegister(u, password, Number.isFinite(budgetNum) ? budgetNum : undefined);
      if (!res.ok) setError(res.error || 'Something went wrong. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1 className="login-title">WalkieTalkie</h1>
        <p className="sheet-note">Sign in to start exploring. Your chat history, visited places, and budget stay with your account.</p>
        <div className="login-tabs">
          <button className={mode === 'login' ? 'login-tab active' : 'login-tab'} onClick={() => { setMode('login'); setError(''); }}>Log in</button>
          <button className={mode === 'register' ? 'login-tab active' : 'login-tab'} onClick={() => { setMode('register'); setError(''); }}>Register</button>
        </div>
        <input className="sheet-input" placeholder="Username" autoCapitalize="none" autoCorrect="off" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input className="sheet-input" type="password" placeholder="Password (min 8 characters)" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') submit(); }} />
        {mode === 'register' && (
          <input className="sheet-input" type="number" placeholder="Budget/day in USD (optional)" value={budget} onChange={(e) => setBudget(e.target.value)} />
        )}
        {error && <p className="login-error">{error}</p>}
        <button className="btn-primary" style={{ width: '100%' }} disabled={busy} onClick={submit}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
        </button>
      </div>
    </div>
  );
}
