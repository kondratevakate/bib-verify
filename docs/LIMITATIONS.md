# Limitations, discussion, and roadmap

`bib-verify` is a deterministic, dependency-free citation auditor. Its
design choices buy portability and speed at the cost of certain
guarantees. This document is an honest accounting of what the tool
does *not* do, so that users do not over-trust its verdicts.

## Core limitation: "not found" is not "fabricated"

The single most important caveat. A `not_found` or `unverified`
verdict means *"no matching record was found in the databases we
query"* — not *"this paper does not exist"*. Legitimate references
routinely fail to resolve:

- **Books and book chapters** — patchy DOI coverage.
- **Datasets and software** — often have a DOI (Zenodo, Figshare) but
  inconsistent metadata, or none at all.
- **Grey literature** — technical reports, theses, white papers,
  standards documents.
- **Very recent preprints** — a window of 24–72 h before arXiv /
  bioRxiv items propagate to Crossref / OpenAlex.
- **Non-English and regional venues** — under-indexed in
  anglophone-centric databases.
- **Older pre-2000 literature** — sparse digital metadata.

**Implication:** never delete a reference solely because `bib-verify`
could not find it. Treat `not_found` as *"verify this one manually"*,
not as proof of fabrication. The tool is tuned to surface candidates
for human judgment, not to issue final verdicts autonomously.

## Database coverage

We query Crossref, arXiv, OpenAlex, and PubMed. We do **not** query
Semantic Scholar, DBLP, ACL Anthology, IEEE Xplore, ADS (astrophysics),
or domain-specific registries. A citation that exists only in DBLP
(common for some CS proceedings) may be reported as `not_found`.

## Heuristic thresholds are empirical, not principled

- **Title similarity** uses Python's `difflib.SequenceMatcher`, a
  character-level ratio. It is fooled by:
  - Shortened or expanded titles (common; we added a strong-anchor
    rule to mitigate, but it is imperfect).
  - LaTeX markup, special characters, and math in titles.
  - Subtitle presence/absence, British/American spelling, translated
    titles.
  The C/0.9, P/0.5, S/0.25 cut-points were tuned on a few dozen
  real entries, not derived from a labelled benchmark. Expect
  occasional mislabels.

- **Author overlap** compares normalized last-name sets. It breaks on:
  - Transliteration variants (Cyrillic, CJK, diacritics).
  - Name changes, hyphenated and compound surnames.
  - Records that list only initials, or that truncate at "et al."
  - CJK name ordering.
  A 60% threshold on 3+ author entries is borrowed from RefChecker;
  it is a reasonable default, not a calibrated decision boundary.

## Single-source-of-truth fragility

When the *authoritative* record is itself incomplete, `bib-verify`
can flag a correct citation. Observed in practice: a Crossref record
for the SIMON dataset returned a partial author list, producing a
spurious 31% author-overlap and a `substituted` flag on an entry that
was actually correct. The tool cannot distinguish "your bib is wrong"
from "Crossref's metadata is wrong" without human inspection.

## What it does NOT verify

- **Citation–claim support.** The tool confirms that a reference
  *exists* and that its metadata matches. It does **not** check that
  the cited paper actually supports the sentence that cites it. That
  is a distinct and harder problem (citation-content verification)
  and is explicitly out of scope for the deterministic core.
- **Predatory / retracted venues.** We do not cross-check against
  Retraction Watch or Beall-style lists.
- **Self-consistency across the bibliography** (duplicate keys,
  inconsistent abbreviation styles) — that is a linter's job
  (`bibtex-tidy`), not ours.

## Operational limits

- **Rate limiting.** arXiv returns HTTP 429 under load; Crossref's
  polite pool throttles. Large bibliographies (100+ entries) can take
  minutes or get partially throttled. We retry with backoff but do
  not yet cache results between runs, so re-running re-queries every
  entry.
- **Offline heuristics encode Western publishing conventions.** The
  `KNOWN_JOURNALS` / `KNOWN_CONFERENCES` lists are anglophone-biased
  and incomplete. Entry-type norms differ by field.
- **The BibTeX parser is regex-based**, not a full grammar
  implementation. It handles balanced braces and common forms, but
  exotic constructs (`@string` macros, `#` string concatenation,
  nested quoting) may parse incorrectly.
- **The post-cutoff-year heuristic is blunt.** It correctly flags
  many hallucinated future-dated entries but will also flag genuine
  2026+ papers that legitimately do not yet have a DOI.

## Discussion: where the deterministic ceiling is

The fundamental trade-off of a deterministic, LLM-free design is that
it can prove a reference *resolves and matches*, but it cannot
*confirm a non-existent reference is truly fabricated*. Tools like
RefChecker add an LLM-driven web-search stage precisely to close that
gap — to distinguish "un-indexed" from "invented". `bib-verify`
deliberately stops at "flag for review" rather than asserting
fabrication, because asserting fabrication without a web search risks
false accusations against real-but-obscure work.

This is a design stance, not an oversight: the tool optimizes for
**zero false deletions of real references** over **maximal
hallucination recall**. A researcher should be able to run it on a
restricted cluster with no API keys and trust that a green verdict is
trustworthy, while treating red verdicts as "investigate", not
"delete".

## Roadmap

Ordered roughly by expected impact-to-effort:

1. **Identifier-hijacking detector** — when a DOI resolves but author
   overlap is low (`substituted`), run a secondary title search; if
   the claimed title resolves to a *different* DOI with high author
   overlap, report "you likely meant DOI X, not DOI Y". This directly
   addresses the most dangerous archetype (the Barch/HCP case in the
   dataset-review case study).
2. **Persistent local cache** (SQLite) keyed by DOI/arXiv/title so
   re-runs are instant and rate limits are avoided.
3. **Zotero Translation Server backend** for canonical, publisher-
   deposited metadata (DOI/arXiv/PMID/ISBN/URL → one record), reducing
   single-source-of-truth fragility.
4. **Confidence scores instead of hard labels** — calibrate against a
   labelled benchmark (e.g. the Chen et al. 2026 dataset) and report
   probabilities rather than binary verdicts.
5. **Additional backends**: DBLP (CS), Semantic Scholar (recall),
   bioRxiv/medRxiv direct (fresh preprints).
6. **Multi-format input**: `.bbl`, `\cite{}` extraction from `.tex`,
   plain-text bibliographies.
7. **Optional LLM deep-verification adapter** — strictly opt-in, to
   confirm `not_found` entries via web search, mirroring RefChecker.
   Kept optional so the default path stays deterministic and offline-
   capable.
8. **Citation–claim support checking** — the hard frontier. Likely a
   separate companion tool rather than part of this one.

Contributions toward any of these are welcome; see
[`CONTRIBUTING.md`](../CONTRIBUTING.md).
