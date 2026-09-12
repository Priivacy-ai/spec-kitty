# DM — FR-016 wins over the hosted no-op note

**Status:** decided by the operator, 2026-08-04
**Raised by:** WP05's implementer, during the hosted-gate swap
**Touches:** `tracker/egress_verdict.py::_channel1_decided_message`, WP03's approved tests

## The conflict

Two approved requirements demanded opposite things for the hosted refusal message, and both
could not hold.

**FR-016** (spec, High): *"The Channel-1 half of the verdict must produce **byte-identical**
refusal text to today's for the three measured outcomes (absence → refused; recorded `false` →
refused; recorded `true` → gate passes to the token check), including the `root=None` case…
A Mission that closes the local gap while perturbing the shipped hosted gate has traded one leak
for another."*

**WP03 review round 1, MEDIUM-2** (a reviewer finding, encoded in three approved tests): the
hosted message must name Channel 1 and carry a no-op note, with *prospective* wording
("would not apply") when Channel 2 is absent and *recorded* wording when a grant exists.

WP05 measured the divergence and reported it rather than accepting the aspiration or quietly
matching the tests. That was the right call — the conflict is real, not an implementation slip.

## Decision

**FR-016 wins.** The hosted Channel-1 refusal is `project_egress_refusal`'s own string, verbatim,
with no recomposition and no added note.

The deciding ground is FR-016's own rationale. `#3030` already shipped that gate; changing its
operator-visible text is a perturbation of shipped behaviour, and this mission's subject is the
*local* gap. The three outcomes FR-016 names are all Channel-2-**absent**, which is precisely the
set that was diverging.

## What MEDIUM-2 was actually complaining about, and why it stays fixed

Its defect was that the absent case asserted a **recorded** grant the operator does not have.
Passing the shipped text through fixes that more cleanly than the prospective note did: the
absent case now says nothing at all about a key that is not there. A genuinely recorded grant
still gets `_HOSTED_GRANT_NOTE_RECORDED`, because that cell is **not** one of FR-016's three
measured outcomes and FR-005 requires the operator be told their key is a no-op. The two messages
remain plainly distinct, and neither asserts an untruth.

## Measured

Pre-tree pinned at `bb2020fea` calling `project_egress_refusal`; post-tree the working tree
calling the verdict at `HOSTED_SERVICE`. Root paths normalised, hashes compared.

| case | verdict |
|---|---|
| Channel-1 absence | **IDENTICAL** |
| recorded `sync.enabled: false` | **IDENTICAL** |
| not consentable | **IDENTICAL** |
| `root=None` (`UNDETERMINED_PROJECT_REFUSAL`) | **IDENTICAL** |
| one-sided corrupted control | **DIFFERS** ← the comparison discriminates |

The control matters: a first attempt corrupted the string on *both* sides, so it reported
IDENTICAL and proved nothing. It was rebuilt one-sided before any conclusion was drawn.

## Accepted costs

1. **All three hosted Channel-1 states share one message**, because `#3030`'s shipped string is
   itself undifferentiated. The `channel1_state` **field** still distinguishes `no_record` /
   `recorded_refusal` / `not_consentable`, so `sync doctor` (WP06) can render the distinction —
   it is only the free-text message that is uniform, exactly as shipped.
2. **The hosted message does not contain the literal `"Channel 1"`.** That string predates this
   mission's channel vocabulary. WP01 anticipated this: its hosted cells assert
   `"Channel 1" in msg or "has not consented to hosted sync" in msg`.
3. **`LOCAL_SUBPROCESS` is unaffected** and keeps three distinct messages — it is a new gate with
   no shipped text to preserve, and WP01 pins its state tokens literally.
4. **The hosted raise site renders `message` alone, so the verdict's `remedies` are not shown
   there.** Nothing may be appended without breaking byte-identity. Measured at
   `HOSTED_SERVICE`: `no_record` carries 2 remedies and renders 0; `recorded_refusal` and
   `not_consentable` carry 1 each and render 0. The load-bearing loss is
   `not_consentable`'s — it tells an identity-less checkout to run `spec-kitty init` first,
   whereas the shipped text sends the operator to `spec-kitty sync opt-in`, which FR-012
   records as *not working* in that state. Shipped behaviour is unchanged (the operator sees
   exactly what `#3030` showed them), and the remedies resurface in `sync doctor`'s renderer
   (FR-014, WP06), which reads the same verdict and is not bound by FR-016. Recorded in
   `tracker_egress_verdict`'s docstring as an explicit FR-016 carve-out, because the
   consumption contract there previously said the hosted path carries an in-message note —
   true before this decision, false after it.

## Follow-on repairs this decision required

- **`tests/architectural/test_egress_consent_boundary.py`** — the `_EGRESS_ALLOWLIST` entry E2
  for `saas_client.py` named `seam_symbol="project_egress_refusal"`, which the swap removed
  from that file. The guard reddened correctly: *"the file is still permitted to transmit while
  the thing that made that safe has been removed."* Re-pointed to `tracker_egress_verdict` with
  a note recording that the exemption is now strictly safer — Channel 1 still decides, and a
  Channel-2 grant is a no-op at this destination. Found by WP05's reviewer, not by WP05, which
  reported one cross-WP artifact (the call-site inventory) and missed this one; T031's
  blast-radius table omits `tests/architectural/`, so the contract shares the gap.
- **A literal-bytes pin** was added alongside the passthrough pin. `verdict.message ==
  project_egress_refusal(root)` proves passthrough but moves with the function if it is ever
  reworded; no literal pin on this text existed anywhere in the tree, so the byte-identity
  claim was stronger than its evidence.

## Files changed by this decision

- `src/specify_cli/tracker/egress_verdict.py` — `_channel1_decided_message` gains
  `channel1_refusal_text` and returns it verbatim for hosted + Channel-2-absent.
- `tests/sync/tracker/test_tracker_egress_verdict_3108.py` — three pins updated: the
  byte-identity assertion replaces the prospective-note pin, the recorded-grant note keeps its
  own pin, and the `"Channel 1"` vocabulary pin is scoped to `LOCAL_SUBPROCESS` with the hosted
  disjunction spelled out.

Both are WP03's approved files, amended by the mission owner because WP05 could not reach them
and correctly did not try.
