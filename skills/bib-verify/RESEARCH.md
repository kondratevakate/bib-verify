# Prior art and design notes for bib-verify

This file documents the existing landscape of citation-verification
tools and which ideas we borrowed (with attribution) when designing
this skill. Captured here so a future community release can cite prior
art correctly and not look like NIH-syndrome reinvention.

## Existing tools

| Tool | Stars | License | Backend | Distinguishing feature |
|---|---|---|---|---|
| [RefChecker](https://github.com/markrussinovich/refchecker) | 369 | MIT | Semantic Scholar, OpenAlex, Crossref, DBLP, ACL Anthology | LLM-powered web search for hallucination assessment |
| [BibTeX Verifier](https://github.com/merfanian/Bibtex-Verifier) | 20 | MIT | Crossref + Semantic Scholar | 100% in-browser, Overleaf integration |
| [Citation-Hallucination-Detection](https://github.com/Vikranth3140/Citation-Hallucination-Detection) | 0 | — | Crossref, OpenAlex, Semantic Scholar | Three-stage pipeline with BM25 fuzzy match |
| [verify_citations](https://github.com/vishakhpk/verify_citations) | low | — | Semantic Scholar | Minimal pip CLI |
| [BibTexChecker](https://www.bibtexchecker.com/) | — | SaaS | Crossref + OpenLibrary | Commercial web service |
| [clibib](https://arxiv.org/html/2604.03159v1) | — | MIT | Zotero Translation Server | Delegates to publisher-deposited bibtex, no LLM |
| [Zotero Translation Server](https://github.com/zotero/translation-server) | — | AGPL | 600+ Zotero translators | Docker container, DOI/arXiv/PMID/ISBN/URL -> canonical bibtex |

## Academic references on citation hallucination

- *BibTeX Citation Hallucinations in Scientific Publishing Agents:
  Evaluation and Mitigation* — [arXiv 2604.03159](https://arxiv.org/html/2604.03159v1).
  Proposes the C/M/F/P/S/X field taxonomy and the clibib tool.
- *CheckIfExist: Detecting Citation Hallucinations in the Era of
  AI-Generated Content* — [arXiv 2602.15871](https://arxiv.org/abs/2602.15871).
- *Source or It Didn't Happen: A Multi-Agent Framework for Citation
  Hallucination Detection* — [arXiv 2605.08583](https://arxiv.org/html/2605.08583).

## Ideas we borrowed and where they come from

### From RefChecker (Russinovich)

- **Author overlap >=60% threshold** for entries with 3+ authors.
  Concrete heuristic to flag "wrong paper" cases.
- **Verdict ladder concept** (Error/Warning/Suggestion/Unverified +
  hallucination LIKELY/UNCERTAIN/UNLIKELY) — better UX than flat
  status. Partially adopted.
- **Identifier-conflict detection**: DOI or arXiv resolves to a
  different paper than the cited title.

### From clibib paper (arXiv 2604.03159)

- **6-way field classification** C/M/F/P/S/X applied per-field, then
  rolled up to entry-level worst.
  - C: Correct (matches ground truth after normalization)
  - M: Missing (field absent in entry, present in ground truth)
  - F: Fabricated (invented, no verifiable source)
  - P: Partially correct (meaningful overlap, not exact)
  - S: Substituted (real but wrong paper or wrong version)
  - X: Not applicable (field inapplicable to entry type)
- **"Substituted" as a distinct category** — distinguishes "DOI is
  real but points to a different paper" from "DOI is fake".
- **Co-occurrence pattern**: if 3+ identity fields (author, venue,
  year) all disagree, conditional probability of wholesale
  substitution is 0.74-0.91. Encode as a hard rule that escalates
  to "likely hallucination".
- **Post-cutoff year heuristic**: a 27.7 pp accuracy drop is observed
  between popular and recent (post-cutoff) papers, indicating heavy
  reliance on parametric memory. Treat year > LLM cutoff as elevated
  risk requiring live lookup.
- **Two-stage architecture** for mitigation: generate, then revise
  against an authoritative source (Zotero TS in their case). +8.0 pp
  field accuracy. Worth implementing as a Claude Code hook in a
  later phase.

### From BibTeX Verifier (merfanian)

- **Four-status taxonomy** (Verified / Auto-updated / Needs review /
  Not found). Similar to ours; we kept richer states.
- **"Auto-updated" middle state** — same paper found but metadata
  differs. Adopted as our "match found, fields normalized"
  intermediate.

## What is NOT borrowed (intentional)

- LLM-powered web search (RefChecker's hallucination assessment) —
  out of scope for a deterministic skill, but could be a separate
  agent that the skill delegates to.
- GROBID PDF fallback — out of scope; we accept .bib only for now.
- Web UI — out of scope; Claude Code is the UI.

## Unique value of this skill vs prior art

What this skill does that nothing above does:

1. **Native Claude Code integration**: auto-triggered when Claude
   generates or edits a `.bib`, results surfaced inline in the
   conversation, fixes applied through the `Edit` tool with user
   approval. No separate CLI invocation.
2. **Stdlib-only fallback**: works without `pip install` or Docker,
   useful in restricted environments (academic clusters, no admin).
3. **AI-style pattern heuristics** specific to LLM-generated bibtex:
   - `@inproceedings` with journal `booktitle` (and vice versa)
   - `"and others"` after fewer than 3 named authors
   - Placeholder IDs (`xxxxx`, `???`, `TBD`, `2210.xxxxx`)
   - `note = "preprint / in press"` without any identifier
   These are not in RefChecker or BibTeX Verifier.

## Roadmap for community release

### Phase 1 — current skill (done)
- Offline heuristics + Crossref/arXiv/OpenAlex/PubMed lookup
- Single-file `.bib` parsing, stdlib-only

### Phase 2 — backend adapters
- Zotero Translation Server: spawn Docker container if available,
  fall back to direct Crossref otherwise.
- RefChecker: subprocess call if `academic-refchecker` is in PATH.

### Phase 3 — better surface
- Field-level C/M/F/P/S/X classification (in progress)
- Multi-format input: `.bbl`, `.tex` with `\cite{}` extraction, plain
  text bibliographies
- Output formats: json, jsonl, csv

### Phase 4 — hooks for proactive use
- PreCommit hook to block commits with broken citations
- Post-Write hook to validate `.bib` immediately after Claude edits
  it
- Pre-tex-compile hook for journals with strict citation
  requirements

### Phase 5 — upstream contributions
- Submit AI-pattern heuristics (entry-type confusion, "and others"
  detection, placeholder patterns) as a PR to RefChecker. These do
  not overlap with their existing checks.
- Submit Zotero TS integration as an adapter to RefChecker.

## License intent

When published, this skill should be MIT licensed to match the
ecosystem (RefChecker, BibTeX Verifier, clibib are all MIT).
