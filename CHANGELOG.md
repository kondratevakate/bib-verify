# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `citation-auditor` agent: autonomously locates a `.bib`, runs the
  verifier, ranks findings by risk, and returns a scannable report.
  Verifies and reports only -- never rewrites the bibliography.

### Changed

- Humanized the README prose: removed AI-writing tells (inflated
  significance phrasing, mechanical bold inline-headers, decorative
  em-dashes) while keeping the technical reference intact.

### Planned

- Zotero Translation Server backend adapter for one-shot canonical
  lookup of DOI/arXiv/PMID/ISBN/URL identifiers.
- RefChecker subprocess adapter when `academic-refchecker` is installed.
- Multi-format input: `.bbl`, `.tex` `\cite{}` extraction, plain-text
  bibliographies.
- Output formats: `json`, `jsonl`, `csv`.
- Upstream PRs to RefChecker with AI-pattern heuristics.
- Persistent local cache (SQLite) to avoid re-querying between runs.

## [0.2.0] - 2026-06-02

### Added

- **Identifier-hijacking detection.** When a cited DOI resolves but to
  a different paper (`substituted`), the tool now runs a secondary
  title search: if the cited title + authors match a *different* real
  DOI (title similarity >= 0.85 AND author overlap >= 0.6), it reports
  "you likely meant DOI X, not DOI Y" and suggests the corrected
  entry. Catches the most dangerous archetype -- a working link to the
  wrong paper -- e.g. the real Barch HCP-task case where DOI `...05.041`
  resolves to the WU-Minn overview but the entry names the task-fMRI
  paper at `...05.033`. New `hijack` field on each verdict and a
  dedicated report block.
- `CITATION.cff` so GitHub renders the "Cite this repository" button
  and provides BibTeX / APA / Zotero handoffs.
- `.zenodo.json` to prepopulate Zenodo DOI metadata on release.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` for the
  GitHub Community Standards baseline.
- `paper/paper.md` and `paper/paper.bib` draft for JOSS submission,
  with "Limitations and future work" and "AI usage statement" sections.
- `examples/case-studies/dataset-review.md` with real-world audit
  results (6 hallucinations caught out of 32 entries).
- `.github/workflows/test.yml` (CI matrix) and `release.yml`
  (auto-release on `v*` tags with notes from this changelog).
- `.github/ISSUE_TEMPLATE/` structured bug-report and feature-request
  forms.
- `docs/LIMITATIONS.md`: honest accounting of database coverage gaps,
  heuristic-threshold caveats, single-source-of-truth fragility, and
  the "not_found is not fabricated" principle; plus the roadmap.
- `docs/AI_USAGE.md`: AI-provenance statement disclosing that the tool
  was built with Claude Opus 4.8 under human direction, and how every
  empirical claim was validated against ground truth.
- Enriched skill description in `SKILL.md` for broader Claude Code
  auto-triggering on user phrasings.
- README: "Real-world results", "Limitations", and "How this was
  built (AI usage)" sections; dynamic CI and release badges.

### Tests

- 5 new tests for identifier-hijacking detection (monkeypatched,
  offline-deterministic). 33 offline tests passing.

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
