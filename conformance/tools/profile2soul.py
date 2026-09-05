#!/usr/bin/env python3
"""Deterministic projector: ``*.agent.yaml`` (spec-kitty built-in agent
profile) -> RFC-1-conformant ``Soul.md``.

Mission: crosslayer-composition-suite-01KYJA33 (M7), WP01, FR-001.

This is, by this mission's own D1 decision, "the programme's least-principled
artifact": spec-kitty's built-in agent profiles carry no ``voice``,
``interaction``, ``locale``, or composition-list data at all -- RFC-1's
Soul.md front matter requires them structurally (see
``resolvePersonaLayer``'s strict-mode check in muster's
``src/crosslayer/composition.ts``, pinned commit
624edd6dddedb86fb89f13084510f02b5a2c7d25), so this script fabricates them
from the frozen defaults table below. C-003 (spec.md) forbids ever citing a
fabricated value as evidence for a pass/fail -- this module and its output
only ever describe *that* fabrication happens and *what* the frozen values
are, never *why one value over another is correct*, because there is no
such thing.

Determinism contract (FR-001): running this script twice against the same
source profile must produce byte-identical output. To hold that contract:

- No wall-clock timestamps anywhere in the output path.
- No unordered ``dict``/``set`` iteration in a way that could vary run to
  run (Python 3.7+ preserves insertion order for plain ``dict``, and this
  module never iterates over an actual ``set``; every field consulted from
  the parsed profile is accessed by explicit key, never by iterating the
  parsed mapping's own key order).
- The only "generated" fact recorded in the output header is a content
  hash of the *source* profile file, which is itself a pure function of
  that file's bytes -- not of when this script happens to run.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

# ---------------------------------------------------------------------------
# Frozen fabricated-defaults table (FR-001 step 2 / PROJECTION.md T003).
#
# RFC-1's Soul.md front matter (Appendix E's JSON Schema, `kind: soul`
# branch) requires a ``locale`` string; an object ``composition`` block
# (``extends``/``mixins``/``merge_policy``); a ``profiles`` list that must
# include ``"default"`` (Section 9); an object ``profile_overrides``; an
# object ``values`` block (required ``priorities``); a ``voice`` block
# with required ``formality``/``warmth``/``verbosity``/``jargon`` integers
# and a required ``formatting`` enum; an ``interaction`` block with required
# ``clarifying_questions``/``uncertainty``/``disagreement``/``confirmations``
# enums; a ``safety`` block with required ``refusal_style``/``privacy``/
# ``speculation`` enums; and an object ``extensions`` block. None of these
# exist anywhere in a spec-kitty agent profile. The values below are frozen
# and documented (never re-derived or varied per-profile) -- see
# PROJECTION.md's "Fabricated Defaults" table, which must be kept in sync
# with this table by hand if it is ever changed.
# ---------------------------------------------------------------------------

FABRICATED_LOCALE: str = "en-US"

FABRICATED_SOUL_SPEC: str = "1.0"

# Appendix E requires ``composition`` to be an *object* with these three
# keys present; ``extends``/``mixins`` are fabricated empty (this mission
# never populates persona composition), so only ``merge_policy`` needs a
# named constant.
FABRICATED_COMPOSITION_MERGE_POLICY: str = "standard"

# Section 9 requires ``profiles`` to include ``"default"``.
FABRICATED_PROFILES: tuple[str, ...] = ("default",)

FABRICATED_VOICE: dict[str, int] = {
    "formality": 50,
    "warmth": 50,
    "verbosity": 50,
    "jargon": 50,
}

# ``voice.formatting`` is a required enum string, not an integer -- kept as
# its own constant (rather than folded into FABRICATED_VOICE) so that dict
# stays homogeneously typed (dict[str, int]).
FABRICATED_VOICE_FORMATTING: str = "plain"

FABRICATED_INTERACTION: dict[str, str] = {
    "clarifying_questions": "when_ambiguous",
    "uncertainty": "explicit",
    "disagreement": "neutral",
    "confirmations": "implicit",
}

# RFC-1's ``safety`` key has no spec-kitty agent-profile equivalent at all
# (see PROJECTION.md's Fabricated Defaults table); frozen at these three
# required enum values, never populated from source data, never varied.
FABRICATED_SAFETY: dict[str, str] = {
    "refusal_style": "explain",
    "privacy": "normal",
    "speculation": "mark",
}

# Structurally-required, structurally-empty per this mission's scope: no
# spec-kitty agent profile carries persona override/extension data, so
# these two render as an empty object (``{}``), never populated, never
# varied.
FABRICATED_EMPTY_OBJECT_FIELDS: tuple[str, ...] = (
    "profile_overrides",
    "extensions",
)

# ---------------------------------------------------------------------------
# Carried fields (FR-001 step 1): mapped directly from the source profile,
# never fabricated, never listed in PROJECTION.md's Fidelity Loss table.
# ---------------------------------------------------------------------------


def _load_profile(source_path: Path) -> dict[str, Any]:
    """Parse a ``*.agent.yaml`` file using this fork's own vendored YAML
    library (``ruamel.yaml``, the same library
    ``src/doctrine/agent_profiles/repository.py`` uses), safe-mode.

    Returns the parsed mapping. Raises ``KeyError`` (via callers) if a
    field FR-001 requires is absent -- this script fails loudly rather
    than silently emitting a blank body section.
    """
    yaml = YAML(typ="safe")
    with source_path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{source_path}: expected a YAML mapping at the top level")
    return data


def _require(profile: dict[str, Any], key: str, source_path: Path) -> str:
    """Fetch a required, carried string field from the parsed profile.

    Raises ``KeyError`` with a message naming both the missing key and the
    source file, rather than defaulting silently.
    """
    if key not in profile or profile[key] is None:
        raise KeyError(f"{source_path}: required field {key!r} is missing")
    value = profile[key]
    if not isinstance(value, str):
        raise TypeError(f"{source_path}: field {key!r} must be a string, got {type(value).__name__}")
    return value


def _require_nested(profile: dict[str, Any], parent: str, child: str, source_path: Path) -> str:
    """Fetch a required, carried string field nested one level deep
    (``specialization.primary-focus`` / ``specialization.avoidance-boundary``).
    """
    parent_value = profile.get(parent)
    if not isinstance(parent_value, dict):
        raise KeyError(f"{source_path}: required section {parent!r} is missing")
    return _require(parent_value, child, source_path)


def _content_hash(source_path: Path) -> str:
    """Return a stable ``sha256:<hex>`` content hash of the source profile
    file's raw bytes. Pure function of file content -- never of wall-clock
    time -- so it is identical across repeated runs against an unchanged
    source file (the property FR-001's determinism check exercises).
    """
    # noqa justification (TID251): this is a file-integrity check over a raw
    # source-profile YAML file (drift detection), not a reimplementation of
    # ``src/charter/hasher.py``'s charter-content hashing -- that module
    # hashes normalized markdown strings with charter-specific BOM/CRLF
    # handling, a different input shape and a different package boundary
    # this standalone conformance tool should not reach into. TID251's own
    # message lists "file-integrity checks" as a legitimate non-charter
    # exemption category; this is one.
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()  # noqa: TID251
    return f"sha256:{digest}"


def _render_block(fields: dict[str, object]) -> str:
    """Render an indented ``key: value`` block, one line per entry."""
    return "\n".join(f"  {key}: {value}" for key, value in fields.items())


def _render_profiles_line() -> str:
    """Render ``profiles: ["default", ...]`` (Section 9 requires at least
    ``"default"``); quoted flow-sequence, one line, order preserved.
    """
    quoted = ", ".join(f'"{name}"' for name in FABRICATED_PROFILES)
    return f"profiles: [{quoted}]"


def _render_front_matter(profile_id: str, name: str, source_hash: str) -> str:
    """Render the RFC-1 YAML front matter block.

    Field order is fixed and hand-written (never a library ``dump()`` of an
    arbitrary mapping) specifically so output is byte-stable across ruamel
    versions and independent of any dict-ordering behavior a YAML library
    might apply internally.

    The ``generated: true`` provenance marker is a YAML *comment* (ignored
    by any YAML parser) on the first line *inside* the front-matter block --
    never a line preceding the opening ``---`` delimiter. RFC-1 Section
    3.1.1 requires the document's literal first line to be exactly ``---``;
    a leading comment before it is not tolerated by muster's front-matter
    extractor in either mode (verified directly against the shipped
    ``@garrison-hq/muster@1.1.0`` package). Placing the marker as a comment
    on the line immediately after the opening delimiter satisfies both
    Section 3.1.1 (the document still opens with a bare ``---`` line) and
    C-003's textual-audit anchor (``^#.*generated:\\s*true``, unindented so
    the anchor's own pattern still matches at column 0).
    """
    profile_overrides_field, extensions_field = FABRICATED_EMPTY_OBJECT_FIELDS
    voice_block = _render_block(dict(FABRICATED_VOICE))
    interaction_block = _render_block(dict(FABRICATED_INTERACTION))
    safety_block = _render_block(dict(FABRICATED_SAFETY))
    # Key order matches RFC-1's documented front-matter keyspace (soul_spec,
    # id, name, locale, composition, profiles, profile_overrides, values,
    # voice, interaction, safety, extensions) -- see spec.md's Overview
    # section and Appendix E's schema.
    return (
        "---\n"
        f"# generated: true, source-hash: {source_hash}\n"
        f'soul_spec: "{FABRICATED_SOUL_SPEC}"\n'
        f"id: {profile_id}\n"
        f"name: {name}\n"
        f"locale: {FABRICATED_LOCALE}\n"
        "composition:\n"
        "  extends: []\n"
        "  mixins: []\n"
        f"  merge_policy: {FABRICATED_COMPOSITION_MERGE_POLICY}\n"
        f"{_render_profiles_line()}\n"
        f"{profile_overrides_field}: {{}}\n"
        "values:\n"
        "  priorities: []\n"
        "voice:\n"
        f"{voice_block}\n"
        f"  formatting: {FABRICATED_VOICE_FORMATTING}\n"
        "interaction:\n"
        f"{interaction_block}\n"
        "safety:\n"
        f"{safety_block}\n"
        f"{extensions_field}: {{}}\n"
        "---\n"
    )


def _render_body(
    name: str,
    initialization_declaration: str,
    purpose: str,
    description: str,
    primary_focus: str,
    avoidance_boundary: str,
) -> str:
    """Render the graded body text (the only content
    ``contradiction-lint.ts`` ever scans, per ``composition.ts``'s
    ``resolvePersonaLayer`` -> ``layerTexts`` mapping).

    Every field FR-001 names as carried appears here, each under its own
    heading, so none of them is silently dropped.
    """
    return (
        f"\n# {name}\n\n"
        "## Identity Declaration\n\n"
        f"{initialization_declaration.strip()}\n\n"
        "## Purpose\n\n"
        f"{purpose.strip()}\n\n"
        "## Description\n\n"
        f"{description.strip()}\n\n"
        "## Specialization\n\n"
        "### Primary Focus\n\n"
        f"{primary_focus.strip()}\n\n"
        "### Avoidance Boundary\n\n"
        f"{avoidance_boundary.strip()}\n"
    )


def project(source_path: Path) -> str:
    """Project a single ``*.agent.yaml`` source file into a full
    ``Soul.md`` document (front matter + body), returned as one string.

    Deterministic: calling this twice with the same ``source_path`` (and
    unchanged file content) returns byte-identical strings.
    """
    profile = _load_profile(source_path)

    profile_id = _require(profile, "profile-id", source_path)
    name = _require(profile, "name", source_path)
    description = _require(profile, "description", source_path)
    purpose = _require(profile, "purpose", source_path)
    initialization_declaration = _require(profile, "initialization-declaration", source_path)
    primary_focus = _require_nested(profile, "specialization", "primary-focus", source_path)
    avoidance_boundary = _require_nested(profile, "specialization", "avoidance-boundary", source_path)

    source_hash = _content_hash(source_path)

    front_matter = _render_front_matter(profile_id, name, source_hash)
    body = _render_body(
        name=name,
        initialization_declaration=initialization_declaration,
        purpose=purpose,
        description=description,
        primary_focus=primary_focus,
        avoidance_boundary=avoidance_boundary,
    )
    return front_matter + body


def main(argv: list[str]) -> int:
    """CLI entry point: ``profile2soul.py <path-to-agent.yaml>``.

    Writes the projected ``Soul.md`` document to stdout. Returns a process
    exit code (0 on success, 2 on usage error, 1 on a malformed/incomplete
    source profile).
    """
    if len(argv) != 2:
        print(f"usage: {argv[0]} <path-to-agent.yaml>", file=sys.stderr)
        return 2

    source_path = Path(argv[1])
    if not source_path.is_file():
        print(f"error: {source_path} is not a file", file=sys.stderr)
        return 2

    try:
        output = project(source_path)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
