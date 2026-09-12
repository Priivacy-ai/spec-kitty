"""FR-004 (#3115): the forbidden remedy is proved forbidden, not asserted.

C-009: no fix for the `#3115` CLI half may work by normalising, collapsing or
stripping whitespace from rendered output before asserting on it.
`overflow="fold"` on `sync.py`'s `Project` column stays -- it exists
deliberately (`sync.py:1430-1436`) so a project identity is never ellipsized
into a prefix the operator cannot pass to `sync purge`. At console width 80
the fold puts the REST OF THE TABLE ROW between the two uuid fragments, so no
amount of whitespace-collapsing rejoins them. "Flatten the output and the
assertion passes" is the obvious wrong fix; this file closes it with a
measurement against a committed, provenance-carrying capture, not a sentence.

The two fixtures this file reads
(``tests/cli/commands/fixtures/render_width_3115/capture_width80.txt`` /
``capture_pinned.txt``) were produced by driving `sync status` through
`typer.testing.CliRunner`, seeded exactly like
`tests/cli/commands/test_sync_status_per_project_3030.py::_seed_contaminated_store`
(WP01/WP07's own reproduction shape), under `TERM=dumb FORCE_COLOR=1`: once
with no render-surface pin at all (the failing shape) and once with
`console.size = (240, 50)` set immediately before the invocation -- the same
pin `tests/conftest.py::_plain_cli_console_seam` applies (WP02, FR-002). Each
capture's sidecar (`*.provenance.json`) records the exact reproduction
script, the commit, the environment variables in force, and the observed
`Console.size` tuple -- see `_load_capture` below, which reds if either
sidecar goes missing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "render_width_3115"

#: The project uuid the #3115 victim tests assert as a contiguous substring.
_UUID = "aaaaaaaa-0000-0000-0000-000000000001"

#: Where `capture_width80.txt` actually splits the uuid across two table
#: lines (measured once, at fixture-generation time -- see
#: `capture_width80.provenance.json`'s `reproduction_script`). Concatenating
#: the two is asserted, not assumed, by
#: `test_full_whitespace_collapse_does_not_repair_the_fold` below.
_UUID_FRAGMENT_1 = "aaaaaaaa-0000-0000-0000-000"
_UUID_FRAGMENT_2 = "000000001"

_REQUIRED_PROVENANCE_FIELDS = (
    "command",
    "commit",
    "env",
    "observed_console_size",
    "reproduction_script_status",
)


def _load_capture(directory: Path, name: str) -> str:
    """Read a committed capture, refusing one with no provenance sidecar.

    "A capture with no provenance is a recollection, and a fixture nobody can
    re-derive is the same shape as a gate that prints like a pass" (T010). A
    hand-written or truncated capture must not pass silently, so this is the
    single read path every test in this file uses -- there is no direct
    ``Path.read_text`` call anywhere else below.
    """
    capture_path = directory / name
    provenance_path = capture_path.with_suffix(".provenance.json")
    assert provenance_path.exists(), (
        f"{capture_path.name} is committed with no {provenance_path.name} "
        "sidecar. A capture with no provenance is a recollection, and a "
        "fixture nobody can re-derive is the same shape as a gate that "
        "prints like a pass (T010)."
    )
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    missing = [field for field in _REQUIRED_PROVENANCE_FIELDS if field not in provenance]
    assert not missing, (
        f"{provenance_path.name} is missing required provenance field(s) "
        f"{missing} -- a sidecar that does not name every condition and "
        "standing status it was captured under does not make the capture "
        "re-derivable."
    )
    return capture_path.read_text(encoding="utf-8")


def test_meta_assertion_bites_on_a_capture_with_no_sidecar(tmp_path: Path) -> None:
    """Non-vacuity for `_load_capture`'s own guard (standing rule: control
    your diagnostic before trusting what it says).

    Plants a capture with no sidecar and proves `_load_capture` rejects it,
    then plants one WITH a (minimal, valid) sidecar and proves that one is
    accepted -- so the assertion above is shown to discriminate, not just to
    exist.
    """
    (tmp_path / "orphan.txt").write_text("no sidecar for this one", encoding="utf-8")
    with pytest.raises(AssertionError, match="no .*\\.provenance\\.json sidecar"):
        _load_capture(tmp_path, "orphan.txt")

    (tmp_path / "accompanied.txt").write_text("has a sidecar", encoding="utf-8")
    (tmp_path / "accompanied.provenance.json").write_text(
        json.dumps(
            {
                "command": "x",
                "commit": "x",
                "env": {},
                "observed_console_size": {"width": 1, "height": 1},
                "reproduction_script_status": "active",
            }
        ),
        encoding="utf-8",
    )
    assert _load_capture(tmp_path, "accompanied.txt") == "has a sidecar"


def test_every_committed_capture_has_a_provenance_sidecar() -> None:
    """The meta-assertion applied to the REAL fixture directory: every
    committed ``*.txt`` capture under ``fixtures/render_width_3115/`` must
    carry its sidecar -- catches a future capture landing without one.
    """
    captures = sorted(_FIXTURE_DIR.glob("*.txt"))
    assert captures, (
        f"no capture files found under {_FIXTURE_DIR} -- this test would "
        "otherwise pass vacuously on an empty fixture set"
    )
    for capture_path in captures:
        _load_capture(_FIXTURE_DIR, capture_path.name)


def test_full_whitespace_collapse_does_not_repair_the_fold() -> None:
    """C-009 / FR-004, proved rather than asserted.

    "The uuid is not a substring" is satisfied just as well by a capture that
    lost the uuid entirely, which would make this test trivially -- and
    silently wrongly -- true. So this test first anchors itself IN the
    capture with three separate, individually-messaged assertions, then
    proves the forbidden remedy does not repair what it claims to.
    """
    raw = _load_capture(_FIXTURE_DIR, "capture_width80.txt")

    # --- In-file positive anchor (post-plan squad): three separate
    # assertions, each with its own message, so a failure names exactly
    # which one broke.
    assert _UUID_FRAGMENT_1 in raw, (
        f"the first uuid fragment {_UUID_FRAGMENT_1!r} is not present in "
        "capture_width80.txt -- this test's own anchor is broken, which "
        "would make the 'uuid is not a substring' assertion below trivially "
        "(and silently wrongly) true"
    )
    assert _UUID_FRAGMENT_2 in raw, (
        f"the second uuid fragment {_UUID_FRAGMENT_2!r} is not present in "
        "capture_width80.txt -- same failure mode as the first fragment, "
        "the other half of it"
    )
    assert _UUID_FRAGMENT_1 + _UUID_FRAGMENT_2 == _UUID, (
        f"the two uuid fragments concatenate to "
        f"{_UUID_FRAGMENT_1 + _UUID_FRAGMENT_2!r}, not the real project "
        f"uuid {_UUID!r} -- the fragments recorded in this file do not "
        "actually reconstruct the identifier they claim to"
    )

    # --- The forbidden remedy itself: full whitespace collapse ---
    collapsed = re.sub(r"\s+", " ", raw)
    idx1 = collapsed.index(_UUID_FRAGMENT_1)
    idx2 = collapsed.index(_UUID_FRAGMENT_2, idx1 + len(_UUID_FRAGMENT_1))
    interleaved = collapsed[idx1 + len(_UUID_FRAGMENT_1) : idx2]

    assert len(interleaved) > 0, (
        "the fold interleaved ZERO characters between the two uuid fragments "
        "after whitespace collapse -- if this is ever true, whitespace "
        "collapse WOULD rejoin the fragments, and C-009's premise no longer "
        "holds for this capture"
    )
    # `len(interleaved) > 0` alone is satisfied by PURE WHITESPACE between the
    # fragments (a single newline, or a run of spaces) -- a capture shaped
    # that way would make the "whitespace collapse doesn't repair the fold"
    # claim false: collapsing IS the repair for whitespace-only interleave.
    # This is the assertion that actually forbids the strip/collapse remedy
    # C-009 names: it requires REAL table content, not just non-zero
    # character count, sitting between the fragments.
    assert interleaved.strip(), (
        "the interleaved content between the two uuid fragments is PURE "
        f"WHITESPACE ({interleaved!r}) -- whitespace collapse would rejoin "
        "the fragments in that case, which is exactly the forbidden remedy "
        "C-009 exists to close off. Real content must survive between the "
        "fragments for 'flattening whitespace does not repair the fold' to "
        "be a true claim about this capture."
    )
    assert _UUID not in collapsed, (
        "re.sub(r'\\s+', ' ', ...) made the uuid a substring of the "
        "collapsed 80-column capture -- the forbidden remedy (C-009) "
        f"appears to work here, which it must never do. {len(interleaved)} "
        f"character(s) of the rest of the table row ({interleaved!r}) sit "
        "between the two fragments even after collapse, which is why "
        "flattening whitespace cannot rejoin them: the fold interleaves the "
        "rest of the row BETWEEN the fragments, it does not merely insert "
        "whitespace inside the identifier."
    )


def test_pinned_width_control_capture_finds_the_uuid_intact() -> None:
    """Red-first discriminator (T011): the identical substring check against
    the pinned-width CONTROL capture (same journal seed, `console.size =
    (240, 50)`) finds the uuid -- proving the assertion above discriminates
    across two captures rather than being trivially true for any capture,
    and is anchored inside the one it is really about.
    """
    pinned = _load_capture(_FIXTURE_DIR, "capture_pinned.txt")
    assert _UUID in pinned, (
        "the pinned-width control capture (console.size = (240, 50), "
        "identical journal seed to capture_width80.txt) does not contain "
        "the uuid intact -- the control itself is broken, which means the "
        "width80 capture's 'uuid not a substring' result discriminates "
        "nothing about width and proves nothing about the fold"
    )
