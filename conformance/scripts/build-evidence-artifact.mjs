#!/usr/bin/env node
// Out-of-map allowance (ownership-map-leeway tactic, one-line rationale):
// WP04's owned_files list the workflow file, trigger-evidence/**, and
// README.md, not conformance/scripts/**; this file is checked in here
// (rather than inlined as a workflow `node -e` one-liner) so the exact same
// summarization logic runs both in CI and in the one-time by-hand run that
// produced this mission's first committed evidence artifact -- inlining it
// twice would have let the two copies drift. No other WP writes this path.
//
// Builds a conformance/skills/trigger-evidence/<run-timestamp>.json evidence
// artifact (FR-005) from the raw `muster skills run --json` report
// (`SkillsRunResult`, src/cli/index.ts:1293/:1583 at v1.2.1), per
// data-model.md's Evidence Artifact shape and
// contracts/evidence-artifact.schema.json.
//
// The raw report carries no `model` field at all (muster resolves the model
// via `process.env["MUSTER_MODEL"] ?? "gpt-4o-mini"` at
// `resolveSkillsBehavioralEndpoint`, src/cli/index.ts:1387, same SHA, and
// never echoes it back into SkillsCaseResult) -- this script reads
// MUSTER_MODEL from its own environment at build time, falling back to the
// same "gpt-4o-mini" default muster itself uses, rather than hardcoding a
// value. Likewise `endpointHost` is derived from MUSTER_ENDPOINT
// (`new URL(...).host`, bare host only -- never the full URL or a
// credential, NFR-002).
//
// Invocation:
//   MUSTER_ENDPOINT=<endpoint> [MUSTER_MODEL=<model>] \
//     node conformance/scripts/build-evidence-artifact.mjs <raw-report.json> <output.json>
//
// Exit 0: the artifact was built and written to <output.json>.
// Exit 1: the raw report has no results, a case is still `skipped: true`
//   (no discrimination data to summarize -- this is the FR-003 skip-guard's
//   job to catch upstream of this step, but this script refuses to paper
//   over it by inventing a runsErrored:0/triggerRate:0 shape for a case that
//   never actually ran), or MUSTER_ENDPOINT is unset.
// Exit 2: missing/unreadable arguments.

import { readFileSync, writeFileSync } from "node:fs";

/** Sums runsErrored across one axis's queryBreakdown (mirrors check-control-discrimination.mjs). */
function sumAxisRunsErrored(axis) {
  if (!axis || !Array.isArray(axis.queryBreakdown)) return null;
  return axis.queryBreakdown.reduce((sum, q) => sum + (q.runsErrored ?? 0), 0);
}

/** Projects one raw SkillsCaseResult into this artifact's caseEvidence shape. */
function summarizeCase(raw) {
  if (raw.skipped === true) {
    throw new Error(
      `case '${raw.id}' is skipped:true (no MUSTER_ENDPOINT was configured for this run) -- ` +
        "refusing to summarize a run that never actually tested routing",
    );
  }
  const shouldTriggerErrored = sumAxisRunsErrored(raw.shouldTriggerAxis);
  const nearMissErrored = sumAxisRunsErrored(raw.nearMissAxis);
  if (shouldTriggerErrored === null || nearMissErrored === null) {
    throw new Error(`case '${raw.id}' has no shouldTriggerAxis/nearMissAxis queryBreakdown`);
  }
  return {
    id: raw.id,
    isControl: raw.isControl === true,
    passed: raw.passed,
    shouldTrigger: {
      triggerRate: raw.shouldTriggerAxis.triggerRate,
      threshold: raw.shouldTriggerAxis.threshold,
      passed: raw.shouldTriggerAxis.passed,
    },
    nearMiss: {
      triggerRate: raw.nearMissAxis.triggerRate,
      threshold: raw.nearMissAxis.threshold,
      passed: raw.nearMissAxis.passed,
    },
    runsErrored: shouldTriggerErrored + nearMissErrored,
  };
}

/** Builds the full evidence-artifact document from a parsed raw report. */
function buildArtifact(report, endpointUrl, model, timestamp) {
  if (!report || !Array.isArray(report.results) || report.results.length === 0) {
    throw new Error("raw report has no non-empty 'results' array");
  }
  return {
    timestamp,
    model,
    endpointHost: new URL(endpointUrl).host,
    cases: report.results.map(summarizeCase),
  };
}

function usageError(message) {
  console.log("build-evidence-artifact: ERROR");
  console.log(`  ${message}`);
  console.log(
    "  usage: MUSTER_ENDPOINT=<endpoint> node build-evidence-artifact.mjs <raw-report.json> <output.json>",
  );
  process.exit(2);
}

function main() {
  const [reportPath, outputPath] = process.argv.slice(2);
  if (!reportPath || !outputPath) {
    usageError("missing required <raw-report.json> and/or <output.json> arguments");
  }

  const endpointUrl = process.env["MUSTER_ENDPOINT"];
  if (!endpointUrl) {
    console.log("build-evidence-artifact: FAIL");
    console.log("  MUSTER_ENDPOINT is not set -- cannot derive endpointHost");
    process.exit(1);
  }
  const model = process.env["MUSTER_MODEL"] ?? "gpt-4o-mini";
  const timestamp = new Date().toISOString();

  let report;
  try {
    report = JSON.parse(readFileSync(reportPath, "utf8"));
  } catch (error) {
    usageError(`cannot read/parse report file '${reportPath}' (${error.message})`);
    return;
  }

  let artifact;
  try {
    artifact = buildArtifact(report, endpointUrl, model, timestamp);
  } catch (error) {
    console.log("build-evidence-artifact: FAIL");
    console.log(`  ${error.message}`);
    process.exit(1);
    return;
  }

  writeFileSync(outputPath, `${JSON.stringify(artifact, null, 2)}\n`);
  console.log(`build-evidence-artifact: OK (${artifact.cases.length} case(s) written to ${outputPath})`);
  process.exit(0);
}

main();
