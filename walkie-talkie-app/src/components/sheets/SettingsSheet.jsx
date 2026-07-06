import Sheet from './Sheet';

export default function SettingsSheet({
  open, onClose, llmTier, setLlmTier, promptStrategy, setPromptStrategy,
  PROMPT_STRATEGIES, userBudget, setUserBudget, saveBudgetPreference,
}) {
  return (
    <Sheet open={open} onClose={onClose} title="Settings">
      <label className="field"><span>Model tier</span>
        <select value={llmTier} onChange={(e) => setLlmTier(e.target.value)}>
          <option value="large">Large (nvidia/nemotron-3-nano-30b-a3b:free)</option>
          <option value="small">Small (nvidia/nemotron-nano-9b-v2:free)</option>
        </select>
      </label>
      <label className="field"><span>Prompt strategy</span>
        <select value={promptStrategy} onChange={(e) => setPromptStrategy(e.target.value)}>
          {Object.entries(PROMPT_STRATEGIES).map(([value, cfg]) => (
            <option key={value} value={value}>{cfg.label}</option>
          ))}
        </select>
      </label>
      <label className="field"><span>My budget/day (USD)</span>
        <input type="number" min={0} value={userBudget}
          onChange={(e) => setUserBudget(e.target.value)} onBlur={saveBudgetPreference} placeholder="USD" />
      </label>
    </Sheet>
  );
}
