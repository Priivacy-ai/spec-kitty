"""WP07: false-negative sample + re-verified broadened-predicate FP figure.

**Strictly informational -- NEVER a shipping gate (spec.md Story 4 AC4, plan.md
IC-07).** This module measures the under-firing side of C-008's Constraints-heading
scoping decision: `find_bare_prose_requirement_ids` (WP03,
`src/specify_cli/requirement_mapping.py`) reuses `_requirement_named_sections`'s
heading-scoping unmodified, and `_is_requirement_heading`'s substring match on
"requirement" does NOT match the corpus's canonical `### Constraints` heading (325 of
368 `kitty-specs/*/spec.md` files -- 88.32% -- use one). A bare-prose `C-NNN`/`NFR-NNN`
item written only under such a heading is therefore invisible to the shipped detector.

C-008's disposition (plan.md "C-008 decision", option (b)) is settled and NOT
reopened here: `_is_requirement_heading` stays byte-identical in production. This
module does not widen it, import it in a way that would let it be widened, or gate
anything on its output. It defines its OWN, entirely local broadened predicate
(`_broadened_is_requirement_heading` below) purely to measure what a hypothetical
broadened detector would newly flag -- mirroring the read-only corpus-scan method
plan.md's PLAN-GOV-002 fix pass already used and documented.

Distinct from WP08's frozen-baseline shrink-only ratchet test: this test always
passes and only records/logs its findings (via `pytest -s` output and the assertions
below, which check shape/type, never a specific count that could regress CI). It
cannot be mistaken for a blocking gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.requirement_mapping import (
    _DECLARED_ID_PATTERNS,
    _REF_FIND_PATTERN,
    _declared_ids,
    find_bare_prose_requirement_ids,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS_GLOB = "kitty-specs/*/spec.md"


def _broadened_is_requirement_heading(line: str) -> bool:
    """Local-only broadened heading predicate: "requirement" OR "constraint".

    Deliberately NOT `specify_cli.requirement_mapping._is_requirement_heading` --
    that production function is never imported, wrapped, or monkeypatched here.
    This is a standalone copy used only to measure a hypothetical broadened scope,
    per plan.md's C-008 decision (option (b): narrow production, measure and
    disclose the broadened alternative instead of shipping it).
    """
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return False
    lowered = stripped.lower()
    return "requirement" in lowered or "constraint" in lowered


def _broadened_requirement_named_sections(spec_content: str) -> list[tuple[str, str]]:
    """Mirrors `_requirement_named_sections`'s scoping, using the broadened predicate."""
    lines = spec_content.splitlines()
    heading_idxs = [i for i, line in enumerate(lines) if line.lstrip().startswith("#")]
    sections: list[tuple[str, str]] = []
    for pos, idx in enumerate(heading_idxs):
        heading_line = lines[idx]
        if not _broadened_is_requirement_heading(heading_line):
            continue
        end = heading_idxs[pos + 1] if pos + 1 < len(heading_idxs) else len(lines)
        heading_text = heading_line.lstrip("#").strip()
        sections.append((heading_text, "\n".join(lines[idx + 1 : end])))
    return sections


def _broadened_bare_prose(spec_content: str) -> list[tuple[str, list[str]]]:
    """Mirrors `find_bare_prose_requirement_ids`'s per-line algorithm (mirrors
    plan.md's "Architecture" section literally), scoped to the broadened sections
    instead of the production, narrow-heading sections.
    """
    document_declared = _declared_ids(spec_content)
    result: list[tuple[str, list[str]]] = []
    for heading_text, body in _broadened_requirement_named_sections(spec_content):
        section_ids: list[str] = []
        for line in body.splitlines():
            if any(pattern.match(line) for pattern in _DECLARED_ID_PATTERNS):
                continue
            for match in _REF_FIND_PATTERN.finditer(line):
                token = match.group(0).upper()
                if token not in document_declared and token not in section_ids:
                    section_ids.append(token)
        if section_ids:
            result.append((heading_text, section_ids))
    return result


@dataclass(frozen=True)
class _SampleFinding:
    corpus_size: int
    narrow_flagged_specs: int
    newly_flagged_specs: list[tuple[str, list[tuple[str, str]]]]


def _run_corpus_sample() -> _SampleFinding:
    specs = sorted(_REPO_ROOT.glob(_CORPUS_GLOB))
    narrow_flagged_specs = 0
    newly_flagged: list[tuple[str, list[tuple[str, str]]]] = []

    for spec_path in specs:
        content = spec_path.read_text(encoding="utf-8")

        narrow = find_bare_prose_requirement_ids(content)
        if narrow:
            narrow_flagged_specs += 1
        narrow_tokens = {(heading, token) for heading, ids in narrow for token in ids}

        broadened = _broadened_bare_prose(content)
        broadened_tokens = {(heading, token) for heading, ids in broadened for token in ids}

        new_tokens = sorted(broadened_tokens - narrow_tokens)
        if new_tokens:
            newly_flagged.append((spec_path.parent.name, new_tokens))

    return _SampleFinding(
        corpus_size=len(specs),
        narrow_flagged_specs=narrow_flagged_specs,
        newly_flagged_specs=newly_flagged,
    )


def test_false_negative_sample_and_broadened_predicate_fp_rate() -> None:
    """Informational: records the false-negative sample + re-verified broadened FP rate.

    This test ALWAYS passes -- it asserts only shape/type invariants (the scan ran,
    returned a list, corpus size is positive), never a specific count. A specific
    count moving does not fail CI; it is not a gate. See the module docstring above
    and `src/specify_cli/requirement_mapping.py`'s module docstring (WP07 section)
    for the recorded, dated figures this measurement produced.
    """
    finding = _run_corpus_sample()

    assert finding.corpus_size > 0
    assert isinstance(finding.newly_flagged_specs, list)
    assert finding.narrow_flagged_specs >= 0

    print(f"\n[WP07 false-negative sample] corpus size: {finding.corpus_size}")
    print(f"[WP07 false-negative sample] production (narrow-heading) flagged specs: {finding.narrow_flagged_specs}")
    print(
        "[WP07 false-negative sample] broadened-predicate newly-flagged specs: "
        f"{len(finding.newly_flagged_specs)}"
    )
    for spec_name, tokens in finding.newly_flagged_specs:
        print(f"  - {spec_name}: {tokens}")
