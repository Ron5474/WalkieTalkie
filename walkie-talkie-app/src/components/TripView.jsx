import { CITIES } from '../constants';

/** Calendar label for itinerary day 1..N from trip start (YYYY-MM-DD). */
function formatTripDayHeading(isoDateStr, dayNum) {
  if (!isoDateStr || !dayNum) return null;
  const parts = isoDateStr.split("-");
  if (parts.length !== 3) return null;
  const y = parseInt(parts[0], 10);
  const mo = parseInt(parts[1], 10) - 1;
  const d = parseInt(parts[2], 10);
  const dt = new Date(y, mo, d + (dayNum - 1));
  if (Number.isNaN(dt.getTime())) return null;
  const weekday = dt.toLocaleDateString(undefined, { weekday: "long" });
  const rest = dt.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
  return `${weekday} — ${rest}`;
}

export default function TripView({
  selectedCity, setSelectedCity, numDaysInput, setNumDaysInput,
  // eslint-disable-next-line no-unused-vars -- part of the shared props interface; not rendered directly in this view
  numDays, setNumDays,
  userBudget, setUserBudget, saveBudgetPreference, travelDates, setTravelDates,
  loading, onGenerate, actionPlan, itineraryMap, holidayBriefing,
  activeSubTab, setActiveSubTab, onMarkCovered, onDayCheckIn,
}) {
  return (
    <div className="trip-view">
      <section className="trip-controls">
        <label className="field"><span>City</span>
          <select value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)}>
            {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="field"><span>Days</span>
          <input type="text" inputMode="numeric" pattern="[0-9]*" value={numDaysInput}
            onChange={(e) => { const v = e.target.value.replace(/[^\d]/g, ''); if (v.length <= 2) setNumDaysInput(v); }}
            onBlur={() => { const n = parseInt(numDaysInput, 10); const safe = Number.isFinite(n) ? Math.min(14, Math.max(1, n)) : 1; setNumDays(safe); setNumDaysInput(String(safe)); }} />
        </label>
        <label className="field"><span>Budget/day (USD)</span>
          <input type="number" min={0} value={userBudget} placeholder="USD"
            onChange={(e) => setUserBudget(e.target.value)} onBlur={saveBudgetPreference} />
        </label>
        <label className="field"><span>Start date</span>
          <input type="date" value={travelDates} onChange={(e) => setTravelDates(e.target.value)} style={{ colorScheme: 'dark' }} />
        </label>
        <button className="btn-primary" onClick={onGenerate} disabled={loading}>Generate itinerary</button>
      </section>

      <section className="action-plan">
        <h2 style={{ fontFamily: "'Playfair Display', serif", color: "var(--gold)", marginBottom: "6px" }}>Holiday Action Plan</h2>
        <p style={{ color: "var(--muted)", fontSize: "14px", marginBottom: "16px", lineHeight: 1.5 }}>
          {Array.isArray(itineraryMap) && itineraryMap.length > 0 ? (
            <>Day-to-day shows <strong style={{ color: "var(--gold)" }}>{itineraryMap.length} day{itineraryMap.length === 1 ? "" : "s"}</strong> from your last generated plan.</>
          ) : (
            <>No multi-day plan loaded yet — set <strong style={{ color: "var(--gold)" }}>Days</strong> in Plan Itinerary and tap Generate itinerary.</>
          )}
          {!travelDates && (
            <span> Add a <strong style={{ color: "var(--gold)" }}>Start date</strong> to see weekday + calendar dates on each day.</span>
          )}
        </p>

        {holidayBriefing?.loading && (
          <p style={{ color: "var(--muted)", fontSize: "14px", marginBottom: "16px" }}>Looking up weather and packing ideas for your dates…</p>
        )}
        {holidayBriefing && !holidayBriefing.loading && holidayBriefing.packing_advice && (
          <div className="briefing-card">
            <h3 style={{ fontFamily: "'Playfair Display', serif", color: "var(--gold)", fontSize: "17px", marginBottom: "10px" }}>
              Weather & what to pack
            </h3>
            <div style={{ color: "#ddd5c0", fontSize: "14px", lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
              {holidayBriefing.packing_advice}
            </div>
          </div>
        )}
        {holidayBriefing && !holidayBriefing.loading && holidayBriefing.error && !holidayBriefing.packing_advice && (
          <p style={{ color: "#b08070", fontSize: "14px", marginBottom: "16px" }}>{holidayBriefing.error}</p>
        )}

        <div className="subtab-row">
          <button className={`subtab ${activeSubTab === 'places' ? 'active' : ''}`} onClick={() => setActiveSubTab('places')}>All Places</button>
          <button className={`subtab ${activeSubTab === 'eats' ? 'active' : ''}`} onClick={() => setActiveSubTab('eats')}>Must Eats</button>
          <button className={`subtab ${activeSubTab === 'itinerary' ? 'active' : ''}`} onClick={() => setActiveSubTab('itinerary')}>Day-to-Day</button>
          <button className="btn-primary" onClick={onDayCheckIn}>Day check-in</button>
        </div>

        {actionPlan.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>Your itinerary is empty or finished! Switch to Plan Itinerary and tap Generate itinerary.</p>
        ) : (
          <>
            {(activeSubTab === 'places' || activeSubTab === 'eats') && (
              actionPlan.filter(n => activeSubTab === 'places' ? n.type === 'place' : n.type === 'eat').map(node => (
                <div key={node.id} className="plan-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <h3 style={{ fontSize: "16px", color: "var(--cream)", marginBottom: "4px" }}>{node.title}</h3>
                    <p style={{ fontSize: "13px", color: "var(--muted)", maxWidth: "450px" }}>{node.anecdote}</p>
                  </div>
                  <button
                    onClick={() => onMarkCovered(node.id, node.title)}
                    className="covered-btn">
                    ✓ Covered
                  </button>
                </div>
              ))
            )}
            {activeSubTab === 'itinerary' && itineraryMap && itineraryMap.map((dayInfo) => {
              const calendarLine = formatTripDayHeading(travelDates, dayInfo.day);
              return (
              <div key={dayInfo.day} style={{ marginBottom: '24px' }}>
                <h3 className="day-heading">
                  Day {dayInfo.day}
                  {calendarLine ? (
                    <span style={{ color: '#c4b69a', fontWeight: 'normal', fontSize: '15px' }}> · {calendarLine}</span>
                  ) : null}
                </h3>
                {dayInfo.locality ? (
                  <p style={{ color: 'var(--muted)', fontSize: '13px', margin: '0 0 12px', lineHeight: 1.45 }}>
                    <strong style={{ color: '#c4b69a', fontWeight: 600 }}>Area focus:</strong> {dayInfo.locality} — same-day stops are grouped for walking this neighborhood.
                  </p>
                ) : null}
                {dayInfo.plan.map(nodeId => {
                  const node = actionPlan.find(n => n.id === nodeId);
                  if (!node) return null; // Already covered!
                  return (
                    <div key={node.id} style={{ background: "var(--raised)", padding: "12px", borderRadius: "8px", marginBottom: "8px", display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: 'var(--cream)', fontWeight: 'bold' }}>{node.title} <span style={{ color: 'var(--muted)', fontSize: '11px', marginLeft: '8px', textTransform: 'uppercase' }}>{node.type}</span></span>
                      <button onClick={() => onMarkCovered(node.id, node.title)} style={{ background: "transparent", color: "var(--gold)", border: "1px solid #c8a96e44", padding: "4px 8px", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>✓ Covered</button>
                    </div>
                  );
                })}
              </div>
            );
            })}
          </>
        )}
      </section>
    </div>
  );
}
