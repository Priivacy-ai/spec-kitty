---
work_package_id: WP01
title: Manifest schema + hash infra (infra WP — C-011 planning-base-red-first N/A)
dependencies: []
requirement_refs:
- C-001
- C-005
- C-006
- NFR-001
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: fix/2681-synthesized-drg-stale
merge_target_branch: fix/2681-synthesized-drg-stale
branch_strategy: Planning artifacts for this mission were generated on fix/2681-synthesized-drg-stale. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2681-synthesized-drg-stale unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Manifest schema + content-hash infra
assignee: ''
agent: "claude"
shell_pid: "2464605"
shell_pid_created_at: "1784214813.3"
history:
- at: '2026-07-16T12:49:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/synthesizer/
create_intent:
- tests/charter/test_bundle_content_hash.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/synthesizer/manifest.py
- src/charter/bundle.py
- src/specify_cli/cli/commands/charter/_fresh_doctrine.py
- tests/charter/synthesizer/test_manifest.py
- tests/integration/test_charter_synthesize_fresh.py
- tests/charter/test_bundle_content_hash.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Manifest schema + hash infra (infra WP — C-011 planning-base-red-first N/A)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `<div>`, `<script>`
Use language identifiers in code blocks: ```python, ```bash

---

## Objectives & Success Criteria

WP01 is the first of four strictly-sequential WPs fixing
[#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681) (synthesized
DRG permanently stuck `stale`). WP01 delivers INTERNAL infrastructure — a new
optional manifest field, a pure content-hash helper, the `finalize_manifest`
refactor, and the `verify_manifest_hash` shim generalization — with **NO
user-observable freshness behavior** (the reader and the three constructor
writers are untouched; nothing an operator runs changes verdict). The
user-observable behavior is delivered and planning-base-red-first-verified in
WP02 (writer) and WP03 (reader).

**C-011 scoping (planning-base-red-first is N/A for WP01)**: because WP01
delivers no user-observable runtime behavior, there is no operator-facing
freshness assertion that is RED on `planning_base_branch` — the new symbols
(`finalize_manifest`, `compute_bundle_content_hash`) do not even exist on the
base, so a test referencing them is UNRUNNABLE (a collection error, not a
clean assertion-RED), and the v2 `verify_manifest_hash` behavior is GREEN on
the base (no field yet). So WP01 does NOT claim a planning-base-red-first
test. Instead WP01 follows red-green-refactor **internally** (TDD for the
shim + helper), and its gate is:
- (i) **green-preserving regression** — existing v2 manifests still
  `verify_manifest_hash` after the field add + the shim (no operator-facing
  break);
- (ii) **new-symbol unit coverage** — the helper (incl. the fail-safe `None`
  cases) and finalizer parity;
- (iii) the **intra-WP verify-shim red→green** — adding the field reddens v2
  verify (a real, momentary red inside WP01), the per-field shim greens it: a
  TDD cycle landed WITHIN WP01, NOT a planning-base-red test.
This is correct scoping of C-011 to the behavior WPs (WP02/WP03), not the
blanket mission-level dilution the `/analyze` gate rejects.

