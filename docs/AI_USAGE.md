# AI usage statement and provenance

This document discloses how artificial intelligence was used to build
`bib-verify`. We publish it because transparency about AI involvement
is precisely the discipline this tool exists to support, and because
a tool that detects AI-generated errors should hold itself to the same
standard it asks of others.

## Short version

`bib-verify` was designed and built by a human author
(Ekaterina Kondrateva) in collaboration with **Claude Opus 4.8**
(Anthropic), operated through Claude Code. The human directed all
design decisions and supplied the domain expertise and the real-world
failure cases; the AI implemented the code, tests, and documentation
under that direction. **Every empirical claim in this repository was
validated against real bibliographies, not asserted by the AI.**

## Why this tool exists (the honest origin)

A short paper submitted to MIDL 2026 was rejected. One of the three
reviewer criticisms was that the paper "appears to be highly
AI-generated" because "two of the four references do not exist in the
way that they are cited." The criticism was correct: the bibliography,
drafted with LLM assistance, contained a placeholder arXiv identifier
and a citation with an incorrect author attribution.

Rather than treat this as a one-off embarrassment, the author built a
tool to detect that failure mode systematically. The irony — using AI
to fix an AI-introduced problem — is intentional and instructive: AI
assistance is useful, but its output requires verification. This tool
*is* that verification, applied to the specific domain where the
original mistake occurred.

## What the AI did

- Wrote the implementation of `verify_bib.py` (parser, resolution
  waterfall, heuristics, classification, reporting) from the author's
  specifications.
- Translated published methods into code — notably the C/M/F/P/S/X
  field classification and co-occurrence detector from Chen et al.
  2026, and the author-overlap threshold from RefChecker.
- Wrote the test suite, fixtures, documentation, and packaging.
- Researched the prior-art landscape (RefChecker, BibTeX Verifier,
  clibib, Zotero Translation Server) and the hallucination statistics
  cited in the README and paper.

## What the human did

- Defined the problem, scope, and design stance (deterministic,
  stdlib-only, "never delete a real reference").
- Supplied the real failure cases that anchor the project: the MIDL
  bibliography and a neuroimaging dataset review with six genuine
  hallucinations.
- Made every consequential decision: which heuristics to trust, how
  to set the strong-anchor rule, what to flag versus escalate, and
  what *not* to claim.
- Reviewed and validated the AI's output against ground truth.

## How AI claims were kept honest (validation, not assertion)

The central credibility question for an AI-built detector is: *how do
you know the detector itself does not hallucinate its findings?* Our
answer is empirical validation against known-truth data:

1. **The MIDL bibliography.** The tool was run against the exact `.bib`
   that a human expert reviewer had independently flagged. The tool's
   findings matched the reviewer's: the same two references were
   identified as problematic, and the corrected entries were resolved
   from Crossref with verifiable DOIs.

2. **The dataset-review case study.** The tool flagged six entries as
   hallucinations; each was manually confirmed by dereferencing the
   DOI and reading the resolved record (e.g. a DOI cited as ADHD
   neuroimaging data resolving to a UK household-energy dataset). See
   [`examples/case-studies/dataset-review.md`](../examples/case-studies/dataset-review.md).

3. **Adversarial test fixtures.** `tests/fixtures/clean.bib` contains
   only entries with authoritative identifiers; the test suite asserts
   the tool raises *zero* flags on it (guarding against false
   positives), while `ai_patterns.bib` and `hallucinated.bib` assert
   the tool fires on known-bad input.

The heuristics and thresholds documented in
[`LIMITATIONS.md`](LIMITATIONS.md) are stated as fallible and
empirically tuned, not as proven-optimal — again, an honesty
constraint imposed by the human author on the AI's tendency to
overclaim.

## Reproducibility of the build

The tool was built in Claude Code sessions. The development trajectory
is recoverable from the git history: an initial single-file skill,
tested against the real MIDL bib, then expanded with literature-derived
heuristics, then packaged as a Claude Code plugin with tests and CI.
Commit messages attribute AI co-authorship via a
`Co-Authored-By: Claude Opus 4.8` trailer.

## Recommendation to users

Use AI to draft your bibliography if it helps — but verify it. Run
this tool, read the report, and dereference anything it flags. A green
verdict from `bib-verify` is trustworthy by design; a red verdict
means *investigate*, not *delete*. The same posture that produced this
tool — assist, then verify — is the one we recommend for the work it
checks.
