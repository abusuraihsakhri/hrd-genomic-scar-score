import test from "node:test";
import assert from "node:assert/strict";
import { scoreRecord, parseCsv, processCsv, serializeCsv } from "../web/scoring.mjs";

test("sums unweighted event counts and ignores metadata", () => {
  assert.equal(scoreRecord({ loh: "10", tai: "5", lst: "2", age: "90" }).score, 17);
  assert.equal(scoreRecord({ v1: "10", v2: "4", v3: "9" }).score, 23);
});
test("rejects partial, negative, decimal, nonnumeric and ambiguous inputs", () => {
  for (const row of [
    { loh: "1", tai: "2" }, { loh: "-1", tai: "2", lst: "3" },
    { loh: "1.5", tai: "2", lst: "3" }, { loh: "nan", tai: "2", lst: "3" },
    { loh: "1", v1: "4", tai: "2", lst: "3" },
  ]) assert.throws(() => scoreRecord(row));
});
test("parses quoted CSV and ignores trailing newline", () => {
  const rows = parseCsv('Sample_ID,loh,tai,lst\r\n"A, ""B""",1,2,3\r\n');
  assert.equal(rows.length, 2);
  assert.equal(rows[1][0], 'A, "B"');
});
test("generates batch output with score", () => {
  const result = processCsv("Sample_ID,loh,tai,lst\nSYN-1,4,5,6\n");
  assert.equal(result.rows[0][4], "15");
  assert.equal(result.rows[0][0], "SYN-1");
});
test("rejects malformed CSV and duplicate names", () => {
  assert.throws(() => processCsv("loh,tai,lst\n1,2\n"));
  assert.throws(() => processCsv("loh,LOH,tai,lst\n1,2,3,4\n"));
  assert.throws(() => parseCsv('"unterminated'));
});
test("protects exported metadata from spreadsheet formula execution", () => {
  const data = processCsv("label,loh,tai,lst\n=1+2,1,2,3\n");
  const serialized = serializeCsv(data);
  assert.match(serialized, /"'=1\+2"/);
  assert.match(serialized, /"score","classification"/);
});
