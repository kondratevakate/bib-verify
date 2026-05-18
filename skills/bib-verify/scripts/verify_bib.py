#!/usr/bin/env python3
"""
verify_bib.py — verify BibTeX entries against academic databases.

Resolution waterfall:
    1. DOI         -> Crossref direct lookup
    2. arXiv ID    -> arXiv API
    3. PMID        -> PubMed E-utilities
    4. Title       -> Crossref search, then OpenAlex fallback

Offline heuristics (always run, no network needed):
    - placeholder patterns: xxxxx, ???, TBD, 2210.xxxxx
    - "and others" author lists
    - @inproceedings entries pointing at journal venues
    - missing DOI on post-2015 papers
    - note = "preprint / in press" without identifier

Dependencies: Python 3.8+ stdlib only. No pip install required.

Usage:
    python verify_bib.py refs.bib
    python verify_bib.py refs.bib --out report.md --fix
    python verify_bib.py refs.bib --json
    python verify_bib.py refs.bib --offline
    python verify_bib.py refs.bib --strict        # exit 1 on issues
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from pathlib import Path

USER_AGENT = "bib-verify/1.0 (https://github.com/anthropics/claude-code; mailto:anonymous@example.com)"
TIMEOUT = 15

PLACEHOLDER_PATTERNS = [
    (re.compile(r"\bx{2,}\b", re.I), "x{2,} placeholder"),
    (re.compile(r"\?{2,}"), "??? placeholder"),
    (re.compile(r"\bTBD\b", re.I), "TBD placeholder"),
    (re.compile(r"\bTODO\b", re.I), "TODO placeholder"),
    (re.compile(r"\d{4}\.x{2,}", re.I), "arXiv ID placeholder (e.g. 2210.xxxxx)"),
    (re.compile(r"\bFIXME\b", re.I), "FIXME placeholder"),
]

# Known journals frequently mistyped as @inproceedings by LLMs.
KNOWN_JOURNALS = {
    "medical image analysis",
    "neuroimage",
    "neuroimage: clinical",
    "human brain mapping",
    "nature",
    "nature methods",
    "nature medicine",
    "nature neuroscience",
    "the lancet",
    "the lancet digital health",
    "the lancet oncology",
    "cell",
    "science",
    "plos one",
    "plos medicine",
    "scientific reports",
    "scientific data",
    "ieee transactions on medical imaging",
    "ieee transactions on pattern analysis and machine intelligence",
    "journal of magnetic resonance imaging",
    "magnetic resonance in medicine",
    "radiology",
    "gigascience",
    "bioinformatics",
    "elife",
    "frontiers in neuroscience",
    "frontiers in neuroinformatics",
    "frontiers in aging neuroscience",
    "journal of open source software",
}

# Known conference proceedings frequently mistyped as @article.
KNOWN_CONFERENCES = {
    "miccai",
    "midl",
    "neurips",
    "nips",
    "icml",
    "iclr",
    "cvpr",
    "iccv",
    "eccv",
    "aaai",
    "ijcai",
    "isbi",
    "embc",
    "ipmi",
}


# ----------------------------------------------------------------------
# BibTeX parsing
# ----------------------------------------------------------------------


@dataclass
class BibEntry:
    key: str
    type: str
    fields: dict
    raw: str = ""

    def get(self, key, default=""):
        return self.fields.get(key.lower(), default)


def _strip_braces(s: str) -> str:
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    elif s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.strip()


def parse_bib(text: str) -> list:
    """Naive but resilient BibTeX parser.

    Handles nested braces in field values by counting depth.
    """
    entries = []
    i = 0
    n = len(text)
    while i < n:
        at = text.find("@", i)
        if at == -1:
            break
        # Find entry type
        m = re.match(r"@(\w+)\s*\{", text[at:])
        if not m:
            i = at + 1
            continue
        bib_type = m.group(1).lower()
        if bib_type in ("comment", "preamble", "string"):
            # Skip these meta-entries
            i = at + m.end()
            continue
        body_start = at + m.end()
        # Find matching closing brace
        depth = 1
        j = body_start
        while j < n and depth > 0:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        if depth != 0:
            break
        body = text[body_start : j - 1]
        # Split body into key, then fields
        comma = body.find(",")
        if comma == -1:
            i = j
            continue
        key = body[:comma].strip()
        rest = body[comma + 1 :]
        fields = _split_fields(rest)
        entries.append(
            BibEntry(
                key=key,
                type=bib_type,
                fields=fields,
                raw=text[at:j],
            )
        )
        i = j
    return entries


def _split_fields(body: str) -> dict:
    """Split BibTeX body into field dict, respecting brace depth."""
    fields = {}
    i = 0
    n = len(body)
    while i < n:
        # Skip whitespace and commas
        while i < n and body[i] in " \t\n\r,":
            i += 1
        if i >= n:
            break
        # Read field name
        m = re.match(r"(\w+)\s*=\s*", body[i:])
        if not m:
            i += 1
            continue
        name = m.group(1).lower()
        i += m.end()
        # Read value: either {...} (balanced), "..." or bare word
        if i >= n:
            break
        if body[i] == "{":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            value = body[i + 1 : j - 1]
            i = j
        elif body[i] == '"':
            j = i + 1
            while j < n and body[j] != '"':
                j += 1
            value = body[i + 1 : j]
            i = j + 1
        else:
            j = i
            while j < n and body[j] not in ",\n":
                j += 1
            value = body[i:j].strip()
            i = j
        fields[name] = value.strip()
    return fields


# ----------------------------------------------------------------------
# Network clients
# ----------------------------------------------------------------------


def _http_json(url: str, timeout: int = TIMEOUT) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None
    except Exception:
        return None


def _http_text(url: str, timeout: int = TIMEOUT, max_retries: int = 2) -> str | None:
    """HTTP GET returning decoded text. Retries once with backoff on 429."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                # Honor Retry-After header if present, else exponential backoff
                ra = e.headers.get("Retry-After") if e.headers else None
                wait = int(ra) if ra and ra.isdigit() else 5 * (2 ** attempt)
                time.sleep(min(wait, 30))
                continue
            return None
        except (urllib.error.URLError, TimeoutError):
            return None
        except Exception:
            return None
    return None


