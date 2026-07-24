---
title: Terminology Guard Exemption Policy
description: "Policy for the four surfaces exempted from spec-kitty terminology guards (docs/adr, docs/migration, archival docs/plans sub-areas, and the Unreleased-only CHANGELOG scan)."
doc_status: active
updated: '2026-06-30'
related: []
---

# Terminology Guard Exemption Policy

This document describes the surfaces deliberately excluded from the two active
terminology drift guards:

- `tests/contract/test_terminology_guards.py` — live-doc scan for deprecated CLI
  option names and removed command patterns
- `tests/architectural/test_no_legacy_terminology.py` — repo-wide scan for
  specific forbidden legacy terms

These exclusions are **intentional policy decisions**, not workarounds. The
rationale for each exempt surface is recorded here so future contributors can
distinguish "this surface is correctly out of scope" from "this surface was
accidentally missed."

## Background

The terminology guards enforce that active, first-party surfaces — source code,
doctrine skills, and live documentation — stay aligned with the canonical
vocabulary. They scan live surfaces only; surfaces that are historical records or
archival snapshots are deliberately out of scope.

Four categories of surfaces are currently exempt from the live-doc component of
the guards. Each is described below.

---

## Exempt Surface 1: `docs/adr/` — Immutable Architectural Decision Records

### What is excluded

All files under `docs/adr/` are excluded from:

- the live-doc scan in `_live_doc_scan_targets()` in
  `tests/contract/test_terminology_guards.py`
- the legacy-term scan `_EXCLUDED_PATH_FRAGMENTS` in
  `tests/architectural/test_no_legacy_terminology.py`

### Why it is exempt

Architectural Decision Records (ADRs) are immutable, byte-invariant snapshots by
convention (NFR-001/C-002/C-006). An ADR records the reasoning behind a decision
at a specific point in time. Once an ADR is written, its body is never modified —
even if the vocabulary it uses has since been superseded. Retroactively altering
an ADR body would corrupt the historical record and undermine the purpose of
decision documentation.

The `docs/adr/` tree was relocated from `architecture/` (which was already
outside the scan perimeter) into `docs/` during the Common Docs consolidation
(mission doc-quality-hardening). The exemption was carried over so that the
relocation did not introduce spurious guard failures on files that are
intentionally historical.

### Scope boundary

The exemption is narrow: only `docs/adr/`. All other pages under `docs/` remain
scanned. This narrowness is pinned by `test_docs_adr_exemption_is_narrow` in both
guard files, which confirms that live docs pages outside the exempt roots are
still being scanned.

---

## Exempt Surface 2: Unreleased-Only CHANGELOG Scan

### What is excluded

Both `CHANGELOG.md` (at the repository root) and `docs/changelog/CHANGELOG.md`
are scanned, but **only the unreleased section** — the portion of the file above
the first versioned heading — is checked for terminology drift. Historical version
sections are not scanned.

### Why it is exempt

A CHANGELOG is an append-at-the-top log. Each released version section records
what changed at the time of that release, using vocabulary that was canonical at
that time. Rewriting historical version sections to conform to vocabulary that
became canonical later would make the CHANGELOG historically inaccurate.

The `Unreleased` section, by contrast, describes work that has not yet shipped
and must reflect current canonical vocabulary.

### How it is implemented

The guard implements this boundary via `_extract_changelog_unreleased()`, which
returns only the content above the first `## [X.Y.Z]` heading. Both CHANGELOG
files are explicitly excluded from the `docs/**/*.md` glob and processed
separately through this extractor, ensuring only the unreleased content is
evaluated.

The `docs/changelog/index.md` index page is not a CHANGELOG file and is still
scanned as a normal live doc.

---

## Exempt Surface 3: Archived Sub-areas Under `docs/plans/`

### What is excluded

Two subdirectories under `docs/plans/` are excluded from the live-doc scan:

- `docs/plans/engineering-notes/`
- `docs/plans/initiatives/`

### Why it is exempt

These subdirectories contain archival records relocated from the previously
unscanned `architecture/` tree during the Common Docs consolidation. Their
content consists of:

- `engineering-notes/` — retained deep-dive notes from earlier development eras
- `initiatives/` — completed initiative records describing work that has already
  concluded
- `notes/` — informal engineering notes from previous development cycles

All three are archival: they document decisions, investigations, and completed
work. Their content uses vocabulary that was current at the time of writing and
is not maintained going forward. Scanning them would produce false positives that
cannot be remediated without rewriting historical context — the same reasoning
that exempts `docs/adr/`.

### Scope boundary

Only the three named subdirectories are exempt. The `docs/plans/` root and all
non-archival pages at the top level of `docs/plans/` remain live surfaces that
are fully scanned.

---

## Exempt Surface 4: `docs/migrations/` — Migration Runbooks

### What is excluded

All files under `docs/migrations/` are excluded from the live-doc scan.

### Why it is exempt

Migration runbooks must *name* the deprecated flags, commands, and workflows they
help users move away from — `--feature`, the pre-3.0 main-centric workflow, legacy
env vars, and so on. The whole purpose of a migration doc is to reference the old
vocabulary verbatim so a reader can find-and-replace it. Scanning these pages
would flag the very terms they exist to document, producing false positives that
cannot be remediated without defeating the doc's purpose. Same reasoning as
`docs/adr/`: the content legitimately carries era-correct vocabulary.

### Scope boundary

Only `docs/migrations/` is exempt. All other live `docs/` pages remain fully
scanned.

---

## Invariant: Exemptions Must Stay Narrow

Each exemption above is explicitly bounded. The guards include non-vacuity and
narrowness checks:

- `test_docs_adr_exemption_is_narrow` (in both guard files) confirms that live
  `docs/` pages outside the exempt roots are still being scanned.
- The CHANGELOG handling must remain via `_extract_changelog_unreleased()` rather
  than a raw glob that would skip the file entirely.
- `test_grep_guards_do_not_scan_historical_artifacts` confirms that no glob
  pattern in the guards directly targets any `FORBIDDEN_SCAN_ROOTS` root.

If a future change widens an exemption beyond its stated boundary — for example,
by exempting all of `docs/plans/` instead of only the three archival
subdirectories, or by treating all of `docs/` as historical — that is a
regression, not maintenance.

---

## Updating This Policy

If a new surface requires an exemption:

1. Update `FORBIDDEN_SCAN_ROOTS` in
   `tests/contract/test_terminology_guards.py`.
2. Update `_EXCLUDED_PATH_FRAGMENTS` in
   `tests/architectural/test_no_legacy_terminology.py` if the legacy-term scan
   is also affected.
3. Update this document to record the rationale and scope boundary for the new
   exemption.
4. Add or update a narrowness test that pins both the exempt surface and the
   non-exempt remainder, so a future glob change cannot silently widen the
   carve-out.
