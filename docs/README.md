# Documentation

This folder contains the documentation source files for Spec Kitty, built using [DocFX](https://dotnet.github.io/docfx/).

The live CLI always negotiates specs and plans interactively; expect every command to open with a discovery interview before artifacts are written.

Spec Kitty is a community-maintained fork of GitHub's [Spec Kit](https://github.com/github/spec-kit), and the documentation keeps references to the upstream project in accordance with the original license.

## Building Locally

To build the documentation locally:

1. Install DocFX:
   ```bash
   dotnet tool install -g docfx
   ```

2. Build the documentation:
   ```bash
   cd docs
   docfx docfx.json --serve
   ```

3. Open your browser to `http://localhost:8080` to view the documentation.

## Structure

- `docfx.json` - DocFX configuration file
- `index.md` - Main documentation homepage
- `toc.yml` - Table of contents configuration
- `installation.md` - Installation guide
- `quickstart.md` - Quick start guide
- `_site/` - Generated documentation output (ignored by git)

## Deployment

Documentation is automatically built and deployed to GitHub Pages when changes are pushed to the `main` branch. The workflow is defined in `.github/workflows/docs.yml`.

## Workflow Status

- [x] Docs deployment pipeline (`.github/workflows/docs.yml`) – tracked and done.
- [x] Release packaging pipeline (`.github/workflows/release.yml`) – tracked and done.