def crossref_by_doi(doi: str) -> dict | None:
    """Resolve a DOI directly via Crossref."""
    doi_clean = doi.strip().rstrip(".").lstrip("doi:").strip()
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi_clean, safe='/.')}"
    data = _http_json(url)
    if data and "message" in data:
        return data["message"]
    return None


def crossref_search(title: str, author: str | None = None, rows: int = 5) -> list:
    params = {"query.bibliographic": title[:300], "rows": str(rows)}
    if author:
        params["query.author"] = author
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    data = _http_json(url)
    if data and "message" in data and "items" in data["message"]:
        return data["message"]["items"]
    return []


def arxiv_lookup(arxiv_id: str) -> dict | None:
    """Look up an arXiv ID. Returns dict with title/authors/year or None."""
    arxiv_id = re.sub(r"^arXiv:", "", arxiv_id.strip(), flags=re.I)
    if not re.match(r"\d{4}\.\d{4,5}(v\d+)?$", arxiv_id) and not re.match(r"[a-z\-]+/\d{7}(v\d+)?$", arxiv_id):
        return None
    # Use HTTPS directly: arxiv.org redirects HTTP -> HTTPS and the
    # follow-up request often times out on slow connections.
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    text = _http_text(url, timeout=30)
    if not text or "<entry>" not in text:
        return None
    # Minimal XML parse
    title_m = re.search(r"<entry>.*?<title>(.+?)</title>", text, re.DOTALL)
    authors = re.findall(r"<author>\s*<name>(.+?)</name>", text, re.DOTALL)
    year_m = re.search(r"<published>(\d{4})", text)
    return {
        "source": "arxiv",
        "id": arxiv_id,
        "title": (title_m.group(1).strip() if title_m else "").replace("\n", " "),
        "authors": [a.strip() for a in authors],
        "year": year_m.group(1) if year_m else None,
    }


