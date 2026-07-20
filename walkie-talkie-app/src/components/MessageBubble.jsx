function formatText(text) {
  const renderPipeTables = (raw) => {
    const lines = raw.split("\n");
    const out = [];
    let i = 0;

    const isPipeRow = (line) => {
      const t = line.trim();
      return (t.match(/\|/g) || []).length >= 2;
    };
    const isSeparatorRow = (line) => {
      const t = line.trim();
      return isPipeRow(t) && /^[|\s:-]+$/.test(t);
    };
    const splitCells = (line) => {
      const t = line.trim();
      const normalized = t.startsWith("|") ? t.slice(1) : t;
      const normalized2 = normalized.endsWith("|") ? normalized.slice(0, -1) : normalized;
      return normalized2.split("|").map((c) => c.trim());
    };

    while (i < lines.length) {
      let j = i + 1;
      while (j < lines.length && lines[j].trim() === "") j += 1;
      if (j < lines.length && isPipeRow(lines[i]) && isSeparatorRow(lines[j])) {
        const headerCells = splitCells(lines[i]);
        i = j + 1;
        const bodyRows = [];
        while (i < lines.length && isPipeRow(lines[i])) {
          bodyRows.push(splitCells(lines[i]));
          i += 1;
        }

        const headHtml = `<tr>${headerCells.map((c) => `<th>${c}</th>`).join("")}</tr>`;
        const bodyHtml = bodyRows
          .map((row) => `<tr>${row.map((c) => `<td>${c}</td>`).join("")}</tr>`)
          .join("");

        out.push(
          `<div class="md-table-wrap"><table class="md-table"><thead>${headHtml}</thead><tbody>${bodyHtml}</tbody></table></div>`
        );
        continue;
      }
      out.push(lines[i]);
      i += 1;
    }
    return out.join("\n");
  };

  const withTables = renderPipeTables(text);
  return withTables
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/🗝️[^\n]*/g, (m) => `<span class="local-secret">${m}</span>`)
    .replace(/Local Secret[^\n]*/g, (m) => `<span class="local-secret">🗝️ ${m}</span>`)
    .replace(/\n/g, "<br>")
    .replace(/<br>\s*<div class="md-table-wrap">/g, '<div class="md-table-wrap">')
    .replace(/<\/div>\s*<br>/g, "</div>");
}

export default function MessageBubble({ msg }) {
  if (msg.hidden) return null;
  const isAI = msg.role === 'assistant';
  return (
    <div className={`message ${msg.role}`}>
      <div className={`avatar ${isAI ? 'ai' : 'user'}`}>{isAI ? '🗺️' : '✈️'}</div>
      <div className={`bubble ${isAI ? 'ai' : 'user'}`}>
        {msg.preview && <img src={msg.preview} alt="uploaded" className="img-preview" />}
        {isAI
          ? <div dangerouslySetInnerHTML={{ __html: formatText(msg.content) }} />
          : <span>{msg.text}</span>}
      </div>
    </div>
  );
}
