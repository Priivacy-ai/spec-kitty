# Research: Charter Preflight Remediation Authority

**Mission**: `charter-preflight-remediation-01KYG9WK`
**Date**: 2026-07-27
**Base**: `main@1aed89411` + spec commit `f39fce1ec`

This document discharges the two questions the spec deferred to plan:

1. Enumerate the closed set of charter-presence resolvers (FR-004 / SC-003).
2. Settle the Assumptions clause: are they answering the *same* question?

It also records one finding that **inverts a premise in the spec's own User Story 2 narrative**.

---

## R-001 — The authoritative charter source is `charter.yaml`, not `charter.md`

**Decision**: The consolidation target for FR-004 is `charter.yaml`. The gate is reading the
canonical artifact; the operator-facing diagnostics are reading the retired one.

**Rationale**: `src/specify_cli/charter_runtime/freshness/computer.py:295-297` states it directly:

> *"Landmine 2 (data-model.md): `charter.yaml` — not `charter.md` — is the authoritative,
> resolving charter source post-inversion. The historical `charter.md`-SHA-vs-
> `metadata.yaml::charter_hash` comparison is retired outright."*

**Why this matters — it corrects the spec.** The spec's User Story 2 narrative reads as though the
gate is the outlier: every diagnostic reports healthy, so the gate must be asking the wrong
question. The direction of error is the reverse. The gate resolves the authoritative artifact; the
diagnostics resolve an artifact that was demoted by the post-inversion work. The operator's
experience described in User Story 2 is accurate and unchanged, but the **fix direction flips**:
converge the diagnostics onto the gate's source, never the gate onto theirs.

This is the same failure mode the post-spec gate caught on the preceding mission (inverted root
cause inherited from a plausible-sounding narrative). It was caught here only because the spec's
checklist made settling it a blocking plan deliverable.

**Alternatives considered**: Converging on `charter.md` — rejected outright; it would re-open a
decision that the post-inversion work deliberately closed, and would make the gate stop resolving
the authoritative source. Treating them as two legitimately different questions and merely renaming
them (the Assumptions fallback, which would have retired C-002) — rejected: see R-002.

---

## R-002 — They are the same question, so C-002's consolidation mandate stands

**Decision**: FR-004 remains "consolidate", not "name them distinctly". C-002 applies as written.

**Rationale**: The canonical bundle manifest (`src/charter/bundle.py:128-132`) declares:

```
tracked_files   = [CHARTER_MD, CHARTER_YAML]
derived_files   = []
content_hash_files = [CHARTER_YAML]
```

