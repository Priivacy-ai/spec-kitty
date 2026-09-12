"""WP09 (FR-007, C-002): the canonical frontmatter boundary raises a *legible*
duplicate-key error that names every duplicated key, and pins
``allow_duplicate_keys=False`` so a future ``typ``/config change cannot silently
reintroduce YAML last-wins semantics.

The read boundary already fails closed (ruamel raises ``DuplicateKeyError``), but
the generic ``except Exception`` wrap at ``frontmatter.py`` erased the key name
behind a bare "Invalid YAML". These tests assert the key(s) survive into the
raised :class:`FrontmatterError` message, and that every duplicate is enumerated
(a single ruamel raise names only the first) via WP03's raw-text detector.
"""

from pathlib import Path

import pytest

from specify_cli.frontmatter import FrontmatterError, FrontmatterManager, read_frontmatter

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, content: str, name: str = "WP01.md") -> Path:
    file_path = tmp_path / name
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_single_duplicate_key_names_the_key(tmp_path: Path) -> None:
    """A dual-key artifact raises a FrontmatterError that NAMES the duplicate key."""
    path = _write(
        tmp_path,
        "---\ntitle: First\ntitle: Second\n---\nbody\n",
    )

    with pytest.raises(FrontmatterError) as exc_info:
        read_frontmatter(path)

    message = str(exc_info.value)
    assert "title" in message, message
    # The legible branch must not fall through to the opaque generic wrap.
    assert "Invalid YAML" not in message, message


def test_all_duplicate_keys_are_enumerated(tmp_path: Path) -> None:
    """Every duplicated key is named, not only the first ruamel would raise on."""
    path = _write(
        tmp_path,
        "---\n"
        "review_feedback: ''\n"
        "review_feedback: path/to/review.md\n"
        "status: draft\n"
        "status: final\n"
        "---\nbody\n",
    )

    with pytest.raises(FrontmatterError) as exc_info:
        read_frontmatter(path)

    message = str(exc_info.value)
    assert "review_feedback" in message, message
    assert "status" in message, message


def test_duplicate_key_message_includes_file_path(tmp_path: Path) -> None:
    """The legible error still points the reader at the offending file."""
    path = _write(
        tmp_path,
        "---\ntitle: a\ntitle: b\n---\nbody\n",
    )

    with pytest.raises(FrontmatterError) as exc_info:
        read_frontmatter(path)

    assert str(path) in str(exc_info.value)


def test_nested_duplicate_key_falls_back_to_named_error(tmp_path: Path) -> None:
    """A *nested* duplicate (not scanned by the top-level detector) still names the key.

    The raw-text detector only enumerates column-0 keys; a nested duplicate makes
    ruamel raise while the detector finds nothing, so the guard falls back to
    ruamel's own (key-naming) message rather than the opaque generic wrap.
    """
    path = _write(
        tmp_path,
        "---\nparent:\n  child: 1\n  child: 2\n---\nbody\n",
    )

    with pytest.raises(FrontmatterError) as exc_info:
        read_frontmatter(path)

    message = str(exc_info.value)
    assert "Duplicate frontmatter key" in message, message
    assert "child" in message, message
    assert "Invalid YAML" not in message, message


def test_allow_duplicate_keys_is_pinned_false() -> None:
    """Regression: the YAML() instance pins allow_duplicate_keys=False explicitly.

    A future ``typ``/config change (e.g. switching away from round-trip mode,
    whose default happens to forbid duplicates) must not silently reintroduce
    last-wins duplicate-key semantics at this canonical read boundary.
    """
    manager = FrontmatterManager()
    assert manager.yaml.allow_duplicate_keys is False


def test_non_duplicate_frontmatter_still_reads(tmp_path: Path) -> None:
    """The guard is inert on well-formed frontmatter — no false positives."""
    path = _write(
        tmp_path,
        "---\ntitle: Only once\nwork_package_id: WP01\n---\nbody\n",
    )

    frontmatter, body = read_frontmatter(path)

    assert frontmatter["title"] == "Only once"
    assert body.strip() == "body"
