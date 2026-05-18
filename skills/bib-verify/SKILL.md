---
name: bib-verify
description: Verify BibTeX citations against academic databases (Crossref, arXiv, OpenAlex, bioRxiv, PubMed). Use whenever the user has a `.bib` file or a list of references and asks to "check citations", "verify references", "find broken citations", "check bibliography", "validate refs", "are these papers real", "proofread bib", or any phrasing about checking whether references actually exist. Also use proactively after editing or generating any document that contains citations (LaTeX papers, README references, blog posts) to catch hallucinated or AI-generated references before the user submits.
---

# bib-verify — citation reality check

## Why this skill exists

LLM-generated references are a recurring failure mode in academic writing:
placeholder arXiv IDs (`2210.xxxxx`), wrong entry types
(`@inproceedings` pointing at a journal), `"Author, F. and others"`
without real co-authors, and silently incorrect DOIs. Reviewers spot
these instantly and reject papers as "AI-generated" — even when the
science is fine.

This skill verifies every BibTeX entry against real academic databases
and produces a structured report listing what is verified, what is
broken, and what should be fixed.

## When to use

Use this skill when:

- The user has a `.bib` or `.bibtex` file and asks to check it.
- The user just finished writing a paper and is about to submit.
- A review came back complaining about citations.
- The user mentions a venue and asks "is this reference correct".
- After any LLM-generated `.bib` content — verify proactively before it
  reaches a reviewer.

Do NOT use this skill for:

- Generating new citations from scratch (use a literature search skill).
- Reformatting `.bib` syntax (use `bibtex-tidy` or similar).

## How it works

The skill bundles a Python script `scripts/verify_bib.py` that:

1. Parses the `.bib` file with a stdlib regex parser (no `bibtexparser`
   dependency).
2. For each entry, runs the resolution waterfall:
   - **DOI** → Crossref direct lookup (`api.crossref.org/works/{doi}`)
   - **arXiv ID** → arXiv API (`export.arxiv.org/api/query`)
   - **PMID** → PubMed E-utilities
   - **Otherwise** → Crossref title search, then OpenAlex fallback
3. Compares the retrieved metadata against the claimed fields and
   flags mismatches (wrong year, wrong venue type, title
   dissimilarity).
4. Runs offline heuristics that catch AI-generated patterns even when
   the entry resolves (placeholder IDs, missing DOIs on recent papers,
   journal/conference type confusion).

## How to run

From the directory containing the `.bib` file:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/bib-verify/scripts/verify_bib.py" \
    path/to/refs.bib --out citation_report.md
```

Claude Code sets `${CLAUDE_PLUGIN_ROOT}` to this plugin's install
directory at runtime, so the same command works regardless of where
the plugin lives on the user's machine.

Options:

- `--out FILE` — write markdown report to file (default: stdout).
- `--json` — emit machine-readable JSON instead of markdown.
- `--offline` — skip network calls, run only heuristic checks (useful
  when no internet).
- `--strict` — exit with non-zero status if any entry has issues
  (good for CI / pre-commit hooks).
- `--fix` — append suggested corrected BibTeX entries to the report.

The script depends only on Python 3.8+ standard library
(`urllib`, `re`, `json`, `difflib`). No `pip install` required.

## Interpreting the report

Each entry gets a verdict:

| Verdict | Meaning | Action |
|---|---|---|
| `verified_by_doi` | DOI resolved in Crossref, metadata consistent | none |
| `verified_by_arxiv` | arXiv ID exists | check DOI/journal version exists |
| `verified_by_title` | Title found with >0.85 similarity | review author/year fields |
| `mismatch` | Found a candidate but year/title/authors disagree | fix or replace |
| `placeholder` | Contains `xxxxx`, `???`, `TBD`, etc. | must fix |
| `not_found` | No record matched | likely hallucinated — verify manually |
| `type_error` | `@inproceedings` for a journal venue or vice versa | change entry type |

## Workflow when running the skill

1. Locate the `.bib` file (ask user if ambiguous; default to
   `papers/**/*.bib` or `*.bib` at project root).
2. Run the script with `--out report.md --fix`.
3. Read the report and surface to the user:
   - Number of entries verified vs problematic.
   - Each broken entry with the specific issue.
   - For each fixable entry, show the suggested corrected BibTeX side
     by side with the current entry.
4. **Do not auto-rewrite the `.bib`** without explicit user approval —
   citation corrections are sensitive (wrong DOI = wrong paper).
5. After user approves fixes, apply them via `Edit` tool entry by entry.

## Common AI-generated patterns this catches

- `arXiv:2210.xxxxx` or any placeholder in eprint/journal fields.
- `note = {preprint / in press}` without arXiv ID, DOI, or URL.
- `author = {Lastname, F. and others}` — "and others" used instead of
  listing co-authors. Real papers list 3+ authors before `et al`.
- `@inproceedings{... booktitle = {Medical Image Analysis}}` — common
  LLM error confusing journal with proceedings.
- `journal = {arXiv preprint arXiv:XXXX.XXXX}` for entries that are
  actually published in a peer-reviewed venue.
- Year mismatch: claimed year disagrees with the year Crossref returns
  for that DOI.

## Network and rate-limit notes

- Crossref: free, no auth, polite pool active when `User-Agent` header
  is set. Script sets it to `bib-verify/1.0 (mailto:anonymous)`. Rate
  limit is generous (~50 req/s).
- arXiv: free, no auth, ~1 req/3s recommended. Script sleeps 1s
  between arXiv calls.
- OpenAlex: free, no auth, polite pool with email. Adds `?mailto=`
  if `BIB_VERIFY_EMAIL` env var is set.
- PubMed E-utilities: free, no auth, but API key recommended. Reads
  `NCBI_API_KEY` env var if present.

If the user's machine has no internet, the script still runs the
offline heuristic checks (placeholders, venue-type confusion, missing
DOIs) — most of the AI-generated bugs are catchable without network.

## Output format example

```markdown
# Citation verification report — refs.bib

**Summary**: 4 entries — 2 verified, 1 mismatch, 1 placeholder.

## ❌ lemaitre2022synthba — placeholder

Issue: `journal = {arXiv preprint arXiv:2210.xxxxx}` — placeholder ID.

Suggested fix (found via title search):
```bibtex
@misc{lemaitre2024synthba,
  title  = {SynthBA: Reliable Brain Age Estimation Across Multiple MRI Sequences and Resolutions},
  author = {Lema{\^i}tre, Paul and Rachmadi, Muhammad Febrian and ...},
  year   = {2024},
  eprint = {2406.00365},
  archivePrefix = {arXiv},
  primaryClass  = {eess.IV}
}
```

## ⚠️ peng2021sfcn — type_error

Issue: entry type is `@inproceedings` but `booktitle = {Medical Image
Analysis}` is a journal. Verified by DOI:
`10.1016/j.media.2020.101871`.

Suggested fix: change to `@article`, replace `booktitle` with
`journal`.

## ✅ bontempi2025faceage — verified_by_doi

DOI: `10.1016/S2589-7500(25)00042-1`
Crossref title: "FaceAge, a deep learning system to estimate
biological age from face photographs..."
```

## Future extensions

- Live link-checking for `url` and `howpublished` fields.
- bioRxiv/medRxiv direct API for fresh preprints (<24h).
- Integration with Zotero local library to suggest replacements from
  the user's own collection.