Both artifacts are tracked/authored — neither derives from the other
(`bundle.py:90-91`: *"Landmine 1 … do NOT fold this into `derived_files` — `charter.yaml` is
tracked/authored, not derived."*). But only `charter.yaml` is the content-hash authority, and
R-001 establishes it as the resolving source. Every surface is therefore trying to answer the same
operator-facing question — "does this project have a usable charter" — and simply disagrees about
which artifact settles it. That is a divergence, not two distinct questions.

**Consequence for the spec**: the Assumptions clause's escape hatch ("if they turn out to be
genuinely different questions, FR-004 becomes *name them differently*") does **not** fire. The
consolidation mandate is live.

---

## R-003 — Enumeration of charter-presence resolvers (closes SC-003)

> **Line citations drift — verify before trusting.** WP03 moved two `computer.py` sites
> (`:318`→`:331`, `:357`→`:377`) merely by adding docstrings, and its first attempt keyed the
> exemption set on those numbers, which the review rejected. Re-verified 2026-07-27 after WP03:
> the sites below are unchanged on the primary checkout. Treat each `:NNN` as a pointer to *the
> resolver described*, never as an address to match — anything mechanical must resolve it from the
> module (see R-007).

Operator-reachable resolvers, by the artifact each keys off:

| # | Site | Keys off | Mutates while reading? |
|---|------|----------|------------------------|
| 1 | `charter_runtime/freshness/computer.py:303` (the implement gate) | `charter.yaml` | no |
| 2 | `charter/context.py:200` (`charter context`) | `charter.md` | **yes** — calls `ensure_charter_bundle_fresh` first |
| 3 | `cli/commands/charter/_common.py:33` | `charter.md` | no |
| 4 | `cli/commands/charter/status.py:56` | `charter.yaml` | no |
| 5 | `cli/commands/charter/_status_collectors.py:62,65` | both | no |
| 6 | `charter/sync.py:98,224` | both | n/a — sync is the reporter itself |
| 7 | `cli/commands/charter_bundle.py:363` | `charter.yaml` | no |
| 8 | `cli/commands/charter/resynthesize.py:102` | `charter.yaml` | no |
| 9 | `charter/context.py:2975-2988` `_project_charter_json_block` → `project_charter.present` in `charter context --json` | `charter.md` | **yes** — `_bundle_root_for_json` calls `ensure_charter_bundle_fresh` |
| 10 | `charter/context.py:339-343` `build_charter_context_include` → `charter context --include section:<id>` | `charter.md` | **yes** — same `_bundle_root_for_json` helper |
| 11 | `specify_cli/dashboard/charter_path.py:52-53` `resolve_project_charter_path` → dashboard HTTP API (404-vs-200) + per-feature `charter.exists` | `charter.md` | **yes** — via `sync_result.canonical_root` |

**Site 10 was missed in the second enumeration** (post-tasks gate, upheld). Same shape as site 9: a
third distinct top-level function (`:306`, separate from `:133` and `:3077`) performing its own
`charter.md` check through the same mutating helper. It is reached from the documented `--include`
flag (`cli/commands/charter/context.py:74`), and the compact-mode renderer actively *tells operators
to run it* (`tests/charter/test_context_section_bodies.py:183`).

It is also the mission's clearest NFR-004 violation: it **raises `ValueError("No charter.md found
for section selector.")`** rather than degrading to a reported state.

**Site 9 was missed in the first enumeration** (post-plan gate, upheld). It is a genuinely distinct
resolver, not a second reading of site 2: `build_charter_context_json` (`:3077`) is a separate
top-level function from `build_charter_context` (`:133`), and `_project_charter_json_block` performs
its own independent `charter.md` existence check and its own independent freshness call. It is wired
to the documented `--json` flag (`cli/commands/charter/context.py:115,142`), so it is operator-facing.

Worse, its mutating helper `_bundle_root_for_json` short-circuits to `None` (falling back to raw
`repo_root`) precisely when `charter.yaml` is missing — the mission's trigger state — so the field's
answer is structurally decoupled from the gate exactly where the two must agree. Omitting it would
have left `charter context --json` reproducing the User Story 2 symptom *after* the fix.

Migration-local resolvers — **out of FR-004 scope** per the spec's Assumptions clause, enumerated
here only so the count is honest:

| # | Site | Definition |
|---|------|------------|
| M1 | `m_3_2_0rc35_unified_bundle.py:160` | `charter_md.exists()` |
| M2 | `m_unify_charter_activation_finalize.py:345` | `legacy_bundle_present(...) or _config_has_activation(...)` |
| M3 | `m_3_1_1_charter_rename.py:153` | `charter_dir.exists() and (charter_dir / "charter.md").exists()` |

**Not a resolver — confirmed out of scope**: `agent mission check-prerequisites` contains **zero**
charter references (verified by case-insensitive grep). It never asks the question. The spec's
Out of Scope section already forbids giving it the capability.

### R-003a — The census history, and why the count kept moving

The resolver count was revised **six times**, each by a different check:

| Count | Source | What it missed |
|---|---|---|
| 2 | spec.md (first draft) | everything but the two surfaces named in the issue |
| 8 | plan / R-003 | `_project_charter_json_block` |
| 9 | post-plan gate | `build_charter_context_include` |
| 10 | post-tasks gate | — |
| 9 | WP04 implementation | corrected: site 6 (`sync.py`) is internal-only under R-007 |
| **10** | **WP04 review cycle 1** | **`dashboard/charter_path.py::resolve_project_charter_path`** |

The final miss is the instructive one. It was invisible to the census test *by construction*: the
scan's `_SCAN_ROOTS` was a hand-written list of three paths, and the dashboard lives outside all
three. The census had escaped the list problem **inside** its roots while reintroducing it **at the
boundary** — so its claim ("any new hand-rolled check anywhere fails this test") was false for
everything it did not look at.

That surface is not incidental: `resolve_project_charter_path` feeds the dashboard's HTTP API
(404-vs-200) and the per-feature `"charter": {"exists": …}` field. On the F2 legacy-bundle fixture
the gate reported `missing` while the dashboard reported present — the exact User Story 2 symptom,
on a live operator surface, discovered only because a reviewer went looking outside the map.

**The lesson, third statement of the same one**: a guard is bounded by its scope, and a hand-written
scope is a hand-written list. R-007 said derive the census rather than enumerate it; the boundary of
the derivation needs the same treatment.

**Pinned count for SC-003**: **10** operator-reachable resolvers, 3 migration-local. The mission
converges the operator-reachable set onto one canonical seam; the migration-local set is pinned so
growth is visible, not converged.

**Three of the ten mutate while answering** (sites 2, 9 and 10, all via `ensure_charter_bundle_fresh`).
None is eligible to be the canonical seam.

---

## R-007 — The census needs a criterion, not a list

**Decision**: the pinned census (SC-003, WP04's T022) must be **derived from a stated criterion**,
not asserted against a hand-written list of sites.

**Rationale — three consecutive enumerations were wrong.** The spec said two. Plan's R-003 said
eight, and the post-plan gate found a ninth. The corrected nine was still wrong, and the post-tasks
gate found a tenth. Each miss had the same shape: a distinct top-level function doing its own
`charter.md` existence check. Continuing to hand-count is not a plan that converges.

This is `DIRECTIVE_043` turned on our own planning artifact: close the class by construction rather
than fixing the instance. A census test that asserts against a list it also defines proves nothing —
it is the planning-artifact equivalent of the vacuous gate NFR-001 exists to forbid.

**The criterion** — the distinction comes from the codebase itself. `_compact_section_block`
(`context.py:2702`) also reads `charter.md`, and is correctly **not** a resolver. Its docstring says
why:

> *"The companion file is an optional display surface (a project's governance authority lives in
> `charter.yaml`), so a missing or unreadable `charter.md` degrades to the empty string rather than
> raising (NFR-005)."*

So:

| A site **is** a charter-presence resolver when… | A site is **not** one when… |
|---|---|
| its `charter.md`/`charter.yaml` existence check determines an operator-visible *answer* about whether the charter exists | it reads the file as optional display content |
| a missing file makes it fail, block, or report absent | a missing file degrades to empty/default without changing any presence answer |

By this criterion: sites 1–10 are resolvers; `_compact_section_block` (`:2713`) is not, and is
excluded deliberately rather than by oversight.

**Consequence for WP04's T022**: the census test must scan for the *pattern* — an existence check on
a charter artifact that gates an operator-visible answer — and assert every such site routes through
the seam. A new hand-rolled resolver appearing anywhere must turn it red. The number 10 is the
current output of that criterion, not the criterion itself.

---

## R-004 — A non-mutating canonical seam already exists and is nearly unused

**Decision**: Adopt `charter.bundle.first_missing_bundle_file` as the canonical presence seam rather
than authoring a new one.

**Rationale**: `src/charter/bundle.py:199` is a **pure existence check** over the manifest's
content-hash files — no content read, no hash, no mutation. It satisfies the spec's edge case
requiring the surviving canonical resolver to answer without mutating the project (which rules out
site 2's `ensure_charter_bundle_fresh` path as the seam).

Its docstring already describes this mission's exact scenario, and names the defect site:

> *"…this returns that path when the bundle has not been generated yet — the fail-loud chokepoints
> raise an actionable 'run the migration / charter generate' error instead of silently persisting an
> un-healable `None` bundle-content hash that the freshness reader
> (`specify_cli.charter_runtime.freshness.computer`) would report as permanently `stale`."*

So the intended remediation for a missing `charter.yaml` was always *"run the migration / charter
generate"* — never `charter sync`. The freshness computer was simply never routed through this seam.
`computer.py:69` makes the omission explicit, calling the helper *"a separate, still-live concern
owned by `charter.bundle` / `…charter._synthesis` — not this module."*

**Live callers today**: exactly one (`cli/commands/charter/_synthesis.py:530`). The seam is correct,
tested (`tests/charter/test_references_missing_failclosed.py`), and under-adopted — which is why
DIRECTIVE_044 favours routing to it over patching parity into each surface.

---

## R-005 — The preflight check registry, and the NFR-001 floor

**Check producers** (3): `_compute_charter_source`, `_compute_synced_bundle`,
`_compute_synthesized_drg` — all in `charter_runtime/freshness/computer.py`.

**Remediation-emitting states** (7 non-`None`):

| Remediation string | Sites | Effective? |
|---|---|---|
| `spec-kitty charter sync` | `:309`, `:318`, `:348`, `:357` | **No** — `charter.sync.sync()` is documented as a pure staleness reporter (`synced` always `False`, `files_written` always empty). This is BC-2. |
| `spec-kitty charter synthesize` | `:447`, `:478`, `:491` | Has a real write path (`synthesize.py:389`); effectiveness to be proven by the FR-003 mechanism, not asserted here. |

**NFR-001 floor**: 7 remediation-emitting states across 3 checks. The floor is stated as a count so
the enforcement cannot pass by finding nothing.

---

## R-006 — The runner backfills a remediation, making the exemption path currently unreachable

**Finding**: `charter_runtime/preflight/runner.py:245` composes the operator-facing blocked reason as

```python
f"{check.name} {check.state}; run `{check.remediation or 'spec-kitty charter status'}`"
```

When a check emits **no** remediation, the runner substitutes `spec-kitty charter status` — a status
reporter, which by construction cannot change any check's state.

**Two consequences:**

1. **This is a second, structurally identical instance of the BC-2 defect class**, sitting on the
   *default* path rather than one branch. Closing BC-2 without closing this leaves the class open,
   which C-001 forbids.
2. **The spec's US1 Acceptance Scenario 3 is currently unsatisfiable.** It requires an exempt check
   to emit no remediation — but the runner guarantees the operator is always shown one. The
   exemption set cannot be honestly implemented until this backfill is addressed.

**Decision**: the FR-003 mechanism must cover the runner's composed output, not only the values
checks return. Verifying the return value alone would pass while the operator still receives an
ineffective instruction — a gate that measures the wrong surface.

---

## Open items carried into implementation

- Per-remediation effectiveness for the three `charter synthesize` states is deliberately **not**
  adjudicated here. The FR-003 mechanism proves effectiveness empirically; hand-adjudicating it in
  plan would substitute my judgement for the gate that is the deliverable.
- Whether `charter.yaml`-missing on a legacy-bundle project is best remediated by the consolidation
  migration or by `charter generate` is an implementation question, constrained by C-004 (the
  migration is inherited, not redefined).