def openalex_search(title: str) -> list:
    params = {"search": title[:300], "per-page": "5"}
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    data = _http_json(url)
    if data and "results" in data:
        return data["results"]
    return []


def pubmed_lookup(pmid: str) -> dict | None:
    pmid = pmid.strip()
    if not pmid.isdigit():
        return None
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
        f"db=pubmed&id={pmid}&retmode=json"
    )
    data = _http_json(url)
    if not data:
        return None
    res = data.get("result", {}).get(pmid)
    if not res:
        return None
    return {
        "source": "pubmed",
        "id": pmid,
        "title": res.get("title", ""),
        "authors": [a.get("name", "") for a in res.get("authors", [])],
        "year": (res.get("pubdate") or "")[:4],
        "venue": res.get("source", ""),
    }


# ----------------------------------------------------------------------
# Verification logic
# ----------------------------------------------------------------------


# Per-field classification labels from Chen et al. 2026 (arXiv:2604.03159):
#   C = Correct, M = Missing, F = Fabricated, P = Partial, S = Substituted, X = N/A
FIELD_LABELS = {"C", "M", "F", "P", "S", "X"}

# Identity fields used for "wholesale entry substitution" co-occurrence check.
IDENTITY_FIELDS = ("title", "author", "year", "journal", "booktitle", "doi")

# LLM training cutoff: papers published after this date have elevated risk
# of being hallucinated because the model is more likely to invent metadata
# from parametric memory. Per Chen et al., post-cutoff accuracy drops 27.7pp.
LLM_TRAINING_CUTOFF_YEAR = 2026


@dataclass
class Verdict:
    key: str
    type: str
    # Entry-level status (rolled up from worst field classification)
    status: str = "unknown"  # verified | needs_review | substituted | hallucination | placeholder | type_error | not_found | unverified
    issues: list = field(default_factory=list)
    match: dict | None = None
    suggested: str | None = None
    # Field-level classification, e.g. {"title": "C", "year": "P", "doi": "S"}
    field_classification: dict = field(default_factory=dict)
    # Risk score 0-100: weighted combination of issues + cutoff + co-occurrence
    risk_score: int = 0


def offline_checks(entry: BibEntry) -> list:
    """Pre-network checks for AI-generated patterns."""
    issues = []
    # Placeholders
    for field_name, value in entry.fields.items():
        for pat, label in PLACEHOLDER_PATTERNS:
            if pat.search(value):
                issues.append(f"placeholder ({label}) in {field_name}: {value[:80]!r}")
                break
    # "and others" lazy author
    author = entry.get("author", "")
    if author and "others" in author.lower():
        n_named = len([a for a in re.split(r"\s+and\s+", author, flags=re.I) if "others" not in a.lower()])
        if n_named < 3:
            issues.append(
                f"author field uses 'and others' after only {n_named} named author(s); "
                "list at least 3 authors before abbreviating"
            )
    # Journal vs proceedings mismatch
    if entry.type == "inproceedings":
        booktitle = entry.get("booktitle", "").lower().strip()
        booktitle = re.sub(r"^the\s+", "", booktitle)
        if booktitle in KNOWN_JOURNALS:
            issues.append(
                f"@inproceedings with booktitle='{booktitle}' which is a journal -- change to @article and rename booktitle -> journal"
            )
    if entry.type == "article":
        journal = entry.get("journal", "").lower().strip()
        for conf in KNOWN_CONFERENCES:
            if conf in journal:
                issues.append(
                    f"@article with journal='{journal}' which looks like a conference -- consider @inproceedings"
                )
                break
        # arXiv preprint masquerading as @article
        if "arxiv" in journal and "x" in journal.lower():
            issues.append("journal field references arXiv with placeholder ID -- use @misc with eprint/archivePrefix")
    # Missing DOI on recent paper
    year_str = entry.get("year", "")
    if year_str.isdigit() and int(year_str) >= 2015:
        if entry.type in ("article", "inproceedings") and not entry.get("doi"):
            if not entry.get("eprint"):
                issues.append(f"no DOI or eprint on {entry.type} from {year_str} -- modern peer-reviewed work should have one")
    # note = "preprint" without ID
    note = entry.get("note", "").lower()
    if note and any(k in note for k in ("preprint", "in press", "forthcoming")):
        if not (entry.get("doi") or entry.get("eprint") or entry.get("url")):
            issues.append(f"note='{note[:60]}' without DOI/eprint/URL -- add identifier so reviewers can verify")
    # Post-cutoff year heuristic: per Chen et al. 2026, accuracy drops 27.7pp
    # for papers after LLM training cutoff. Flag for mandatory live lookup.
    if year_str.isdigit() and int(year_str) > LLM_TRAINING_CUTOFF_YEAR:
        if not (entry.get("doi") or entry.get("eprint")):
            issues.append(
                f"year {year_str} is after LLM training cutoff ({LLM_TRAINING_CUTOFF_YEAR}) "
                "and there is no DOI/eprint -- high hallucination risk, manual verification required"
            )
    return issues


