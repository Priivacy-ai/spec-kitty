#!/usr/bin/env node
/**
 * check-doctrine-manifest-completeness.mjs (absence guard)
 *
 * Contract: kitty-specs/doctrine-rule-manifests-01KYH7AM/contracts/
 *   doctrine-manifest-completeness-contract.md
 *
 * This script closes the one gap muster's own error paths do not cover: a
 * rule entry silently dropped from a manifest produces no finding of any
 * kind and a clean `exit 0` from muster itself.
 *
 * Invocation: node conformance/scripts/check-doctrine-manifest-completeness.mjs
 *   (no arguments, run from the repository root, Node stdlib only -- fs/path,
 *   no npm dependency, no network access, no environment variables.)
 *
 * Algorithm:
 *   1. Expected rule count per in-scope directive -- read each of the 13
 *      directive files and count `integrity_rules` bullets via a line-based
 *      block scan (no YAML parser): enter the block at a line matching
 *      /^integrity_rules:/, exit at the next line matching /^[A-Za-z_]+:/,
 *      count lines inside the block matching /^\s*-\s/. Recomputed fresh on
 *      every run -- never hardcoded as a lookup table.
 *   2. Actual rule count per shipped manifest -- read each of the 13
 *      manifest files as plain text and count lines matching
 *      /^\s*- ruleId:/.
 *   3. Manifest existence -- confirm all 13 expected manifest files exist at
 *      conformance/doctrine/<directive-stem>.yaml (paired 1:1 by filename
 *      stem) and that the control manifest exists at
 *      conformance/doctrine/control/045-drifted.yaml with exactly 1 rule
 *      entry.
 *
 *      DIVISION OF LABOR (deliberate, do not blur): this script's filename-
 *      stem pairing is the ENTIRE extent of what it checks about a
 *      manifest's identity -- it never reads or validates a manifest's
 *      `sopFile:` field. A manifest can exist at the right path, with the
 *      right rule count, and still point its `sopFile:` at a deleted
 *      directive file or a typo'd path; this script reports OK for that
 *      manifest regardless. That specific failure mode is guarded
 *      EXCLUSIVELY by the drift gate's STRUCTURAL_ABSENCE jq filter entry
 *      (check-doctrine-drift-gate.sh) -- do not add sopFile: validation
 *      here; the two scripts do not overlap.
 *   4. Compare and report -- for each directive, assert
 *      actualManifestRuleCount === expectedDirectiveRuleCount. On any
 *      mismatch (including a manifest file being entirely absent, treated
 *      as an actual count of 0), print every offending directive by name
 *      and both counts; exit 1. On full agreement across all 13 directives
 *      plus the control's existence, print a one-line confirmation --
 *      reporting the manifest/rule counts actually found, not the hardcoded
 *      length of DIRECTIVE_STEMS -- and exit 0.
 *
 *      FLOOR ASSERTION (do not remove): an in-scope directive's
 *      `integrity_rules` block must always yield at least one rule.
 *      expectedDirectiveRuleCount === 0 is never legitimate -- it means the
 *      block scan failed to parse the directive (e.g. the `integrity_rules:`
 *      key itself is missing or malformed), not that the directive has zero
 *      rules. Without this floor, a compound failure -- an unparseable
 *      directive (expected=0) whose manifest was ALSO deleted (actual=0) --
 *      passes `0 === 0` silently, reintroducing this mission's own defect
 *      class inside the guard written to close it. This is checked and
 *      named BEFORE the actual/expected comparison, independent of whatever
 *      actual happens to be.
 *
 * Exit codes: 0 = all 13 counts match and control exists with exactly 1
 * rule; 1 = any mismatch, named explicitly; this script never exits 2
 * (reserved for "muster itself errored" -- this script never invokes muster).
 */

import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const REPO_ROOT = process.cwd();
const DIRECTIVE_DIR = join(REPO_ROOT, "src/doctrine/directives/built-in");
const MANIFEST_DIR = join(REPO_ROOT, "conformance/doctrine");
const CONTROL_MANIFEST = join(MANIFEST_DIR, "control/045-drifted.yaml");

