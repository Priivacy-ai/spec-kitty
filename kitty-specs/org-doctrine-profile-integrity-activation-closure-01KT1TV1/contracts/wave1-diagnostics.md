# Contract: Wave 1 — Diagnostics Integrity

## C1.1 Profile load diagnostics (FR-005, FR-006)

- **Given** a layer (built-in/org/project) containing one valid and one invalid profile YAML
  **When** `AgentProfileRepository` loads
  **Then** `list_all()` returns only the valid profile, and `skipped_profiles()` returns one `SkippedProfile{layer, path, profile_id|None, error_summary}` for the invalid file.
- **Given** an invalid file whose profile-id cannot be parsed
  **Then** its `SkippedProfile.profile_id is None` (the org "no profile-id" case is preserved).
- **Given** every current drop site (5 `warnings.warn` + silent `continue`/`pass`)
  **Then** each routes through one `_record_skip()` helper (no diagnostic is dropped).

## C1.2 Determinism & health of built-ins (NFR-002, NFR-005)

- **Given** the same set of files
  **When** the repository is loaded twice
  **Then** `skipped_profiles()` returns byte-identical, sorted records (sort key `(layer_rank, path)`); scans are sorted.
- **Given** the shipped built-in profiles
  **Then** loading yields zero `SkippedProfile` records.

## C1.3 Diagnostics survive on the service (FR-007)

- **Given** `DoctrineService.agent_profiles` accessed twice
  **Then** the cached repository instance exposes the same `skipped_profiles()` for all configured layers (no re-scan needed).

## C1.4 Doctor health report (FR-008, FR-009, FR-010, NFR-001)

- **Given** a pack with a valid DRG but one invalid profile
  **When** `spec-kitty doctor doctrine` runs (human)
  **Then** output shows the pack as **degraded**, listing the invalid profile by layer/path/error, while still listing valid profiles. `healthy` is derived from `valid_count == discovered_count`, **not** snapshot presence (I-H1).
- **When** `spec-kitty doctor doctrine --json` runs
  **Then** the JSON includes machine-readable invalid-profile records with stable fields `layer`, `path`, `profile_id` (nullable), `error_summary` — a passthrough of `SkippedProfile` (I-H2). Human and JSON derive from one `DoctrineHealthReport`.
- **Given** built-in doctrine + a representative one-pack fixture
  **Then** the command completes in ≤ 2s, building the report once (single `DoctrineService`/DRG load).

## C1.5 Dead-symbol wiring (FR-035, FR-036, FR-020)

- **Given** a `.kittify/config.yaml` with malformed charter-pack shape
  **When** `charter activate <kind> <id>` (or `charter context`) runs
  **Then** it fails closed presenting the `CHARTER_PACK_CONFIG_INVALID` code + remediation, mutates no activation state, and `CharterPackConfigError` now has a live external caller (no longer a dead symbol).
- **Given** the dead-symbol gate
  **Then** the 7 stale allowlist entries (`next._internal_runtime.events::*`, `lanes.auto_rebase::AutoRebaseReport`) are removed, the 2 charter sub-app exports are normalized to one registration pattern, and the gate passes for these in-scope symbols. The 2 git/lanes offenders are out of scope (allowlist-with-tracker fallback only).
- **Given** `_app.py:47`
  **Then** the FR-008 comment misattribution is corrected (general `activate` is FR-004; FR-008 is the in-flight-warning branch).