def _normalize_name(name: str) -> str:
    """Normalize an author name for overlap comparison: lowercase last name."""
    # Handle "Last, First" or "First Last"
    name = name.strip()
    if "," in name:
        last = name.split(",")[0]
    else:
        parts = name.rsplit(" ", 1)
        last = parts[-1] if parts else name
    return re.sub(r"[^a-z]", "", last.lower())


def _author_overlap(claimed: str, found_authors: list) -> float:
    """Return fraction of claimed authors found in the resolved record.

    Per RefChecker, <60% overlap on 3+ author entries flags a likely
    substitution. We compare last-name sets.
    """
    if not claimed or not found_authors:
        return 1.0  # cannot judge
    claimed_set = {
        _normalize_name(a) for a in re.split(r"\s+and\s+", claimed, flags=re.I)
        if a.strip() and "others" not in a.lower()
    }
    claimed_set.discard("")
    found_set = {_normalize_name(a) for a in found_authors if a.strip()}
    found_set.discard("")
    if not claimed_set or not found_set:
        return 1.0
    overlap = len(claimed_set & found_set) / len(claimed_set)
    return overlap


def _classify_fields(entry: BibEntry, match: dict) -> dict:
    """Field-level C/M/F/P/S/X classification per Chen et al. 2026.

    Compares each significant field in the entry against the resolved
    record. Returns dict of {field_name: label}.
    """
    classification = {}
    if not match:
        return classification

    # Title
    # Thresholds tuned to real-world shortened-title cases: users often trim
    # long published titles, which gives SequenceMatcher ratio ~0.5-0.7.
    # We treat that range as P (partial); S/F reserved for clearly different papers.
    claimed_title = re.sub(r"[{}]", "", entry.get("title", "")).strip()
    found_title = match.get("title", "")
    if claimed_title and found_title:
        sim = _title_similarity(claimed_title, found_title)
        if sim >= 0.9:
            classification["title"] = "C"
        elif sim >= 0.5:
            classification["title"] = "P"
        elif sim >= 0.25:
            classification["title"] = "S"
        else:
            classification["title"] = "F"
    elif claimed_title and not found_title:
        classification["title"] = "X"
    elif not claimed_title and found_title:
        classification["title"] = "M"

    # Year
    claimed_year = entry.get("year", "")
    found_year = str(match.get("year") or "")
    if claimed_year and found_year:
        if claimed_year == found_year:
            classification["year"] = "C"
        elif abs(int(claimed_year) - int(found_year)) <= 1 if (claimed_year.isdigit() and found_year.isdigit()) else False:
            classification["year"] = "P"
        else:
            classification["year"] = "S"
    elif claimed_year and not found_year:
        classification["year"] = "X"
    elif not claimed_year and found_year:
        classification["year"] = "M"

    # Author overlap
    claimed_authors = entry.get("author", "")
    found_authors = match.get("authors", []) or []
    # Crossref-style match dicts use match["authors"] only if we wrote it; otherwise we
    # cannot compare cleanly. Skip silently when found_authors empty.
    if claimed_authors and found_authors:
        overlap = _author_overlap(claimed_authors, found_authors)
        if overlap >= 0.85:
            classification["author"] = "C"
        elif overlap >= 0.6:
            classification["author"] = "P"
        elif overlap >= 0.3:
            classification["author"] = "S"
        else:
            classification["author"] = "F"

    # DOI: exact-match check only (already validated during lookup)
    claimed_doi = entry.get("doi", "").lower().strip()
    found_doi = (match.get("doi") or "").lower().strip()
    if claimed_doi and found_doi:
        classification["doi"] = "C" if claimed_doi == found_doi else "S"
    elif claimed_doi and not found_doi:
        classification["doi"] = "X"
    elif not claimed_doi and found_doi:
        classification["doi"] = "M"

    return classification