// The 13 in-scope directives, paired 1:1 by filename stem with their
// shipped manifest (contracts/doctrine-rule-manifest-shape.md's naming
// convention: manifest basename mirrors the directive's stem minus
// `.directive`).
const DIRECTIVE_STEMS = [
  "001-architectural-integrity-standard",
  "010-specification-fidelity-requirement",
  "018-doctrine-versioning-requirement",
  "028-search-tool-discipline",
  "029-agent-commit-signing-policy",
  "030-test-and-typecheck-quality-gate",
  "033-targeted-staging-policy",
  "034-test-first-development",
  "035-bulk-edit-occurrence-classification",
  "039-lynn-cole-engineering-culture",
  "042-common-docs",
  "044-canonical-sources-and-unification",
  "045-prs-only-and-read-intent",
];

/**
 * Count `integrity_rules` bullets in a directive file via a line-based
 * block scan. No YAML parser.
 */
function countIntegrityRules(filePath) {
  const lines = readFileSync(filePath, "utf-8").split("\n");
  let inBlock = false;
  let count = 0;
  for (const line of lines) {
    if (/^integrity_rules:/.test(line)) {
      inBlock = true;
      continue;
    }
    if (inBlock && /^[A-Za-z_]+:/.test(line)) {
      inBlock = false;
      continue;
    }
    if (inBlock && /^\s*-\s/.test(line)) {
      count += 1;
    }
  }
  return count;
}

/**
 * Count `- ruleId:` entries in a manifest file. Returns 0 if the file does
 * not exist (an absent manifest is treated as an actual rule count of 0,
 * per the contract).
 */
function countManifestRuleIds(filePath) {
  if (!existsSync(filePath)) {
    return 0;
  }
  const lines = readFileSync(filePath, "utf-8").split("\n");
  let count = 0;
  for (const line of lines) {
    if (/^\s*- ruleId:/.test(line)) {
      count += 1;
    }
  }
  return count;
}

const mismatches = [];
let totalExpected = 0;
let totalActual = 0;
let manifestsFound = 0;

for (const stem of DIRECTIVE_STEMS) {
  const directiveFile = join(DIRECTIVE_DIR, `${stem}.directive.yaml`);
  const manifestFile = join(MANIFEST_DIR, `${stem}.yaml`);

  const expected = countIntegrityRules(directiveFile);
  const manifestExists = existsSync(manifestFile);
  const actual = countManifestRuleIds(manifestFile);

  totalExpected += expected;
  totalActual += actual;
  if (manifestExists) {
    manifestsFound += 1;
  }

  // Floor assertion FIRST, independent of `actual`: an in-scope directive
  // must always yield at least one integrity_rules entry. expected === 0
  // means the block scan could not parse this directive's integrity_rules
  // block -- named as its own mismatch so it can never silently match an
  // also-missing manifest (0 === 0).
  if (expected === 0) {
    mismatches.push(
      `  ${stem}: directive yielded 0 integrity_rules (floor violation -- an in-scope directive must always yield at least one rule; treat this as an unparseable integrity_rules block, not a legitimate zero)`
    );
  } else if (actual !== expected) {
    if (!manifestExists) {
      mismatches.push(
        `  ${stem}: manifest file conformance/doctrine/${stem}.yaml not found (expected ${expected} rules, found 0)`
      );
    } else {
      const diff = expected - actual;
      mismatches.push(
        `  ${stem}: directive has ${expected} integrity_rules, manifest has ${actual} rule entries (missing: ${diff})`
      );
    }
  }
}

// Control manifest: must exist, must have exactly 1 rule entry.
const controlExists = existsSync(CONTROL_MANIFEST);
const controlRuleCount = controlExists ? countManifestRuleIds(CONTROL_MANIFEST) : 0;
let controlOk = controlExists && controlRuleCount === 1;
if (!controlOk) {
  mismatches.push(
    `  control manifest conformance/doctrine/control/045-drifted.yaml not found or has ${controlRuleCount} rule entries (expected exactly 1)`
  );
}

if (mismatches.length > 0) {
  console.log("doctrine manifest completeness: MISMATCH");
  for (const line of mismatches) {
    console.log(line);
  }
  process.exit(1);
}

console.log(
  `doctrine manifest completeness: OK (${manifestsFound} manifests, ${totalActual} rules, 1 control)`
);
process.exit(0);
