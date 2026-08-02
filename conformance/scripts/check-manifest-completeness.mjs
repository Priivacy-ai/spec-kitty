#!/usr/bin/env node
// Verifies that conformance/skills/manifest.yaml's type:static case count
// and name set exactly match the real src/doctrine/skills/* directory tree,
// offset by the one deliberately-broken FR-005 control case (see
// conformance/skills/manifest.yaml's control-name-mismatch entry) -- AND
// that the control case actually discriminates a real name-mismatch failure,
// verified by observing muster's own --json output rather than by any
// property test on the fixture's text (see "Discrimination redesign" below).
//
// FR-007. Node stdlib only (fs, path, child_process) for everything except
// the discrimination check, which shells out to the pinned muster CLI --
// see "Discrimination redesign" for why that coupling was added and is
// unavoidable.
// Contract: kitty-specs/sk-skills-static-conformance-01KYG7GE/contracts/
//           completeness-check-cli-contract.md
//
// Invocation: node conformance/scripts/check-manifest-completeness.mjs
// Working directory: repository root. No arguments, no env vars.
// Network: none directly, but the discrimination check below execs
// `npx --offline @garrison-hq/muster@<pinned>`, which requires the pinned
// package to already be warm in the local npm cache -- see
// conformance/README.md's "two-step cache-warm-then-offline procedure" and
// "Local prerequisite" note.
//
// ─── History (context for the redesign below; none of these property
// checks exist in this file anymore) ───────────────────────────────────────
//
// Post-merge mission review (M1) originally added: (a) an assertion that
// every case's skillDir resolves to an existing directory containing a
// SKILL.md (HIGH-1 first half), (b) an assertion that skill-tree case ids
// equal their resolved directory's basename (HIGH-2 -- kept below, see
// checkSkillCaseIdsMatchBasename), and (c) a *property* check on the
// control case: read its frontmatter `name:` via a hand-rolled regex and
// assert it differs from its directory basename (HIGH-1 second half).
//
// PR #29 review round 2 found three gaps in (c) and patched them in place:
// a null/hollowed name scored as "still discriminating" (F-1), a quoted
// name's quotes were compared literally so a quoted-and-aligned name slipped
// through (F-5), and a skillDir-pointing-at-a-file was misreported (F-6,
// unrelated to (c) but fixed alongside it).
//
// A third-pass audit then found FOUR MORE ways to defeat the *property*
// check in (c), all leaving muster's own exit code AND this script both
// green: deleting the `description:` line (the schema-validation early
// return in muster's own validateStatic() means validateName() -- the
// function that would emit the name-mismatch violation -- never runs, so
// the fixture still legitimately scores ok:false for a *different* reason,
// which the property check cannot tell apart from a genuine name mismatch);
// a duplicate `name:` key, an unterminated quote, and a tab-indented value
// (all three throw inside the YAML parser during frontmatter extraction,
// caught by `catch { parsed = {} }`, landing on the same schema-early-return
// path as the description-deletion bypass); and a folded scalar (`name:
// >-`) which a real YAML parser reads correctly but this script's own
// regex-based `readFrontmatterName()` read as the literal string `">-"`.
//
// Three rounds of patching, seven distinct bypasses, all sharing one root
// cause: this script's property check (`frontmatterName !== basename`) and
// muster's own scoring (`ok === expectations.ok`) are each satisfied by a
// strictly larger set of conditions than "muster actually detected and
// reported the name mismatch" -- neither one asks that question directly.
// A text-regex "frontmatter reader" that is not a YAML parser cannot be
// patched into being one; enumerating its gaps one bypass at a time is not
// a terminating process.
//
// ─── Discrimination redesign (current design) ──────────────────────────────
//
// The control-discrimination check no longer tests any property of the
// fixture's text. It runs the pinned muster CLI once, in --json mode
// (readMusterResultsById(), below), and asserts on what muster ITSELF
// reported for the control case: that `violations[]` contains an entry with
// `path === "name"` whose `message` matches
// `/must equal the parent directory name/` (the exact string muster's
// validateName() emits -- confirmed against @garrison-hq/muster@1.1.0's
// pinned source, src/adapters/skills/validate.ts, and against a live
// `--json` run against this repo's own manifest; see conformance/README.md).
//
// This directly measures the behaviour the control exists to exercise. Every
// one of the seven known bypasses above either prevents that specific
// violation from ever being produced (hollowing/quoting/schema-early-return
// bypasses -- muster instead reports a generic parse-error or a schema
// violation, never the name-mismatch message) or removes it by aligning the
// name (muster then reports no `name`-path violation at all). None of them
// can produce the exact `{path: "name", message: /must equal the parent
// directory name/}` shape while also failing to be a genuine, present,
// misaligned name -- there is no proxy left to fool, because the assertion
// is a direct read of muster's own conclusion, not a re-derivation of it.
//
// The corresponding check on the 53 real skill cases asserts that muster
// reports zero *error*-severity violations for each -- not a literally empty
// `violations[]` array. A live run against this manifest shows
// `spec-kitty-runtime-next` legitimately carries two warning-severity
// violations (a nested-SKILL.md layout note) while still being a
// conforming, `ok: true` skill; asserting a literally empty array would
// make this check fail against the current, correct, un-tampered manifest.
// Filtering on `severity === "error"` matches muster's own pass/fail
// arithmetic exactly (`hasError = violations.some(v => v.severity ===
// "error")` in validateStatic()'s caller), so this check can never disagree
// with muster about what "clean" means.
//
// `expectations.violations` in the manifest cannot carry either assertion:
// muster 1.1.0's own pass/fail rule is exactly `passed = ok ===
// c.expectations.ok` (src/cli/index.ts:956 at the pinned tag) -- the
// `violations:` list in the manifest is documentation only, never compared.
// This script's own read of the LIVE `--json` output is therefore the only
// place either assertion can live.
//
// What FR-007 still checks by property, unchanged: every case's skillDir
// resolves to an existing directory containing a SKILL.md
// (checkSkillDirsResolve), skill-tree case ids equal their resolved
// directory's basename (checkSkillCaseIdsMatchBasename), the manifest's
// static-case count reconciles against the real skill tree plus exactly one
// control case, and there is exactly one control case
// (checkControlCaseCount). These serve manifest completeness -- a
// genuinely separate purpose from control discrimination -- and are cheap,
// local, and have no gaps of their own: keeping them here (rather than
// folding them into the muster-based check) also means a missing/corrupt
// control fixture directory (bypass class: delete the whole directory) is
// still reported with a clear, specific message before this script ever
// shells out to muster at all.
//
// Muster itself is out of scope for this fix (C-001, no muster change):
// this script cannot and does not change how `muster skills run` computes
// its own `ok`/`passed` fields -- it only adds an independent,
// fork-side assertion on muster's own reported violations.

