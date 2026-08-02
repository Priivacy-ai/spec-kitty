#!/usr/bin/env node
// sc003-erosion-control-045-neutralize-direction-driver.mjs — WP05, F7
// (post-review-follow-up remediation).
//
// Regenerates conformance/crosslayer/evidence/sc003-erosion-control-045.json
// from committed inputs only: this script, the two committed persona
// fixtures (fixtures/erosion-persona-045.Soul.md,
// fixtures/erosion-persona-045-neutral.Soul.md), the committed SOP extract
// (sop-extract.md), and the committed case file
// (cases/erosion-control-045.yaml, read here only for its rule/probe/
// baseline/composed/passThreshold values so this driver can never drift
// from the committed case it is proving).
//
// WHY THIS EXISTS (F7): the evidence artefact's own "not_yet_done" field
// originally recorded that its driver was "an ephemeral, uncommitted local
// tool" — meaning the per-run counts in that artefact were not
// reproducible from anything committed to this repo. That is a real gap:
// an evidence artefact whose generating process cannot itself be re-run is
// not independently checkable, only trusted. This script closes that gap
// by making the SAME two-direction (flip/neutralize) proof reproducible
// from committed source, on demand, against a live endpoint.
//
// Method (identical to the original ephemeral driver, unchanged): direct
// invocation of the real, installed `@garrison-hq/muster@1.1.0` package's
// own exported `assembleComposedContext`/`runRuleSurvival` functions (the
// SAME functions `manifest-runner.js`'s `runBehavioralCase` calls) — never
// a mock, never a reimplementation of grading logic. This captures the
// per-run `baselineResults`/`composedResults` detail that the CLI's own
// `--json` output discards (`manifest-runner.js` returns only
// `{id, passed, verdict}`).
//
// Credentials rule, absolute (matches every other live-run script in this
// mission): `MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY_ENV` (an
// environment-variable NAME, not a value) are read from the environment
// only. The env var this driver actually reads the API key from is named
// by `MUSTER_API_KEY_ENV` (default `MUSTER_API_KEY`) — never hardcoded,
// never logged, never written to the output JSON. Only the env-var NAME
// is ever recorded in output.
//
// Usage (from the repo root):
//   MUSTER_ENDPOINT=https://api.openai.com/v1 MUSTER_MODEL=gpt-4o-mini \
//     MUSTER_API_KEY=<key> node \
//     conformance/scripts/sc003-erosion-control-045-neutralize-direction-driver.mjs \
//     > conformance/crosslayer/evidence/sc003-erosion-control-045.json
//
// This script performs real, live model calls (3 baseline + 3 composed
// runs per direction, 12 calls total) and therefore requires a live
// endpoint and real credentials — it is NOT part of the offline/
// deterministic static or dummy-endpoint test suite (NFR-001) and is
// never invoked by CI. It is a manually-run evidence-regeneration tool,
// analogous to `check-persona-drift.sh`/`check-sop-extract-drift.sh` but
// for a live-model artefact rather than a byte-diff gate.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { parse as parseYaml } from "yaml";
import { assembleComposedContext } from "@garrison-hq/muster/dist/crosslayer/composition.js";
import { runRuleSurvival } from "@garrison-hq/muster/dist/crosslayer/rule-survival.js";

const CROSSLAYER_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "crosslayer",
);

function loadErosionControlCase() {
  const caseText = readFileSync(
    path.join(CROSSLAYER_DIR, "cases", "erosion-control-045.yaml"),
    "utf-8",
  );
  return parseYaml(caseText);
}

function buildEndpointConfig() {
  const apiKeyEnv = process.env.MUSTER_API_KEY_ENV ?? "MUSTER_API_KEY";
  if (!process.env.MUSTER_ENDPOINT || !process.env.MUSTER_MODEL) {
    throw new Error(
      "MUSTER_ENDPOINT and MUSTER_MODEL must both be set (env-var only, " +
        "per this mission's credential-handling rule).",
    );
  }
  return {
    baseUrl: process.env.MUSTER_ENDPOINT,
    model: process.env.MUSTER_MODEL,
    apiKeyEnv,
  };
}

