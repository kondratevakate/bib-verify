---
title: 'bib-verify: a deterministic detector for hallucinated and AI-generated citations in BibTeX'
tags:
  - Python
  - BibTeX
  - LaTeX
  - hallucination detection
  - citation verification
  - academic writing
  - reproducibility
authors:
  - name: Ekaterina Kondrateva
    orcid: 0000-0003-3623-6106
    corresponding: true
    affiliation: 1
affiliations:
  - name: "Department of Radiation Oncology (Maastro), GROW Research Institute for Oncology and Reproduction, Maastricht University Medical Centre+, Maastricht University, The Netherlands"
    index: 1
date: 2 June 2026
bibliography: paper.bib
# This paper was written with AI assistance (Claude Opus 4.8); see the
# "AI usage statement" section and AI_USAGE.md for full provenance.
---

# Summary

`bib-verify` is an open-source Python tool and Claude Code [@anthropic2025claude]
plugin that audits BibTeX files for hallucinated, fabricated, and
AI-generated citations. It implements a deterministic resolution
waterfall (DOI → Crossref [@crossref], arXiv ID → arXiv API,
PMID → PubMed E-utilities, title → Crossref/OpenAlex
[@openalex]) combined with offline pattern heuristics that catch
LLM-style citation errors, and a per-field classification scheme
(C/M/F/P/S/X) following @chen2026bibtex. The tool runs on the Python
standard library alone, requires no API keys for default usage, and
integrates into editor workflows as both a command-line tool, a
Claude Code skill auto-triggered by user phrasing, and a
`PostToolUse` hook that runs offline heuristics inline after every
`.bib` edit.

# Statement of need

The rate of fully fabricated references in scientific publishing has
risen sharply with widespread adoption of generative AI writing
assistants. An audit of 2.5 million PubMed Central Open Access papers
[@topaz2026lancet] found that the fraction of papers with at least
one fully fabricated citation rose from approximately 1 in 2,828 in
2023 to 1 in 277 in early 2026 — a roughly 12-fold increase in two
years. A broader audit of 111 million references across arXiv,
bioRxiv, SSRN, and PubMed Central [@zhao2026hallucinations]
conservatively estimates approximately 147,000 non-existent
references appearing in 2025 alone.

The failure mode that generative AI introduces differs qualitatively
from historical citation-error patterns. Pre-LLM bibliographic
errors were dominated by metadata mistakes — incorrect author
spellings, wrong page numbers, mistyped years — that pointed at real
papers [@review2024scoping]. AI-introduced citation errors are
qualitatively different: they fabricate entire papers that do not
exist, or they assign valid identifiers (DOI, arXiv ID) to citations
that describe a different work. A manual audit of 100 confirmed
hallucinated citations across accepted NeurIPS 2025 papers
[@ansari2026neurips] classified 66% as full fabrications and the
remainder as partial attribute corruption or identifier hijacking
(working DOI/arXiv link pointing to the wrong paper).

Existing tools address parts of this problem. RefChecker
[@russinovich2026refchecker] is the most comprehensive citation
validator, supporting PDF, LaTeX, and BibTeX input across five
academic databases, with optional LLM-powered hallucination
assessment. Web-based tools such as BibTeX Verifier
[@merfanian2025bibtexverifier] perform in-browser validation against
Crossref and Semantic Scholar [@semanticscholar]. clibib
[@chen2026bibtex] delegates resolution to the Zotero Translation
Server [@zotero] for publisher-deposited bibliographic metadata.
What is absent from this landscape is a deterministic, stdlib-only
tool that runs in restricted environments, integrates natively into
LLM-assisted writing workflows, and specifically targets the
AI-pattern failure modes that distinguish hallucinated citations
from ordinary metadata errors.

`bib-verify` addresses this gap. It provides:

1. **Offline AI-pattern heuristics** that run in milliseconds
   without network access. These detect placeholder arXiv
   identifiers (e.g. `arXiv:2210.xxxxx`), `@inproceedings` entries
   whose `booktitle` is a journal name (and the inverse), lazy
   `"and others"` author lists with fewer than three named authors,
   missing identifiers on post-2015 peer-reviewed work, and
   `note = "preprint"` entries lacking any verifiable identifier.
