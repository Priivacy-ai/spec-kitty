"""Per-owner exemption loader for the kernel.clock dual gate (FR-012/NFR-004).

Each ``<owner>.txt`` file in this directory lists the CURRENT, still-open
violations owned by one package-remediation work package of mission
``kernel-clock-single-door`` (WP05-WP14; ``<owner>`` matches a key of
``research/census.yaml``'s ``ownership_map``, WP-prefix stripped: ``doctrine``,
``glossary``, ``charter``, ``runtime``, ``specify_sync``,
``specify_status_merge``, ``specify_core``, ``specify_cli_agent``,
``specify_cli_rest``, ``specify_auth_compat``, ``specify_misc``, ``shared``).
Every entry was generated verbatim from this WP's own detector output (WP01b;
never hand-typed), so the recorded lines byte-match what the gate actually
flags today.

Two line shapes coexist in one file:

    IMPORT:<repo-relative path>
    CALL:<repo-relative path>:<line>

``IMPORT`` entries exempt a whole FILE from the import-ban
(``test_clock_import_ban.py`` -- FR-012(a) is file-granularity: a file either
raw-imports ``datetime`` or it doesn't, so there is nothing finer to track).
``CALL`` entries exempt one exact call SITE from the call-ban
(``test_clock_call_ban.py`` -- FR-012(b) is call-site granularity: a file can
fix one ``.now()`` call while a sibling call on another line survives, so the
ratchet must track individual lines, not whole files, or a partial fix would
either falsely stay red or silently re-exempt a still-open sibling call).

Blank lines and ``#``-prefixed comment lines are ignored. Unioned across every
``*.txt`` file in this directory (plan Sec 1.3, MAJOR-2): a remediation WP
edits only its OWN file, so parallel lanes never touch the same allow-list
file and can never merge-conflict on it. Terminal acceptance (WP15, SC-003)
is every file in this directory holding zero live entries.
"""

from __future__ import annotations

from pathlib import Path

_EXEMPTIONS_DIR = Path(__file__).resolve().parent
_IMPORT_PREFIX = "IMPORT:"
_CALL_PREFIX = "CALL:"


def _iter_exemption_lines() -> list[str]:
    lines: list[str] = []
    for path in sorted(_EXEMPTIONS_DIR.glob("*.txt")):
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
    return lines


def load_import_exemptions() -> frozenset[str]:
    """Every repo-relative path exempted from the import-ban (FR-012(a))."""
    return frozenset(
        line[len(_IMPORT_PREFIX) :] for line in _iter_exemption_lines() if line.startswith(_IMPORT_PREFIX)
    )


def load_call_exemptions() -> frozenset[tuple[str, int]]:
    """Every ``(repo-relative path, line)`` pair exempted from the call-ban (FR-012(b))."""
    exemptions: set[tuple[str, int]] = set()
    for line in _iter_exemption_lines():
        if not line.startswith(_CALL_PREFIX):
            continue
        remainder = line[len(_CALL_PREFIX) :]
        path_part, _, lineno_part = remainder.rpartition(":")
        exemptions.add((path_part, int(lineno_part)))
    return frozenset(exemptions)