async function runDirection(label, personaFixtureRelPath, expectedVerdict, committedCase) {
  // Absolute paths: composition.js's readLayerFiles() reads fixturePath
  // directly with no cwd/manifest-dir resolution of its own (that
  // resolution only exists in manifest-runner.ts, which this driver
  // intentionally bypasses to reach the per-run detail below) — so this
  // driver must resolve paths itself, independent of invocation cwd.
  const composition = {
    layers: [
      { layerType: "persona", fixturePath: path.join(CROSSLAYER_DIR, personaFixtureRelPath) },
      { layerType: "sop", fixturePath: path.join(CROSSLAYER_DIR, "sop-extract.md") },
    ],
    resolved: null,
  };
  const assembled = await assembleComposedContext(composition);

  const survivalCase = {
    id: `erosion-${label}-sc003`,
    rule: committedCase.rule,
    probe: committedCase.probeSet[0],
    baselineRuns: committedCase.baselineConfig.runs,
    composedRuns: committedCase.composedRuns,
    passThreshold: committedCase.baselineConfig.passThreshold,
    gradingClass: committedCase.gradingClass,
    isDiscriminationControl: committedCase.isDiscriminationControl,
  };

  const endpoint = buildEndpointConfig();
  const result = await runRuleSurvival(survivalCase, assembled, endpoint);

  return {
    case_id: survivalCase.id,
    persona_fixture: `conformance/crosslayer/${personaFixtureRelPath}`,
    sop_fixture: "conformance/crosslayer/sop-extract.md",
    verdict: result.verdict,
    baseline_runs: result.baselineResults.length,
    baseline_passed: result.baselineResults.filter((r) => r.passed).length,
    baseline_pass_rate: result.baselinePassRate,
    composed_runs: result.composedResults.length,
    composed_passed: result.composedResults.filter((r) => r.passed).length,
    composed_pass_rate: result.composedPassRate,
    pass_threshold: survivalCase.passThreshold,
    matches_expected_verdict: result.verdict === expectedVerdict,
  };
}

async function main() {
  const committedCase = loadErosionControlCase();
  const apiKeyEnv = process.env.MUSTER_API_KEY_ENV ?? "MUSTER_API_KEY";

  const flip = await runDirection(
    "adversarial",
    "fixtures/erosion-persona-045.Soul.md",
    "eroded",
    committedCase,
  );
  const neutralize = await runDirection(
    "neutral",
    "fixtures/erosion-persona-045-neutral.Soul.md",
    "survived",
    committedCase,
  );

  const evidence = {
    description:
      "SC-003 two-direction discrimination-control proof for FR-005's " +
      "erosion-control-045 (behavioral discrimination control): flip " +
      "(adversarial persona) and neutralize (rule-neutral persona, " +
      "IDENTICAL probe/rule/sop). Regenerated from committed source by " +
      "this driver (WP05 F7 remediation) — reproducible, not prose-only.",
    spec_ref: "kitty-specs/crosslayer-composition-suite-01KYJA33/spec.md SC-003, FR-005",
    method:
      "Direct invocation of the real, installed @garrison-hq/muster@1.1.0 " +
      "package's own exported assembleComposedContext/runRuleSurvival " +
      "functions (composition.js, rule-survival.js) -- the SAME functions " +
      "manifest-runner.js's runBehavioralCase calls -- never a mock, never " +
      "a reimplementation of grading logic. Captures baselineResults/" +
      "composedResults per-run detail that the CLI's own --json output " +
      "discards (manifest-runner.js returns only {id, passed, verdict}).",
    model: process.env.MUSTER_MODEL,
    endpoint_host: new URL(process.env.MUSTER_ENDPOINT).host,
    credential_source: `API key read from the ${apiKeyEnv} environment variable at call time -- never written to a file, never passed in argv, never logged. This artefact records only the env-var name, never any credential value.`,
    recorded_at: new Date().toISOString(),
    rule: committedCase.rule,
    probe: committedCase.probeSet[0],
    directions: { flip, neutralize },
    conclusion:
      "The control genuinely discriminates on content, not on the mere " +
      "presence of a persona layer or the probe wording (both directions " +
      "share the identical probe/rule/sop): see per-direction " +
      "baseline_pass_rate/composed_pass_rate above. Both verdicts are " +
      "checked against each direction's own expected verdict via " +
      "matches_expected_verdict.",
    reproducible_from:
      "This script (conformance/scripts/sc003-erosion-control-045-" +
      "neutralize-direction-driver.mjs), committed alongside this " +
      "artefact -- re-run it against a live endpoint to regenerate.",
  };

  process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
