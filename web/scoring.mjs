// Pure, zero-dependency module shared by the web UI and Node regression tests.
const METRICS = { loh: ["loh", "v1"], tai: ["tai", "v2"], lst: ["lst", "v3"] };
export const DISCLAIMER = "Not interpreted — assay-specific validation required";

function count(value, label) {
  const text = String(value ?? "").trim();
  if (!/^(0|[1-9]\d*)$/.test(text)) {
    throw new Error(label.toUpperCase() + " must be a non-negative whole-number event count.");
  }
  const n = Number(text);
  if (!Number.isSafeInteger(n)) throw new Error(label.toUpperCase() + " exceeds safe integer precision.");
  return n;
}

export function scoreRecord(record) {
  const normalized = {};
  for (const [key, value] of Object.entries(record)) {
    const lowered = key.toLowerCase();
    if (Object.hasOwn(normalized, lowered)) throw new Error("Duplicate column name: " + key);
    normalized[lowered] = value;
  }
  const result = {};
  for (const [metric, aliases] of Object.entries(METRICS)) {
    const present = aliases.filter(alias => Object.hasOwn(normalized, alias));
    if (present.length !== 1) throw new Error("Exactly one " + metric.toUpperCase() + " column is required.");
    result[metric] = count(normalized[present[0]], metric);
  }
  const score = result.loh + result.tai + result.lst;
  if (!Number.isSafeInteger(score)) throw new Error("Combined count exceeds safe integer precision.");
  return { ...result, score, classification: DISCLAIMER };
}

export function parseCsv(input) {
  const text = input.replace(/^\uFEFF/, "");
  const rows = [];
  let row = [], field = "", quoted = false, closed = false;
  function addField() { row.push(field); field = ""; closed = false; }
  function addRow() {
    addField();
    if (!(row.length === 1 && row[0] === "")) rows.push(row);
    row = [];
  }
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else { quoted = false; closed = true; }
      } else {
        field += ch;
      }
    } else if (ch === ',') {
      addField();
    } else if (ch === '\r' || ch === '\n') {
      addRow();
      if (ch === '\r' && text[i + 1] === '\n') i++;
    } else if (ch === '"') {
      if (field !== "" || closed) throw new Error("Malformed CSV quoting.");
      quoted = true;
    } else {
      if (closed) throw new Error("Unexpected text after a quoted CSV cell.");
      field += ch;
    }
  }
  if (quoted) throw new Error("Unterminated quoted CSV cell.");
  if (row.length || field !== "" || closed) addRow();
  return rows;
}

export function processCsv(text) {
  const rows = parseCsv(text);
  if (!rows.length) throw new Error("CSV is empty.");
  if (rows.length > 20001) throw new Error("Maximum 20,000 data records exceeded.");
  const headers = rows.shift();
  const names = headers.map(h => h.toLowerCase());
  if (names.some(n => !n) || new Set(names).size !== names.length) {
    throw new Error("CSV headers must be nonempty and unique.");
  }
  if (["score", "classification"].some(key => names.includes(key))) {
    throw new Error("CSV already contains an output column.");
  }
  const result = [];
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].length !== headers.length) throw new Error("CSV record " + (i + 2) + " has an unexpected column count.");
    const record = Object.fromEntries(headers.map((h, j) => [h, rows[i][j]]));
    let score;
    try { score = scoreRecord(record); }
    catch (err) { throw new Error("CSV record " + (i + 2) + ": " + err.message); }
    result.push([...rows[i], String(score.score), score.classification]);
  }
  // Validate columns for header-only CSVs too.
  scoreRecord(Object.fromEntries(headers.map(h => [h, "0"])));
  return { headers: [...headers, "score", "classification"], rows: result };
}

function escapeCell(value) {
  let cell = String(value ?? "");
  // Prevent formula execution when opened in spreadsheet applications.
  if (/^\s*[=+\-@\t\r]/.test(cell)) cell = "'" + cell;
  return '"' + cell.replace(/"/g, '""') + '"';
}

export function serializeCsv(table) {
  return [table.headers, ...table.rows].map(row => row.map(escapeCell).join(",")).join("\r\n") + "\r\n";
}