def _entry_status_from_fields(classification: dict, default: str) -> str:
    """Roll up field-level labels to entry-level status.

    Co-occurrence rule from Chen et al.: if 3+ identity fields are S or F,
    this is "wholesale entry substitution" (p=0.74-0.91) -> hallucination.

    Strong-anchor rule: P (Partial) on title is acceptable if the entry has
    an authoritative anchor (DOI=C, or author=C + year=C). Many users
    legitimately shorten long published titles; this is not a hallucination.
    """
    if not classification:
        return default
    identity_classes = [classification.get(f) for f in ("title", "author", "year", "doi") if classification.get(f)]
    severe = sum(1 for c in identity_classes if c in ("S", "F"))
    if severe >= 3:
        return "hallucination"
    if "F" in classification.values():
        return "hallucination"
    if "S" in classification.values():
        return "substituted"
    # P on title alone with strong anchor (DOI=C, or author+year both C) is OK
    has_doi_anchor = classification.get("doi") == "C"
    has_au_year_anchor = classification.get("author") == "C" and classification.get("year") == "C"
    has_strong_anchor = has_doi_anchor or has_au_year_anchor
    p_fields = [f for f, c in classification.items() if c == "P"]
    if p_fields and not has_strong_anchor:
        return "needs_review"
    if len(p_fields) >= 2 and not has_doi_anchor:
        # Multiple partials without DOI anchor -> still warrant review
        return "needs_review"
    if all(c == "C" for c in classification.values() if c not in ("M", "X")):
        return "verified"
    if any(c == "P" for c in classification.values()):
        # Has P but with strong anchor -- keep default verified status, P is just a soft note
        return default
    return default


def _compute_risk_score(verdict: Verdict) -> int:
    """0-100 risk score: combines issue count + status + cutoff."""
    score = 0
    status_weight = {
        "verified": 0,
        "verified_by_doi": 0,
        "verified_by_arxiv": 5,
        "verified_by_title": 10,
        "needs_review": 30,
        "substituted": 60,
        "mismatch": 50,
        "placeholder": 80,
        "type_error": 30,
        "hallucination": 90,
        "not_found": 75,
        "unverified": 40,
        "unknown": 50,
    }
    score += status_weight.get(verdict.status, 50)
    score += min(20, 4 * len(verdict.issues))
    return min(100, score)


def _title_similarity(a: str, b: str) -> float:
    norm = lambda s: re.sub(r"[^\w\s]", " ", s.lower()).strip()
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def _crossref_title(item: dict) -> str:
    t = item.get("title")
    if isinstance(t, list) and t:
        return t[0]
    return t or ""


def _crossref_year(item: dict) -> str | None:
    for k in ("published-print", "published-online", "issued", "created"):
        v = item.get(k, {})
        parts = v.get("date-parts") if isinstance(v, dict) else None
        if parts and parts[0]:
            return str(parts[0][0])
    return None


