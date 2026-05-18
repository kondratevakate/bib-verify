---
name: verify-bib
description: Verify a BibTeX file against academic databases; catch hallucinated and AI-generated citations before submission.
arguments:
  - name: path
    description: Path to .bib file (default: search for *.bib in cwd or papers/)
    required: false
---

Run citation verification on the BibTeX file specified in $ARGUMENTS
(or, if no argument given, find the most likely target by searching
for `*.bib` files in the current directory and `papers/` subtree).

Workflow:

1. Locate the target `.bib` file. If multiple candidates exist, ask
   the user which one to verify.

2. Run the verification script:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/skills/bib-verify/scripts/verify_bib.py \
       "$bib_file" --fix --out bib_verification_report.md
   ```

3. Read the report and surface the high-risk entries inline in the
   conversation. Sort by `risk_score` descending so the worst issues
   come first.

4. For each problematic entry, show:
   - The entry key, status, and risk score.
   - The field-level classification (C/M/F/P/S/X).
   - The specific issue(s) found.
   - The suggested replacement BibTeX, when available.

5. **Do not auto-rewrite the `.bib` file.** Citation corrections are
   sensitive (a wrong DOI swaps in a different paper entirely). Ask
   the user to confirm each replacement, then apply via the `Edit`
   tool one entry at a time.

6. After applying fixes, re-run the script to confirm everything is
   green.

For details on classification labels and verification logic, see the
`bib-verify` skill documentation.
