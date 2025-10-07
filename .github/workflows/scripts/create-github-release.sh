#!/usr/bin/env bash
set -euo pipefail

# create-github-release.sh
# Create a GitHub release with all template zip files
# Usage: create-github-release.sh <version>

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <version>" >&2
  exit 1
fi

VERSION="$1"

# Remove 'v' prefix from version for release title
VERSION_NO_V=${VERSION#v}

gh release create "$VERSION" \
  .genreleases/spec-kitty-template-copilot-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-copilot-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-claude-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-claude-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-gemini-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-gemini-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-cursor-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-cursor-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-opencode-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-opencode-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-qwen-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-qwen-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-windsurf-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-windsurf-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-codex-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-codex-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-kilocode-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-kilocode-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-auggie-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-auggie-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-roo-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-roo-ps-"$VERSION".zip \
  .genreleases/spec-kitty-template-q-sh-"$VERSION".zip \
  .genreleases/spec-kitty-template-q-ps-"$VERSION".zip \
  --title "Spec Kitty Templates - $VERSION_NO_V" \
  --notes-file release_notes.md