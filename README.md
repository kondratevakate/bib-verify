# bib-verify

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)](https://docs.anthropic.com/claude-code)
[![Tests](https://github.com/kondratevakate/bib-verify/actions/workflows/test.yml/badge.svg)](https://github.com/kondratevakate/bib-verify/actions/workflows/test.yml)
[![GitHub release](https://img.shields.io/github/v/release/kondratevakate/bib-verify?include_prereleases&label=release)](https://github.com/kondratevakate/bib-verify/releases)
[![GitHub stars](https://img.shields.io/github/stars/kondratevakate/bib-verify?style=social)](https://github.com/kondratevakate/bib-verify)

> Catch hallucinated and AI-generated citations in your BibTeX files
> before a reviewer does.

A Claude Code plugin that verifies every `.bib` entry against real
academic databases (Crossref, arXiv, OpenAlex, PubMed) and flags
LLM-style citation patterns — placeholder arXiv IDs, fake co-author
lists, `@inproceedings` pointing at journals, and DOIs that resolve
to entirely different papers.

## Why now

Citation errors have always existed: a 2024 scoping review across 105
studies found a baseline reference-error rate of ~32.7%. Most of those
were metadata errors — wrong page numbers, wrong volume, misspelled
authors — pointing at real papers.

**Generative AI changed the failure mode.** The new problem is not
inaccurate references to real papers; it is *fabricated* references
to papers that never existed.

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

> The old citation problem was noisy metadata. The new citation problem
> is **false epistemic scaffolding**: papers, authors, venues, and
> identifiers that look real enough to pass review, but do not
> correspond to an actual source.

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

Sounds like a normal ML reference. Journal is real. Volume and pages
look right. The paper does not exist. **`bib-verify` catches this via
Crossref title search returning zero matches.**

### 2. Partial attribute corruption — real authors, mutated metadata

Real co-authors, but title / venue / year shuffled.

Real example from the NeurIPS audit: a citation to *MuSR* listed the
paper as **EMNLP 2023** with one author added and two omitted. The
real paper is **ICLR 2024** with the original author list.

**`bib-verify` catches this via the author-overlap heuristic (RefChecker
rule: <60% overlap on 3+ author entries) and the C/M/F/P/S/X field
classification surfacing year / venue mismatches.**

### 3. Identifier hijacking — working DOI, wrong paper

The most dangerous archetype. The arXiv ID or DOI resolves, the link
opens, the page renders — but the paper at the other end of the
identifier is not the paper being cited.

> *The most dangerous hallucinated citation is not the one with a
> broken link. It is the one with a working link to the wrong paper.*

**`bib-verify` catches this via the "Substituted" (S) status: when a
DOI resolves but the title/author overlap with the resolved record
falls below threshold, the entry is escalated regardless of identifier
validity.**

### Bonus archetypes

- **Placeholder hallucination** — `arXiv:2210.xxxxx`, `note = {URL to be updated}`. Caught offline in zero seconds.
- **Inherited hallucination** — fake citation that propagated through training data from a withdrawn preprint. Caught when no canonical record exists in any indexed database.

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
