---
work_package_id: WP09
title: 'The /tmp root-walk artifact: name the offender, pin the invariant filesystem-independently'
dependencies: []
requirement_refs:
- FR-012
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: 9ed8757b6fa46ef3fa51544ff791ded9765df4ee
created_at: '2026-07-31T15:33:04.594244+00:00'
subtasks:
- T027
- T028
history: []
authoritative_surface: tests/sync/
execution_mode: code_change
owned_files:
- tests/sync/test_sync_consent_default_deny.py
tags: []
tracker_refs: []
---

# WP09 — The `/tmp` root-walk artifact

Squarely on the mission's theme: **a local verification result that is about the machine rather than
about the code.** A developer whose machine has a repo-root marker at or above `/tmp` gets a mysterious
consent-gate failure instead of a message naming the offending directory.

`tests/sync/test_sync_consent_default_deny.py::test_unresolvable_routing_does_not_consent_to_sync`
currently depends on `locate_project_root`'s walk-up finding **no** `.git`/`.kittify` marker anywhere
above `tmp_path` — **and** on `SPECIFY_REPO_ROOT` being unset, **which it never asserts**. The existing
test `delenv`s only `SPEC_KITTY_HOME`, and `SPECIFY_REPO_ROOT` is **tier-1 authoritative** in
`core/paths.py`.

## The decision, taken in the plan and not left open

Both halves land; this is not an either/or.

## Definition of done — measurable evidence

### T027 — the filesystem-independent pin

The **invariant** — *routing that cannot be determined denies* — gets a pin that **does not depend on
the filesystem at all**: force the resolution seam to yield "unresolvable" and assert
`is_sync_enabled_for_checkout()` is `False`. **So a hostile machine cannot silently remove coverage of
the requirement.** It **passes in both environments** (with and without a planted marker).

This *strengthens* the fail-closed pin by adding a filesystem-independent one; **it never relaxes it.**

### T028 — the walk-up test keeps its form and gains an asserted precondition

The existing walk-up test (`:127-152`) keeps its **cwd-based form** and gains an **asserted
precondition** reporting:

- the **first ancestor** carrying a `.git`/`.kittify` marker, and
- **the value of `SPECIFY_REPO_ROOT`**.

So the developer knows what to delete.

### Red first — both halves, as a consequence

With a marker planted above the tmp root:

- **before the change**, the current test fails on the **bare consent assertion** — the mysterious
  failure, demonstrated;
- **after the change**, it fails **naming the offending ancestor**;
- and the **new filesystem-independent pin passes in both environments**.

The failure text is quoted in each case (NFR-007) — a tally moving is not evidence.

### T028 — C-001 binds, absolutely

**No production routing change.** No change to `locate_project_root` or
`resolve_checkout_sync_routing_readonly`, and **none to `SPECIFY_REPO_ROOT`'s precedence**. The
`/tmp`-root-walk failure is a machine-specific artefact that reproduces on pristine `upstream/main` and
**passes on CI**; the issue is emphatic that production routing must not be changed for it.

### Assertion-of-absence discipline

*Any test whose assertion is "X did not happen" needs to state why X would otherwise have happened*, or
a new short-circuit upstream silently adopts it. Both pins here assert a **refusal**, so each states the
condition under which consent **would** have been granted.

### NFR-008 — every count line carries its collected count

**Added post-tasks: WP09 was one of only two WPs in this mission carrying no collected-count
obligation.** Every count line this WP quotes — the red with a marker planted, the red after the
change, and the green from the filesystem-independent pin in **both** environments — is quoted
**beside `tests/sync/test_sync_consent_default_deny.py`'s own collected count**, measured with
`pytest --collect-only -q` on that single file at the commit under test and **stated before the first
red**. T027 adds a test, so the collected count **moves by a stated amount**; a count that moved by an
unstated amount is a defect in the edit and is reconciled, not absorbed. *A count line that does not
reconcile against its file's collected count is not evidence, and is re-measured rather than argued
about.* A `1 failed, N passed` whose `1 + N` does not equal the collected count means something was
deselected or errored at collection, and the run is not the run it claims to be.

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-003**: output to a file, tail of the file read; quote the count line **with its
assertion text**, never "exit 0"; **an empty output file is no measurement**. **NFR-004**: never run
`tests/sync` and `tests/cli` sessions concurrently on one machine.

### CI note this WP is load-bearing for

`fast-tests-sync` is gated on `needs.changes.outputs.sync` (`ci-quality.yml:1101`), and the `push`
escape only fires on `main`/`develop`/`2.x` (`:39-42`), **never on this feature branch**. The `changes`
filter's `sync` predicate includes `tests/sync/**`, and **this WP edits `tests/sync/test_sync_consent_default_deny.py`**
(as WP05 edits `tests/sync/conftest.py`) — so the shard **will** run. **This must still be verified,
not assumed**: if the job's conclusion is `skipped`, no claim about it is admissible (R4, SC-010).

## Files other agents hold

`tests/sync/conftest.py` and `tests/sync/test_leak_guard_probe_3115.py` are **WP05's** — including the
armed filename-token guard at `tests/sync/conftest.py:242-259`, which is off limits to everyone.
`tests/sync/tracker/test_saas_client.py` is **WP06's, then WP14's**. `src/**` is **nobody's** — C-001
makes that absolute for this WP in particular.
