import pytest
from charter.evidence.corpus_loader import CorpusLoader, CorpusLoaderError


def test_exact_match_python():
    snap = CorpusLoader().load("python")
    assert snap is not None
    assert snap.profile_key == "python"
    assert len(snap.entries) >= 3
    assert snap.snapshot_id.startswith("python-v")


def test_prefix_match():
    """python+django+pytest resolves to python corpus."""
    snap = CorpusLoader().load("python+django+pytest")
    assert snap is not None
    assert snap.profile_key == "python"


def test_generic_fallback():
    """Unknown language falls back to generic corpus."""
    snap = CorpusLoader().load("rust")
    assert snap is not None
    assert snap.profile_key == "generic"


def test_none_when_no_file(tmp_path):
    """Returns None when no matching file and no generic fallback."""
    loader = CorpusLoader(corpus_root=tmp_path)
    result = loader.load("cobol")
    assert result is None


def test_snapshot_id_recorded():
    snap = CorpusLoader().load("python")
    assert snap is not None
    assert snap.snapshot_id
    assert "v" in snap.snapshot_id


def test_javascript_corpus():
    snap = CorpusLoader().load("javascript")
    assert snap is not None
    assert snap.profile_key == "javascript"
    assert len(snap.entries) >= 2


def test_loaded_at_is_iso_utc():
    snap = CorpusLoader().load("python")
    assert snap is not None
    assert snap.loaded_at  # non-empty


def test_malformed_snapshot_id_raises(tmp_path):
    """CorpusLoaderError raised on invalid snapshot_id format."""
    bad_yaml = "schema_version: '1'\nprofile_key: test\nsnapshot_id: INVALID_FORMAT\nentries: []\n"
    (tmp_path / "test.corpus.yaml").write_text(bad_yaml)
    loader = CorpusLoader(corpus_root=tmp_path)
    with pytest.raises((CorpusLoaderError, ValueError)):
        loader.load("test")