**Definition of Done** (each item ties to the plan's traceability table):

- [ ] `bundle_content_hash: str | None = None` added to `SynthesisManifest`
      (NON-volatile — never added to `write_pipeline._VOLATILE_MANIFEST_
      FIELDS`); `schema_version` widened to `Literal["2", "3"]` with the
      default KEPT `"2"` (the bump to `"3"` is WP02's job — see the
      "Why the default bump is deferred" note). Satisfies NFR-001, C-001.
- [ ] `charter.bundle.compute_bundle_content_hash(repo_root) -> str | None`
      + `BUNDLE_CONTENT_HASH_FILES` exist, PURE and UNWIRED (zero production
      callers after this WP), per-file `hash_content` then combine digests.
      Satisfies C-005 (single canonical write-side recipe).
- [ ] **C1 fail-safe**: `compute_bundle_content_hash` returns `None` (→ the
      reader will map to `stale`, never a crash) when `.kittify/charter/` is
      missing OR any of the four files is missing/unreadable — the read
      guard catches **both `OSError` AND `UnicodeDecodeError`** (a non-UTF-8
      bundle file raises `UnicodeDecodeError`, a `ValueError` subclass NOT
      caught by `OSError`). Satisfies the spec fail-posture (spec.md:47).
- [ ] `finalize_manifest(manifest) -> SynthesisManifest` exists in
      `manifest.py`, exported, zero production callers after this WP except
      the fresh-seed reroute (T005). Satisfies C-006.
- [ ] `verify_manifest_hash`'s legacy fallback is generalized to the
      per-field `_raw_field_names`-subset recipe (raw `hashlib.sha256(
      canonical_yaml(subset))`, NOT a pop-list, NOT `compute_manifest_hash`)
      — a v2 manifest lacking `bundle_content_hash` still verifies AND the
      T006(b) DISCRIMINATING tamper fixture (a manifest that CARRIES
      `bundle_content_hash` on disk but whose stored `manifest_hash` excluded
      it, then tampered) RAISES. That fixture is what actually proves
      per-field vs pop-list (a pop-list would false-ACCEPT it). Satisfies the
      pre-fix-manifest backward-compat edge case.
- [ ] `_fresh_seed_manifest_text` routes through `finalize_manifest`; output
      still round-trips + verifies; `schema_version` stays `"2"`
      intentionally.
- [ ] Intra-WP TDD (NOT planning-base-red): land the T004 shim and the T002
      helper red-green-refactor within WP01 — the T006(b) discriminating
      tamper fixture + the absent-key fixture prove the shim is per-field
      (not a pop-list); the T007 helper unit tests (incl. non-UTF-8→None)
      prove the fail-safe. These are internal TDD cycles + green-preserving
      regression, not an operator-facing planning-base-red test (see the
      C-011 scoping note above).
- [ ] Reader (`computer.py`) + the three `SynthesisManifest(` writer
      constructors are byte-for-byte untouched (`git diff --stat` shows only
      WP01's 6 owned files).
- [ ] `mypy --strict` + `ruff check` clean on every changed file (NFR-004);
      ≥90% new-line coverage (NFR-005).

## Context & Constraints

**Read first** (dense load-bearing detail lives here, not repeated in full):

- `.kittify/charter/charter.md` — project charter (governance).
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/spec.md` — FR/NFR/C,
  AS-1..6, Edge Cases (esp. the pre-fix-manifest edge + fail-posture MUST).
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/plan.md` — WP01
  section (Scope, C1 fail-safe, intra-WP TDD tests, Risks) + the Charter
  Check C-011 scoping (WP01/WP04 = no user-observable behavior → N/A).
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/data-model.md` — the
  `finalize_manifest`, `verify_manifest_hash` shim, and
  `compute_bundle_content_hash` contracts (exact recipes).
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/research.md` — facts
  #5, #8, #13, #14, #15, #16, #17 + Decisions 3, 5, 6.
- The mission tracer files (`tracer-approach.md`,
  `tracer-design-decisions.md`, `tracer-tooling-friction.md`) — append your
  own implementation notes to these as you work.

**Why the `schema_version` default bump is deferred to WP02** (research fact
#17): `write_pipeline.promote` (`write_pipeline.py:668`) and
`resynthesize_pipeline._rewrite_manifest` (`resynthesize_pipeline.py:188`)
hardcode `"schema_version": "2"` in the raw dict they HASH but construct
`SynthesisManifest(...)` with NO `schema_version` kwarg (model default). If
WP01 bumped the default to `"3"`, those writers would write a `"3"` instance
whose hash was computed over `"2"` → `verify_manifest_hash` RAISES →
`test_promote_writes_manifest_with_valid_self_hash` + the resynthesize no-op
test go RED at WP01's boundary — an ACCIDENTAL divergence-RED. So WP01
widens the `Literal` but KEEPS the default `"2"`; WP02 bumps it atomically
with the writer conversion.

**Why the fresh-seed reroute (T005) is in WP01** (research fact #15):
`_fresh_seed_manifest_text` computes `hashlib.sha256(canonical_yaml(without_
hash))` over a raw dict LACKING `bundle_content_hash`, then writes
`canonical_yaml(manifest.model_dump())` which — the moment the field exists —
INCLUDES `bundle_content_hash: null`. Stored hash ≠ recomputable hash on the
bare field addition alone. WP01 adds the field, so WP01 must keep this 4th
persist site consistent.

## Branch Strategy

- **Strategy**: single-branch topology — no worktree/lane split.
- **Planning base branch**: `fix/2681-synthesized-drg-stale`
- **Merge target branch**: `fix/2681-synthesized-drg-stale`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 – Add `bundle_content_hash` field + widen `schema_version` Literal

- **Purpose**: Land the new field additively; widen the literal without
  touching the default.
- **Steps**:
  1. In `src/charter/synthesizer/manifest.py`, change line 79
     `schema_version: Literal["2"] = "2"` → `Literal["2", "3"] = "2"`
     (literal widened, default UNCHANGED).
  2. Add `bundle_content_hash: str | None = None` after `built_in_only`
     (after line 109) with a docstring: it holds the `"sha256:..."` content-
     identity digest from `charter.bundle.compute_bundle_content_hash`; it is
     **substantive (non-volatile)** and MUST NOT be added to
     `write_pipeline._VOLATILE_MANIFEST_FIELDS`.
  3. Update the class docstring (lines 64-74) with a "Schema version 3" note.
  4. Do NOT touch `compute_manifest_hash`/`verify_manifest_hash`/callers here.
- **Files**: `src/charter/synthesizer/manifest.py`
- **Parallel?**: Yes, alongside T002 (different file).
- **Notes**: `ConfigDict(frozen=True, extra="forbid")` rejects UNKNOWN keys,
  not ABSENT optional keys — a pre-fix v2 file still `model_validate`s.

### Subtask T002 – Pure, unwired `compute_bundle_content_hash` (C1 fail-safe)

- **Purpose**: Land the single canonical write-side hashing recipe with zero
  callers (behavior-inert).
- **Steps**:
  1. In `src/charter/bundle.py`, add `BUNDLE_CONTENT_HASH_FILES:
     tuple[str, ...] = ("governance.yaml", "directives.yaml",
     "references.yaml", "metadata.yaml")` near the path constants — the SAME
     four names as `computer.py::_BUNDLE_FILES` (intentional minor
     duplication per Decision 5; do NOT import from the `specify_cli` reader
     — that inverts the dependency direction). Optionally add
     `REFERENCES_YAML = Path(".kittify/charter/references.yaml")` next to the
     sibling constants for consistency.
  2. Add `def compute_bundle_content_hash(repo_root: Path) -> str | None:`.
     For each name in `BUNDLE_CONTENT_HASH_FILES` (declared order): resolve
     `repo_root / ".kittify" / "charter" / name`; if it does not exist,
     return `None`; else read it with
     `path.read_text(encoding="utf-8")` inside
     `try/except (OSError, UnicodeDecodeError): return None` (**C1** — the
     `UnicodeDecodeError` arm is mandatory: a non-UTF-8 file raises it and it
     is NOT an `OSError`). Hash each file's text independently via
     `charter.hasher.hash_content` (relative import `from .hasher import
     hash_content`). Join the four `"sha256:..."` digests with `"\n"`, hash
     the joined string AGAIN via `hash_content`, return that.
  3. No raw `hashlib` anywhere in this function (TID251 — `hash_content` is
     the only hashing entrypoint here).
  4. Add both symbols to `bundle.py`'s `__all__`.
  5. Confirm zero callers: `grep -rn "compute_bundle_content_hash" src/`
     shows only the definition + `__all__`.
- **Files**: `src/charter/bundle.py`
- **Parallel?**: Yes, alongside T001.
- **Notes**: Per-file hashing (NOT concat-then-hash-once) is REQUIRED —
  `canonical_yaml` only strips a LEADING BOM of the whole payload, so a BOM
  on files 2-4 would survive under single-hash → #2009-class false-`stale`
  (research fact #14).

### Subtask T003 – Extract `finalize_manifest()`

- **Purpose**: Land the single canonical finalizer (Decision 6) — the seam
  WP02 routes every persist site through.
- **Steps**:
  1. In `manifest.py`, add:
     ```python
     def finalize_manifest(manifest: SynthesisManifest) -> SynthesisManifest:
         """Recompute manifest_hash from the full instance and return a copy."""
         zeroed = manifest.model_copy(update={"manifest_hash": "0" * 64})
         return manifest.model_copy(
             update={"manifest_hash": compute_manifest_hash(zeroed)}
         )
     ```
  2. Add `"finalize_manifest"` to `__all__`. No writer callers in WP01
     (only T005 uses it).
- **Files**: `src/charter/synthesizer/manifest.py`
- **Parallel?**: No — benefits from T001 landing first.
- **Notes**: Behavior-preserving — identical content → same `manifest_hash`
  as the current inline `compute_manifest_hash` path (T006(c) pins this).

### Subtask T004 – Generalize `verify_manifest_hash`'s legacy fallback

- **Purpose**: MANDATORY backward-compat shim — without it, adding the field
  breaks `verify_manifest_hash` for every existing v2 manifest carrying
  `built_in_only` (research fact #16: stored `abc25ece…` vs recomputed
  `c15b61e0…`), surfacing via `charter status`/`doctor`/`bundle validate`.
- **Steps**:
  1. In `verify_manifest_hash` (lines 197-222), replace the existing
     legacy-fallback block (lines 210-217) with the generalized recipe:
     ```python
     computed = compute_manifest_hash(manifest)
     if computed != manifest.manifest_hash:
         raw_field_names = manifest._raw_field_names
         if raw_field_names is not None:
             subset = {
                 k: v
                 for k, v in manifest.model_dump(mode="python").items()
                 if k in raw_field_names and k != "manifest_hash"
             }
             legacy_computed = hashlib.sha256(  # noqa: TID251 - production raw SHA-256 owner
                 canonical_yaml(subset)
             ).hexdigest()
             if legacy_computed == manifest.manifest_hash:
                 return
         raise ValueError(
             f"manifest_hash mismatch (stored {manifest.manifest_hash[:12]}..., "
             f"computed {computed[:12]}...)"
         )
     ```
  2. **Critical**: the subset MUST be gated per-field by `k in
     raw_field_names` (the actual on-disk keys captured at `load_yaml` time,
     `manifest.py:172-174`), NOT a fixed pop-list — a fixed pop-list would
     silently weaken tamper detection for every v3 file. This subsumes the
     old `built_in_only`-absent special case.
  3. Keep the module's `hashlib` import + the `# noqa: TID251` rationale
     (this module is a documented raw-SHA-256 owner).
- **Files**: `src/charter/synthesizer/manifest.py`
- **Parallel?**: No — highest-risk subtask; validate with T006(a)/(b) before
  moving on.

### Subtask T005 – Route `_fresh_seed_manifest_text` through `finalize_manifest`

- **Purpose**: Fix the 4th persist site in the same commit as the field
  addition (research fact #15).
- **Steps**:
  1. In `src/specify_cli/cli/commands/charter/_fresh_doctrine.py`, replace
     the manual hash-then-validate in `_fresh_seed_manifest_text` (lines
     55-82) with build-instance-then-finalize:
     ```python
     from charter.synthesizer.manifest import SynthesisManifest, finalize_manifest
     manifest = SynthesisManifest.model_validate(
         {**without_hash, "manifest_hash": "0" * 64}
     )
     manifest = finalize_manifest(manifest)
     return canonical_yaml(manifest.model_dump(mode="python")).decode("utf-8")
     ```
  2. `without_hash["schema_version"]` STAYS `"2"` (data-model.md — the reader
     short-circuits on `built_in_only` before any version check, and
     `versioning.py`'s v2 repair guards on `!= "2"`; bumping would only
     perturb `test_bundle_validate_fresh_seed.py`'s golden). Do not bump it
     in a later WP either.
  3. Remove the now-dead `import hashlib` if `_fresh_seed_manifest_text` was
     its only consumer; keep `canonical_yaml`.
- **Files**: `src/specify_cli/cli/commands/charter/_fresh_doctrine.py`
- **Parallel?**: No — depends on T003.
- **Notes**: `_materialize_fresh_doctrine`'s idempotency contract is
  preserved (`finalize_manifest` is pure/deterministic).

### Subtask T006 – Intra-WP shim/parity tests + production fresh-seed pin

- **Purpose**: The green-preserving regression + finalizer parity + the
  intra-WP verify-shim red→green (NOT a planning-base-red operator test —
  these exercise the internal `verify_manifest_hash`/`finalize_manifest`
  contracts). Landed in `test_manifest.py` + `test_charter_synthesize_
  fresh.py`.
- **Steps**:
  1. **(a) verify-shim absent-key** (`test_manifest.py`): a v2 manifest YAML
     carrying `built_in_only` but NOT `bundle_content_hash` (matching every
     post-Phase-7 on-disk manifest — see `_seed_manifest` shape in
     `tests/specify_cli/charter_freshness/test_computer.py:73-98`), written +
     `load_yaml`'d, `verify_manifest_hash()` does NOT raise. This is the
     green-preserving-regression half: it goes momentarily RED the instant
     the field is added (T001) and GREEN once the per-field shim lands (T004)
     — the intra-WP TDD cycle.
  2. **(b) DISCRIMINATING tamper** (`test_manifest.py`) — the fixture must
     distinguish a per-field `_raw_field_names`-gated shim from a fixed
     pop-list shim (a pop-list would silently pass tamper detection off).
     Build the fixture so `bundle_content_hash` is PRESENT on disk but the
     stored `manifest_hash` was computed by the LEGACY raw hash over the
     OTHER fields ONLY (i.e. excluding `bundle_content_hash`):
     - Construct the manifest dict WITH a real `bundle_content_hash` value.
     - Compute `manifest_hash` as `hashlib.sha256(canonical_yaml(subset))`
       over the subset that EXCLUDES `bundle_content_hash` (and
       `manifest_hash`) — i.e. reproduce what a legacy writer that never knew
       about the field would have stored. Write that to disk.
     - Now MUTATE the on-disk `bundle_content_hash` to a different value.
     - `load_yaml` → `verify_manifest_hash()` MUST RAISE `ValueError`.
     **Why this discriminates**: a fixed pop-list shim always drops
     `bundle_content_hash` before recomputing, so it would recompute the
     legacy over-the-other-fields hash → MATCH the stored value → FALSE-
     ACCEPT the tampered file. The per-field shim gates on `_raw_field_names`
     — the on-disk file DOES carry `bundle_content_hash`, so it is IN the
     subset → the mutated value is included → recompute mismatches → RAISE.
     (The earlier finalize_manifest-built tamper fixture does NOT
     discriminate: both shim shapes raise on it, because the stored hash
     COVERS the field. This legacy-excluded-then-tampered fixture is the one
     that actually proves per-field.)
  3. **(c) finalizer parity** (`test_manifest.py`): `finalize_manifest(inst).
     manifest_hash` == `compute_manifest_hash(inst.model_copy(update=
     {"manifest_hash": "0"*64}))` for identical content.
  4. **(d) production fresh-seed verify** (`test_charter_synthesize_fresh.py`):
     extend `test_synthesize_on_fresh_project_via_public_cli` (~line 162 —
     today asserts only `"built_in_only: true" in text`) to additionally
     `load_yaml` + `verify_manifest_hash` the REAL `_fresh_seed_manifest_text`
     output — assert it does not raise. Do not remove the existing assertion.
- **Files**: `tests/charter/synthesizer/test_manifest.py`,
  `tests/integration/test_charter_synthesize_fresh.py`
- **Parallel?**: (a)-(c) depend on T003/T004; (d) depends on T005.
- **Notes**: (b)'s legacy-excluded stored hash is computed exactly the way
  `verify_manifest_hash`'s OWN fallback computes its comparison — raw
  `hashlib.sha256(canonical_yaml(subset))` over the non-`manifest_hash`
  subset — so the fixture is self-consistent with a legacy writer and the
  ONLY thing under test is whether the shim's subset is per-field-gated.

### Subtask T007 – Helper unit tests (missing-file→None, non-UTF-8→None, happy path)

- **Purpose**: Author the new `tests/charter/test_bundle_content_hash.py`
  (planned-new, `create_intent`) — new-symbol unit coverage for the fail-safe
  helper. This is intra-WP TDD (write the test against the new symbol, watch
  it fail because the symbol/behavior is not there yet, implement, watch it
  pass) — NOT a planning-base-red operator test (`compute_bundle_content_hash`
  does not exist on `planning_base_branch`, so the test is unrunnable there,
  not a clean assertion-RED).
- **Steps** — TDD within WP01 (test-then-implement against T002):
  1. **Happy path**: seed all 4 bundle files under a tmp
     `.kittify/charter/`, assert `compute_bundle_content_hash(tmp)` returns a
     `"sha256:..."` string, and that it is DETERMINISTIC for fixed content
     (call twice, equal) and mtime-agnostic (touch a file's mtime without
     changing content → same hash).
  2. **Missing-file→None**: seed 3 of the 4 files (omit one) → assert `None`;
     also `.kittify/charter/` entirely absent → `None`.
  3. **Non-UTF-8→None (C1)**: seed the 4 files but write one with invalid
     UTF-8 bytes (e.g. `path.write_bytes(b"\xff\xfe not utf8")`) → assert
     `compute_bundle_content_hash(tmp)` returns `None` (proves the
     `UnicodeDecodeError` arm is caught — this test FAILS with an uncaught
     `UnicodeDecodeError` if T002 catches only `OSError`).
  4. **Per-file BOM/CRLF independence** (optional but recommended): two repos
     with byte-identical CONTENT but one file carrying a BOM/CRLF variant
     that `hash_content` normalizes away produce the SAME hash — guards the
     per-file-hashing rationale (fact #14).
- **Files**: `tests/charter/test_bundle_content_hash.py` (NEW)
- **Parallel?**: Yes, alongside T006 (different file), once T002 lands.

## Test Strategy

```bash
pytest tests/charter/test_bundle_content_hash.py -q
pytest tests/charter/synthesizer/test_manifest.py -q
pytest tests/integration/test_charter_synthesize_fresh.py -q
# Keep-green regression net (WP01 must not regress these):
pytest tests/charter/synthesizer/test_write_pipeline.py \
    tests/charter/synthesizer/test_orchestrator_resynthesize.py \
    tests/integration/test_charter_synthesize_built_in_only.py \
    tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py \
    tests/doctrine/test_versioning.py \
    tests/specify_cli/upgrade/test_bundle_validate_fresh_seed.py -q
mypy --strict src/charter/synthesizer/manifest.py src/charter/bundle.py \
    src/specify_cli/cli/commands/charter/_fresh_doctrine.py
ruff check src/charter/synthesizer/manifest.py src/charter/bundle.py \
    src/specify_cli/cli/commands/charter/_fresh_doctrine.py \
    tests/charter/synthesizer/test_manifest.py \
    tests/integration/test_charter_synthesize_fresh.py \
    tests/charter/test_bundle_content_hash.py
```

NFR-005: exercise every branch, esp. each `None`-return in
`compute_bundle_content_hash` (missing dir, missing single file, non-UTF-8)
and the `raw_field_names is None` guard in `verify_manifest_hash`.

## Risks & Mitigations

- **Highest**: T004 regressing to a fixed pop-list → silently weakens tamper
  detection. Mitigation: the T006(b) DISCRIMINATING fixture (field present on
  disk, stored hash computed EXCLUDING it, then tampered) — a pop-list shim
  false-ACCEPTS it, the per-field shim REJECTS it. A finalize_manifest-built
  tamper fixture does NOT discriminate (both shim shapes raise), so it MUST
  be the legacy-excluded-then-tampered shape.
- **C1**: catching only `OSError` → a non-UTF-8 bundle file crashes
  `charter status`/preflight. Mitigation: T007's non-UTF-8 test.
- **Scope creep**: touching the reader or the three constructor writers.
  Mitigation: `git diff --stat` shows only WP01's 6 owned files.

## Review Guidance

- Confirm the freshness decision is genuinely unchanged (the reader is
  untouched) — WP03's tests are not yet authored, so run nothing there, but
  confirm no `computer.py` diff.
- Confirm `grep -rn "compute_bundle_content_hash\|finalize_manifest" src/`
  shows the new symbols with callers only in `manifest.py`/`bundle.py`
  themselves + the one `_fresh_doctrine.py` `finalize_manifest` call (T005).
- Re-verify T004's per-field gating against data-model.md's shim recipe, AND
  confirm the T006(b) tamper fixture is the DISCRIMINATING shape (field
  present on disk, stored hash computed EXCLUDING it, then tampered → RAISES)
  — a finalize_manifest-built tamper fixture does not prove per-field. If
  T006(b) is not the discriminating shape, the per-field claim is unproven —
  reject.
- Confirm the C1 `UnicodeDecodeError` arm is present and T007 exercises it.
- Confirm WP01 is framed as C-011 planning-base-red-first **N/A** (infra WP,
  no user-observable behavior) — NOT as a "planning-base-red behavior WP".
  The gate is green-preserving regression + new-symbol unit coverage + the
  intra-WP verify-shim TDD cycle, not an operator-facing planning-base-red
  test.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Initial entry**:

- 2026-07-16T12:49:44Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.
- 2026-07-16T15:13:40Z – claude – shell_pid=2464605 – Assigned agent via action command
- 2026-07-16T15:54:45Z – claude – shell_pid=2464605 – single_branch: work on target fix/2681-synthesized-drg-stale (759d24fa6,74472f402); adversarial gate PASSED
- 2026-07-16T16:00:20Z – user – shell_pid=2464605 – gate passed; single_branch on target
- 2026-07-16T19:26:57Z – user – shell_pid=2464605 – mission complete; adversarial gates passed; #2681 fixed
