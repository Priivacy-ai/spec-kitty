"""C-011 (ATDD-First Discipline) pin for WP03's SOP-extract drift gate (FR-007).

Mission crosslayer-composition-suite-01KYJA33, WP03. The operator ruled
C-011 (charter.md:504) binding over charter.yaml's ``tdd_required: false``,
which requires a failing-first test pinning each WP's user-observable
behavior. WP03 originally shipped with no test of its own; this file is a
DOCUMENTED ONE-TIME DEVIATION from strict red-before-green ordering — the
gate script (``conformance/scripts/check-sop-extract-drift.sh``) and the
committed extract (``conformance/crosslayer/sop-extract.md``) already
existed and were merged before this test was authored, so the true
red-first commit ordering cannot be reconstructed retroactively. See the
WP03 work-log Activity Log entry for the red/green demonstration performed
against a throwaway clone of the pre-implementation commit.

What this pins (the gate's OBSERVABLE behavior, not its internals):

- a clean tree (on-disk extract matches a fresh re-extraction of AGENTS.md)
  exits 0;
- a mutated ``sop-extract.md`` exits 1, AND the mutation is still present on
  disk afterward (the shipped defect this design specifically avoids: the
  naive in-place ``mktemp`` overwrite-then-diff variant would exit 0 on
  genuine drift and destroy the mutation — see the WP03 review record);
- a mutated ``AGENTS.md`` (the shared, read-only source) also exits 1
  (drift is detected from either side of the comparison);
- the default (no-argument) invocation never writes ``sop-extract.md``,
  even when there is drift to report;
- ``--write`` regenerates ``sop-extract.md`` in place from AGENTS.md and
  leaves a subsequent default invocation clean (exit 0) — the supported
  remedy for a legitimate AGENTS.md policy edit (WP03 Fix 2).

Everything runs against a SANDBOXED COPY of the real script/AGENTS.md/
sop-extract.md content built fresh per test (see ``_build_sandbox``) —
never against the live repository checkout. The script resolves its own
REPO_ROOT from ``${BASH_SOURCE[0]}``'s location, so copying it (plus the
two files it reads/writes) into a ``tmp_path`` sandbox that mirrors the
real relative layout (``conformance/scripts/...`` next to
``conformance/crosslayer/...`` and a sibling ``AGENTS.md``) is sufficient
to exercise it in full isolation; the real ``AGENTS.md`` and
``conformance/crosslayer/sop-extract.md`` in this checkout are never
touched by this test file.
"""

from __future__ import annotations

import hashlib
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tests.utils import REPO_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_SCRIPT = REPO_ROOT / "conformance" / "scripts" / "check-sop-extract-drift.sh"
_AGENTS_MD = REPO_ROOT / "AGENTS.md"
_EXTRACT = REPO_ROOT / "conformance" / "crosslayer" / "sop-extract.md"


