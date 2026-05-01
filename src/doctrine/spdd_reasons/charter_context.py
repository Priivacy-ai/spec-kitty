"""SPDD/REASONS charter-context guidance renderer.

Appends the action-scoped "SPDD/REASONS Guidance" subsection to the charter
context lines list. The action scoping follows FR-009 / contracts/charter-
context.md:

| action     | canvas content surfaced                            |
|------------|----------------------------------------------------|
| specify    | Requirements, Entities                             |
| plan       | Approach, Structure                                |
| tasks      | Operations, WP boundaries                          |
| implement  | Full canvas (R, E, A, S, O, N, S)                  |
| review     | Comparison surface (R, O, N, S)                    |

Activation is decided by ``is_spdd_reasons_active(repo_root)``. This helper
itself does NOT re-check activation — the caller in ``charter.context`` owns
that gate (single source of truth, C-002).
"""

from __future__ import annotations

# Per-action bullet content. 3-6 short bullets each (FR-009).
_GUIDANCE: dict[str, list[str]] = {
    "specify": [
        "Capture Requirements (R): user-visible behaviour and acceptance signals.",
        "Capture Entities (E): nouns, identifiers, and data shapes the spec must name.",
        "Cite source quotes from the user prompt; mark gaps as [NEEDS CLARIFICATION].",
        "Defer Approach (A) and Structure (S) decisions to the plan phase.",
    ],
    "plan": [
        "Translate Requirements/Entities into Approach (A): chosen tactic and trade-offs.",
        "Document Structure (S): module/package boundaries and contract surfaces.",
        "Surface Norms (N): performance, security, reliability budgets and policy constraints.",
        "Note Safeguards (S) — guardrails and risk mitigations the plan must honour.",
    ],
    "tasks": [
        "Decompose Approach into Operations (O): ordered, owner-scoped work items.",
        "Set WP boundaries: each WP owns one slice of (A, S) and lists its Requirements refs.",
        "Cross-reference each WP back to Requirements and Entities it satisfies.",
        "Keep Operations (O) small enough that each WP can be reviewed in one sitting.",
    ],
    "implement": [
        "Honour the full canvas: Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards.",
        "Before coding, restate the WP-scoped Requirements (R) and Entities (E) in your own words.",
        "Execute Operations (O) in the order recorded; do not skip ahead silently.",
        "Capture deviations in the canvas 'Deviations' subsection — never in scattered comments.",
        "Verify Norms (N) and Safeguards (S) before marking the WP for review.",
    ],
    "review": [
        "Reviewer's comparison surface is the Requirements, Operations, Norms, Safeguards quartet (R, O, N, S).",
        "Verify Requirements (R) are met by the diff and tests.",
        "Verify Operations (O) ran end-to-end and produced expected artefacts.",
        "Verify Norms (N) — performance, type-checking, coverage, and policy budgets.",
        "Verify Safeguards (S) — guardrails honoured; flag undocumented deviations.",
    ],
}


def append_spdd_reasons_guidance(lines: list[str], mission: str, action: str) -> None:
    """Append the SPDD/REASONS Guidance subsection to *lines*.

    Idempotent and side-effect free other than appending to *lines*. Unknown
    *action* values produce a minimal advisory subsection so callers never see
    a silent no-op.
    """
    normalized = action.strip().lower()
    bullets = _GUIDANCE.get(normalized)

    lines.append("")
    lines.append(f"  SPDD/REASONS Guidance (action: {normalized}):")
    if bullets is None:
        lines.append(f"    - SPDD/REASONS pack active. No action-scoped bullets registered for action '{normalized}'.")
    else:
        for bullet in bullets:
            lines.append(f"    - {bullet}")

    canvas_path = f"kitty-specs/{mission}/reasons-canvas.md" if mission else "kitty-specs/<mission>/reasons-canvas.md"
    lines.append(f"    - Reference: {canvas_path} (when present).")
