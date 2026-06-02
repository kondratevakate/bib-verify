# bib-verify

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)](https://docs.anthropic.com/claude-code)
[![Tests](https://github.com/kondratevakate/bib-verify/actions/workflows/test.yml/badge.svg)](https://github.com/kondratevakate/bib-verify/actions/workflows/test.yml)
[![GitHub release](https://img.shields.io/github/v/release/kondratevakate/bib-verify?include_prereleases&label=release)](https://github.com/kondratevakate/bib-verify/releases)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20511185.svg)](https://doi.org/10.5281/zenodo.20511185)
[![GitHub stars](https://img.shields.io/github/stars/kondratevakate/bib-verify?style=social)](https://github.com/kondratevakate/bib-verify)

> Catch hallucinated and AI-generated citations in your BibTeX files
> before a reviewer does.

A Claude Code plugin that verifies every `.bib` entry against real
academic databases (Crossref, arXiv, OpenAlex, PubMed) and flags the
citation patterns LLMs tend to produce: placeholder arXiv IDs, fake
co-author lists, `@inproceedings` entries pointing at journals, and
DOIs that resolve to a different paper than the one cited.

## Why now

Citation errors aren't new. A 2024 scoping review across 105 studies
put the baseline reference-error rate around 32.7%. But most of those
were metadata slips — a wrong page, a misspelled author — on papers
that genuinely exist.

Generative AI changed what goes wrong. The new failure isn't a sloppy
reference to a real paper; it's a clean-looking reference to a paper
that was never written.

In biomedical literature, the rate of papers with at least one fully
fabricated reference rose roughly **12-fold in two years**:

| Period | Fraction of papers with ≥1 fabricated reference |
|---|---|
| 2023 | 1 in 2,828 (~0.035%) |
| 2025 | 1 in 458 (~0.218%) |
| Early 2026 | **1 in 277 (~0.361%)** |

*Source: Topaz et al., audit of 2.5M PubMed Central Open Access papers,
The Lancet. A broader 2026 audit of 111M references across arXiv,
bioRxiv, SSRN and PMC estimates ~147,000 hallucinated citations in 2025
alone (Zhao et al.).*

> The old problem was sloppy metadata pointing at real papers. The new
> problem is references to papers that don't exist, dressed up well
> enough to survive review.

## Three archetypes of hallucinated citations

From an audit of 100 confirmed hallucinations in NeurIPS 2025 papers
(Ansari, NeurIPS 2026):

### 1. Total fabrication (66 / 100 cases)

Plausible authors, plausible title, real venue, invented entirely.

```bibtex
@article{fake_avatar_paper,
  author  = {Smith, John and Doe, Jane},
  title   = {Deep learning techniques for avatar-based interaction in virtual environments},
  journal = {IEEE Transactions on Neural Networks and Learning Systems},
  volume  = {32}, number = {12}, pages = {5600--5612},
  year    = {2021}
}
```

Sounds like a normal ML reference. The journal is real, the volume and
pages look right, and the paper does not exist. A Crossref title search
comes back empty, which is how `bib-verify` flags it.

### 2. Partial attribute corruption: real authors, mutated metadata

Real co-authors, but the title, venue, or year has been shuffled.

A real example from the NeurIPS audit: a citation to *MuSR* listed the
paper as EMNLP 2023, with one author added and two dropped. The actual
paper is ICLR 2024 with a different author list. `bib-verify` catches
this through author overlap (below 60% on entries with three or more
authors) and field-level classification that surfaces the wrong year
or venue.

### 3. Identifier hijacking: working DOI, wrong paper

This is the one that worries me most. The DOI resolves, the link opens,
the page loads. But the paper at the other end is not the one being
cited, so every surface check a reviewer might run still passes.

> The most dangerous hallucinated citation isn't the one with a broken
> link. It's the one with a working link to the wrong paper.

As of v0.2.0, `bib-verify` doesn't just flag this case — it tells you
which DOI you probably meant. When a DOI resolves but the title and
authors don't match, the tool searches for the cited title; if that
title belongs to a different real DOI, it names the correct one. The
working link no longer counts as proof of validity.

### Two more patterns worth knowing

- **Placeholder hallucination** — `arXiv:2210.xxxxx` or `note = {URL to be updated}`. Caught offline, instantly.
- **Inherited hallucination** — a fake citation that propagated through training data from a withdrawn preprint. Caught when no canonical record exists in any indexed database.

## What this catches

### Offline heuristics (no network needed)

- Placeholder patterns: `xxxxx`, `???`, `TBD`, `2210.xxxxx`
- `author = "Smith, J. and others"` with fewer than 3 named authors
- `@inproceedings` with a journal `booktitle` (and vice versa)
- Missing DOI/eprint on post-2015 peer-reviewed work
- `note = "preprint"` without any identifier
- Year after LLM training cutoff with no identifier

### Network checks (Crossref + arXiv + OpenAlex + PubMed)

- DOI does not resolve.
- arXiv ID does not exist.
- DOI resolves but to a different paper (Substituted).
- Author overlap with resolved record below 60% (for 3+ authors).
- Year mismatch between claim and authoritative source.
- No matching record exists anywhere (likely hallucinated).

### Field-level classification (C/M/F/P/S/X)

Per Chen et al. 2026 (arXiv:2604.03159), each field gets a label:

| Label | Meaning |
|---|---|
| **C** | Correct |
| **M** | Missing |
| **F** | Fabricated |
| **P** | Partial (meaningful overlap, not exact) |
| **S** | Substituted (resolves to a different paper) |
| **X** | Not applicable |

Entry-level status rolls up from the worst field, with a strong-anchor
exception: if DOI=C and author=C, a partial title is tolerated (users
often shorten long published titles).

If 3+ identity fields (title, author, year, doi) classify as S or F
together, the entry is escalated to `hallucination`. Per Chen et al.,
this co-occurrence pattern has conditional probability 0.74-0.91 of
indicating wholesale entry substitution.

## Landscape — how this compares to existing tools

| Tool | Stars | License | Verification sources | Interface | Distinguishing feature |
|---|---:|---|---|---|---|
| [![RefChecker](https://img.shields.io/github/stars/markrussinovich/refchecker?style=flat&label=⭐)](https://github.com/markrussinovich/refchecker) **RefChecker** | 369+ | MIT | Semantic Scholar, OpenAlex, Crossref, DBLP, ACL Anthology | CLI + Web UI | LLM-powered web search for hallucination assessment; PDF/LaTeX/BibTeX ingest |
| [![BibTeX Verifier](https://img.shields.io/github/stars/merfanian/Bibtex-Verifier?style=flat&label=⭐)](https://github.com/merfanian/Bibtex-Verifier) **BibTeX Verifier** | 20+ | MIT | Crossref, Semantic Scholar | In-browser web app | 100% client-side, Overleaf integration |
| [![Citation-Hallucination-Detection](https://img.shields.io/github/stars/Vikranth3140/Citation-Hallucination-Detection?style=flat&label=⭐)](https://github.com/Vikranth3140/Citation-Hallucination-Detection) **Citation-Hallucination-Detection** | 0+ | — | Crossref, OpenAlex, Semantic Scholar | JSONL CLI | BM25 fuzzy match + optional LLM verification |
| [![verify_citations](https://img.shields.io/github/stars/vishakhpk/verify_citations?style=flat&label=⭐)](https://github.com/vishakhpk/verify_citations) **verify_citations** | low | — | Semantic Scholar | CLI (`pip`) | Minimal hobby tool |
| **[BibTexChecker](https://www.bibtexchecker.com/)** | — | SaaS | Crossref, OpenLibrary | Web service | Commercial |
| **clibib** ([paper](https://arxiv.org/abs/2604.03159)) | — | MIT | Zotero Translation Server | Python lib | Delegates to publisher-deposited bibtex via Zotero TS |
| [**Zotero Translation Server**](https://github.com/zotero/translation-server) | — | AGPL | 600+ Zotero translators (Crossref, DBLP, PubMed, ...) | Docker | DOI / arXiv / PMID / ISBN / URL → canonical bibtex |
| [![bib-verify](https://img.shields.io/github/stars/kondratevakate/bib-verify?style=flat&label=⭐)](https://github.com/kondratevakate/bib-verify) **bib-verify** *(this plugin)* | this repo | MIT | Crossref, arXiv, OpenAlex, PubMed | Claude Code plugin + CLI | Auto-trigger inside Claude Code; stdlib-only; AI-pattern offline heuristics |

### What this plugin adds that others don't

1. **Native Claude Code integration.** Triggered automatically when
   Claude writes citations. PostToolUse hook runs offline heuristics
   inline after every `.bib` edit. Suggested fixes applied through
   `Edit` with user approval.
2. **Zero-dependency stdlib core.** Works on academic clusters with
   no admin, no Docker, no `pip install`. Python 3.8+ stdlib only.
3. **AI-style pattern heuristics** specific to LLM-generated BibTeX:
   entry-type confusion, `"and others"` laziness, placeholder
   detection. These are not in RefChecker or BibTeX Verifier.

## Real-world results

Applied to a draft dataset review (32 BibTeX entries, anonymized), the
tool surfaced the following issues on the first pass:

| Status | Count | Examples |
|---|---:|---|
| Verified by DOI | 22 | Standard correct entries |
| **Hallucination** | **6** | DOIs resolved but to entirely different papers (see below) |
| Substituted | 1 | DOI valid, but the cited paper at that DOI is a different work by overlapping authors |
| Mismatch | 1 | Closest title-search match below similarity threshold |
| Placeholder | 2 | `arXiv:2210.xxxxx`-style identifiers |

Selected hallucinations caught (DOI → cited title vs. resolved title):

- `kessler2021adhd` — cited as *"A neuroimaging dataset on response
  inhibition and selective attention in ADHD"*; DOI `10.1038/s41597-021-00921-y`
  actually resolves to *"The IDEAL household energy dataset, electricity, gas,
  contextual sensor data and survey data for 255 UK homes"*. **Cross-domain
  DOI swap.**
- `barch2013hcptask` — cited as *"Function in the human connectome:
  task-fMRI..."* with Barch et al.; DOI resolves to *"The WU-Minn Human
  Connectome Project: An overview"* by Van Essen et al. **Same project,
  different paper — classic identifier hijacking.**
- `casey2018abcd` — cited title and DOI describe two different ABCD
  publications. **15% author overlap with resolved record.**

After applying the suggested fixes, the same `.bib` produced: **29
verified by DOI, 1 verified by arXiv, 1 needs review (year discrepancy),
1 minor mismatch.** Net: 31% → 6% problematic entries, a 5x improvement
on a single pass.

> If reviewer #2 had pulled any of those six DOIs, the paper would have
> been desk-rejected as AI-generated. This is exactly the failure mode
> `bib-verify` is designed to prevent.

## Install

### Via Claude Code plugin marketplace *(when published)*

```bash
claude plugin install kondratevakate/bib-verify
```

### Manual install (works today)

```bash
git clone https://github.com/kondratevakate/bib-verify ~/.claude/plugins/bib-verify
```

Verify the plugin loaded:

```bash
claude /plugins
```

You should see `bib-verify` listed.

## Use

### Inside Claude Code

Just ask:

> Verify the citations in `papers/draft.bib`

The skill triggers automatically, runs the check, and surfaces
problematic entries inline. You approve each suggested fix; Claude
applies them via `Edit`.

You can also invoke the slash command directly:

```
/verify-bib papers/draft.bib
```

### From the command line

```bash
# Quick offline check (heuristics only, no network calls)
python ~/.claude/plugins/bib-verify/skills/bib-verify/scripts/verify_bib.py \
    refs.bib --offline

# Full check with suggested fixes
python ~/.claude/plugins/bib-verify/skills/bib-verify/scripts/verify_bib.py \
    refs.bib --fix --out report.md

# Strict mode for CI / pre-commit
python ~/.claude/plugins/bib-verify/skills/bib-verify/scripts/verify_bib.py \
    refs.bib --strict --offline
```

## Plugin components

- **Skill** (`skills/bib-verify/`) — triggered when you ask Claude
  to check citations in any phrasing.
- **Agent** (`citation-auditor`) — runs a full bibliography audit on
  its own and hands back a ranked findings report. Good for a
  pre-submission sweep or when a reviewer says your references look
  fake. It verifies and reports; it never rewrites your `.bib`.
- **Slash command** (`/verify-bib`) — explicit invocation.
- **PostToolUse hook** — runs offline heuristics automatically every
  time Claude edits a `.bib` file. Non-blocking by default.

## Pre-commit hook

Block commits that introduce broken citations:

```bash
# .git/hooks/pre-commit
for bib in $(git diff --cached --name-only --diff-filter=ACM | grep '\.bib$'); do
    python ~/.claude/plugins/bib-verify/skills/bib-verify/scripts/verify_bib.py \
        "$bib" --strict --offline || exit 1
done
```

Keep `--offline` in pre-commit to avoid network calls on every commit.
Run the full network check manually before pushing.

## Limitations

This tool flags candidates for human review; it does not issue final
verdicts autonomously. The most important caveat: **a `not_found`
result is not proof of fabrication** — books, datasets, grey
literature, very recent preprints, and under-indexed non-English
venues legitimately fail to resolve. Never delete a reference solely
because `bib-verify` could not find it. The tool also does not verify
that a cited paper actually *supports* the claim it is attached to.

See [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) for the full
accounting (database coverage, threshold caveats, single-source-of-
truth fragility) and the development roadmap.

## How this was built (AI usage)

`bib-verify` was built with AI assistance (Claude Opus 4.8, via Claude
Code) under human direction — a deliberate irony, since the tool
exists to catch AI-introduced citation errors. Every empirical claim
here was validated against ground-truth bibliographies rather than
asserted by the model. Full provenance, including which parts were
human-decided versus AI-implemented and how claims were verified, is
in [`docs/AI_USAGE.md`](docs/AI_USAGE.md).

## Dependencies

Python 3.8+ standard library only. No `pip install` required.

Optional environment variables:

- `BIB_VERIFY_EMAIL` — sets the OpenAlex polite-pool `mailto`
  parameter for better rate limits.
- `NCBI_API_KEY` — PubMed E-utilities API key.

## Prior art and credits

This plugin builds on prior work in citation verification:

- [RefChecker](https://github.com/markrussinovich/refchecker) by Mark
  Russinovich — the most comprehensive citation validator. We borrowed
  the 60% author-overlap threshold.
- [clibib](https://arxiv.org/abs/2604.03159) and the BibTeX
  Hallucinations paper by Chen et al. — source of the C/M/F/P/S/X
  field classification, the co-occurrence hallucination detector,
  and the post-cutoff year heuristic.
- [BibTeX Verifier](https://github.com/merfanian/Bibtex-Verifier) by
  merfanian — in-browser MIT-licensed alternative.

Hallucination archetype taxonomy and statistics in this README draw on:

- Ansari et al., *Hallucinated Citations in NeurIPS 2025: A Manual
  Audit of 100 Cases*, NeurIPS 2026.
- Topaz et al., *Fabricated References in Biomedical Literature
  2023–2026*, The Lancet (audit of 2.5M PMC Open Access papers,
  4,046 fake citations across 2,810 papers).
- Zhao et al., 2026 — large-scale audit of 111M references across
  arXiv, bioRxiv, SSRN, PubMed Central.

See [`skills/bib-verify/RESEARCH.md`](skills/bib-verify/RESEARCH.md)
for the full prior-art audit.

## Citation

If you use bib-verify in your research, please cite it via its archived
Zenodo record:

> Kondrateva, E. (2026). *bib-verify: Catch hallucinated and
> AI-generated citations in BibTeX files*. Zenodo.
> https://doi.org/10.5281/zenodo.20511185

GitHub's "Cite this repository" button (powered by `CITATION.cff`)
generates BibTeX and APA entries with this DOI.

## License

[MIT](LICENSE). See `LICENSE`.

## Contributing

Issues and PRs welcome at <https://github.com/kondratevakate/bib-verify>.

Particularly useful contributions:

- Additional offline heuristics for AI-generated patterns we have
  not yet seen.
- More known-journal entries in `KNOWN_JOURNALS` (currently 30+).
- Adapters for additional backends: Zotero Translation Server,
  RefChecker subprocess, Semantic Scholar, DBLP.
- Multi-format input: `.bbl`, `.tex` with `\cite{}` extraction.

---

<p align="center">
  <a href="https://github.com/kondratevakate/bib-verify/issues/new">Report an issue</a> ·
  <a href="https://github.com/kondratevakate/bib-verify/fork">Fork this repo</a> ·
  <a href="https://github.com/kondratevakate/bib-verify/discussions">Start a discussion</a>
</p>
