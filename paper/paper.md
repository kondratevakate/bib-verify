---
title: 'bib-verify: a deterministic detector for hallucinated and AI-generated citations in BibTeX'
tags:
  - Python
  - BibTeX
  - LaTeX
  - hallucination detection
  - citation verification
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
# Written with AI assistance (Claude Opus 4.8); see the AI usage
# statement below and AI_USAGE.md for full provenance.
---

# Summary

`bib-verify` checks a BibTeX file against academic databases and flags
references that do not exist or resolve to the wrong paper. It runs a
resolution waterfall (DOI to Crossref [@crossref], arXiv ID to the arXiv
API, PMID to PubMed, title to Crossref and OpenAlex [@priem2022openalex]),
combined with offline heuristics for the citation defects that large
language models tend to introduce. Each field is classified using the
C/M/F/P/S/X scheme of @chen2026bibtex. The tool depends only on the
Python standard library, needs no API keys for default use, and ships
as a command-line script and a Claude Code [@anthropic2025claude]
plugin with a skill, an agent, and a hook that audits a `.bib` after
every edit.

# Statement of need

Fabricated references have become common as generative AI writing
tools have spread. An audit of 2.5 million PubMed Central papers
[@topaz2026lancet] found the share with at least one fabricated
citation rose from about 1 in 2,828 in 2023 to 1 in 277 in early 2026,
roughly a twelve-fold increase in two years. A larger audit of 111
million references [@zhao2026hallucinations] estimates around 147,000
non-existent citations in 2025 alone.

The new failure mode differs from older ones. Pre-LLM citation errors
were mostly metadata slips on papers that genuinely exist
[@review2024scoping]. AI-introduced errors instead invent whole papers,
or attach a valid identifier to a citation that describes a different
work. A manual audit of 100 confirmed hallucinations in NeurIPS 2025
papers [@ansari2026neurips] found 66% were full fabrications; the rest
mixed real and invented metadata, including a working DOI or arXiv link
pointing to the wrong paper.

Several tools address parts of this. RefChecker
[@russinovich2026refchecker] validates PDF, LaTeX, and BibTeX input
across five databases with optional LLM web search. BibTeX Verifier
[@merfanian2025bibtexverifier] runs in the browser against Crossref and
Semantic Scholar [@semanticscholar]. clibib [@chen2026bibtex] delegates
resolution to the Zotero Translation Server [@zotero]. What none
provides is a deterministic, standard-library-only checker that runs in
restricted environments, plugs into the LLM-assisted writing loop
itself, and targets the patterns specific to AI-generated BibTeX.

`bib-verify` fills that gap with four contributions beyond simple
existence checks. It runs offline heuristics that catch placeholder
identifiers (`arXiv:2210.xxxxx`), entry-type confusion (an
`@inproceedings` whose venue is a journal), lazy `"and others"` author
lists, and missing identifiers on recent work, all without a network
call. It applies the C/M/F/P/S/X classification per field, rolling up
to an entry verdict with a strong-anchor exception so a shortened title
is tolerated when the DOI and authors match. It escalates to a
`hallucination` verdict when three or more identity fields disagree,
following the co-occurrence pattern (conditional probability 0.74 to
0.91) reported by @chen2026bibtex. And it detects identifier hijacking:
when a DOI resolves but the title and authors disagree, the tool
searches for the cited title and, if that title belongs to a different
real DOI with matching authors, names the DOI the entry should have
used. A working link is never treated as proof of validity.

# Validation

`bib-verify` was tested against two real bibliographies. On a draft
dataset review of 32 entries written with LLM help, the first pass
flagged 6 fully hallucinated references (in one case a DOI cited as
ADHD neuroimaging data that resolves to a UK household-energy dataset),
1 substitution, 1 mismatch, and 2 placeholders. Each hallucination was
confirmed by hand. After applying the suggested fixes, 30 entries
verified cleanly, a roughly five-fold drop in problems on a single
pass. On the BibTeX of a rejected MIDL 2026 paper whose reviewer noted
that "two of the four references do not exist in the way that they are
cited," the tool independently flagged the same two and produced
corrected entries from Crossref.

# Limitations

`bib-verify` queries a fixed set of databases, so a `not_found` verdict
means absence from those indices, not proof of fabrication: books,
datasets, grey literature, fresh preprints, and under-indexed
non-English venues may legitimately fail to resolve. The tool is tuned
to minimize false deletions of real references and flags candidates for
review rather than asserting fabrication on its own. Its similarity and
author-overlap thresholds are tuned empirically rather than against a
labelled benchmark. It confirms that a reference exists and that its
metadata matches; it does not check whether the cited work supports the
claim it is attached to. Planned work includes a persistent cache, a
Zotero Translation Server backend, and an optional opt-in LLM stage to
separate un-indexed references from truly fabricated ones.
`LIMITATIONS.md` records the full accounting.

# AI usage statement

In keeping with the transparency the tool is built to support, the
author discloses that `bib-verify` was implemented with a large
language model (Claude Opus 4.8, Anthropic) through Claude Code, under
human direction. The author defined the design, supplied the real-world
failure cases, and made the consequential decisions; the model wrote
code, tests, and documentation. Every empirical claim here was checked
against ground truth, including a human reviewer's independent
assessment of the MIDL bibliography and manual dereferencing of each
flagged DOI, rather than asserted by the model. `AI_USAGE.md` gives the
full provenance.

# Acknowledgements

The author thanks the anonymous MIDL 2026 reviewer whose feedback
motivated this work, and acknowledges RefChecker
[@russinovich2026refchecker], clibib [@chen2026bibtex], and BibTeX
Verifier [@merfanian2025bibtexverifier] as prior art that informed the
design.

# References
