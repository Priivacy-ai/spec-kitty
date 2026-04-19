"""Evidence orchestration for charter synthesis."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path

import ruamel.yaml

from charter.evidence.code_reader import CodeReadingCollector
from charter.evidence.corpus_loader import CorpusLoader
from charter.synthesizer.evidence import CodeSignals, CorpusSnapshot, EvidenceBundle


@dataclass
class EvidenceResult:
    """Result of evidence collection — always has a bundle (may be empty)."""

    bundle: EvidenceBundle
    warnings: list[str] = field(default_factory=list)


class EvidenceOrchestrator:
    """Coordinates evidence collection from all configured sources."""

    def __init__(
        self,
        repo_root: Path,
        url_list: tuple[str, ...] = (),
        skip_code: bool = False,
        skip_corpus: bool = False,
        corpus_root: Path | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._url_list = url_list
        self._skip_code = skip_code
        self._skip_corpus = skip_corpus
        self._corpus_root = corpus_root

    def collect(self) -> EvidenceResult:
        """Run all enabled collectors with exception isolation."""
        warnings: list[str] = []
        code_signals: CodeSignals | None = None
        corpus_snapshot: CorpusSnapshot | None = None

        if not self._skip_code:
            try:
                collector = CodeReadingCollector(self._repo_root)
                code_signals = collector.collect()
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Code-reading evidence collection failed: {exc}")

        if not self._skip_corpus:
            profile_key = code_signals.stack_id if code_signals else "generic"
            try:
                loader = CorpusLoader(corpus_root=self._corpus_root)
                corpus_snapshot = loader.load(profile_key)
                if corpus_snapshot is None:
                    warnings.append(
                        f"No corpus found for profile '{profile_key}' or 'generic'; "
                        "synthesis proceeds without corpus evidence."
                    )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Corpus loading failed: {exc}")

        bundle = EvidenceBundle(
            code_signals=code_signals,
            url_list=self._url_list,
            corpus_snapshot=corpus_snapshot,
            collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        return EvidenceResult(bundle=bundle, warnings=warnings)


def load_url_list_from_config(repo_root: Path) -> tuple[str, ...]:
    """Read charter.synthesis_inputs.url_list from .kittify/config.yaml.

    Returns empty tuple if the key is absent or the file does not exist.
    """
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return ()
    yaml = ruamel.yaml.YAML()
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            config = yaml.load(fh) or {}
    except Exception:  # noqa: BLE001
        return ()
    charter_cfg = config.get("charter") or {}
    synthesis_inputs = charter_cfg.get("synthesis_inputs") or {}
    raw = synthesis_inputs.get("url_list") or []
    return tuple(u for u in raw if u and isinstance(u, str))
