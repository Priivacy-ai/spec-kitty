"""Canonical local input checks for privacy-preserving specification review."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
from typing import Final

from .models import DisclosureComponent, DisclosureManifest, PaidPricingDisclosure


MAX_SPEC_BYTES: Final = 256 * 1024
SCANNER_VERSION: Final = "heuristic-v2"
SCANNER_WARNING: Final = (
    "Heuristic scanner refusal reduces accidental disclosure risk but does not guarantee anonymization."
)
_TOKEN_ASSIGNMENT: Final = re.compile(r"\b(?:api[_-]?(?:key|token)|token|secret|password)\s*[:=]\s*\S+", re.IGNORECASE)
_PEM_MARKER: Final = re.compile(r"-----BEGIN (?:[A-Z ]*PRIVATE KEY|OPENSSH PRIVATE KEY)-----")
_CREDENTIAL_URL: Final = re.compile(r"https?://[^\s/@:]+:[^\s/@]+@", re.IGNORECASE)
_EMAIL: Final = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE: Final = re.compile(r"(?<!\w)(?:\+?\d[\d() -]{7,}\d)(?!\w)")
_ISO_DATE: Final = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_CORPORATE: Final = re.compile(r"\b(?:confidential|internal[-_ ]?only|corp(?:orate)?\.)\b", re.IGNORECASE)
_LONG_ENTROPY: Final = re.compile(r"[A-Za-z0-9+/=_-]{80,}")


class PreflightDiagnostic(StrEnum):
    """Safe classifications for local refusals before any external action."""

    PATH = "invalid_spec_path"
    MISSING = "missing_spec"
    SIZE = "spec_too_large"
    SENSITIVE = "sensitive_content"
    MANIFEST_DRIFT = "manifest_drift"
    CONSENT = "consent_required"


class SensitiveCategory(StrEnum):
    """Supported scanner categories, without retaining matched values."""

    TOKEN_ASSIGNMENT = "token_assignment"  # noqa: S105 - scanner category, not a credential
    PRIVATE_KEY = "private_key"
    CREDENTIAL_URL = "credential_url"
    EMAIL = "email"
    PHONE = "phone"
    CORPORATE = "corporate_marker"
    LONG_ENTROPY = "long_entropy_string"


class PreflightRefusal(ValueError):
    """A metadata-only refusal that intentionally excludes file content."""

    def __init__(
        self,
        diagnostic: PreflightDiagnostic,
        path: Path,
        *,
        sensitive_category: SensitiveCategory | None = None,
    ) -> None:
        self.diagnostic = diagnostic
        self.path = path
        self.sensitive_category = sensitive_category
        suffix = f" category={sensitive_category.value}" if sensitive_category is not None else ""
        super().__init__(f"spec review input refused: {diagnostic.value} at {path}{suffix}")


@dataclass(frozen=True)
class ScanFinding:
    """A safe scanner location: category plus 1-based line and column only."""

    category: SensitiveCategory
    line: int
    column: int


@dataclass(frozen=True)
class MissionSpecContext:
    """Resolved repository and Mission directory used to select exact `spec.md`."""

    repo_root: Path
    mission_dir: Path

    @classmethod
    def create(cls, *, repo_root: Path, mission_dir: Path) -> MissionSpecContext:
        """Resolve and contain a Mission directory within its repository root."""
        resolved_root = repo_root.resolve(strict=True)
        resolved_mission = mission_dir.resolve(strict=True)
        if not resolved_root.is_dir() or not resolved_mission.is_dir() or not _is_within(resolved_mission, resolved_root):
            raise PreflightRefusal(PreflightDiagnostic.PATH, mission_dir)
        return cls(repo_root=resolved_root, mission_dir=resolved_mission)


@dataclass(frozen=True)
class ReviewRubric:
    """Versioned exact rubric bytes, including the scanner version in metadata."""

    version: str
    serialized: bytes
    scanner_version: str

    def __post_init__(self) -> None:
        if not self.version or not self.serialized or not self.scanner_version:
            raise ValueError("invalid review rubric")

    @property
    def manifest_version(self) -> str:
        """Return the version string consent binds, including scanner revision."""
        return f"{self.version}+scanner-{self.scanner_version}"


@dataclass(frozen=True)
class ReviewResponseSchema:
    """Versioned exact response-schema bytes that are included in the prompt."""

    version: str
    serialized: bytes

    def __post_init__(self) -> None:
        if not self.version or not self.serialized:
            raise ValueError("invalid response schema")

    @property
    def manifest_component(self) -> DisclosureComponent:
        """Return the digest metadata for the exact schema bytes sent downstream."""
        return DisclosureComponent.from_bytes(self.version, self.serialized)


@dataclass(frozen=True)
class ReviewPromptTemplate:
    """Versioned prompt-template bytes included in disclosure and stdin composition."""

    version: str
    serialized: bytes

    def __post_init__(self) -> None:
        if not self.version or not self.serialized:
            raise ValueError("invalid prompt template")

    @property
    def manifest_component(self) -> DisclosureComponent:
        """Return the digest metadata for the exact template bytes sent downstream."""
        return DisclosureComponent.from_bytes(self.version, self.serialized)


@dataclass(frozen=True)
class PreflightDisclosure:
    """Disclosure metadata plus immutable local rubric/schema inputs."""

    context: MissionSpecContext
    manifest: DisclosureManifest
    rubric: ReviewRubric
    response_schema: ReviewResponseSchema
    prompt_template: ReviewPromptTemplate


@dataclass(frozen=True)
class SpecSnapshot:
    """The one immutable post-consent specification buffer for a future runner."""

    payload: bytes
    text: str
    line_count: int
    scanner_version: str


def build_disclosure(
    *,
    context: MissionSpecContext,
    transport: str,
    requested_model_route: str,
    rubric: ReviewRubric,
    response_schema: ReviewResponseSchema,
    prompt_template: ReviewPromptTemplate,
    paid_pricing: PaidPricingDisclosure | None = None,
) -> PreflightDisclosure:
    """Inspect only canonical `spec.md` and produce a consent-bound manifest."""
    path = _canonical_spec_path(context)
    payload = _read_limited_spec(path)
    _refuse_sensitive(payload, path)
    manifest = DisclosureManifest.create(
        transport=transport,
        requested_model_route=requested_model_route,
        spec_path="spec.md",
        spec=DisclosureComponent.from_bytes("spec", payload),
        rubric=DisclosureComponent.from_bytes("rubric", rubric.serialized),
        response_schema=response_schema.manifest_component,
        prompt_template=prompt_template.manifest_component,
        rubric_version=rubric.manifest_version,
        paid_pricing=paid_pricing,
    )
    return PreflightDisclosure(
        context=context,
        manifest=manifest,
        rubric=rubric,
        response_schema=response_schema,
        prompt_template=prompt_template,
    )


def confirm_and_load_spec(disclosure: PreflightDisclosure, consent_manifest_sha256: str) -> SpecSnapshot:
    """Recheck consent and every manifest component, then read one immutable buffer."""
    path = _canonical_spec_path(disclosure.context)
    if consent_manifest_sha256 != disclosure.manifest.manifest_sha256:
        raise PreflightRefusal(PreflightDiagnostic.CONSENT, path)
    if not disclosure.manifest.has_valid_digest():
        raise PreflightRefusal(PreflightDiagnostic.MANIFEST_DRIFT, path)
    payload = _read_limited_spec(path)
    _refuse_sensitive(payload, path)
    current = DisclosureManifest.create(
        transport=disclosure.manifest.transport,
        requested_model_route=disclosure.manifest.requested_model_route,
        spec_path=disclosure.manifest.spec_path,
        spec=DisclosureComponent.from_bytes("spec", payload),
        rubric=DisclosureComponent.from_bytes("rubric", disclosure.rubric.serialized),
        response_schema=disclosure.response_schema.manifest_component,
        prompt_template=disclosure.prompt_template.manifest_component,
        rubric_version=disclosure.rubric.manifest_version,
        paid_pricing=disclosure.manifest.paid_pricing,
    )
    if current.manifest_sha256 != disclosure.manifest.manifest_sha256:
        raise PreflightRefusal(PreflightDiagnostic.MANIFEST_DRIFT, path)
    text = payload.decode("utf-8")
    return SpecSnapshot(
        payload=payload,
        text=text,
        line_count=_line_count(text),
        scanner_version=disclosure.rubric.scanner_version,
    )


def scan_sensitive_markers(payload: bytes) -> tuple[ScanFinding, ...]:
    """Return heuristic marker positions only; false positives and negatives remain possible."""
    normalized = _normalize_for_scanning(payload)
    patterns = (
        (SensitiveCategory.TOKEN_ASSIGNMENT, _TOKEN_ASSIGNMENT),
        (SensitiveCategory.PRIVATE_KEY, _PEM_MARKER),
        (SensitiveCategory.CREDENTIAL_URL, _CREDENTIAL_URL),
        (SensitiveCategory.EMAIL, _EMAIL),
        (SensitiveCategory.PHONE, _PHONE),
        (SensitiveCategory.CORPORATE, _CORPORATE),
        (SensitiveCategory.LONG_ENTROPY, _LONG_ENTROPY),
    )
    findings: list[ScanFinding] = []
    for category, pattern in patterns:
        for match in pattern.finditer(normalized):
            if category is SensitiveCategory.PHONE and _ISO_DATE.fullmatch(match.group()):
                continue
            if category is SensitiveCategory.LONG_ENTROPY:
                candidate = match.group()
                if not any(char.isalpha() for char in candidate) or not any(char.isdigit() for char in candidate):
                    continue
            line, column = _line_and_column(normalized, match.start())
            findings.append(ScanFinding(category=category, line=line, column=column))
    return tuple(findings)


def _canonical_spec_path(context: MissionSpecContext) -> Path:
    candidate = context.mission_dir / "spec.md"
    if candidate.is_symlink():
        raise PreflightRefusal(PreflightDiagnostic.PATH, candidate)
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as error:
        raise PreflightRefusal(PreflightDiagnostic.MISSING, candidate) from error
    if resolved.parent != context.mission_dir or resolved.name != "spec.md" or not resolved.is_file():
        raise PreflightRefusal(PreflightDiagnostic.PATH, candidate)
    return resolved


def _read_limited_spec(path: Path) -> bytes:
    try:
        size = path.stat().st_size
    except FileNotFoundError as error:
        raise PreflightRefusal(PreflightDiagnostic.MISSING, path) from error
    if size > MAX_SPEC_BYTES:
        raise PreflightRefusal(PreflightDiagnostic.SIZE, path)
    payload = path.read_bytes()
    if len(payload) > MAX_SPEC_BYTES:
        raise PreflightRefusal(PreflightDiagnostic.SIZE, path)
    return payload


def _refuse_sensitive(payload: bytes, path: Path) -> None:
    findings = scan_sensitive_markers(payload)
    if findings:
        raise PreflightRefusal(
            PreflightDiagnostic.SENSITIVE,
            path,
            sensitive_category=findings[0].category,
        )


def _normalize_for_scanning(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace").lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


def _line_and_column(text: str, offset: int) -> tuple[int, int]:
    line_start = text.rfind("\n", 0, offset) + 1
    return text.count("\n", 0, offset) + 1, offset - line_start + 1


def _line_count(text: str) -> int:
    return max(1, len(text.splitlines()))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