def _build_sandbox(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Copy the real script + its two inputs into an isolated sandbox.

    Returns (script_path, agents_md_path, extract_path) inside the sandbox,
    laid out at the same relative positions the real script expects
    (``conformance/scripts/check-sop-extract-drift.sh`` two levels below a
    repo root that also holds ``AGENTS.md`` and
    ``conformance/crosslayer/sop-extract.md``).
    """
    scripts_dir = tmp_path / "conformance" / "scripts"
    crosslayer_dir = tmp_path / "conformance" / "crosslayer"
    scripts_dir.mkdir(parents=True)
    crosslayer_dir.mkdir(parents=True)

    script_path = scripts_dir / "check-sop-extract-drift.sh"
    agents_path = tmp_path / "AGENTS.md"
    extract_path = crosslayer_dir / "sop-extract.md"

    script_path.write_text(_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    agents_path.write_text(_AGENTS_MD.read_text(encoding="utf-8"), encoding="utf-8")
    extract_path.write_text(_EXTRACT.read_text(encoding="utf-8"), encoding="utf-8")

    return script_path, agents_path, extract_path


def _run(script_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script_path), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_clean_sandbox_exits_zero_twice(tmp_path: Path) -> None:
    """A clean sandbox (extract matches a fresh re-extraction) exits 0, repeatably."""
    script_path, _agents_path, _extract_path = _build_sandbox(tmp_path)

    first = _run(script_path)
    second = _run(script_path)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr


def test_mutated_extract_exits_one_and_mutation_survives(tmp_path: Path) -> None:
    """A hand-edited sop-extract.md is detected as drift, and is NOT clobbered.

    Pins the exact defect the shipped mktemp + `git diff --no-index` design
    avoids: an overwrite-then-diff variant would regenerate the extract
    in place before comparing, silently erasing the mutation while still
    reporting drift-free. Here the mutation must still be readable on disk
    after the script exits 1.
    """
    script_path, _agents_path, extract_path = _build_sandbox(tmp_path)

    original = extract_path.read_text(encoding="utf-8")
    mutated = original.replace(
        "SOP policy extract (FR-007, OQ-6 option (b)).",
        "SOP policy extract (FR-007, OQ-6 option (b)). MUTATED-BY-TEST",
        1,
    )
    assert mutated != original, "fixture sop-extract.md did not contain the expected anchor text"
    extract_path.write_text(mutated, encoding="utf-8")

    result = _run(script_path)

    assert result.returncode == 1, result.stderr
    assert extract_path.read_text(encoding="utf-8") == mutated, (
        "the drift gate must not overwrite the on-disk extract while merely "
        "checking for drift — the mutation must survive the run"
    )


def test_mutated_agents_md_exits_one(tmp_path: Path) -> None:
    """A hand-edited AGENTS.md (source drift) is also detected."""
    script_path, agents_path, _extract_path = _build_sandbox(tmp_path)

    original = agents_path.read_text(encoding="utf-8")
    mutated = original.replace(
        "Direct pushes are prohibited.",
        "Direct pushes are prohibited (MUTATED-BY-TEST).",
        1,
    )
    assert mutated != original, "fixture AGENTS.md did not contain the expected anchor text"
    agents_path.write_text(mutated, encoding="utf-8")

    result = _run(script_path)

    assert result.returncode == 1, result.stderr


def test_default_invocation_never_writes_extract_even_with_drift(tmp_path: Path) -> None:
    """The default (no-argument) call stays read-only, even when it reports drift.

    WP04's CI call site depends on this: --write must never become reachable
    during a normal (argument-less) invocation.
    """
    script_path, _agents_path, extract_path = _build_sandbox(tmp_path)

    mutated = extract_path.read_text(encoding="utf-8") + "\nMUTATED-BY-TEST\n"
    extract_path.write_text(mutated, encoding="utf-8")

    result = _run(script_path)

    assert result.returncode == 1, result.stderr
    assert extract_path.read_text(encoding="utf-8") == mutated, (
        "default invocation must never write conformance/crosslayer/sop-extract.md"
    )


def test_write_flag_regenerates_and_default_is_then_clean(tmp_path: Path) -> None:
    """--write repairs drift in place; a subsequent default call then exits 0.

    Also pins the on-disk file MODE across a successful --write (MEDIUM-1):
    the committed extract is tracked at git mode 100644, but the --write
    remedy builds its replacement via `mktemp` (which creates files 0600)
    and then `mv`s it over the destination. `mv`'s cross-device fallback
    (and, as it turns out, even a same-filesystem `rename(2)`, since the
    destination directory entry then simply points at the mktemp-created
    inode) carries that 0600 mode onto the destination, silently regressing
    every real `sop-extract.md` from 644 to 600 on every successful --write
    despite `git status` reporting a clean tree throughout (git tracks only
    the executable bit, never the full mode). A 600 extract cannot be read
    by a different uid/container mount when this extract is composed into a
    context window alongside a persona and a skill.
    """
    script_path, _agents_path, extract_path = _build_sandbox(tmp_path)

    # Force a known starting mode matching the real repo's git-tracked 644,
    # regardless of what umask produced when the sandbox file was written.
    extract_path.chmod(0o644)
    mode_before = stat.S_IMODE(extract_path.stat().st_mode)
    assert mode_before == 0o644

    mutated = extract_path.read_text(encoding="utf-8").replace(
        "## Branch Protection and CI",
        "## Branch Protection and CI MUTATED-BY-TEST",
        1,
    )
    extract_path.write_text(mutated, encoding="utf-8")
    extract_path.chmod(0o644)
    assert _run(script_path).returncode == 1, "fixture setup: mutation should have been detected as drift"

    write_result = _run(script_path, "--write")
    assert write_result.returncode == 0, write_result.stderr
    assert extract_path.read_text(encoding="utf-8") != mutated, (
        "--write must actually overwrite the mutated extract"
    )
    mode_after = stat.S_IMODE(extract_path.stat().st_mode)
    assert mode_after == 0o644, (
        f"--write must preserve the extract's mode (expected 0o644, got {oct(mode_after)}) — "
        "mktemp creates its scratch file 0600, and mv must not let that carry onto the "
        "committed destination"
    )

    default_after_write = _run(script_path)
    assert default_after_write.returncode == 0, default_after_write.stderr


def test_unknown_argument_is_rejected(tmp_path: Path) -> None:
    """An unrecognized argument fails loudly instead of silently no-oping.

    Pins both the exit code AND the stderr text: asserting returncode == 1
    alone would also be satisfied by an unrelated exit-1 cause (e.g. a
    missing file, or a heading-not-found error), which would silently stop
    testing the thing this test claims to test.
    """
    script_path, _agents_path, _extract_path = _build_sandbox(tmp_path)

    result = _run(script_path, "--bogus")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "unknown argument" in result.stderr, result.stdout + result.stderr


def _sha256(path: Path) -> str:
    # File-integrity check (before/after AGENTS.md hash comparison), not a
    # charter hash-content use — TID251 explicitly exempts this case.
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251


def test_write_never_modifies_agents_md(tmp_path: Path) -> None:
    """--write regenerates the extract but must never touch AGENTS.md.

    The script's own header comment asserts this twice ("AGENTS.md itself is
    a shared, read-only input; neither this extract nor its drift check
    ever modifies it" / "AGENTS.md itself is never written by this script —
    only read"), but nothing pinned it before this test. Runs --write
    against a sandbox where the extract is drifted (so --write has real
    work to do) and hashes AGENTS.md before and after.
    """
    script_path, agents_path, extract_path = _build_sandbox(tmp_path)

    mutated = extract_path.read_text(encoding="utf-8") + "\nMUTATED-BY-TEST\n"
    extract_path.write_text(mutated, encoding="utf-8")

    agents_hash_before = _sha256(agents_path)
    agents_text_before = agents_path.read_text(encoding="utf-8")

    write_result = _run(script_path, "--write")
    assert write_result.returncode == 0, write_result.stderr

    assert _sha256(agents_path) == agents_hash_before, (
        "check-sop-extract-drift --write must never write conformance/../AGENTS.md "
        "(the shared, read-only source) — only conformance/crosslayer/sop-extract.md"
    )
    assert agents_path.read_text(encoding="utf-8") == agents_text_before


def test_write_on_renamed_heading_fails_and_extract_is_untouched(tmp_path: Path) -> None:
    """A renamed pinned heading must make --write fail, not emit an empty section.

    Regression pin for the MEDIUM defect introduced alongside --write:
    extract_section() used to print nothing when its heading never matched
    a line in AGENTS.md (a renamed heading, for instance), and `regenerate`
    would emit an empty section without complaint — so --write "succeeded"
    (exit 0) while silently deleting the section from the committed
    sop-extract.md, and a subsequent default (no-argument) check would then
    report clean. The fix makes extract_section fail loudly (non-zero, a
    message naming the missing heading) instead. This test renames one of
    the two pinned headings in the sandbox copy of AGENTS.md and asserts
    --write now errors out, and — just as importantly — that the committed
    extract file is completely untouched by the failed attempt (not
    truncated, not partially rewritten, not emptied).
    """
    script_path, agents_path, extract_path = _build_sandbox(tmp_path)

    original_agents = agents_path.read_text(encoding="utf-8")
    renamed = original_agents.replace(
        "## Branch Protection and CI",
        "## Branch Protection and CI Policy",
        1,
    )
    assert renamed != original_agents, (
        "fixture AGENTS.md did not contain the expected pinned heading "
        "'## Branch Protection and CI'"
    )
    agents_path.write_text(renamed, encoding="utf-8")

    extract_hash_before = _sha256(extract_path)
    extract_text_before = extract_path.read_text(encoding="utf-8")

    write_result = _run(script_path, "--write")

    assert write_result.returncode != 0, (
        "--write must fail when a pinned heading is missing from AGENTS.md, "
        "not silently regenerate an empty section and exit 0"
    )
    assert "heading not found" in write_result.stderr, write_result.stdout + write_result.stderr
    assert "Branch Protection and CI" in write_result.stderr, (
        write_result.stdout + write_result.stderr
    )
    assert _sha256(extract_path) == extract_hash_before, (
        "a failed --write must leave the committed sop-extract.md completely "
        "untouched, not half-overwritten or emptied"
    )
    assert extract_path.read_text(encoding="utf-8") == extract_text_before

    # The default (no-argument) check must also fail closed on the same
    # renamed heading — not just --write.
    default_result = _run(script_path)
    assert default_result.returncode != 0, default_result.stdout + default_result.stderr
    assert "heading not found" in default_result.stderr, (
        default_result.stdout + default_result.stderr
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
