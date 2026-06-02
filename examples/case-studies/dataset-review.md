# Case study: dataset-review (32 entries)

This case study documents a real audit run on an in-progress
systematic dataset review for a neuroimaging cohort paper. The
`.bib` was assembled with LLM assistance over several drafting
sessions. Sensitive project details are anonymized.

## Initial audit

```
Summary: 32 entries -- hallucination=6, mismatch=1, placeholder=2,
                       substituted=1, verified_by_doi=22
```

Six entries had a DOI that resolved successfully but to an entirely
different paper. Three illustrative examples:

### Example 1: cross-domain DOI swap (most severe)

```bibtex
@article{kessler2021adhd,
  title  = {A neuroimaging dataset on response inhibition and selective ...},
  author = {Kessler, R. and others},
  doi    = {10.1038/s41597-021-00921-y},
  year   = {2021}
}
```

The DOI resolves correctly, but to:

> *"The IDEAL household energy dataset, electricity, gas, contextual
> sensor data and survey data for 255 UK homes"* — Pullinger et al.,
> Scientific Data 2021.

Domain mismatch on 100%. The LLM had attached a real Scientific Data
DOI to a fabricated ADHD-neuroimaging citation.

### Example 2: identifier hijacking within the same project

```bibtex
@article{barch2013hcptask,
  title  = {Function in the human connectome: task-fMRI and individual ...},
  author = {Barch, D. M. and others},
  doi    = {10.1016/j.neuroimage.2013.05.041},
  year   = {2013}
}
```

The cited title is a real Barch et al. 2013 paper in *NeuroImage*.
But the DOI in the bib resolves to:

> *"The WU-Minn Human Connectome Project: An overview"* — Van Essen
> et al., *NeuroImage* 80, 2013.

Both papers exist. Both are from the same HCP project. The LLM
mixed them up: it produced the correct title but attached the DOI
of a sibling paper. This is the most dangerous failure mode —
`bib-verify` catches it via author-overlap heuristic (15% overlap
between claimed and resolved author lists).

### Example 3: ABCD study

```bibtex
@article{casey2018abcd,
  title  = {The Adolescent Brain Cognitive Development (ABCD) study: ...},
  author = {Casey, B. J. and others},
  doi    = {10.1016/j.dcn.2018.04.004},
  year   = {2018}
}
```

The DOI resolves to *"Recruiting the ABCD sample: Design
considerations and procedures"* by Garavan et al. — a different
ABCD-project paper than the methodology paper the author intended
to cite. 10% author overlap.

## Post-fix audit

After substituting the suggested corrected entries:

```
Summary: 32 entries -- mismatch=1, needs_review=1,
                       verified_by_arxiv=1, verified_by_doi=29
```

The remaining two non-green statuses were:

- `cneuromod` (dataset entry without a canonical DOI in Crossref;
  manual reference)
- `gifford2025algonauts` (arXiv version verified, year says 2024 not
  2025 — minor)

## Lessons

1. **DOI resolution is necessary but not sufficient.** All six
   hallucinations had DOIs that resolved successfully. A naive
   "does the link open?" check would have certified them as valid.

2. **Author overlap is the most discriminating signal for
   identifier hijacking.** Across the six cases, claimed-author
   overlap with the resolved record ranged from 10% to 31% — all
   below the 60% threshold.

3. **Same-project substitution is hardest to spot manually.**
   Reviewers familiar with the HCP / ABCD literature would
   recognize the author names and the project context, lowering
   their guard. `bib-verify` does not lower its guard.

4. **One pass changes the quality bar from "submittable" to
   "robust to a hostile reviewer".** Going from 6 hallucinations
   visible in a `.bib` to 0 within one audit cycle is a meaningful
   quality jump that requires no rewriting of the prose.

## Reproduction

The exact reports were:

- `verification/2026-05-31_initial_audit.md`
- `verification/2026-05-31_post_fix.md`

Both produced via:

```bash
python ~/.claude/plugins/bib-verify/skills/bib-verify/scripts/verify_bib.py \
    datasets.bib --fix --out report.md
```
