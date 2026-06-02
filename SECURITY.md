# Security Policy

## Reporting a Vulnerability

If you discover a security issue in bib-verify, please email
**kondratevakate@gmail.com** with subject prefix `[security]`.
Do not open a public issue.

You should expect:

- Acknowledgement within 5 business days.
- A coordinated disclosure timeline if the issue is confirmed.

## Threat model

bib-verify is a client-side tool that:

- Reads `.bib` files from disk.
- Makes outbound HTTPS requests to Crossref, arXiv, OpenAlex, and
  PubMed E-utilities.
- Writes a verification report to disk.

Concerns we take seriously:

| Concern | Mitigation |
|---|---|
| Malicious `.bib` causing crash / DoS via regex backtracking | Parser uses non-backtracking constructs; report any input that hangs |
| URL injection via `eprint` / `doi` field values | All identifiers are URL-encoded before sending to APIs |
| Logging sensitive user data | Reports contain only entry contents from the input `.bib` plus API responses; no telemetry, no analytics |
| Supply-chain attack via dependencies | We use Python stdlib only; no third-party runtime dependencies |

## Out of scope

- Bugs that only affect citation correctness, not security — please
  open a normal [Bug report](.github/ISSUE_TEMPLATE/bug_report.yml).
- Issues in Crossref, arXiv, OpenAlex, or PubMed themselves — report
  to those services directly.