import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { basename, dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");
const SKILLS_DIR = join(REPO_ROOT, "src", "doctrine", "skills");
const MANIFEST_PATH = join(REPO_ROOT, "conformance", "skills", "manifest.yaml");

// Must match conformance/README.md's pinned version exactly (C-003,
// NFR-002) -- never a range. Keep these two in sync by hand; there is no
// single source of truth to derive both from without adding a package.json
// dependency this suite deliberately does not carry.
const MUSTER_VERSION = "1.1.0";

// The manifest carries exactly one non-skill-tree case: the FR-005
// discrimination control (control-name-mismatch, skillDir: control/...).
// It is deliberately excluded from the src/doctrine/skills/* comparison
// below and accounted for here as a named constant, never an inline magic
// number, per WP01's hard rule 5 / data-model.md's CompletenessCheckResult
// invariant.
const CONTROL_CASE_COUNT = 1;

// The exact violation shape muster's validateName() emits for a name/
// directory mismatch (src/adapters/skills/validate.ts, pinned v1.1.0):
// `path: "name"`, `message: name "<name>" must equal the parent directory
// name "<basename>"`. Matched by substring rather than reproducing the full
// interpolated string, so this does not need updating if the surrounding
// fixture names ever change.
const NAME_MISMATCH_PATH = "name";
const NAME_MISMATCH_MESSAGE_PATTERN = /must equal the parent directory name/;

// Step 1: read the real skill set. Filter by directory-entry TYPE, never by
// excluding a literal filename -- src/doctrine/skills/ also contains a
// plain README.md file, and excluding it by name (instead of by type) would
// silently regress if a second stray non-skill file ever landed there. A
// directory only counts as a skill if it also contains a SKILL.md
// (MEDIUM-5) -- an empty probe directory is not a skill.
function readActualSkillNames() {
  const entries = readdirSync(SKILLS_DIR, { withFileTypes: true });
  return entries
    .filter((e) => e.isDirectory())
    .filter((e) => existsSync(join(SKILLS_DIR, e.name, "SKILL.md")))
    .map((e) => e.name);
}

// Step 2: parse the manifest as plain text (no YAML parser -- see the
// schema's "$comment"). Cases are block-style YAML, one key per line, with
// `- id:` immediately followed by `type:`, `skillDir:`, `profile:`, and
// `expectations:` inside the same list item at a fixed indent. We only need
// the (id, skillDir) pairs, which appear as an `- id:` line followed a few
// lines later by a `skillDir:` line, before the next `- id:` line starts a
// new case.
function readManifestCases() {
  const text = readFileSync(MANIFEST_PATH, "utf8");
  const lines = text.split("\n");
  const cases = [];
  let current = null;
  for (const line of lines) {
    const idMatch = line.match(/^\s*- id:\s*(\S+)\s*$/);
    if (idMatch) {
      if (current) cases.push(current);
      current = { id: idMatch[1], skillDir: null };
      continue;
    }
    const skillDirMatch = line.match(/^\s*skillDir:\s*(\S+)\s*$/);
    if (skillDirMatch && current && current.skillDir === null) {
      current.skillDir = skillDirMatch[1];
    }
  }
  if (current) cases.push(current);
  return cases;
}

// Resolves every manifest case's skillDir to an absolute path and classifies
// it as either a skill-tree case (resolves one level directly under
// SKILLS_DIR) or a control case (everything else) -- purely structural,
// never inferred from the case's `id` string.
function resolveAndClassify(manifestCases) {
  const skillCases = [];
  const controlCases = [];
  for (const c of manifestCases) {
    if (!c.skillDir) {
      controlCases.push({ ...c, resolved: null });
      continue;
    }
    const resolved = join(dirname(MANIFEST_PATH), c.skillDir);
    const rel = relative(SKILLS_DIR, resolved);
    const isSkillTree = rel !== "" && !rel.startsWith("..") && !rel.includes("/");
    const entry = { ...c, resolved };
    if (isSkillTree) skillCases.push(entry);
    else controlCases.push(entry);
  }
  return { skillCases, controlCases };
}

// Every case's skillDir must resolve to an existing directory containing a
// SKILL.md. Runs for every case, skill-tree or control -- a missing/corrupt
// control fixture (e.g. the whole directory deleted) is reported here,
// clearly and locally, before this script ever shells out to muster.
function checkSkillDirsResolve(allCases) {
  const errors = [];
  const structurallyOk = new Set();
  for (const c of allCases) {
    if (!c.skillDir || !c.resolved) {
      errors.push(`case '${c.id}': manifest entry has no skillDir`);
      continue;
    }
    if (!existsSync(c.resolved)) {
      errors.push(
        `case '${c.id}': skillDir '${c.skillDir}' does not resolve to an existing directory`,
      );
      continue;
    }
    if (!statSync(c.resolved).isDirectory()) {
      errors.push(
        `case '${c.id}': skillDir '${c.skillDir}' resolves to a file, not a directory`,
      );
      continue;
    }
    const skillMdPath = join(c.resolved, "SKILL.md");
    if (!existsSync(skillMdPath)) {
      errors.push(`case '${c.id}': skillDir '${c.skillDir}' has no SKILL.md`);
      continue;
    }
    structurallyOk.add(c.id);
  }
  return { errors, structurallyOk };
}

// Every skill-tree case's id must equal the basename of the directory its
// skillDir resolves to. Without this, membership is classified by skillDir
// while the name set is built from id, and the two can silently diverge
// (e.g. one case's skillDir repointed at another skill's directory).
function checkSkillCaseIdsMatchBasename(skillCases) {
  const errors = [];
  for (const c of skillCases) {
    const actualBasename = basename(c.resolved);
    if (c.id !== actualBasename) {
      errors.push(
        `case '${c.id}': skillDir '${c.skillDir}' resolves to directory ` +
          `'${actualBasename}', which does not match the case id '${c.id}'`,
      );
    }
  }
  return errors;
}

// Structural count check only: exactly one case must be classified as a
// control case (skillDir outside src/doctrine/skills/). This is unrelated
// to whether that control *discriminates* anything -- that question is
// answered by checkControlDiscriminatesInMuster(), below, from muster's own
// --json output.
function checkControlCaseCount(controlCases) {
  const errors = [];
  if (controlCases.length !== CONTROL_CASE_COUNT) {
    errors.push(
      `expected exactly ${CONTROL_CASE_COUNT} control case(s) (skillDir outside src/doctrine/skills/), found ${controlCases.length}: ` +
        `${controlCases.map((c) => c.id).join(", ") || "(none)"}`,
    );
  }
  return errors;
}

// Invokes the pinned muster CLI once, in --json mode, against this suite's
// own manifest, and returns a Map from case id to its structured
// SkillsCaseResult ({ id, type, passed, violations }) -- confirmed shape
// against @garrison-hq/muster@1.1.0's pinned source (src/cli/index.ts,
// doSkillsRun()) and against a live run.
//
// A non-zero muster exit code (e.g. a genuine conformance regression, such
// as the control's name being aligned so muster's own ok flips to true) is
// NOT treated as "muster is unavailable": doSkillsRun() always writes its
// JSON report to stdout before returning the outcome-derived exit code, so
// stdout is still present and parseable. Only an actually-missing/failed
// invocation (no parseable stdout at all) falls through to the actionable
// "muster is not available" message below, rather than a raw stack trace.
function readMusterResultsById() {
  const args = [
    "--offline",
    `@garrison-hq/muster@${MUSTER_VERSION}`,
    "skills",
    "run",
    MANIFEST_PATH,
    "--json",
  ];
  let stdout;
  try {
    stdout = execFileSync("npx", args, {
      cwd: REPO_ROOT,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    if (typeof error.stdout === "string" && error.stdout.trim().length > 0) {
      // Non-zero exit, but muster still emitted its JSON report -- use it.
      stdout = error.stdout;
    } else {
      failWithMusterUnavailable(error);
    }
  }

  let parsed;
  try {
    parsed = JSON.parse(stdout);
  } catch (parseError) {
    console.log("manifest completeness: ERROR");
    console.log(
      `  muster --json output was not valid JSON (${parseError.message}) -- cannot run the discrimination check`,
    );
    process.exit(1);
  }
  if (!parsed || !Array.isArray(parsed.results)) {
    console.log("manifest completeness: ERROR");
    console.log(
      "  muster --json output did not have the expected { results: [...] } shape -- cannot run the discrimination check",
    );
    process.exit(1);
  }
  return new Map(parsed.results.map((r) => [r.id, r]));
}

// Prints an actionable message -- not a raw stack trace -- when the pinned
// muster CLI cannot be run at all, and exits 1. This is the operational
// consequence of the discrimination redesign: this script now requires
// muster to be installed (specifically, warm in npm's local cache for
// `npx --offline` to find). CI already installs it (the preceding "Run
// muster skills conformance" workflow step warms the same cache this step
// then reads from); local developers must run the cache-warm step manually
// once -- see conformance/README.md's "Local prerequisite" note.
function failWithMusterUnavailable(error) {
  console.log("manifest completeness: ERROR");
  console.log(
    "  could not run the pinned muster CLI needed for the discrimination-control check:",
  );
  console.log(
    `    npx --offline @garrison-hq/muster@${MUSTER_VERSION} skills run <manifest> --json`,
  );
  console.log(`  underlying error: ${error.message}`);
  console.log(
    "  this script now depends on muster being installed locally. Warm the npm cache once with:",
  );
  console.log(`    npm install --no-save @garrison-hq/muster@${MUSTER_VERSION}`);
  console.log(
    "  then re-run this script (see conformance/README.md's 'Local prerequisite' note).",
  );
  process.exit(1);
}

// The discrimination-control assertion (see "Discrimination redesign" in
// the header comment): for the control case(s), muster's OWN --json output
// must contain a { path: "name", message: /must equal the parent directory
// name/ } violation. This is a direct read of muster's conclusion, not a
// re-derivation of a property from the fixture's text -- every known bypass
// either prevents this specific violation from being produced at all
// (hollowing, quoting-defeated-by-a-real-parser, schema-early-return via a
// deleted description or a parser-throwing frontmatter) or removes it by
// genuinely aligning the name, in which case it is correct and desired that
// this check fires.
function checkControlDiscriminatesInMuster(controlCases, structurallyOk, resultsById) {
  const errors = [];
  for (const c of controlCases) {
    if (!structurallyOk.has(c.id)) continue; // already reported by checkSkillDirsResolve
    const result = resultsById.get(c.id);
    if (!result) {
      errors.push(
        `control case '${c.id}': not present in muster --json output -- cannot verify it discriminates a name mismatch`,
      );
      continue;
    }
    const violations = Array.isArray(result.violations) ? result.violations : [];
    const hasNameMismatch = violations.some(
      (v) => v.path === NAME_MISMATCH_PATH && NAME_MISMATCH_MESSAGE_PATTERN.test(String(v.message)),
    );
    if (!hasNameMismatch) {
      errors.push(
        `control case '${c.id}': muster's own --json output has no ` +
          `{ path: "name", message: /must equal the parent directory name/ } violation -- ` +
          `this control no longer proves muster actually detected a name mismatch ` +
          `(observed violations: ${JSON.stringify(violations)})`,
      );
    }
  }
  return errors;
}

// The complementary assertion: every real skill case must have zero
// error-severity violations in muster's own --json output. Deliberately NOT
// "an empty violations[] array" -- a live run shows spec-kitty-runtime-next
// legitimately carries warning-severity violations (a nested-SKILL.md
// layout note) while still being a conforming skill; filtering on
// `severity === "error"` matches muster's own pass/fail arithmetic exactly
// (see header comment) instead of introducing a stricter, disagreeing
// definition of "clean".
function checkSkillCasesCleanInMuster(skillCases, structurallyOk, resultsById) {
  const errors = [];
  for (const c of skillCases) {
    if (!structurallyOk.has(c.id)) continue; // already reported by checkSkillDirsResolve
    const result = resultsById.get(c.id);
    if (!result) {
      errors.push(`skill case '${c.id}': not present in muster --json output`);
      continue;
    }
    const violations = Array.isArray(result.violations) ? result.violations : [];
    const errorViolations = violations.filter((v) => v.severity === "error");
    if (errorViolations.length > 0) {
      errors.push(
        `skill case '${c.id}': muster reported ${errorViolations.length} error-severity ` +
          `violation(s) for a real skill (expected none): ${JSON.stringify(errorViolations)}`,
      );
    }
  }
  return errors;
}

function main() {
  const actualSkillNames = readActualSkillNames();
  const actualSkillSet = new Set(actualSkillNames);

  const manifestCases = readManifestCases();
  // Every case this mission emits is `type: static` (behavioral cases are
  // out of scope), so the total case count IS the manifest's static-case
  // count -- this includes the one FR-005 ControlCase, per
  // data-model.md's CompletenessCheckResult (manifestStaticCaseCount ==
  // actualSkillCount + CONTROL_CASE_COUNT).
  const manifestStaticCaseCount = manifestCases.length;

  const { skillCases, controlCases } = resolveAndClassify(manifestCases);
  const allCases = [...skillCases, ...controlCases];

  // Pass 1: cheap, local, property-based structural checks (FR-007
  // completeness). Fail fast here without ever shelling out to muster --
  // a missing/corrupt control fixture directory, a file where a directory
  // is expected, or a miscounted control-case set are all reported clearly
  // by these alone.
  const structuralErrors = [];
  const { errors: resolveErrors, structurallyOk } = checkSkillDirsResolve(allCases);
  structuralErrors.push(...resolveErrors);
  structuralErrors.push(
    ...checkSkillCaseIdsMatchBasename(skillCases.filter((c) => structurallyOk.has(c.id))),
  );
  structuralErrors.push(...checkControlCaseCount(controlCases));

  if (structuralErrors.length > 0) {
    console.log("manifest completeness: MISMATCH");
    for (const e of structuralErrors) console.log(`  ${e}`);
    process.exit(1);
  }

  // Pass 2: the observation-based discrimination check. Invokes muster
  // exactly once, in --json mode, and asserts on what muster ITSELF
  // reported -- see "Discrimination redesign" in the header comment.
  const musterResultsById = readMusterResultsById();
  const discriminationErrors = [
    ...checkControlDiscriminatesInMuster(controlCases, structurallyOk, musterResultsById),
    ...checkSkillCasesCleanInMuster(skillCases, structurallyOk, musterResultsById),
  ];

  if (discriminationErrors.length > 0) {
    console.log("manifest completeness: MISMATCH");
    for (const e of discriminationErrors) console.log(`  ${e}`);
    process.exit(1);
  }

  // Pass 3: manifest/tree name-set completeness (unchanged from the
  // original FR-007 implementation).
  const manifestSkillNames = skillCases.map((c) => basename(c.resolved));
  const manifestSkillSet = new Set(manifestSkillNames);

  const missing = actualSkillNames
    .filter((name) => !manifestSkillSet.has(name))
    .sort();
  const extra = manifestSkillNames
    .filter((name) => !actualSkillSet.has(name))
    .sort();

  const countMatches =
    manifestStaticCaseCount === actualSkillNames.length + CONTROL_CASE_COUNT;
  const ok = countMatches && missing.length === 0 && extra.length === 0;

  if (ok) {
    console.log(
      `manifest completeness: OK (${actualSkillNames.length} skills + ${CONTROL_CASE_COUNT} control = ${actualSkillNames.length + CONTROL_CASE_COUNT} cases; discrimination-control verified via muster --json)`,
    );
    process.exit(0);
  }

  console.log("manifest completeness: MISMATCH");
  console.log(
    `  missing from manifest (present under src/doctrine/skills/, no case found): ${missing.length ? missing.join(", ") : "(none)"}`,
  );
  console.log(
    `  extra in manifest (case present, no matching src/doctrine/skills/<name> directory): ${extra.length ? extra.join(", ") : "(none)"}`,
  );
  if (missing.length === 0 && extra.length === 0 && !countMatches) {
    console.log(
      `  count mismatch with no name-level difference detected: expected ${actualSkillNames.length + CONTROL_CASE_COUNT} static+control cases (${actualSkillNames.length} skills + ${CONTROL_CASE_COUNT} control), found ${manifestStaticCaseCount} static cases in manifest`,
    );
  }
  process.exit(1);
}

main();
