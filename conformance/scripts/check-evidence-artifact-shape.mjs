#!/usr/bin/env node
// Verifies FR-005's committed evidence artifact
// (conformance/skills/trigger-evidence/<run-timestamp>.json) against
// contracts/evidence-artifact.schema.json's shape, plus an independent
// credential-leak text scan over the raw file bytes.
//
// The schema check alone is NOT sufficient (contract, section 3): a full
// URL with an embedded `?api_key=...` query parameter is still a
// perfectly valid JSON string for `endpointHost` -- it contains no `@`, so
// the schema's own credential guard (`pattern: "^[^@]*$"`) never fires.
// The leak scan below is a second, independent pass over the raw text,
// deliberately redundant with -- but not replaced by -- the repo-wide
// NFR-002 grep this suite also runs separately (`command grep -rE
// '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' ...`); this script
// reuses the same pattern, scoped to one file, so a leak in a committed
// evidence artifact is caught even by a reviewer who runs only this one
// script.
//
// Node stdlib only (fs). No JSON-schema library dependency: the schema at
// contracts/evidence-artifact.schema.json is small and fixed-shape enough
// that a hand-written validator (below) mirrors it exactly without adding
// a dependency this mission does not otherwise carry.
//
// Contract: kitty-specs/skill-trigger-routing-suite-01KYVRB9/contracts/
//           verification-scripts-cli-contract.md, section 3.
// Schema: kitty-specs/skill-trigger-routing-suite-01KYVRB9/contracts/
//         evidence-artifact.schema.json
//
// Invocation: node conformance/scripts/check-evidence-artifact-shape.mjs <evidence.json>
//
// Exit 0: the file is valid JSON, satisfies the schema, and the
//   credential-leak scan finds nothing.
// Exit 1: missing/malformed schema field(s), OR a credential-leak match --
//   naming the specific field or the specific leak, never a bare "invalid."
// Exit 2: no file argument given, or the file cannot be read at all.

import { readFileSync } from "node:fs";

