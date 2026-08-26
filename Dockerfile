# DKR-M1-02-CORE — spec-kitty CLI reproducible local image contract.
#
# Governance: HIC-BOOT-012a (out-of-fabric M1 prework).
# Build authority: HIC-M1-DOCKER-SUPPLY (docs/decisions/HIC-M1-DOCKER-SUPPLY.md)
# authorizes network for `docker build` (base-image pulls) and for
# pip/uv/npm dependency installs from PyPI/registries. The one hard
# prohibition carried forward unconditionally is: never git push/fetch/pull
# any checked-out repo. pyproject.toml additionally pins spec-kitty-events
# as a git+https://github.com direct reference (PROGRAM.md §2 wheel-install
# exception), so the builder fetches one dependency repo over git — that
# fetch is authorized by spec-kitty#144, still never touches a checked-out
# repo, and needs GitHub credentials supplied as a BuildKit secret (#144):
#
#   docker build --secret id=netrc,src=$HOME/.netrc \
#     -t dkr-m1-02-spec-kitty:contract .
#
# $HOME/.netrc must carry a github.com entry, e.g.
#   machine github.com login x-access-token password <token>
# The EXPERIMENTAL repos are private, so an anonymous fetch fails; the
# secret is mounted into the builder's RUN only (never baked into any
# layer) and requires BuildKit (default since docker 23).
#
# Base pin: python:3.12-slim-bookworm, pinned by pullable registry manifest
# digest (RepoDigest) per docs/bootstrap/DKR-M1-01-DIGEST-CORRECTION.json,
# which supersedes the CONFIG .Id originally recorded in
# DKR-M1-01-TOPOLOGY-CONTRACT.json (a different, non-pullable digest space).
# Verified on this host: `docker image inspect python:3.12-slim-bookworm
# --format '{{.RepoDigests}}'` returns exactly this digest (see HANDOFF.json
# `base_image.local_repo_digest`).
FROM python:3.12-slim-bookworm@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3 AS builder

# --- Reproducible dependency install --------------------------------------
# The project is uv-managed (uv.lock is the single source of truth for pinned
# versions/hashes; see Makefile `dev-setup` / `test` targets and run_tests.sh).
# Reproducible install: pin the uv build-tool version, then let uv install
# exactly what uv.lock names (frozen — no resolution, no upgrade).
WORKDIR /app
RUN pip install --no-cache-dir uv==0.5.13

# uv resolves the git-pinned spec-kitty-events direct reference with the git
# CLI; python:3.12-slim ships without it (#144).
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/
# hatchling force-includes packs/built-in into the wheel (public product
# doctrine only — see pyproject.toml [tool.hatch.build.targets.wheel]
# force-include comment); packs/internal is maintainer-only and deliberately
# NOT copied into the build context, so it can never end up in this image.
COPY packs/built-in/ ./packs/built-in/

# The netrc secret authenticates git's fetch of the private EXPERIMENTAL repos
# pinned above; mounted read-only for this RUN only, absent from every layer.
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    uv sync --frozen --all-extras

# --- Runtime image ----------------------------------------------------------
FROM python:3.12-slim-bookworm@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3 AS runtime

# No Docker socket, no host home, no canonical/control-state mount, no SSH
# agent, no external endpoint are declared anywhere in this image, and it
# talks to nothing outside its own filesystem. The one build-time exception
# is the builder's netrc secret above: it exists only inside that single RUN
# and is never copied into this stage — no credential reaches the runtime.
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Reproducibility evidence: freeze the exact resolved environment into the
# image itself (still root here, so the write succeeds) so `docker run --rm
# dkr-m1-02-spec-kitty:contract cat /app/dependency-manifest.txt` reproduces
# the SBOM-ish manifest without re-running uv.
RUN /app/.venv/bin/python -m pip freeze > /app/dependency-manifest.txt

# Native smoke gate: prove the installed CLI actually runs before the image
# is considered built successfully.
RUN /app/.venv/bin/spec-kitty --help > /dev/null

# Unprivileged runtime user — the product-container prohibitions forbid a
# host-home mount, and running as root inside the container is unnecessary.
# Applied last so the app tree (owned by root from the builder COPY) stays
# readable/executable for uid 10001 without needing a recursive chown.
RUN useradd --create-home --uid 10001 speckitty
USER speckitty

ENTRYPOINT ["spec-kitty"]
CMD ["--help"]
