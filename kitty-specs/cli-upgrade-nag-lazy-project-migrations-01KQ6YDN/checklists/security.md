# Security Requirements Quality Checklist

**Purpose**: Validate that `spec.md` writes its **security-relevant requirements** with enough completeness, clarity, and measurability that a planner and reviewer can hold the implementation accountable. This checklist tests *requirements quality*, not implementation behavior.
**Created**: 2026-04-27
**Mission**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN`
**Spec**: [`../spec.md`](../spec.md)
**Audience**: Reviewer / security-conscious planner.
**Depth**: Standard.
**Threat surface in scope**: a local CLI tool that (a) reads project metadata from the current directory, (b) writes a per-user cache file, (c) optionally fetches a "latest version" string from a remote source, (d) prints user-actionable upgrade hints, and (e) applies on-disk migrations to the current project. Attacker model: untrusted project on disk, untrusted network response, locally-controlled environment variables, multi-tenant CI runners.

---

## Threat Model & Trust Boundaries

- [ ] CHK001 — Is the threat model for the upgrade-nag and lazy-migration paths documented (attackers, assets, trust boundaries)? [Gap, Traceability]
- [ ] CHK002 — Are the trust boundaries between *installed CLI*, *current-project metadata on disk*, *per-user cache*, and *remote latest-version source* explicitly named in the spec? [Completeness, Spec §"Key Entities"]
- [ ] CHK003 — Is it specified that `.kittify/metadata.yaml` from the current directory is treated as untrusted input (in case the user `cd`s into a hostile project)? [Gap, Spec §"Edge cases"]
- [ ] CHK004 — Is it specified that the latest-version source response is treated as untrusted input (no implicit trust of payload contents beyond a documented schema)? [Gap, Spec §A-002, §NFR-002]
- [ ] CHK005 — Is the assumption that the user's `$XDG_CACHE_HOME` (or fallback) is a trusted, user-only writable location validated, including the case of multi-user systems? [Assumption, Spec §A-001]

## Data Protection at Rest

- [ ] CHK006 — Are file-permission requirements specified for the per-user nag cache (e.g., 0600, owner-only)? [Gap, Spec §A-001]
- [ ] CHK007 — Are requirements specified for what data the nag cache may NOT contain (no usernames, no project paths, no telemetry IDs)? [Gap, Spec §A-001, §NFR-008]
- [ ] CHK008 — Are requirements specified for behavior when the cache file already exists with permissions wider than required (refuse to read? rewrite with tighter mode? warn?)? [Gap, Edge Case]
- [ ] CHK009 — Is symlink-attack resistance for cache reads/writes addressed in the requirements (refuse to follow symlinks pointing outside the cache dir)? [Gap, Edge Case]
- [ ] CHK010 — Are requirements specified for what happens when the cache directory itself is a symlink to an attacker-controlled location? [Gap, Edge Case]

## Network Path Security (Latest-Version Source)

- [ ] CHK011 — Are TLS / certificate-verification requirements specified for the latest-version network call? [Gap, Spec §A-002, §NFR-002]
- [ ] CHK012 — Is a maximum response size for the latest-version fetch specified, to bound resource exhaustion from a hostile or compromised endpoint? [Gap, Spec §NFR-002]
- [ ] CHK013 — Is the allowlist of hostnames the nag path is permitted to contact specified (and pinned to a small documented set, with no DNS-rebind surprises)? [Gap, Spec §NFR-008] [Ambiguity]
- [ ] CHK014 — Are requirements specified for what HTTP redirects are followed (and to what schemes / hosts), or that redirects are not followed at all? [Gap, Edge Case]
- [ ] CHK015 — Are requirements specified for handling responses that parse but contain a *lower* version than installed (no "downgrade" hint, no panic)? [Gap, Spec §"Edge cases"]
- [ ] CHK016 — Are requirements specified for handling responses with non-semver, malformed, or unexpectedly-large version strings (no command injection into upgrade hints)? [Gap]
- [ ] CHK017 — Are requirements specified for proxy / `HTTP(S)_PROXY` handling, including whether the spec opts in or refuses to use a proxy, given that a hostile proxy can rewrite version data? [Gap, Edge Case]
- [ ] CHK018 — Is it specified that the network call MUST NOT include any user-identifying headers (username, machine ID, project path, query strings)? [Gap, Spec §NFR-008]

## Input Validation — Project Metadata

- [ ] CHK019 — Are YAML-loading requirements specified to use a safe-load path (no arbitrary tag construction, no Python-object instantiation from `.kittify/metadata.yaml`)? [Gap, Spec §"Key Entities → Current-project metadata"]
- [ ] CHK020 — Are bounds specified for sizes/depth of `.kittify/metadata.yaml` parsing (to prevent YAML bombs / aliasing attacks)? [Gap, Edge Case]
- [ ] CHK021 — Are validation requirements specified for the `spec_kitty.schema_version` field (must be integer in a documented range; reject negative, NaN, strings, lists)? [Completeness, Spec §"Key Entities → Current-project metadata"] [Gap]
- [ ] CHK022 — Is "current project detection" defined precisely enough (e.g., walks upward looking for `.kittify/`) that an attacker cannot trick the CLI into treating an attacker-controlled directory as the current project? [Clarity, Spec §"Domain Language → Current project"] [Gap]
- [ ] CHK023 — Is the case where `.kittify/` exists but is owned by a different user explicitly addressed (refuse, warn, or proceed)? [Gap, Edge Case]

## Input Validation — Environment & CLI Surfaces

- [ ] CHK024 — Is the precedence between `CI=*`, no-TTY detection, `--no-nag`, and `SPEC_KITTY_NO_NAG` defined precisely so a single attacker-controlled env var cannot re-enable network access against the user's intent (or vice versa)? [Clarity, Spec §A-007]
- [ ] CHK025 — Is the configuration surface for the throttle window (NFR-009) constrained to safe value ranges (e.g., refuse negative or absurdly large values rather than silently divide by zero or overflow)? [Completeness, Spec §NFR-009] [Gap]
- [ ] CHK026 — Is the case where the attacker controls `$XDG_CACHE_HOME` (and points it at a sensitive system file) addressed in the requirements? [Gap, Edge Case]
- [ ] CHK027 — Is the case where the attacker controls `$HOME` (e.g., container shell) addressed? [Gap, Edge Case]

## Output Hygiene & User-Facing Messages

- [ ] CHK028 — Are requirements specified for sanitizing version strings, install-method strings, and migration IDs before embedding them in human-readable upgrade hints (no ANSI-escape injection, no shell-metacharacter injection into shown commands)? [Gap, Spec §FR-006]
- [ ] CHK029 — Are requirements specified for sanitizing the same fields before embedding in JSON output (so a hostile latest-version response cannot break consumer parsers or smuggle structured data)? [Gap, Spec §FR-022]
- [ ] CHK030 — Is it specified that error messages and stack traces from the nag path MUST NOT leak local filesystem paths beyond what the user provided? [Gap, Spec §NFR-002]
- [ ] CHK031 — Is the upgrade hint for `unknown` install method explicitly *not* a runnable shell command (to prevent users blindly pasting into a shell)? [Gap, Spec §FR-007, §A-008]
- [ ] CHK032 — Are requirements specified for what the CLI prints when the install-method detection itself errors out (must not leak environment, must not crash the host command)? [Gap]

## Migration Path Security

- [ ] CHK033 — Are requirements specified for the integrity of the migration registry (only ship migrations that are part of the installed CLI package; do not load migration code from the project's `.kittify/`)? [Gap, Spec §FR-018]
- [ ] CHK034 — Is the rule "migrations execute under the user's privileges and may write anywhere a normal command can" stated explicitly, so users understand what `spec-kitty upgrade` is authorized to do? [Gap, Spec §"Scenario E"] [Ambiguity]
- [ ] CHK035 — Are requirements specified for the dry-run path (FR-012, FR-019) being **read-only at the OS level**, with no side-effects beyond reading project files? [Completeness, Spec §FR-012, §FR-019]
- [ ] CHK036 — Are requirements specified for behavior when a migration fails partway: is the project left in a documented partial state, or rolled back? Without this, an attacker could engineer a project that triggers a partial-state where downstream commands behave unsafely. [Gap, Recovery]
- [ ] CHK037 — Is it specified that `--yes` / `--force` does NOT bypass schema-incompatibility blocks (FR-010 — too-new project), only confirmation prompts? [Clarity, Spec §FR-010, §FR-017, §A-006]
- [ ] CHK038 — Are requirements specified for what happens when two `spec-kitty upgrade` processes race against the same project (file lock, refuse, last-write-wins)? [Gap, Edge Case]

## Self-Upgrade Path (`--cli`) Security

- [ ] CHK039 — Is the scope of "supported self-upgrade behavior" in FR-016 enumerated by install method, with explicit exclusions for any method that cannot be self-upgraded safely (e.g., system package, source install)? [Clarity, Spec §FR-016] [Ambiguity]
- [ ] CHK040 — Are requirements specified for whether `--cli` ever **executes** an upgrade command on the user's behalf vs. only **prints** it, and the security implications of either choice are noted? [Gap, Spec §FR-016, §C-004]
- [ ] CHK041 — Is C-004 (no forced CLI self-update during normal command startup) consistent with FR-016, so no startup path can be coaxed into self-upgrade by env var or flag? [Consistency, Spec §C-004, §FR-016]

## Determinism & Side-Channel Hardening

- [ ] CHK042 — Are requirements specified that the nag must not behave differently between two invocations purely because a remote source is reachable (i.e., no observable side channel that leaks "network is up" beyond the printed line itself)? [Clarity, Spec §"Scenario A"] [Ambiguity]
- [ ] CHK043 — Are requirements specified to prevent timing differences between the "fresh cache, no network" path and the "stale cache, network call" path being used as an oracle for whether a particular CLI version is installed? [Gap, Edge Case]
- [ ] CHK044 — Are requirements specified that NFR-001's <100 ms target must hold even when the cache file is corrupt or maliciously crafted (no exponential parser blowup)? [Completeness, Spec §NFR-001]

## Supply Chain & Dependency Posture

- [ ] CHK045 — Is the explicit prohibition on adding hosted SaaS / tracker / sync dependencies (NFR-008, C-007) accompanied by a requirement that the planner's allowed hostnames are reviewed at PR time? [Completeness, Spec §NFR-008, §C-007] [Gap]
- [ ] CHK046 — Is C-009 ("no new mandatory runtime dependency outside `typer`, `rich`, `ruamel.yaml`, plus stdlib") enforceable at review time (e.g., dependency-policy test)? [Measurability, Spec §C-009]
- [ ] CHK047 — Is the requirement that `ruamel.yaml` (per the charter) must be invoked in safe mode for any externally-influenced YAML stated in the spec or deferred to plan with a clear note? [Gap, Spec §"Key Entities → Current-project metadata"]

## Privacy

- [ ] CHK048 — Is it specified that no telemetry, analytics ping, or user-identifying string leaves the machine from the upgrade-nag path (beyond the unavoidable User-Agent of the network library, which itself should be documented)? [Completeness, Spec §NFR-008] [Gap]
- [ ] CHK049 — Is the User-Agent / request signature for the latest-version call specified (or required to be specified during planning) so security review can audit the outbound surface? [Gap]
- [ ] CHK050 — Are requirements specified that the nag cache and any debug logs MUST NOT record project paths, project slugs, or mission identifiers? [Gap]

## Failure & Exception Path Security

- [ ] CHK051 — Are exception-path requirements specified so that an unexpected error in the planner cannot bypass the safe/unsafe gate (i.e., "fail closed" for unsafe commands when planner errors out)? [Completeness, Spec §FR-008, §FR-024]
- [ ] CHK052 — Are exception-path requirements specified so that an unexpected error in the *nag* path is "fail open" but does not cascade into corrupting the cache file? [Clarity, Spec §NFR-002] [Ambiguity]
- [ ] CHK053 — Are requirements specified for handling SIGINT / SIGTERM mid-cache-write, mid-network-fetch, and mid-migration apply (no half-written cache, no partially-applied migration without flag)? [Gap, Edge Case, Recovery]

## Security Acceptance Criteria & Traceability

- [ ] CHK054 — Are at least one Success Criterion or Acceptance Criterion explicitly tied to a security property (e.g., "zero outbound network calls in CI" — SC-005 covers this; are similar SCs needed for cache-perm hardening, YAML safe-load, payload size limit)? [Coverage, Spec §SC-005] [Gap]
- [ ] CHK055 — Is there a documented mapping from each security-relevant requirement to a verification mechanism (unit test, integration test, dependency policy, doc review)? [Traceability] [Gap]
- [ ] CHK056 — Are security-relevant assumptions (A-001 cache location trust, A-002 PyPI as authoritative source, A-007 CI/non-interactive predicate) flagged for security review during planning? [Assumption, Spec §"Assumptions"]

---

## Notes

- This checklist deliberately stays at the requirements level. Any item marked `[Gap]` should be either added to `spec.md` before planning, or deferred with a recorded rationale in the plan's decision log (per DIRECTIVE_003 — Decision Documentation Requirement).
- Security defaults the spec already gets right: no SaaS dependency (C-007/NFR-008), no forced self-update at startup (C-004), no global registry (C-002/FR-021), no cross-project state (FR-021), CI determinism (FR-005/NFR-004/SC-005), injectable latest-version source (A-002), local-only operation (C-001/C-007).
- The dominant unaddressed surfaces are: (1) network-path hardening for the latest-version fetch, (2) safe-load and bounds on `.kittify/metadata.yaml`, (3) cache file permissions and symlink resistance, (4) output sanitization in upgrade hints, (5) fail-closed behavior of the planner for unsafe commands.
- Address `[Gap]` and `[Ambiguity]` items by editing `spec.md` (preferred) or by recording a justified deferral in the plan's decision log.