const CREDENTIAL_LEAK_PATTERN = /(sk-|api[_-]?key\s*[:=]\s*["']?)[A-Za-z0-9]{10,}/gi;
const DATE_TIME_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;

const TOP_LEVEL_REQUIRED = ["timestamp", "model", "endpointHost", "cases"];
const TOP_LEVEL_ALLOWED = new Set(TOP_LEVEL_REQUIRED);
const CASE_REQUIRED = ["id", "isControl", "passed", "shouldTrigger", "nearMiss", "runsErrored"];
const CASE_ALLOWED = new Set(CASE_REQUIRED);
const AXIS_REQUIRED = ["triggerRate", "threshold", "passed"];
const AXIS_ALLOWED = new Set(AXIS_REQUIRED);

/** Redacts a matched credential-shaped substring for safe display in error output. */
function redact(match) {
  const visible = match.slice(0, 6);
  return `${visible}...(redacted, length ${match.length})`;
}

/** Scans raw file text for credential-shaped substrings, independent of JSON validity. */
function scanForCredentialLeak(rawText) {
  const matches = [...rawText.matchAll(CREDENTIAL_LEAK_PATTERN)].map((m) => m[0]);
  if (matches.length === 0) return [];
  return matches.map((m) => `credential-leak: found a credential-shaped substring: ${redact(m)}`);
}

/** Checks top-level required fields, extra-field rejection, and each field's basic type. */
function validateTopLevel(doc) {
  const errors = [];
  for (const field of TOP_LEVEL_REQUIRED) {
    if (doc[field] === undefined) errors.push(`missing required top-level field '${field}'`);
  }
  for (const key of Object.keys(doc)) {
    if (!TOP_LEVEL_ALLOWED.has(key)) errors.push(`unexpected top-level field '${key}'`);
  }
  if (typeof doc.timestamp === "string" && !DATE_TIME_PATTERN.test(doc.timestamp)) {
    errors.push(`'timestamp' is not a valid ISO-8601 date-time: ${JSON.stringify(doc.timestamp)}`);
  }
  if (typeof doc.model === "string" && doc.model.length === 0) {
    errors.push("'model' must not be empty");
  }
  if (typeof doc.endpointHost === "string") {
    if (doc.endpointHost.length === 0) errors.push("'endpointHost' must not be empty");
    if (doc.endpointHost.includes("@")) {
      errors.push(
        `'endpointHost' contains '@' (credential-in-URL guard): ${JSON.stringify(doc.endpointHost)}`,
      );
    }
  }
  if (doc.cases !== undefined && (!Array.isArray(doc.cases) || doc.cases.length === 0)) {
    errors.push("'cases' must be a non-empty array");
  }
  return errors;
}

/** Checks one axisEvidence object (shouldTrigger/nearMiss). */
function validateAxis(caseId, axisName, axis) {
  const errors = [];
  const label = `case '${caseId}'.${axisName}`;
  if (typeof axis !== "object" || axis === null) {
    return [`${label}: missing or not an object`];
  }
  for (const field of AXIS_REQUIRED) {
    if (axis[field] === undefined) errors.push(`${label}: missing required field '${field}'`);
  }
  for (const key of Object.keys(axis)) {
    if (!AXIS_ALLOWED.has(key)) errors.push(`${label}: unexpected field '${key}'`);
  }
  for (const field of ["triggerRate", "threshold"]) {
    const value = axis[field];
    if (typeof value === "number" && (value < 0 || value > 1)) {
      errors.push(`${label}.${field} must be within [0, 1], got ${value}`);
    }
  }
  return errors;
}

/** Checks one caseEvidence object. */
function validateCase(index, kase) {
  if (typeof kase !== "object" || kase === null) {
    return [`cases[${index}]: not an object`];
  }
  const caseId = typeof kase.id === "string" ? kase.id : `cases[${index}]`;
  const errors = [];
  for (const field of CASE_REQUIRED) {
    if (kase[field] === undefined) errors.push(`case '${caseId}': missing required field '${field}'`);
  }
  for (const key of Object.keys(kase)) {
    if (!CASE_ALLOWED.has(key)) errors.push(`case '${caseId}': unexpected field '${key}'`);
  }
  if (kase.runsErrored !== undefined) {
    const isNonNegativeInteger = Number.isInteger(kase.runsErrored) && kase.runsErrored >= 0;
    if (!isNonNegativeInteger) {
      errors.push(`case '${caseId}'.runsErrored must be a non-negative integer, got ${JSON.stringify(kase.runsErrored)}`);
    }
  }
  if (kase.shouldTrigger !== undefined) errors.push(...validateAxis(caseId, "shouldTrigger", kase.shouldTrigger));
  if (kase.nearMiss !== undefined) errors.push(...validateAxis(caseId, "nearMiss", kase.nearMiss));
  return errors;
}

/** Validates the parsed document against the full evidence-artifact schema. */
function validateSchema(doc) {
  const errors = validateTopLevel(doc);
  if (Array.isArray(doc.cases)) {
    doc.cases.forEach((kase, index) => errors.push(...validateCase(index, kase)));
  }
  return errors;
}

function main() {
  const filePath = process.argv[2];
  if (!filePath) {
    console.log("evidence-artifact-shape: ERROR");
    console.log("  usage: check-evidence-artifact-shape.mjs <evidence.json>");
    process.exit(2);
  }

  let rawText;
  try {
    rawText = readFileSync(filePath, "utf8");
  } catch (error) {
    console.log("evidence-artifact-shape: ERROR");
    console.log(`  cannot read file '${filePath}' (${error.message})`);
    process.exit(2);
  }

  const leakErrors = scanForCredentialLeak(rawText);

  let doc;
  let parseError = null;
  try {
    doc = JSON.parse(rawText);
  } catch (error) {
    parseError = error;
  }

  const errors = [...leakErrors];
  if (parseError) {
    errors.push(`file is not valid JSON (${parseError.message})`);
  } else {
    errors.push(...validateSchema(doc));
  }

  if (errors.length > 0) {
    console.log("evidence-artifact-shape: FAIL");
    for (const error of errors) console.log(`  ${error}`);
    process.exit(1);
  }

  console.log(`evidence-artifact-shape: OK (${doc.cases.length} case(s) validated)`);
  process.exit(0);
}

main();
