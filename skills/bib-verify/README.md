# bib-verify

A Claude Code user-level skill that verifies BibTeX citations against
real academic databases (Crossref, arXiv, OpenAlex, PubMed). Catches
hallucinated references, placeholder IDs, journal/conference type
confusion, and other common AI-generated citation mistakes before they
reach a reviewer.

## Install location

This skill lives in `~/.claude/skills/bib-verify/` and is automatically
available in every Claude Code session for this user.

## Trigger phrases

Claude will load this skill when you say things like:

- "verify the citations in `refs.bib`"
- "check my bibliography for broken references"
- "are these papers real?"
- "find any hallucinated citations in the paper"
- "validate refs before I submit"

## Manual usage (without Claude)

```bash
# Quick offline check (heuristics only, no network)
python ~/.claude/skills/bib-verify/scripts/verify_bib.py refs.bib --offline

# Full check with suggested fixes
python ~/.claude/skills/bib-verify/scripts/verify_bib.py refs.bib --fix --out report.md

# JSON for piping to other tools
python ~/.claude/skills/bib-verify/scripts/verify_bib.py refs.bib --json

# Strict mode for CI / pre-commit hook
python ~/.claude/skills/bib-verify/scripts/verify_bib.py refs.bib --strict
```

## What gets flagged

### Without network (offline heuristics)

- Placeholder patterns: `xxxxx`, `???`, `TBD`, `TODO`, `2210.xxxxx`
- `author = "Smith, J. and others"` with fewer than 3 named authors
- `@inproceedings` with a journal `booktitle` (and vice versa)
- Missing DOI or arXiv ID on post-2015 peer-reviewed work
- `note = "preprint"` or `"in press"` without any identifier

### With network (Crossref + arXiv + OpenAlex + PubMed)

- DOI does not resolve.
- arXiv ID does not exist.
- DOI resolves but the title disagrees with the claimed title.
- Year mismatch between claim and authoritative source.
- No matching record exists anywhere (likely hallucinated).
- Title search returns a different paper than the one cited.

## Dependencies

Python 3.8+ standard library only. No `pip install` required.

## Pre-commit hook (optional)

To block commits that introduce broken citations, add to
`.git/hooks/pre-commit`:

```bash
#!/bin/bash
for bib in $(git diff --cached --name-only --diff-filter=ACM | grep '\.bib$'); do
    python ~/.claude/skills/bib-verify/scripts/verify_bib.py "$bib" --strict --offline \
      || { echo "bib-verify failed for $bib"; exit 1; }
done
```

Note: keep `--offline` in the hook to avoid network calls during commit.
Run the full network check manually before pushing.
