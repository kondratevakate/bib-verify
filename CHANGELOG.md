# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Zotero Translation Server backend adapter for one-shot canonical
  lookup of DOI/arXiv/PMID/ISBN/URL identifiers.
- RefChecker subprocess adapter when `academic-refchecker` is installed.
- Multi-format input: `.bbl`, `.tex` `\cite{}` extraction, plain-text
  bibliographies.
- Output formats: `json`, `jsonl`, `csv`.
- Upstream PRs to RefChecker with AI-pattern heuristics.

## [0.1.0] - 2026-05-18

Initial release.

### Added

- Stdlib-only Python script `verify_bib.py` (no `pip install` required).
- Resolution waterfall: DOI -> Crossref, arXiv ID -> arXiv API,
  PMID -> PubMed, title -> Crossref/OpenAlex.
- Offline heuristics for AI-generated patterns:
  - Placeholder IDs (`xxxxx`, `???`, `2210.xxxxx`).
  - `"and others"` author lists with fewer than 3 named authors.
  - `@inproceedings` with journal `booktitle` (and vice versa).
  - Missing DOI/eprint on post-2015 work.
  - `note = "preprint"` without identifier.
  - Year after LLM training cutoff with no identifier.
- Field-level classification (C/M/F/P/S/X) per Chen et al. 2026.
- Substituted-status detection for DOI-resolves-but-different-paper.
- Co-occurrence hallucination detector (3+ identity field mismatch).
- Author overlap heuristic (60% threshold for 3+ authors) per RefChecker.
- Strong-anchor rollup rule: P on title tolerated with DOI=C + author=C.
- Risk score 0-100 per entry, reports sorted by risk descending.
- Markdown and JSON report formats.
- `--strict` mode for CI / pre-commit hooks.
- Claude Code plugin packaging:
  - `bib-verify` skill with comprehensive trigger phrases.
  - `/verify-bib` slash command.
  - `PostToolUse` hook for automatic verification after `.bib` edits.
