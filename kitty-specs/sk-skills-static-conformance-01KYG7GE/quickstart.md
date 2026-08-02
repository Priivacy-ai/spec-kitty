# Quickstart: Skills Static Conformance Suite — Local Verification

**Mission**: `sk-skills-static-conformance-01KYG7GE` | **Date**: 2026-07-27

All commands run from the spec-kitty fork's repository root. Requires
Node ≥22 (muster's `engines.node` floor) and network access **only** for the
one-time cache-warm step.

This file doubles as the mission's mandatory real-CLI verification
procedure (binding constraint 7 / plan.md's Verification Strategy) — every
step here must be run for real against the actual 53-skill tree during
implementation, not asserted from a unit test or agent judgment alone.

---

## 1. Cache-warm, then run fully offline (FR-002, AC-1)

```sh
# One-time, network enabled: warms npm's local cache for the pinned version.
npm install --no-save @garrison-hq/muster@1.1.0

# From here on, disable network (illustrative — CI enforces this via a
# network-disabled runner step; locally, unplugging/airplane-mode or an
# npm/npx offline flag both demonstrate the same property):
npx --offline @garrison-hq/muster@1.1.0 skills run conformance/skills/manifest.yaml
echo "exit code: $?"   # MUST print 0
```

Alternative cache-warm path documented for CI (`npm ci` restoring a pinned
`devDependency` instead of `npm install --no-save`) — either satisfies
FR-002's two-step procedure; `conformance/README.md` documents both.

**This step must be run for real** against the actual, unmodified
`conformance/skills/manifest.yaml` (54 cases: 53 skills + 1 control) during
WP01/WP02 implementation, and the real exit code recorded in the mission's
work log — not inferred from the manifest's contents by inspection.

---

## 2. Prove discrimination both ways (FR-005, AC-2, SC-003)

```sh
# Baseline: the control case is declared ok:false and the fixture is
# genuinely broken (name/directory mismatch) — the suite as shipped exits 0.
npx --offline @garrison-hq/muster@1.1.0 skills run conformance/skills/manifest.yaml
echo "baseline exit code: $?"   # MUST print 0

# Manual proof step (documented in README as a manual check, NOT part of CI):
# temporarily flip the control case's declared expectation.
trap 'mv -f conformance/skills/manifest.yaml.bak conformance/skills/manifest.yaml 2>/dev/null' EXIT
sed -i.bak 's/ok: false/ok: true/' conformance/skills/manifest.yaml   # control case only — verify by hand which line changed
[ "$(diff conformance/skills/manifest.yaml.bak conformance/skills/manifest.yaml | grep -c '^<')" = "1" ] || { echo "sed touched an unexpected number of lines" >&2; exit 1; }

npx --offline @garrison-hq/muster@1.1.0 skills run conformance/skills/manifest.yaml
echo "flipped exit code: $?"   # MUST print non-zero (1)

# Restore:
mv conformance/skills/manifest.yaml.bak conformance/skills/manifest.yaml
git diff --exit-code conformance/skills/manifest.yaml
```

**This step must be run for real** during implementation (both directions:
un-flipped exit 0, flipped exit non-zero), with both real exit codes
recorded in the work log — this is the operator's explicit "prove the FR-005
control case behaves as specified" requirement, not a design assertion.

---

## 3. Manifest completeness check, both ways (FR-007, SC-006)

Do not run this step concurrently with any other `spec-kitty` command in
this checkout.

```sh
# Baseline: the true tree — 53 skill directories, 54 manifest cases.
node conformance/scripts/check-manifest-completeness.mjs
echo "baseline exit code: $?"   # MUST print 0

# Induce a mismatch (either direction demonstrates the same property):
mkdir -p src/doctrine/skills/__temp-completeness-probe
echo '---
name: __temp-completeness-probe
description: temporary fixture for FR-007 verification only, deleted immediately after use.
---
' > src/doctrine/skills/__temp-completeness-probe/SKILL.md

node conformance/scripts/check-manifest-completeness.mjs
echo "mismatch exit code: $?"   # MUST print non-zero (1) and name
                                  # "__temp-completeness-probe" as missing from the manifest

# Clean up immediately — this directory must never be committed:
rm -rf src/doctrine/skills/__temp-completeness-probe
node conformance/scripts/check-manifest-completeness.mjs
echo "restored exit code: $?"   # MUST print 0 again
```

**This step must be run for real** during implementation, with the failure
message's exact wording (naming `__temp-completeness-probe`, or whichever
probe skill was used) captured in the work log as proof the check names
specific skills rather than reporting a bare count mismatch (FR-007's
explicit requirement).

---

## 4. CI workflow — real run, timing capture (FR-003, NFR-001)

This step cannot be simulated locally; it requires a real GitHub Actions
run on the mission's own PR:

1. Open the mission's PR against `MOES-Media/spec-kitty` on the mission
   branch `kitty/mission-sk-skills-static-conformance`.
2. Confirm `.github/workflows/conformance.yml` triggers and both steps
   (muster `skills run`, then the FR-007 completeness check) show green.
3. Record that run's `run_id` and actual wall-clock minutes in
   `conformance/README.md`'s timing table — mirroring the exact pattern in
   `docs/plans/testing/ci-job-timings.md` (a specific `run_id`, a specific
   minutes figure, explicitly not an asserted ceiling).
4. If the PR is opened from a fork (no repository secrets available),
   confirm the job still completes green with no secret-related failure
   (C-002, AC-3) — the static path requires none.

---

## 5. Full local pre-PR check (what a contributor runs before opening a PR)

```sh
npx --offline @garrison-hq/muster@1.1.0 skills run conformance/skills/manifest.yaml \
  && node conformance/scripts/check-manifest-completeness.mjs \
  && echo "conformance: both checks green"
```

This is the exact sequence `conformance/README.md` documents as the local
pre-PR command (FR-006).
