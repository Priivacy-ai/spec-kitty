#!/usr/bin/env node
// Verifies that every given trigger query-set YAML file (FR-001,
// muster@v1.2.1's `fixtures/skills/trigger-queries/*.yaml` shape) has the
// required scalar fields and satisfies the MIN_QUERIES_PER_AXIS=8 hard gate
// per axis -- the same gate muster's own `runTriggerConformance` enforces
// at `src/adapters/skills/trigger.ts:404-405` (constant `:66`, muster
// commit 16f0d34c3126fab5df2ee0b6e1e304a4d9bcb8e3, tag v1.2.1). A file that
// fails this gate is silently zeroed by muster itself (both axes report
// `triggerRate: 0`, `passed: false`) rather than genuinely graded -- this
// script exists so that silent zeroing is caught here, locally and fast,
// instead of being misread later as "the model never triggered."
//
// Node stdlib only (fs, path). No YAML library dependency: the query-set
// files this mission authors are a small, disciplined subset of YAML (flat
// top-level scalar/list keys, double-quoted list entries, full-line or
// trailing `#` comments) -- parseQuerySetYaml() below is a minimal, private
// parser for exactly that subset, not a general-purpose YAML reader.
//
// Contract: kitty-specs/skill-trigger-routing-suite-01KYVRB9/contracts/
//           verification-scripts-cli-contract.md, section 1.
//
// Invocation: node conformance/scripts/check-trigger-queryset-shape.mjs <file.yaml> [<file.yaml> ...]
// Working directory: irrelevant -- every path is resolved as given (shell
// globbing, e.g. `conformance/skills/trigger-queries/*.yaml`, happens in
// the caller, never inside this script).
//
// Exit 0: every given file satisfies every check below.
// Exit 1: at least one file fails at least one check, OR zero files were
//   given at all. A zero-file invocation is deliberately NOT exit 0: an
//   empty argument list (e.g. a caller's glob expanding to nothing because
//   the trigger-queries directory is empty or was deleted) must never be
//   indistinguishable from "every file passed" -- a prior inline version of
//   this exact check (a Python `for f in glob.glob(...): ...` loop) was
//   found to silently report success on an empty glob, because an empty
//   loop body leaves its `ok` accumulator at its initial `True` value. See
//   this script's own falsification proof for the zero-file case, run
//   alongside the 7-entry-axis rejection case.
//
// Anti-vacuity note (FR-001 findings from WP01's review of the throwaway
// inline predecessor of this check): the hard gate above is `.length`-only,
// and muster's own `gradeAxis` (trigger.ts:242-244) sums `runsTriggered`/
// `runsTotal` over every entry without deduplicating or rejecting blanks --
// so a duplicated or empty-string query silently inflates an axis's entry
// count without adding a distinct probe, and would still pass muster's own
// gate. This script additionally rejects (distinctness check, non-blank
// check, both below) even though today's real files have neither defect.

import { readFileSync } from "node:fs";

const REQUIRED_SCALAR_FIELDS = ["id", "source", "threshold"];
const REQUIRED_AXIS_FIELDS = ["shouldTrigger", "nearMiss"];
const MIN_QUERIES_PER_AXIS = 8;

/**
 * Strips a trailing `#`-comment from one line, respecting double-quoted
 * strings (a `#` inside a quoted query string is never a comment marker).
 * A line that is entirely a comment (optionally indented) reduces to an
 * empty/whitespace-only string, which the caller then skips.
 */
function stripInlineComment(line) {
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      inQuote = !inQuote;
    } else if (ch === "#" && !inQuote) {
      return line.slice(0, i);
    }
  }
  return line;
}

/** Strips one layer of surrounding double quotes, if present. */
function parseScalarToken(token) {
  if (token.length >= 2 && token.startsWith('"') && token.endsWith('"')) {
    return token.slice(1, -1);
  }
  return token;
}

/**
 * Minimal parser for this mission's flat query-set YAML subset: top-level
 * scalar keys (`id:`, `source:`, `threshold:`) and top-level list keys
 * (`shouldTrigger:`, `nearMiss:`) whose items are `- ...` lines. Tolerates
 * both this suite's own authored style (2-space-indented, double-quoted
 * entries) and PyYAML's `safe_dump` default style (zero-indent, unquoted
 * entries) -- the latter is not a hypothetical: it is the exact output
 * shape this mission's own rejection-case construction procedure produces
 * (round-tripping a file through `yaml.safe_load`/`yaml.safe_dump` to
 * truncate an axis), so a parser that only accepted the first style would
 * make that rejection case fail for the wrong reason (an unparseable file
 * reporting 0 entries) rather than the intended reason (7 entries).
 */