def _crossref_to_bibtex(item: dict, key: str) -> str:
    """Render a Crossref response as a BibTeX entry."""
    cr_type = item.get("type", "journal-article")
    bib_type = {
        "journal-article": "article",
        "proceedings-article": "inproceedings",
        "book": "book",
        "book-chapter": "inbook",
        "posted-content": "misc",
        "report": "techreport",
    }.get(cr_type, "misc")
    title = _crossref_title(item)
    authors = []
    for a in item.get("author", []) or []:
        family = a.get("family", "")
        given = a.get("given", "")
        if family and given:
            authors.append(f"{family}, {given}")
        elif family:
            authors.append(family)
    author_str = " and ".join(authors)
    year = _crossref_year(item) or ""
    venue = ""
    if "container-title" in item and item["container-title"]:
        venue = item["container-title"][0]
    doi = item.get("DOI", "")
    venue_field = "journal" if bib_type == "article" else "booktitle"
    lines = [f"@{bib_type}{{{key},"]
    lines.append(f"  title   = {{{title}}},")
    if author_str:
        lines.append(f"  author  = {{{author_str}}},")
    if venue:
        lines.append(f"  {venue_field:<7} = {{{venue}}},")
    if year:
        lines.append(f"  year    = {{{year}}},")
    if doi:
        lines.append(f"  doi     = {{{doi}}}")
    lines.append("}")
    return "\n".join(lines)


def _finalize(v: Verdict, entry: BibEntry) -> Verdict:
    """Apply field-level classification and risk score before returning."""
    if v.match and not v.match.get("_needs_review"):
        v.field_classification = _classify_fields(entry, v.match)
        escalated = _entry_status_from_fields(v.field_classification, v.status)
        # Only escalate, never demote
        priority = {
            "verified": 0, "verified_by_doi": 0, "verified_by_arxiv": 0, "verified_by_title": 0,
            "needs_review": 30, "type_error": 30, "unverified": 40,
            "mismatch": 50, "substituted": 60, "not_found": 75,
            "placeholder": 80, "hallucination": 90, "unknown": 50,
        }
        if priority.get(escalated, 0) > priority.get(v.status, 0):
            v.issues.append(f"escalated from '{v.status}' to '{escalated}' based on field-level classification")
            v.status = escalated
        # Author overlap check (RefChecker heuristic, threshold 0.6 for 3+ authors)
        claimed_authors = entry.get("author", "")
        if claimed_authors and v.match.get("authors"):
            authors_named = [a for a in re.split(r"\s+and\s+", claimed_authors, flags=re.I) if "others" not in a.lower()]
            if len(authors_named) >= 3:
                overlap = _author_overlap(claimed_authors, v.match["authors"])
                if overlap < 0.6:
                    v.issues.append(
                        f"author overlap with resolved record is only {overlap:.0%} "
                        "(threshold 60% for 3+ author entries) -- likely wrong paper"
                    )
                    if v.status in ("verified_by_doi", "verified_by_arxiv", "verified_by_title"):
                        v.status = "substituted"
    v.risk_score = _compute_risk_score(v)
    return v


