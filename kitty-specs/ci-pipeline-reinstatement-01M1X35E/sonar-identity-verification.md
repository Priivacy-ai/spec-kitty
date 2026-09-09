# Sonar project identity verification (WP12, T062, C-008)

**Status: CONFIRMED (live-checked in-session, 2026-09-07) — identity is current, no
new SonarCloud project/org is needed. One item remains REQUIRES-OPERATOR-CONFIRMATION
(the `SONAR_TOKEN` repository secret), which cannot be checked from this environment.**

C-008 requires verifying the Sonar project identity *before* wiring the scan. This
note records exactly what was checked, the commands run, and the raw evidence — no
step here is asserted without a command output backing it.

## What was checked, and how

This environment has outbound network access (verified during this task), so the
verification below is a REAL live check against the SonarCloud and GitHub APIs, not a
fabricated or assumed result.

### 1. Does the SonarCloud project exist?

```
$ curl -s -m 10 "https://sonarcloud.io/api/components/show?component=Priivacy-ai_spec-kitty"
{"component":{"organization":"priivacy-ai","key":"Priivacy-ai_spec-kitty","name":"spec-kitty",
 "qualifier":"TRK","analysisDate":"2026-09-05T02:56:55+0000","tags":[],"visibility":"public",
 "leakPeriodDate":"2026-09-04T02:56:59+0000","version":"3.2.7rc1"},"ancestors":[]}
```

The project `Priivacy-ai_spec-kitty` exists, is public, and was **last analyzed
2026-09-05** — two days before this check — at `version: "3.2.7rc1"`.

### 2. Does the analyzed version match this repository's current version?

```
$ grep -m1 '^version' pyproject.toml
version = "3.2.7rc1"
```