function parseQuerySetYaml(text) {
  const doc = {};
  let currentListKey = null;

  for (const rawLine of text.split("\n")) {
    const line = stripInlineComment(rawLine);
    if (line.trim() === "") continue;

    const topLevelMatch = line.match(/^([A-Za-z][A-Za-z0-9_]*):\s*(.*)$/);
    if (topLevelMatch) {
      const [, key, rest] = topLevelMatch;
      if (rest.trim() === "") {
        doc[key] = [];
        currentListKey = key;
      } else {
        doc[key] = parseScalarToken(rest.trim());
        currentListKey = null;
      }
      continue;
    }

    const listItemMatch = line.match(/^\s*-\s*(.*)$/);
    if (listItemMatch && currentListKey !== null) {
      doc[currentListKey].push(parseScalarToken(listItemMatch[1].trim()));
    }
  }

  return doc;
}

/** Checks one file's required scalar fields. Returns an array of error strings. */
function checkScalarFields(fileLabel, doc) {
  const errors = [];
  for (const field of REQUIRED_SCALAR_FIELDS) {
    if (doc[field] === undefined || doc[field] === "") {
      errors.push(`${fileLabel}: missing required field '${field}'`);
    }
  }
  return errors;
}

/** Checks one axis array's shape: present, an array, >=8 entries, distinct, non-blank. */
function checkAxis(fileLabel, doc, axisName) {
  const errors = [];
  const axis = doc[axisName];

  if (!Array.isArray(axis)) {
    errors.push(`${fileLabel}: '${axisName}' is missing or not a list`);
    return errors;
  }
  if (axis.length < MIN_QUERIES_PER_AXIS) {
    errors.push(
      `${fileLabel}: ${axisName} has ${axis.length} entries, need >= ${MIN_QUERIES_PER_AXIS}`,
    );
  }

  const blankIndexes = axis
    .map((entry, i) => (entry.trim() === "" ? i : -1))
    .filter((i) => i !== -1);
  if (blankIndexes.length > 0) {
    errors.push(
      `${fileLabel}: ${axisName} has ${blankIndexes.length} blank/whitespace-only entr${
        blankIndexes.length === 1 ? "y" : "ies"
      } (index${blankIndexes.length === 1 ? "" : "es"} ${blankIndexes.join(", ")}) -- a blank query inflates the axis count without adding a distinct probe`,
    );
  }

  const seen = new Set();
  const duplicates = new Set();
  for (const entry of axis) {
    if (seen.has(entry)) duplicates.add(entry);
    seen.add(entry);
  }
  if (duplicates.size > 0) {
    errors.push(
      `${fileLabel}: ${axisName} has ${duplicates.size} duplicate entr${
        duplicates.size === 1 ? "y" : "ies"
      } (${[...duplicates].map((d) => JSON.stringify(d)).join(", ")}) -- muster's own gradeAxis (trigger.ts:242-244) sums over every entry without deduplicating, so a duplicate silently double-weights one probe`,
    );
  }

  return errors;
}

/** Checks one file end to end: read, parse, scalar fields, both axes. */
function checkFile(filePath) {
  let text;
  try {
    text = readFileSync(filePath, "utf8");
  } catch (error) {
    return [`${filePath}: cannot read file (${error.message})`];
  }

  let doc;
  try {
    doc = parseQuerySetYaml(text);
  } catch (error) {
    return [`${filePath}: cannot parse as a query-set YAML file (${error.message})`];
  }

  return [
    ...checkScalarFields(filePath, doc),
    ...checkAxis(filePath, doc, REQUIRED_AXIS_FIELDS[0]),
    ...checkAxis(filePath, doc, REQUIRED_AXIS_FIELDS[1]),
  ];
}

function main() {
  const filePaths = process.argv.slice(2);

  if (filePaths.length === 0) {
    console.log("trigger-queryset-shape: FAIL");
    console.log(
      "  no query-set files were given -- an empty argument list (e.g. a glob that " +
        "expanded to zero files) is a failure, never a vacuous pass",
    );
    process.exit(1);
  }

  const errors = filePaths.flatMap((filePath) => checkFile(filePath));

  if (errors.length > 0) {
    console.log("trigger-queryset-shape: FAIL");
    for (const error of errors) console.log(`  ${error}`);
    process.exit(1);
  }

  console.log(`trigger-queryset-shape: OK (${filePaths.length} file(s) checked)`);
  process.exit(0);
}

main();
