import { scoreRecord, processCsv, serializeCsv } from "./scoring.mjs";

const get = id => document.getElementById(id);
get("single-form").addEventListener("submit", event => {
  event.preventDefault();
  get("single-error").textContent = "";
  try {
    const result = scoreRecord({
      loh: get("loh").value, tai: get("tai").value, lst: get("lst").value
    });
    get("score").textContent = String(result.score);
    get("interpretation").textContent = result.classification;
  } catch (err) {
    get("score").textContent = "—";
    get("interpretation").textContent = "No clinical classification assigned";
    get("single-error").textContent = err.message;
  }
});

let latestResult = null;
get("batch-form").addEventListener("submit", async event => {
  event.preventDefault();
  get("batch-error").textContent = "";
  get("batch-status").textContent = "Processing locally…";
  get("export-btn").disabled = true;
  latestResult = null;
  const file = get("csv-file").files[0];
  if (!file) { get("batch-error").textContent = "Select a CSV file."; return; }
  if (file.size > 2 * 1024 * 1024) {
    get("batch-status").textContent = "No file processed.";
    get("batch-error").textContent = "File exceeds 2 MB limit.";
    return;
  }
  get("process-btn").disabled = true;
  try {
    latestResult = processCsv(await file.text());
    get("batch-status").textContent = String(latestResult.rows.length) + " records calculated. Results remain on this device.";
    get("export-btn").disabled = false;
  } catch (err) {
    get("batch-status").textContent = "No file processed.";
    get("batch-error").textContent = err.message;
  } finally {
    get("process-btn").disabled = false;
  }
});

get("csv-file").addEventListener("change", () => {
  latestResult = null;
  get("export-btn").disabled = true;
  get("batch-status").textContent = "No file processed.";
  get("batch-error").textContent = "";
});

get("export-btn").addEventListener("click", () => {
  if (!latestResult) return;
  const csv = serializeCsv(latestResult);
  const url = URL.createObjectURL(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "hrd_genomic_scar_results.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
