# Contract: SonarCloud QA config slice

The observable contracts this mission must uphold (verified by the tests + reviews cited in `acceptance-matrix.json`).

## C1 — projectVersion is single-sourced (#2421, FR-001/FR-002)
- **Producer**: `scripts/ci/sonar_project_version.py` — reads `[project].version` from `pyproject.toml` via `tomllib`.
- **Invariant**: returns exactly `pyproject.toml`'s version; **raises `ProjectVersionError` (never returns/prints empty)** on missing/unreadable/blank version.
- **Consumer**: the `sonarcloud` job in `.github/workflows/ci-quality.yml` injects `-Dsonar.projectVersion=<version>` (or appends `sonar.projectVersion=<version>` in the Materialize step), guarded by `[ -z "$version" ] && exit 1`.
- **Boundary note**: the `sonarcloud` job runs only on `schedule`/`workflow_dispatch` (never PR/push) — so the wiring is verified **statically** (SC-001a), and the live baseline reset (SC-001b) is a post-merge observation on the next nightly cron / manual dispatch.

## C2 — the review tool is strictly read-only (FR-005/FR-006, NFR-001)
- `scripts/ci/sonarcloud_branch_review.sh` issues **only HTTP `GET`s** through a single `_http_get` seam (`--get`, no `-X`/`--request`, no `POST`/`PUT`/`DELETE`/`PATCH`). No subcommand bypasses the seam.
- Subcommands: `quality-gate`, `coverage`, `uncovered <file>`, `issues`, `version`/`analyses` (the last backs SC-001b).
- Needs **no `SONAR_TOKEN`** — public read endpoints; the smoke test passes with the token unset, network stubbed to fixtures.

## C3 — coverage reconciliation clarifies, never masks (#2422, FR-003/FR-004, C-002, NFR-002)
- `docs/guides/coverage-signals.md` documents why SonarCloud `coverage`/`new_coverage` and the internal `diff-coverage` gate differ (file-set + philosophy), backed by API evidence.
- **No `sonar.sources`/`sonar.exclusions` change** unless a genuine misconfiguration is found (none was) — narrowing Sonar scope would mask untested code (no-ratchet standing order).
