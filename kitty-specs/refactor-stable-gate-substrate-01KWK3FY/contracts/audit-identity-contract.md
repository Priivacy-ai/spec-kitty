# Audit-Identity Contract — refactor-stable-gate-substrate-01KWK3FY

Binding rules for IC-02 (untrusted) and IC-03 (surface). The audits remain twins; the
IDENTITY MODEL is what unifies (consolidating the twins into a shared module is
explicitly out of scope — named as follow-up material in the FR-009 #2072 comment).

1. **Row identity** = `(rel_path, enclosing_qualname, token)` via
   `composite_key_from_file` — for SinkRow, ResolutionRow AND SelectionRow. The
   line-drop alternative is STRUCK (collision-proven: 7/30 + 6/27).
2. **All FOUR comparison sites convert**: untrusted `main()` Check-2; the duplicated
   compare in `test_untrusted_path_containment.py:328`; surface `main()` Check-2
   (ResolutionRow); the SelectionRow check. Leaving any raw `rel:line` compare is a
   review reject.
3. **Both directions guarded**: undercount (discovered ∖ inventory → RED) AND the NEW
   overcount (inventory ∖ discovered → RED, minus `[inventory-only]`-tagged rows; each
   tag must reference the change that removed the sink).
4. **Split-brain reconciliation (surface)**: after conversion the inventory has ONE
   identity model; `test_single_mission_surface_resolver.py` (a different family, its
   own Design-S seeds) must pass UNMODIFIED — its seed consumption reads the same
   line-locator column, which remains present.
5. **Theater triad per audit** (drift/content/ghost+undercount legs at the audit's
   entry point), plus the #2306 regression case: the exact historical failure shape
   (documented sink shifted one line) must stay green.
6. **Inventory readability**: the markdown stays reviewer-facing — human columns
   unchanged, tokens rendered compactly; the freshen path is documented in the
   inventory header.
