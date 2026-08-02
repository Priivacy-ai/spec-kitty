#!/usr/bin/env node
// Verifies FR-002's twin-phrasing cross-reference: for each declared
// duplicate-pair (2-member) or run-family (3-member) cluster, every
// member's near-miss set contains at least one string byte-identical to a
// should-trigger string in each of the other declared members' query-set
// files -- the sharpest available discrimination probe between confusable
// skills (data-model.md "Duplicate Pair / Run-Family Cluster").
//
// The cluster declaration below is loaded by filename convention
// (`<skill-id>-<purpose>-queries.yaml`, research.md §8), never by reading
// conformance/skills/behavioral-manifest.yaml's case list -- so this check
// stays meaningful even if a manifest case is temporarily commented out
// during authoring (contract's own explicit requirement, section 2).
//
// Node stdlib only (fs, path). Reuses the same minimal query-set YAML
// parser as check-trigger-queryset-shape.mjs (duplicated here rather than
// imported: this mission's owned_files for WP03 are exactly the manifest
// plus these four standalone scripts, no shared helper module).
//
// Contract: kitty-specs/skill-trigger-routing-suite-01KYVRB9/contracts/
//           verification-scripts-cli-contract.md, section 2.
//
// Invocation: node conformance/scripts/check-twin-phrasing.mjs <trigger-queries-dir>
//
// Exit 0: every declared pair/triple relationship is satisfied in both
//   directions.
// Exit 1: at least one declared relationship's required borrowed phrase is
//   missing, naming the specific unsatisfied direction; OR the directory
//   argument was omitted.
// Exit 2: a declared cluster member's query-set file could not be found or
//   parsed at all -- this is a fixture/naming-convention problem, not a
//   discrimination finding, so it is kept distinct from exit 1.

import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

// ─── Cluster declaration (data-model.md "Duplicate Pair / Run-Family
// Cluster") ──────────────────────────────────────────────────────────────
// Each entry is a list of skill-ids that form one cluster. `nearMissPurpose`
// names the file each member's near-miss set is read from; `shouldTriggerPurpose`
// names the file each *other* member's should-trigger set is read from.
// A 2-member duplicate-pair entry is fully self-referential (both purposes
// are `duplicate-pair` -- the only file that exists for those members). The
// 3-member run-family triple is NOT self-referential: its near-miss source
// is each member's `-run-family-queries.yaml`, but its should-trigger
// source is each member's `-duplicate-pair-queries.yaml` -- this mirrors
// WP02's own verified triple-cross-reference self-check exactly (its T014
// activity log), which compared `fam[s]['nearMiss']` against
// `dup[other]['shouldTrigger']`, not `fam[other]['shouldTrigger']`. WP02's
// own task file directive (T010 step 2) is that a run-family file's
// `shouldTrigger` is a verbatim copy of its duplicate-pair file's
// `shouldTrigger` for the same skill, so the two sources agree in practice
// today -- but this script reproduces WP02's actual comparison, not an
// equivalent-by-coincidence one, so it stays correct even if that
// duplication convention is ever relaxed.
const CLUSTERS = [
  { nearMissPurpose: "duplicate-pair", shouldTriggerPurpose: "duplicate-pair", members: ["ad-hoc-profile-load", "spk-doctrine-profile-load"] },
  { nearMissPurpose: "duplicate-pair", shouldTriggerPurpose: "duplicate-pair", members: ["spec-kitty-runtime-next", "spk-run-next"] },
  { nearMissPurpose: "duplicate-pair", shouldTriggerPurpose: "duplicate-pair", members: ["spec-kitty-runtime-review", "spk-run-review-wp"] },
  { nearMissPurpose: "duplicate-pair", shouldTriggerPurpose: "duplicate-pair", members: ["spec-kitty-implement-review", "spk-run-implement-review"] },
  { nearMissPurpose: "duplicate-pair", shouldTriggerPurpose: "duplicate-pair", members: ["spec-kitty-git-workflow", "spk-admin-git-workflow"] },
  { nearMissPurpose: "run-family", shouldTriggerPurpose: "duplicate-pair", members: ["spk-run-next", "spk-run-review-wp", "spk-run-implement-review"] },
];

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

function parseScalarToken(token) {
  if (token.length >= 2 && token.startsWith('"') && token.endsWith('"')) {
    return token.slice(1, -1);
  }
  return token;
}

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

