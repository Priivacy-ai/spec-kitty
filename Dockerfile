# DKR-M1-02-CORE — spec-kitty CLI reproducible local image contract.
#
# Governance: HIC-BOOT-012a (out-of-fabric M1 prework, unreceipted).
# Build policy (hard, non-negotiable): NO NETWORK. Every base image and every
# installed package must already be present on this host. Build with:
#   docker build --pull=never --network=none -t dkr-m1-02-spec-kitty:contract .
#
# Base pin: python:3.12-slim-bookworm, locally-verified image ID
#   sha256:9420c53ba876a39b83e2f08732920b62782c33d94cd04860a13c3eaf9dc1a5b0
# (see docs/bootstrap/DKR-M1-01-TOPOLOGY-CONTRACT.json; confirmed identical
# to `docker image inspect python:3.12-slim-bookworm --format '{{.Id}}'` on
# this host — see HANDOFF.json `base_image.local_image_id`).
#
# NOTE ON PIN FORM: `FROM repo@sha256:<Image-Id>` is intentionally NOT used
# here. Docker's `image@sha256:...` reference syntax resolves against the
# registry MANIFEST digest (RepoDigest), a different value from the local
# Image ID above; pinning the FROM line to the Image ID makes BuildKit treat
# it as an unresolved remote ref and attempt a registry manifest fetch (a
# real, offline-run reproduction of this: BuildKit called
# `docker.io/library/python … [auth] pull token` before failing with
# "unexpected media type … not found" — network contact this contract
# forbids, and it fails anyway since an Image ID is not a valid manifest
# digest). The tag below is pinned instead, and its local Image ID is
# verified as build evidence (HANDOFF.json), which is the offline-correct
# way to satisfy "pin the base by tag + the local digest" without forcing a
# registry round-trip.
FROM python:3.12-slim-bookworm AS builder

# --- Reproducible dependency install --------------------------------------
# The project is uv-managed (uv.lock is the single source of truth for pinned
# versions/hashes; see Makefile `dev-setup` / `test` targets and run_tests.sh).
# The canonical, reproducible install for this contract is:
#
#     pip install --no-cache-dir uv==0.5.13   # pins the uv build-tool version
#     uv sync --frozen --all-extras           # installs exactly uv.lock, no
#                                              # resolution, no network beyond
#                                              # the packages uv.lock names
#
# Both steps require fetching packages (the `uv` tool itself, and every
# dependency uv.lock names) from PyPI. Under this contract's hard no-network
# rule, NEITHER step may run unless every required artifact is already
# reachable from a local, offline source (a vendored wheelhouse mounted via
# `docker build --build-context`, or a pre-baked local package index). No such
# local supply exists on this host today (verified: the operator's uv/pip
# wheel cache holds only macOS arm64 wheels — see HANDOFF.json
# `dependency_gap` — while this image targets linux/amd64 + linux/arm64
# inside the container's glibc/Debian environment; a macOS wheel is not
# installable in a Linux container). This RUN step is left intact,
# uncommented, and unmodified from the reproducible-install contract on
# purpose: it is the actual command this image must run once real offline
# package supply exists, and its failure under --network=none is the
# authoritative, reproducible evidence of the current supply gap (see
# HANDOFF.json). Do not delete or stub it to fake a pass.
WORKDIR /app
RUN pip install --no-cache-dir uv==0.5.13

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/

RUN uv sync --frozen --all-extras

# --- Runtime image ----------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# No Docker socket, no host home, no canonical/control-state mount, no SSH
# agent, no provider credentials, no external endpoint are declared anywhere
# in this Dockerfile — the image talks to nothing outside its own filesystem.
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Unprivileged runtime user — the product-container prohibitions forbid a
# host-home mount, and running as root inside the container is unnecessary.
RUN useradd --create-home --uid 10001 speckitty
USER speckitty

# Reproducibility evidence: freeze the exact resolved environment into the
# image itself so `docker run --rm dkr-m1-02-spec-kitty:contract cat
# /app/dependency-manifest.txt` reproduces the SBOM-ish manifest without
# re-running uv.
RUN /app/.venv/bin/python -m pip freeze > /app/dependency-manifest.txt

# Native smoke gate: prove the installed CLI actually runs before the image
# is considered built successfully.
RUN /app/.venv/bin/spec-kitty --help > /dev/null

ENTRYPOINT ["spec-kitty"]
CMD ["--help"]