2. **Per-field classification** following @chen2026bibtex: each
   field is labeled C (Correct), M (Missing), F (Fabricated), P
   (Partial), S (Substituted), or X (Not applicable). Entry-level
   verdicts roll up from the worst field with a strong-anchor
   exception: a partial title is tolerated when DOI=C and author=C,
   because users routinely shorten long published titles.
3. **A co-occurrence hallucination detector** based on the
   conditional-probability finding of @chen2026bibtex that wholesale
   entry substitution co-occurs in three or more identity fields
   (title, author, year, DOI) with probability 0.74–0.91. When three
   or more identity fields classify as S or F, the entry is
   escalated to a `hallucination` verdict regardless of identifier
   validity.
4. **Identifier-hijacking detection** via author-overlap
   thresholding (60% on three-or-more-author entries, following
   @russinovich2026refchecker). A DOI that resolves to a real but
   substantially-different author list is the most dangerous
   citation failure mode because the link "works" — `bib-verify`
   flags it as `substituted` rather than treating the working DOI as
   evidence of validity.
5. **Claude Code plugin integration**: a skill that auto-triggers on
   user phrasing about citation verification, a `/verify-bib` slash
   command for explicit invocation, and a `PostToolUse` hook that
   runs offline heuristics after every `.bib` edit. This places
   verification in the same workflow loop where LLM-generated
   citations are introduced.

# Validation

Validation was performed in two phases. First, the tool was applied
to a draft systematic dataset review with 32 BibTeX entries written
with LLM assistance. The initial audit identified 6 fully
hallucinated entries (DOIs resolving to entirely unrelated papers in
one case to a UK household-energy dataset cited as ADHD
neuroimaging data), 1 substituted entry, 1 mismatch, and 2
placeholder identifiers. After applying suggested fixes, the same
file produced 30 verified entries with only one minor year
discrepancy and one dataset-without-DOI mismatch remaining — a
roughly 5-fold reduction in problematic citations on a single pass.

Second, the tool was applied to the BibTeX of a MIDL 2026 short
paper that had been rejected with the reviewer comment "two of the
four references do not exist in the way that they are cited". The
audit confirmed both flagged references as hallucinated (a real
arXiv-style placeholder identifier and a citation to a non-existent
paper at the cited author) and produced replacement entries from
Crossref with full author lists and verified DOIs.

# Limitations and future work

`bib-verify` is deterministic and queries a fixed set of databases
(Crossref, arXiv, OpenAlex, PubMed). Consequently a `not_found`
verdict indicates absence from those indices, not proof of
fabrication: books, datasets, grey literature, very recent preprints,
and under-indexed non-English venues may legitimately fail to
resolve. The tool is therefore tuned to minimize false deletions of
real references — it flags candidates for human review rather than
asserting fabrication autonomously. Title-similarity and
author-overlap thresholds are empirically tuned rather than
calibrated against a labelled benchmark, and the offline heuristics
encode anglophone publishing conventions. The tool verifies that a
reference exists and that its metadata matches; it does not verify
that the cited work supports the claim made in the citing sentence,
which is a distinct and harder problem. Planned work includes an
identifier-hijacking detector (secondary title search when a DOI
resolves but author overlap is low), a persistent local cache, a
Zotero Translation Server backend for canonical metadata, and an
optional opt-in LLM web-search stage to distinguish un-indexed from
truly fabricated references. A full accounting is maintained in the
project's `LIMITATIONS.md`.

# AI usage statement

In keeping with the transparency this tool is designed to support,
the authors disclose that `bib-verify` was implemented with the
assistance of a large language model (Claude Opus 4.8, Anthropic)
operated through Claude Code, under human direction. The human author
defined the design, supplied the real-world failure cases, and made
all consequential decisions; the model implemented code, tests, and
documentation. Critically, every empirical claim in this work was
validated against ground-truth bibliographies — a human reviewer's
independent assessment of the MIDL bibliography, and manual
dereferencing of each flagged DOI in the dataset-review case study —
rather than asserted by the model. The project's `AI_USAGE.md`
documents this provenance in full.

# Acknowledgements

The author thanks the anonymous MIDL 2026 reviewer 55zB whose
critical feedback motivated this work, and acknowledges
@russinovich2026refchecker, @chen2026bibtex, and
@merfanian2025bibtexverifier as prior art whose design choices
informed the tool architecture.

# References