def verify_entry(entry: BibEntry, offline: bool = False, sleep: float = 0.0) -> Verdict:
    v = Verdict(key=entry.key, type=entry.type, issues=offline_checks(entry))

    # Hard placeholder verdict if any placeholder issue found
    if any("placeholder" in iss for iss in v.issues):
        v.status = "placeholder"
        # still try to fix via title search (below) unless offline

    if offline:
        if v.status == "unknown":
            v.status = "skipped_offline"
        return _finalize(v, entry)

    # 1. DOI
    doi = entry.get("doi")
    if doi and not any(p[0].search(doi) for p in PLACEHOLDER_PATTERNS):
        item = crossref_by_doi(doi)
        if sleep:
            time.sleep(sleep)
        if item:
            cr_title = _crossref_title(item)
            cr_year = _crossref_year(item)
            claim_title = entry.get("title")
            sim = _title_similarity(claim_title, cr_title) if claim_title else 1.0
            # Build authors list for field classification
            cr_authors = []
            for a in item.get("author", []) or []:
                family = a.get("family", "")
                given = a.get("given", "")
                if family:
                    cr_authors.append(f"{family}, {given}" if given else family)
            if sim < 0.6:
                # DOI resolves but title disagrees -- this is Substituted (S), not just mismatch
                v.status = "substituted"
                v.issues.append(
                    f"DOI resolves but title disagrees (sim={sim:.2f}): "
                    f"claimed '{(claim_title or '')[:60]}' vs Crossref '{cr_title[:60]}' -- Substituted"
                )
            else:
                v.status = "verified_by_doi" if v.status == "unknown" else v.status
            claim_year = entry.get("year")
            if claim_year and cr_year and claim_year != cr_year:
                v.issues.append(f"year mismatch: claimed {claim_year}, Crossref says {cr_year}")
            v.match = {
                "source": "crossref",
                "doi": item.get("DOI"),
                "title": cr_title,
                "year": cr_year,
                "type": item.get("type"),
                "authors": cr_authors,
            }
            return _finalize(v, entry)
        else:
            v.issues.append(f"DOI '{doi}' not found in Crossref")

    # 2. arXiv
    arxiv_id = None
    if entry.get("eprint") and entry.get("archiveprefix", "").lower() in ("arxiv", ""):
        arxiv_id = entry.get("eprint")
    elif "arxiv" in entry.get("journal", "").lower():
        m = re.search(r"(\d{4}\.\d{4,5})", entry.get("journal", ""))
        if m:
            arxiv_id = m.group(1)
    if arxiv_id and not any(p[0].search(arxiv_id) for p in PLACEHOLDER_PATTERNS):
        ax = arxiv_lookup(arxiv_id)
        if sleep:
            time.sleep(max(sleep, 1.0))  # arXiv requires ~1s
        if ax:
            v.match = ax
            if v.status == "unknown":
                v.status = "verified_by_arxiv"
            return _finalize(v, entry)
        else:
            v.issues.append(f"arXiv ID {arxiv_id} did not resolve")

    # 3. PMID
    pmid = entry.get("pmid")
    if pmid:
        pm = pubmed_lookup(pmid)
        if pm:
            v.match = pm
            if v.status == "unknown":
                v.status = "verified_by_doi"
            return _finalize(v, entry)
        else:
            v.issues.append(f"PMID {pmid} not found")

    # 4. Title search
    title = entry.get("title", "")
    title = re.sub(r"[{}]", "", title)
    if title:
        first_author = entry.get("author", "").split(" and ")[0].split(",")[0].strip()
        candidates = crossref_search(title, author=first_author if first_author else None)
        if sleep:
            time.sleep(sleep)
        if not candidates:
            candidates = openalex_search(title)
            if sleep:
                time.sleep(sleep)
        if candidates:
            top = candidates[0]
            if "title" in top and isinstance(top.get("title"), list):
                top_title = top["title"][0]
            else:
                top_title = top.get("title") or top.get("display_name") or ""
            sim = _title_similarity(title, top_title)
            # Extract authors from Crossref/OpenAlex format
            top_authors = []
            for a in top.get("author", []) or []:
                family = a.get("family", "")
                given = a.get("given", "")
                if family:
                    top_authors.append(f"{family}, {given}" if given else family)
            if not top_authors:  # OpenAlex format
                for au in top.get("authorships", []) or []:
                    name = (au.get("author") or {}).get("display_name", "")
                    if name:
                        top_authors.append(name)
            if sim >= 0.85:
                v.match = {
                    "source": "crossref/openalex",
                    "title": top_title,
                    "similarity": round(sim, 3),
                    "doi": top.get("DOI") or top.get("doi"),
                    "year": _crossref_year(top) if "DOI" in top else None,
                    "authors": top_authors,
                }
                if v.status == "unknown":
                    v.status = "verified_by_title"
                if "DOI" in top and top.get("DOI"):
                    v.suggested = _crossref_to_bibtex(top, entry.key)
                return _finalize(v, entry)
            else:
                v.issues.append(
                    f"closest match similarity {sim:.2f} too low: "
                    f"'{top_title[:80]}' (DOI: {top.get('DOI', '?')})"
                )
                v.status = "mismatch" if v.status == "unknown" else v.status
                # If similarity is non-trivial (0.4+), still surface as candidate-needs-review
                if sim >= 0.4 and "DOI" in top and top.get("DOI"):
                    v.match = {
                        "source": "crossref/openalex",
                        "title": top_title,
                        "similarity": round(sim, 3),
                        "doi": top.get("DOI"),
                        "year": _crossref_year(top),
                        "_needs_review": True,
                    }
                    v.suggested = _crossref_to_bibtex(top, entry.key)
        else:
            v.issues.append("no candidate found via Crossref or OpenAlex title search")
            v.status = "not_found" if v.status == "unknown" else v.status

    if v.status == "unknown":
        v.status = "not_found"
    return _finalize(v, entry)


