# JOSS submission checklist

Tracking readiness for a submission to the
[Journal of Open Source Software](https://joss.theoj.org). JOSS
publishes a short paper with a citable DOI after open peer review of
the software itself.

## Submission requirements

| Requirement | Status | Notes |
|---|---|---|
| OSI-approved license | done | MIT |
| Public version-controlled repository | done | github.com/kondratevakate/bib-verify |
| `paper.md` (250–1000 words) | done | `paper/paper.md` |
| `paper.bib` with references | done | `paper/paper.bib` |
| Statement of need | done | in `paper.md` |
| Installation instructions | done | README |
| Example usage | done | README + case study |
| Automated tests | done | 37 tests, CI on 3 OS x 3 Python |
| Community guidelines (contribute / report / support) | done | CONTRIBUTING, CODE_OF_CONDUCT, SECURITY |
| Author list with ORCIDs | partial | second author to be added on invitation |
| Archived release with DOI | done | Zenodo concept DOI 10.5281/zenodo.20511184; v0.2.1 DOI ...185; also on Software Heritage |

## Known risks to flag honestly

JOSS evaluates two things that are worth being candid about before
submitting:

1. **"Substantial scholarly effort."** JOSS may reject software it
   considers too small or a thin wrapper around existing APIs. Our
   defense: the tool is not a wrapper — it adds novel offline
   AI-pattern heuristics, the C/M/F/P/S/X field classification, the
   co-occurrence hallucination detector, and identifier-hijacking
   detection, validated against real bibliographies. A co-author who
   independently built a related tool for teaching strengthens the
   "real research application" case considerably.

2. **Authorship.** Every listed author must have made a significant
   contribution (code, design, documentation, tests, or substantial
   review / domain input). A co-author should therefore contribute
   materially — for example by merging heuristics from their own tool,
   reviewing the approach, or co-writing the paper — before submission.
   This is both a JOSS requirement and the honest way to do it.

## Adding a co-author (mechanical steps)

When the co-author's contribution and details are confirmed, update
three files in one pass:

- `paper/paper.md` — add to the `authors:` YAML block with `orcid`,
  `affiliation`, and (if shared first authorship) an equal-contribution
  note.
- `CITATION.cff` — add to the `authors:` list.
- `.zenodo.json` — add to the `creators` list.

Keep author order and contribution statements consistent across all
three.

## Pre-submission steps

1. Cut a Zenodo-archived release (below) and add the DOI to `paper.md`,
   `CITATION.cff`, and a README badge.
2. Confirm the co-author's contribution is merged and their details are
   in all three author files.
3. Read `paper.md` aloud once; confirm it is 250–1000 words and free of
   AI-writing tells.
4. Submit at https://joss.theoj.org/papers/new with the repository URL
   and the archive DOI.

## Zenodo archival (one-time setup)

1. Sign in at https://zenodo.org and open the GitHub tab in your
   account settings.
2. Find `kondratevakate/bib-verify` and flip its toggle on. This tells
   Zenodo to watch the repository for new releases.
3. Back on GitHub, publish a release from an existing tag (e.g.
   `v0.2.0`) at
   https://github.com/kondratevakate/bib-verify/releases — the
   auto-release workflow may already have created it; if so, just
   confirm it is published, not a draft.
4. Zenodo archives the release automatically and mints a DOI. The
   `.zenodo.json` already in the repo supplies the metadata.
5. Copy the DOI badge from the Zenodo record and add it to the README
   and `paper.md`.

Note: Zenodo only archives releases created *after* you flip the
toggle. If `v0.2.0` was released before that, cut a fresh patch release
(e.g. `v0.2.1`) so Zenodo picks it up.
