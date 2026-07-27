# Adversarial Review Log — Org-Charter Activations Runtime Wiring

Squad cadence at every planning point-cut (pre-spec, post-spec, post-tasks). Model discipline applied (opus for design/sizing/anti-laziness judgment; sonnet for grounded code-truth + Sonar census). All lenses profile-loaded, read-only, isolated in the clone.

## Round 1 — Pre-spec grounding (2 × sonnet)

- **Code-truth**: gap CONFIRMED on HEAD `71b2787e8` — `OrgCharterPolicy.activations` folded then orphaned. Fix shape = resolve-time union mirroring `_read_org_required_selections`/`_load_doctrine_selection`; shared identity key; validate-don't-drop. Layering: `charter` can't import `specify_cli.doctrine.org_charter` (ADR 2026-03-27-1).
- **Tracker**: no duplicate/blocker; #1799 correct parent; #2196/#2216 ruled out. Origin lineage: propagation was IN-SCOPE (origin requirement 008) but DROPPED cross-WP. Third recurrence of the class (#1465/#1242/#2365) → regression invariant warranted.

## Round 2 — Post-spec (2 × opus) → spec rev 2

- **alphonso (design)** — SOUND-WITH-CORRECTIONS. Findings folded:
  1. **`--json` arrays are DRG-fed, activation-blind** — activations surface only in the TEXT stanza. → C-004 scope fence; SC-001 asserts `.text`.
  2. **Compact mode renders no activations** — bootstrap-only. → regression test forces bootstrap.
  3. **FR-004 raise swallowed by `_render_activation_block`'s `except`** — must sit pre-`try`.
  4. Drop `_fold_policies` byte-parity claim → first-seen union.
  5–6. Layering move CONFIRMED clean (org_charter already imports `charter.activations`).
- **paula (sizing)** — UNDERSIZED ~1.5–2× on the unresolved surface question → resolved to text-stanza (option a, 1 WP). Named the fakeable red-first seams (`render_activation_stanza`/`resolve_for_context`) → NFR-001 forbidden-entry-points. Flagged the accreting third rescan copy → FR-006.

## Round 3 — Post-tasks (opus anti-laziness + sonnet Sonar census) → WP01 rev 2 (10 subtasks)

- **reviewer-renata (anti-laziness)** — WP NEEDS-TIGHTENING. Owned-files verified COMPLETE. Blocking folds:
  1. **T004 safety-net claim FALSE** — the org-union branch of `_load_doctrine_selection` (`context.py:795-813`) has ZERO existing coverage (`test_org_charter_union.py` covers a different function). → new T003 characterization test, authored first, gates the extraction.
  2. **FR-004 double-swallow** — `_load_governance_activations` has its own `except: return []` (`:2652`); org read must be a SEPARATE call → T007.
  3. **SC-001 short-circuit** — `if not activations: return ""` (`:2680`) early-returns on org-only case; union must precede it → T007.
  4. **T001 harness wrong** — `_write_org_pack` writes an agent-profile pack (no activations); `_governance_text`/`advise` = compact (no stanza). → T001 reuses only `_write_config`, writes real `org-charter.yaml`, forces bootstrap.
  5. **Red-first must be RECORDED** → T001/T002.
  6. Runtime import gap — `ActivationEntry` is `TYPE_CHECKING`-only in context.py.
- **Sonar census (sonnet)** — folds:
  7. **T005 extraction is REQUIRED** — `_read_org_required_selections` is ~19–20 Sonar cognitive-complexity today (over the 15 ceiling; ruff-green, Sonar-red — the metrics diverge on 4-level nesting). Extraction fixes it as a side effect; don't bolt a parallel copy.
  8. **Campsite (SAFE)** — `_enumerate_org_pack_paths`'s silent `except: return []` (`:693`) → add `_LOGGER.debug`.

## OUT — tracked home (follow-up ticket, NOT folded)

- Cross-module `"org-charter.yaml"` literal spread (7 files: `pack_assembler.py`, `org_charter_loader.py`, `pack_validator.py`, `doctrine.py`, `_doctrine_collect.py`, + the two edited) — broader consolidation, out of this WP's blast radius.
- `f"required_{kind}"` S1192 (≥3× in `org_charter.py`, different section than the identity-key edit).
- **Deferred enhancements** (spec Deferred Items, file under #1799 at close): structured `activations` key in `charter context --json`; compact-mode activation rendering. Both affect project + org equally.

_To file at mission close: one follow-up issue for the two OUT Sonar items + one for the deferred JSON/compact enhancements (referenced in the #2365 close comment)._