# ----------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------


STATUS_ICON = {
    "verified": "OK",
    "verified_by_doi": "OK",
    "verified_by_arxiv": "OK",
    "verified_by_title": "OK",
    "needs_review": "REVIEW",
    "mismatch": "WARN",
    "substituted": "SUBST",
    "placeholder": "FAIL",
    "type_error": "WARN",
    "hallucination": "HALLU",
    "not_found": "FAIL",
    "unverified": "?",
    "skipped_offline": "SKIP",
    "unknown": "?",
}


def render_markdown(verdicts: list, bib_path: str, include_fix: bool = False) -> str:
    lines = [f"# Citation verification report -- {bib_path}", ""]
    counts = {}
    for v in verdicts:
        counts[v.status] = counts.get(v.status, 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    lines.append(f"**Summary:** {len(verdicts)} entries -- {summary}")
    lines.append("")

    # Sort by risk score descending (highest risk first), break ties by status priority
    verdicts_sorted = sorted(verdicts, key=lambda v: (-v.risk_score, v.key))

    for v in verdicts_sorted:
        icon = STATUS_ICON.get(v.status, "?")
        lines.append(f"## [{icon}] {v.key} -- {v.status} (risk {v.risk_score}/100)")
        lines.append("")
        if v.field_classification:
            labels = ", ".join(f"{k}={cls}" for k, cls in sorted(v.field_classification.items()))
            lines.append(f"**Field classification** (C=Correct, P=Partial, S=Substituted, F=Fabricated, M=Missing, X=N/A): {labels}")
            lines.append("")
        if v.issues:
            for iss in v.issues:
                lines.append(f"- {iss}")
            lines.append("")
        if v.match:
            needs_review = v.match.get("_needs_review")
            header = "**Candidate found (NEEDS MANUAL REVIEW — low similarity):**" if needs_review else "**Match found:**"
            lines.append(header)
            for k, val in v.match.items():
                if k.startswith("_"):
                    continue
                lines.append(f"- {k}: {val}")
            lines.append("")
        if include_fix and v.suggested:
            label = "**Suggested replacement (verify first):**" if v.match and v.match.get("_needs_review") else "**Suggested replacement:**"
            lines.append(label)
            lines.append("```bibtex")
            lines.append(v.suggested)
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify BibTeX entries against academic databases")
    ap.add_argument("bib", help="path to .bib file")
    ap.add_argument("--out", help="output file for the report (default: stdout)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--offline", action="store_true", help="skip network calls, run heuristics only")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any entry has issues")
    ap.add_argument("--fix", action="store_true", help="include suggested replacement BibTeX in report")
    ap.add_argument("--sleep", type=float, default=0.2, help="seconds between API calls (default 0.2)")
    args = ap.parse_args(argv)

    bib_path = Path(args.bib)
    if not bib_path.exists():
        print(f"error: file not found: {bib_path}", file=sys.stderr)
        return 2
    text = bib_path.read_text(encoding="utf-8", errors="replace")
    entries = parse_bib(text)
    if not entries:
        print(f"warning: no BibTeX entries found in {bib_path}", file=sys.stderr)
        return 0

    verdicts = []
    for i, e in enumerate(entries):
        print(f"[{i+1}/{len(entries)}] {e.key}...", file=sys.stderr, flush=True)
        v = verify_entry(e, offline=args.offline, sleep=args.sleep)
        verdicts.append(v)

    if args.json:
        output = json.dumps([asdict(v) for v in verdicts], indent=2, ensure_ascii=False)
    else:
        output = render_markdown(verdicts, str(bib_path), include_fix=args.fix)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"report written to {args.out}", file=sys.stderr)
    else:
        print(output)

    if args.strict:
        bad = sum(
            1 for v in verdicts
            if v.status in ("placeholder", "not_found", "mismatch", "type_error", "substituted", "hallucination")
        )
        if bad:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
