"""Migrate a project's charter interview ``answers.yaml`` to the canonical
governance selection-key vocabulary (FR-005, mission
``charter-authority-flip-01M14RB3`` WP03/T016).

CR-01 (``kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md`` line 163)
retires the governing-term selection key on ``charter.yaml``'s ``governance:``
section (``doctrine:`` -> ``charter:``, ``src/charter/schemas.py:209``). Some
projects' ``.kittify/charter/interview/answers.yaml`` -- a companion artifact
that historically mirrored the same nested selection shape -- may still carry
the retired key on disk. This script migrates it *in place*.

Design constraints (research.md Seam 2, tasks.md T016):

* **Token-literal-free (executable code only).** The retiring/canonical
  governing-term strings are built from numeric byte values, not literal
  source tokens, so no *executable code literal* in this module carries the
  term it migrates away from. This constraint governs code, not prose -- the
  docstrings and comments in this module (including this sentence, and the
  CR-01 cross-reference above) freely name the term for readability.
* **Scoped substitution, never a blanket replace.** Only an EXACT top-level
  YAML mapping key -- the retiring term immediately followed by ``:`` at the
  start of a line -- is renamed. A historical proper-noun mission slug such
  as ``doctrine-catfooding-2196`` embedded in a comment never matches this
  pattern (it is neither at line-start nor followed immediately by ``:``), so
  it survives untouched (occurrence_map.yaml's ``comments:doctrine-
  catfooding-2196`` exception).
* **Targeted text substitution, never a ruamel load/dump round-trip.** A
  full YAML parse->reserialize renormalizes untouched bytes (quoting,
  flow-style, comment placement) even when nothing semantically changed
  (R5, research.md risk register) -- this would fail the "changes only
  frozen target bytes" contract. The migration therefore operates on the
  raw text via a single anchored regex substitution.
* **Pre-image restore on failure.** The original bytes are read up front and
  written back verbatim if anything goes wrong before the migration
  completes, so a partial or failed migration never leaves the file in an
  inconsistent state.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

__all__ = [
    "AnswersMigrationError",
    "migrate_answers_file",
]

# Built from numeric byte values (never a literal token in this module's
# source) per the token-literal-free constraint above.
_LEGACY_TERM = bytes([100, 111, 99, 116, 114, 105, 110, 101]).decode("ascii")
_CANONICAL_TERM = bytes([99, 104, 97, 114, 116, 101, 114]).decode("ascii")

#: Matches ONLY an exact top-level ``<legacy>:`` mapping key at the start of
#: a line. Anchoring to line-start plus an immediately-following colon scopes
#: the substitution to the governance selection key alone -- a hyphenated
#: proper-noun slug embedded in prose or a comment (e.g. a historical mission
#: identifier) never starts a line with ``<legacy>:`` and is therefore never
#: touched.
_LEGACY_KEY_LINE = re.compile(rf"^{re.escape(_LEGACY_TERM)}:", re.MULTILINE)

#: Matches an exact top-level ``<canonical>:`` mapping key at the start of a
#: line -- used to detect the both-keys edge case below.
_CANONICAL_KEY_LINE = re.compile(rf"^{re.escape(_CANONICAL_TERM)}:", re.MULTILINE)


class AnswersMigrationError(RuntimeError):
    """Raised when the answers.yaml migration cannot complete safely."""


def _substitute_governance_key(text: str) -> tuple[str, int]:
    """Return ``text`` with the legacy top-level key line renamed, plus the count.

    If a canonical top-level ``<canonical>:`` key line is ALREADY present,
    the legacy key is left untouched rather than renamed: blindly renaming
    would produce two top-level ``<canonical>:`` mapping keys, which
    ``ruamel.yaml``'s safe loader rejects as a duplicate-key error. This
    mirrors ``charter.sync``'s dict-level compat shim
    (``_apply_legacy_governance_selection_key_compat`` /
    ``apply_legacy_governance_selection_key_compat``), which likewise prefers
    the canonical value and silently ignores the legacy one when both are
    present.
    """
    if _CANONICAL_KEY_LINE.search(text):
        return text, 0
    return _LEGACY_KEY_LINE.subn(f"{_CANONICAL_TERM}:", text)


def _write_bytes(path: Path, data: bytes) -> None:
    """Thin seam over the actual write so tests can inject a mid-migration failure."""
    path.write_bytes(data)


def _restore_bytes(path: Path, preimage: bytes) -> None:
    """Seam over the pre-image restore write, separate from :func:`_write_bytes`
    so a test can inject a *restore*-time failure independently of the forward
    write."""
    path.write_bytes(preimage)


def migrate_answers_file(path: Path) -> int:
    """Migrate ``path`` in place; return the number of keys renamed.

    Reads the pre-image once, computes a targeted substitution, and writes
    the result back only when at least one legacy key was found (a file
    already on the canonical key -- or with no governance-selection block at
    all -- is left byte-for-byte unchanged). On any failure the pre-image is
    restored before the exception propagates, so the file on disk is never
    left in a partially-migrated state.

    A missing/unreadable ``path`` raises :class:`AnswersMigrationError`
    (not a raw ``OSError``/``FileNotFoundError``), so direct callers of this
    function -- unlike :func:`main`, which pre-checks ``path.exists()`` and
    short-circuits before ever calling this -- get the typed error too.
    """
    try:
        preimage = path.read_bytes()
    except OSError as exc:
        raise AnswersMigrationError(f"Failed to read {path} for migration.") from exc
    try:
        text = preimage.decode("utf-8")
        new_text, count = _substitute_governance_key(text)
        if count == 0:
            return 0
        _write_bytes(path, new_text.encode("utf-8"))
        return count
    except Exception as exc:
        try:
            _restore_bytes(path, preimage)
        except OSError as restore_exc:
            raise AnswersMigrationError(
                f"Failed to migrate {path}, and restoring its pre-image also "
                f"failed ({restore_exc!r}); the file may be left in a "
                "partially-migrated state."
            ) from exc
        raise AnswersMigrationError(
            f"Failed to migrate {path}; pre-image restored byte-for-byte."
        ) from exc


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate a charter interview answers.yaml file's governance "
            "selection key to the canonical vocabulary (CR-01 companion, FR-005)."
        )
    )
    parser.add_argument(
        "answers_path",
        type=Path,
        nargs="?",
        default=Path(".kittify/charter/interview/answers.yaml"),
        help="Path to the answers.yaml file to migrate (default: %(default)s).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    answers_path: Path = args.answers_path
    if not answers_path.exists():
        sys.stdout.write(f"migrate_charter_interview_answers: {answers_path} not found; nothing to do.\n")
        return 0

    try:
        renamed = migrate_answers_file(answers_path)
    except AnswersMigrationError as exc:
        sys.stderr.write(f"migrate_charter_interview_answers: FAILED: {exc}\n")
        return 1

    if renamed:
        sys.stdout.write(
            f"migrate_charter_interview_answers: renamed {renamed} governance "
            f"selection key(s) in {answers_path}.\n"
        )
    else:
        sys.stdout.write(
            f"migrate_charter_interview_answers: {answers_path} already on the "
            "canonical key; no changes made.\n"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - module-level CLI guard
    raise SystemExit(main())