/** Loads and parses one query-set file, returning its axis arrays or an error. */
function loadQuerySetFile(dir, purpose, skillId) {
  const filePath = join(dir, `${skillId}-${purpose}-queries.yaml`);
  if (!existsSync(filePath)) {
    return { filePath, error: `file not found (expected by naming convention: ${filePath})` };
  }
  let text;
  try {
    text = readFileSync(filePath, "utf8");
  } catch (error) {
    return { filePath, error: `cannot read file (${error.message})` };
  }
  const doc = parseQuerySetYaml(text);
  if (!Array.isArray(doc.shouldTrigger) || !Array.isArray(doc.nearMiss)) {
    return { filePath, error: "missing shouldTrigger/nearMiss arrays" };
  }
  return { filePath, shouldTrigger: doc.shouldTrigger, nearMiss: doc.nearMiss };
}

/** Loads every member's near-miss source and should-trigger source file for one cluster. */
function loadClusterFiles(dir, cluster) {
  const loadErrors = [];
  const nearMissById = {};
  const shouldTriggerById = {};

  for (const skillId of cluster.members) {
    const nearMissFile = loadQuerySetFile(dir, cluster.nearMissPurpose, skillId);
    if (nearMissFile.error) {
      loadErrors.push(`${skillId} (${cluster.nearMissPurpose}): ${nearMissFile.error}`);
    } else {
      nearMissById[skillId] = nearMissFile;
    }

    if (cluster.shouldTriggerPurpose === cluster.nearMissPurpose) {
      if (!nearMissFile.error) shouldTriggerById[skillId] = nearMissFile;
      continue;
    }
    const shouldTriggerFile = loadQuerySetFile(dir, cluster.shouldTriggerPurpose, skillId);
    if (shouldTriggerFile.error) {
      loadErrors.push(`${skillId} (${cluster.shouldTriggerPurpose}): ${shouldTriggerFile.error}`);
    } else {
      shouldTriggerById[skillId] = shouldTriggerFile;
    }
  }

  return { loadErrors, nearMissById, shouldTriggerById };
}

/**
 * Checks that `from`'s near-miss source contains at least one string
 * byte-identical to a string in `to`'s should-trigger source. Returns an
 * error string naming the unsatisfied direction, or null if satisfied.
 */
function checkDirection(fromId, fromNearMissFile, toId, toShouldTriggerFile) {
  const toShouldTriggerSet = new Set(toShouldTriggerFile.shouldTrigger);
  const hasMatch = fromNearMissFile.nearMiss.some((phrase) => toShouldTriggerSet.has(phrase));
  if (!hasMatch) {
    return `${fromId} -> ${toId}: no near-miss match found (expected a nearMiss entry in ` +
      `${fromNearMissFile.filePath} byte-identical to a shouldTrigger entry in ${toShouldTriggerFile.filePath})`;
  }
  return null;
}

function checkCluster(dir, cluster) {
  const { loadErrors, nearMissById, shouldTriggerById } = loadClusterFiles(dir, cluster);
  if (loadErrors.length > 0) {
    return { loadErrors, directionErrors: [] };
  }

  const directionErrors = [];
  for (const fromId of cluster.members) {
    for (const toId of cluster.members) {
      if (fromId === toId) continue;
      const error = checkDirection(fromId, nearMissById[fromId], toId, shouldTriggerById[toId]);
      if (error) directionErrors.push(error);
    }
  }
  return { loadErrors: [], directionErrors };
}

function main() {
  const dir = process.argv[2];

  if (!dir) {
    console.log("twin-phrasing: FAIL");
    console.log("  usage: check-twin-phrasing.mjs <trigger-queries-dir>");
    process.exit(1);
  }

  const allLoadErrors = [];
  const allDirectionErrors = [];

  for (const cluster of CLUSTERS) {
    const { loadErrors, directionErrors } = checkCluster(dir, cluster);
    allLoadErrors.push(...loadErrors);
    allDirectionErrors.push(...directionErrors);
  }

  if (allLoadErrors.length > 0) {
    console.log("twin-phrasing: ERROR");
    for (const error of allLoadErrors) console.log(`  ${error}`);
    process.exit(2);
  }

  if (allDirectionErrors.length > 0) {
    console.log("twin-phrasing: FAIL");
    for (const error of allDirectionErrors) console.log(`  ${error}`);
    process.exit(1);
  }

  console.log(
    `twin-phrasing: OK (${CLUSTERS.length} cluster(s), ` +
      `${CLUSTERS.reduce((sum, c) => sum + c.members.length * (c.members.length - 1), 0)} ordered direction(s) checked)`,
  );
  process.exit(0);
}

main();
