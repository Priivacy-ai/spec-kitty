# C-011 evidence artefact — the independent population reproduction

**This is the artefact C-011 requires: "a checked-in evidence artefact produced by the spec-phase
classifier, which is preserved and identified by path."** Until this commit no artefact satisfied it, and
SC-001's set-equality had no external anchor — the circularity C-011 exists to prevent
(*"the cheapest WP-b path is tune the predicate until it yields 40"*).

## Provenance

| | |
|---|---|
| **Authored by** | the post-spec gate's independent third lens, from the specification's predicate text alone |
| **Never compared** | against the spec author's own classifier before publication |
| **Measured at** | `upstream/main @ 5d49d31ed6505627d98d8f95d8502c9bf6a2f5ac` |
| **Tree identity** | `git diff --stat 5d49d31ed HEAD -- tests/` is **empty** — the `tests/` tree this measured is byte-identical to the one on `feat/isolated-home-pin-guard`, so the figures are checkable today without a checkout |
| **Tuning** | none. Every headline figure reproduced on the first run. |

## Contents, hash-pinned

| File | `sha256` | What it is |
|---|---|---|
| `clf.py` | `f85e19b0e73df5e2962068520c88e36edd087ec402cef8cd4db44d8687663ae3` | The instrument. AST only; binds `ast.withitem` receivers, so `pytest.MonkeyPatch.context()` sites resolve. |
| `step3.py` | `d12f224880cd731ea88c589e9d2d3083a7aa4a595ddf6b1494b3f31a974b3328` | The producer of `members.json` (imports `clf`). |
| `members.json` | `b88f0f68fa1bd252c84117b2b47e6c419239c89fb5ddf9fc35619df2edd230e9` | **The evidence.** 40 entries, `{path, qual, line, sites, fixture}`. |
| `verify.py` | `f4eae256bb93d0bfd67997a7e43729427b764da9d6bbebf663a9f7fc884ec45c` | **Not part of the provenance** — added in the post-plan remediation because the preserved scripts cannot verify the artefact (see below). Imports the sibling `clf`, re-derives, exits non-zero on mismatch. |

**All three are checked in VERBATIM.** Both scripts carry absolute paths from the session that produced
them; that is deliberate and they are **not** to be tidied. An artefact whose provenance is its
independence stops being evidence the moment the party it is meant to check edits it. Provenance beats
convenience — re-run instructions below work around the hardcoded paths rather than removing them.

## Reproduction — use `verify.py`

```bash
cd /home/jeroennouws/dev/sk-missions/3121
timeout 600 python3 kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/research/\
spec_kitty_home_pin_evidence/verify.py     # prints "C-011 OK: 40 members ..." and exits 0
```

**Do not run `step3.py` to verify.** It is preserved verbatim, and verbatim means it still inserts the
ephemeral session scratchpad on `sys.path` (`:2`) and writes `members.json` **there** (`:60`) — so on this
machine it imports a scratchpad copy of `clf` and rewrites a temp file, and on any other machine it raises
`FileNotFoundError`. The plan phase's claim that *"re-running `step3.py` rewrites `members.json`
byte-for-byte identically"* was **true of a temp file and vacuous with respect to the artefact C-011
designates**; it is withdrawn. `verify.py` is the working counterpart and is what makes C-011 re-derivable
by a reviewer, which is C-011's entire value.

`clf.py`'s `ROOT` is hardcoded to `/home/jeroennouws/dev/sk-missions/3121`, so re-derivation is anchored to
this checkout; `verify.py` reports a diagnosable mismatch rather than a stack trace if the tree moves. Pure
stdlib — no venv, no `uv`.

## What it independently confirms

Every figure below came out of this instrument, not out of the specification:

| Figure | Value |
|---|---|
| Effect-class sites / files | **40 / 36** |
| Members, scope-chain attribution | **40** in **36** files |
| Members with more than one site | **0** |
| Kind split at the keyed def | **30 fixture / 10 test-body / 0 helper** |
| Members, innermost attribution | **39** |
| Symmetric difference, scope-chain vs innermost | exactly `tests/sync/tracker/test_tracker_egress_refusal_3108.py:1165` |
| Members under the superseded decorator-limbed predicate | **30** |

The last two rows are the arithmetic that settles FR-001's justification: the decorator limb excluded
**40 − 30 = 10** sites, and the silhouette limb under the scope-chain rule FR-001 binds excluded **0** —
not the "9 against 1" FR-001 published, which are the innermost-attribution figures C-004 refuses. Fixed in
the same commit that landed this artefact.

## How SC-001 and SC-003 consume it

`members.json` carries `(path, qual, line, sites)`, not `composite_key`. **The identification of which 40
sites are members is external — it comes from this artefact.** The key *encoding* is then derived by the
repository's canonical primitive, `composite_key_from_file(path, lineno)` from
`tests/architectural/_ratchet_keys.py`, applied to each site in `sites`.

That derivation is **not** circular: it is a pure function of `(file, lineno)` supplied by the repo, not by
R1a's classifier. The anchor — *which* sites — never passes through the instrument under test. One source
of truth is kept by deriving at test time rather than checking in a second, normalised copy.

> **Read this before deriving keys.** The bare `composite_key` is **not** unique across the 40 members —
> measured, it yields only **19** distinct values, one of them shared by **11** members. See the plan's
> BLOCKER-1. The key must be path-qualified, which is also what the sole-door idiom C-012 names already
> does (`ConstructionSite(rel_path, qualname, token, …)`, `_sole_door_scan.py:524-529`).
