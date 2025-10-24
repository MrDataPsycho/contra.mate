# Documentation Setup

This directory contains the MkDocs documentation for Contramate.

## Setup

Install documentation dependencies:

```bash
# Install docs dependency group
uv sync --group docs
```

## Local Development

Serve the documentation locally:

```bash
# Start live preview server
uv run mkdocs serve
```

Then visit http://127.0.0.1:8000 in your browser.

## Build

Build the static site:

```bash
uv run mkdocs build
```

The built site will be in the `site/` directory.

## Deployment

Documentation is automatically deployed to GitHub Pages when changes are pushed to the `main` branch.

The GitHub Actions workflow is configured in `.github/workflows/docs.yml`.

## Writing Documentation

Add your markdown files to this `docs/` directory and reference them in `mkdocs.yml`.

Example structure:
```
docs/
  index.md           # Home page
  getting-started/
    installation.md
  components/
    agents.md
```

## Resources

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [mkdocstrings](https://mkdocstrings.github.io/)