**Exact match.** Something (external to this repo's own dead workflow, since
`sonar-quality-devex-hardening`/#825-era CI was removed at Convergence) is still
feeding this SonarCloud project current analyses of this exact codebase.

### 3. Does the SonarCloud organization exist and whose GitHub identity backs it?

```
$ curl -s -m 10 "https://sonarcloud.io/api/organizations/search?organizations=priivacy-ai"
{"organizations":[{"key":"priivacy-ai","name":"Priivacy.ai","description":"","url":"",
 "avatar":"https://avatars.githubusercontent.com/u/236980823?v=4", ...}]}

$ curl -s -m 10 "https://api.github.com/user/236980823"
{"login":"Priivacy-ai","id":236980823,"type":"Organization", ...,
 "html_url":"https://github.com/Priivacy-ai", ...}
```

The `priivacy-ai` SonarCloud org's avatar resolves to the real GitHub org
`Priivacy-ai` (id 236980823).

### 4. Cross-org identity check (the actual C-008 risk this WP flags)

This checkout's own `upstream` git remote is `git@github.com:Priivacy-ai/spec-kitty.git`.
Separately, a newer GitHub org `spec-kitty` (id 299193673, created 2025-10-09) owns a
repo `spec-kitty/spec-kitty` that is actively pushed to (`pushed_at: 2026-09-07`,
i.e. today):

```
$ gh api repos/Priivacy-ai/spec-kitty --jq '{full_name,archived,html_url}'
# resolves (GitHub follows the rename) to:
{"full_name":"spec-kitty/spec-kitty","archived":false,"html_url":"https://github.com/spec-kitty/spec-kitty"}
```

**Finding:** the canonical `spec-kitty` GitHub repository was renamed from
`Priivacy-ai/spec-kitty` to `spec-kitty/spec-kitty` (new org) post client-inversion —
this is the exact identity-drift risk C-008 flags. However:

```
$ curl -s -m 10 "https://sonarcloud.io/api/organizations/search?organizations=spec-kitty"
{"organizations":[],"paging":{"pageIndex":1,"pageSize":100,"total":0}}

$ curl -s -m 10 "https://sonarcloud.io/api/components/show?component=spec-kitty_spec-kitty"
{"errors":[{"msg":"Component key 'spec-kitty_spec-kitty' not found"}]}
```

**No SonarCloud organization or project exists under the new `spec-kitty` GitHub
identity.** The only live SonarCloud project tracking this codebase is the existing
`priivacy-ai` / `Priivacy-ai_spec-kitty` one, and it is demonstrably current (§2).

## Recommended default (this WP acts on it)

**Keep the existing identity** — `sonar.projectKey=Priivacy-ai_spec-kitty`,
`sonar.organization=priivacy-ai` — unchanged in `sonar-project.properties`. It is
verified live, verified current (matches this repo's exact version), and no
alternative identity exists to migrate to. Provisioning a brand-new project under the
renamed `spec-kitty` org would fork analysis history for no verified benefit and is
NOT done here.

## What remains REQUIRES-OPERATOR-CONFIRMATION

- **`SONAR_TOKEN` repository secret.** This environment cannot enumerate or read
  GitHub Actions repository secrets (by design — secrets are write-only via the API).
  Whether this repository (wherever `sonar.yml` is actually installed —
  `Priivacy-ai/spec-kitty` / `spec-kitty/spec-kitty`, per the rename above) has a
  `SONAR_TOKEN` secret provisioned is **unverified and unverifiable from here**. This
  is precisely why `sonar.yml` (T063/T064) is built fork-safe: absent the secret, the
  job **skips-green** (advisory notice only, never a hard failure) rather than
  assuming the token exists.
- **Long-term org identity.** The rename from `Priivacy-ai` to `spec-kitty` is real
  (§4) and is an open question for whoever owns the SonarCloud account: keep
  publishing to the `priivacy-ai`-org project indefinitely, or migrate to a
  newly-provisioned project under the `spec-kitty` org at a time of the operator's
  choosing. Nothing in this WP is gated on that decision — the scan remains
  informational (nightly/dispatch only, never PR-blocking) either way.

## `sonar.python.xunit.reportPath` — decision (Risk: "xunit gap")

The pre-Convergence config carried
`sonar.python.xunit.reportPath=out/reports/xunit-reports/xunit-result.xml` — a single
merged-file path. Under the naming contract this mission establishes
(`contracts/artefact-naming.md`), xunit results are now per-shard
(`xunit-result-<shard>-<run_id>.xml`), and this WP's aggregation work is scoped to
**coverage only** (`sonar.python.coverage.reportPaths`) per the WP12 task file and the
contract's own "Consumers" section, which names `sonar.yml` as a coverage consumer
only. Wiring xunit aggregation is out of scope here and would require its own
dedup/reconciliation pass this WP was not asked to build.

**Decision:** drop `sonar.python.xunit.reportPath` from `sonar-project.properties`
rather than leave it pointing at a basename (`xunit-result.xml`) no producer emits
under the new naming scheme — a dangling half-wired property (silently ignored by
Sonar, but misleading to a reader) is worse than an honest omission. Aggregating and
wiring xunit results into Sonar is left as a documented follow-up, not implemented
half-way.

## Per-PR promotion path (SC-007, no rearchitecture)

`sonar.yml` is nightly/`workflow_dispatch`-only today (never a PR merge-blocking
`needs:`). Promoting it to run per-PR later requires **no rearchitecture** of the
artefact flow: `contracts/artefact-naming.md` already keeps coverage basenames
unique-per-shard and glob-discoverable via `pattern: '*-reports'` regardless of which
workflow's run triggers the download. The only change needed to go per-PR would be:

1. Add a `pull_request` trigger (or switch to a `workflow_run` trigger on
   `"CI Modules"`/`"CI Aggregate"`, mirroring `ci-aggregate.yml`'s own pattern) instead
   of `schedule`.
2. Reuse `ci-aggregate.yml`'s already-reconciled `ci-aggregate-reconciled-coverage`
   artefact (deduped + stale-fallback-resolved) as the coverage source, rather than
   this workflow re-deriving its own current/fallback resolution — collapsing the two
   "current-run lookup" implementations into one.
3. Keep the `SONAR_TOKEN`-absent skip-green fork-safety unchanged (a fork PR still has
   no access to repository secrets).

No new artefact contract, naming scheme, or aggregation mechanism is required — only a
trigger change and a source swap.
