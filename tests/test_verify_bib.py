"""Tests for verify_bib.py.

Offline tests run without network. Network tests are marked with the
@pytest.mark.network decorator and can be skipped with -m "not network".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the script importable as a module
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = REPO_ROOT / "skills" / "bib-verify" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import verify_bib as vb  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


# ----------------------------------------------------------------------
# BibTeX parser
# ----------------------------------------------------------------------


class TestParser:
    def test_parses_clean_file(self):
        text = (FIXTURES / "clean.bib").read_text(encoding="utf-8")
        entries = vb.parse_bib(text)
        assert len(entries) == 3
        keys = [e.key for e in entries]
        assert "peng2021sfcn" in keys
        assert "hoopes2022synthstrip" in keys
        assert "sullivan2019pyvista" in keys

    def test_handles_nested_braces(self):
        text = "@article{key1, title={Nested {brace} test}, year={2024}}"
        entries = vb.parse_bib(text)
        assert len(entries) == 1
        assert entries[0].get("title") == "Nested {brace} test"

    def test_handles_multiline_fields(self):
        text = (FIXTURES / "clean.bib").read_text(encoding="utf-8")
        entries = vb.parse_bib(text)
        peng = next(e for e in entries if e.key == "peng2021sfcn")
        # author field wraps across multiple lines
        assert "Peng, Han" in peng.get("author")
        assert "Smith, Stephen M." in peng.get("author")

    def test_empty_file(self):
        assert vb.parse_bib("") == []

    def test_skips_meta_entries(self):
        text = "@comment{ignored}\n@string{var=value}\n@article{real, year={2024}}"
        entries = vb.parse_bib(text)
        assert len(entries) == 1
        assert entries[0].key == "real"


# ----------------------------------------------------------------------
# Offline heuristics
# ----------------------------------------------------------------------


class TestOfflineHeuristics:
    @pytest.fixture
    def ai_entries(self):
        text = (FIXTURES / "ai_patterns.bib").read_text(encoding="utf-8")
        return vb.parse_bib(text)

    def test_detects_xxxxx_placeholder(self, ai_entries):
        ghost = next(e for e in ai_entries if e.key == "ghost_synthba")
        issues = vb.offline_checks(ghost)
        assert any("placeholder" in i.lower() for i in issues)

    def test_detects_inproceedings_journal_confusion(self, ai_entries):
        bad = next(e for e in ai_entries if e.key == "peng_typeconfusion")
        issues = vb.offline_checks(bad)
        assert any("inproceedings" in i.lower() and "journal" in i.lower() for i in issues)

    def test_detects_lonely_and_others(self, ai_entries):
        lonely = next(e for e in ai_entries if e.key == "lonely_author")
        issues = vb.offline_checks(lonely)
        assert any("and others" in i.lower() for i in issues)

    def test_detects_missing_identifier_on_recent_paper(self, ai_entries):
        no_id = next(e for e in ai_entries if e.key == "no_identifier_2023")
        issues = vb.offline_checks(no_id)
        assert any("doi or eprint" in i.lower() for i in issues)

    def test_detects_vague_preprint_note(self, ai_entries):
        vague = next(e for e in ai_entries if e.key == "vague_preprint")
        issues = vb.offline_checks(vague)
        assert any("preprint" in i.lower() and "identifier" in i.lower() for i in issues)

    def test_detects_question_mark_placeholder(self, ai_entries):
        qmark = next(e for e in ai_entries if e.key == "placeholder_qmark")
        issues = vb.offline_checks(qmark)
        assert any("placeholder" in i.lower() for i in issues)

    def test_clean_file_has_no_offline_issues(self):
        text = (FIXTURES / "clean.bib").read_text(encoding="utf-8")
        for entry in vb.parse_bib(text):
            issues = vb.offline_checks(entry)
            assert issues == [], f"{entry.key} unexpectedly flagged: {issues}"


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


class TestAuthorOverlap:
    def test_full_overlap(self):
        claimed = "Smith, John and Doe, Jane"
        found = ["Smith, John", "Doe, Jane"]
        assert vb._author_overlap(claimed, found) == 1.0

    def test_partial_overlap(self):
        claimed = "Smith, John and Doe, Jane and Park, Sam"
        found = ["Smith, J.", "Bogus, X.", "Park, S."]
        # 2 of 3 last names match (Smith, Park)
        assert vb._author_overlap(claimed, found) == pytest.approx(2 / 3)

    def test_zero_overlap(self):
        assert vb._author_overlap("Smith, John", ["Wong, K."]) == 0.0

    def test_ignores_and_others(self):
        claimed = "Smith, John and others"
        found = ["Smith, John", "Doe, Jane"]
        assert vb._author_overlap(claimed, found) == 1.0  # only Smith counted in claimed

    def test_empty_inputs(self):
        assert vb._author_overlap("", ["Smith"]) == 1.0
        assert vb._author_overlap("Smith, J", []) == 1.0


class TestFieldClassification:
    def test_exact_match_all_C(self):
        entry = vb.BibEntry(
            key="k", type="article",
            fields={"title": "Hello World", "year": "2024", "doi": "10.1/abc",
                    "author": "Smith, John"},
        )
        match = {"title": "Hello World", "year": "2024", "doi": "10.1/abc",
                 "authors": ["Smith, John"]}
        cls = vb._classify_fields(entry, match)
        assert cls["title"] == "C"
        assert cls["year"] == "C"
        assert cls["doi"] == "C"
        assert cls["author"] == "C"

    def test_partial_title_classified_P(self):
        # Realistic shortened-title case: user trimmed a long published title.
        entry = vb.BibEntry(
            key="k", type="article",
            fields={
                "title": "FaceAge predicting biological age from face photographs with deep learning",
                "year": "2025",
            },
        )
        match = {
            "title": "FaceAge predicting biological age from face photographs to improve prognostication a model development study",
            "year": "2025",
        }
        cls = vb._classify_fields(entry, match)
        assert cls["title"] == "P"

    def test_completely_wrong_title_F_or_S(self):
        entry = vb.BibEntry(
            key="k", type="article",
            fields={"title": "Quantum Physics"},
        )
        match = {"title": "Pancake Recipes Through the Ages"}
        cls = vb._classify_fields(entry, match)
        assert cls["title"] in ("S", "F")


class TestEntryStatusRollup:
    def test_all_C_verified(self):
        cls = {"title": "C", "year": "C", "author": "C", "doi": "C"}
        assert vb._entry_status_from_fields(cls, "verified_by_doi") == "verified"

    def test_F_anywhere_escalates_to_hallucination(self):
        cls = {"title": "C", "year": "C", "author": "F"}
        assert vb._entry_status_from_fields(cls, "verified_by_doi") == "hallucination"

    def test_S_anywhere_escalates_to_substituted(self):
        cls = {"title": "C", "year": "C", "author": "S"}
        assert vb._entry_status_from_fields(cls, "verified_by_doi") == "substituted"

    def test_three_severe_co_occurrence_is_hallucination(self):
        cls = {"title": "S", "year": "S", "author": "S", "doi": "C"}
        assert vb._entry_status_from_fields(cls, "verified") == "hallucination"

    def test_P_title_with_strong_anchor_kept_verified(self):
        # Shortened title is common; DOI=C + author=C should override
        cls = {"title": "P", "year": "C", "author": "C", "doi": "C"}
        assert vb._entry_status_from_fields(cls, "verified_by_doi") == "verified_by_doi"

    def test_P_title_without_anchor_escalates(self):
        cls = {"title": "P", "year": "C"}  # no DOI, no author
        assert vb._entry_status_from_fields(cls, "verified_by_title") == "needs_review"


class TestIdentifierHijacking:
    """The cited DOI resolves but to a different paper; the claimed
    title+authors point to a *different* real DOI. Uses monkeypatched
    crossref_search so the test is deterministic and offline."""

    def _entry(self):
        # Mimics the Barch HCP-task case: a real paper cited with a DOI
        # that actually belongs to a sibling paper of the same project.
        return vb.BibEntry(
            key="barch2013hcptask",
            type="article",
            fields={
                "title": "Function in the human connectome: task-fMRI and individual differences",
                "author": "Barch, Deanna M. and Burgess, Gregory C. and Harms, Michael P.",
                "doi": "10.1016/j.neuroimage.2013.05.033",  # cited (wrong) DOI
                "year": "2013",
            },
        )

    def test_detects_hijack_when_title_and_authors_point_elsewhere(self, monkeypatch):
        # The claimed title+authors match a DIFFERENT DOI in the search results.
        fake_candidates = [
            {
                "title": ["Function in the human connectome: task-fMRI and individual differences in behavior"],
                "DOI": "10.1016/j.neuroimage.2013.05.033.CORRECT",
                "author": [
                    {"family": "Barch", "given": "Deanna M."},
                    {"family": "Burgess", "given": "Gregory C."},
                    {"family": "Harms", "given": "Michael P."},
                ],
            }
        ]
        monkeypatch.setattr(vb, "crossref_search", lambda *a, **k: fake_candidates)
        v = vb.Verdict(key="barch2013hcptask", type="article", status="substituted")
        vb._detect_identifier_hijacking(v, self._entry(), sleep=0)
        assert v.hijack is not None
        assert v.hijack["correct_doi"] == "10.1016/j.neuroimage.2013.05.033.CORRECT"
        assert any("identifier hijacking" in i.lower() for i in v.issues)

    def test_no_hijack_when_authors_disagree(self, monkeypatch):
        # Same title, but totally different authors -> a different paper,
        # NOT a hijack. Must not fire (keeps false positives down).
        fake_candidates = [
            {
                "title": ["Function in the human connectome: task-fMRI and individual differences"],
                "DOI": "10.9999/unrelated",
                "author": [
                    {"family": "Nguyen", "given": "T."},
                    {"family": "Okonkwo", "given": "B."},
                    {"family": "Silva", "given": "R."},
                ],
            }
        ]
        monkeypatch.setattr(vb, "crossref_search", lambda *a, **k: fake_candidates)
        v = vb.Verdict(key="barch2013hcptask", type="article", status="substituted")
        vb._detect_identifier_hijacking(v, self._entry(), sleep=0)
        assert v.hijack is None

    def test_no_hijack_when_candidate_doi_equals_cited(self, monkeypatch):
        # Candidate found, but its DOI is the same as the cited one -> not
        # a hijack (just the normal substituted case).
        entry = self._entry()
        fake_candidates = [
            {
                "title": ["Function in the human connectome: task-fMRI and individual differences"],
                "DOI": entry.get("doi"),  # same as cited
                "author": [
                    {"family": "Barch", "given": "Deanna M."},
                    {"family": "Burgess", "given": "Gregory C."},
                    {"family": "Harms", "given": "Michael P."},
                ],
            }
        ]
        monkeypatch.setattr(vb, "crossref_search", lambda *a, **k: fake_candidates)
        v = vb.Verdict(key="barch2013hcptask", type="article", status="substituted")
        vb._detect_identifier_hijacking(v, entry, sleep=0)
        assert v.hijack is None

    def test_no_hijack_when_no_candidates(self, monkeypatch):
        monkeypatch.setattr(vb, "crossref_search", lambda *a, **k: [])
        v = vb.Verdict(key="barch2013hcptask", type="article", status="substituted")
        vb._detect_identifier_hijacking(v, self._entry(), sleep=0)
        assert v.hijack is None

    def test_hijack_sets_suggested_when_empty(self, monkeypatch):
        fake_candidates = [
            {
                "title": ["Function in the human connectome: task-fMRI and individual differences"],
                "DOI": "10.1016/j.neuroimage.2013.05.033.CORRECT",
                "author": [
                    {"family": "Barch", "given": "Deanna M."},
                    {"family": "Burgess", "given": "Gregory C."},
                    {"family": "Harms", "given": "Michael P."},
                ],
                "container-title": ["NeuroImage"],
                "type": "journal-article",
                "issued": {"date-parts": [[2013]]},
            }
        ]
        monkeypatch.setattr(vb, "crossref_search", lambda *a, **k: fake_candidates)
        v = vb.Verdict(key="barch2013hcptask", type="article", status="substituted")
        vb._detect_identifier_hijacking(v, self._entry(), sleep=0)
        assert v.suggested is not None
        assert "CORRECT" in v.suggested


# ----------------------------------------------------------------------
# End-to-end on fixtures
# ----------------------------------------------------------------------


class TestOfflineEndToEnd:
    def test_clean_fixture_passes_strict(self):
        text = (FIXTURES / "clean.bib").read_text(encoding="utf-8")
        verdicts = [
            vb.verify_entry(e, offline=True)
            for e in vb.parse_bib(text)
        ]
        bad = [v for v in verdicts if v.status in ("placeholder", "type_error", "hallucination")]
        assert bad == [], f"clean fixture should not be flagged, got: {[(v.key, v.status) for v in bad]}"

    def test_ai_patterns_fixture_all_flagged(self):
        text = (FIXTURES / "ai_patterns.bib").read_text(encoding="utf-8")
        verdicts = [
            vb.verify_entry(e, offline=True)
            for e in vb.parse_bib(text)
        ]
        # Every entry in ai_patterns.bib should generate at least one issue
        unflagged = [v for v in verdicts if not v.issues]
        assert unflagged == [], f"ai patterns should be flagged: {[v.key for v in unflagged]}"


# ----------------------------------------------------------------------
# Network tests (skip if no internet)
# ----------------------------------------------------------------------


@pytest.mark.network
class TestNetworkResolution:
    def test_crossref_resolves_known_doi(self):
        item = vb.crossref_by_doi("10.1016/j.media.2020.101871")
        assert item is not None
        assert "neural networks" in vb._crossref_title(item).lower()

    def test_crossref_returns_none_for_fake_doi(self):
        item = vb.crossref_by_doi("10.9999/totally-fake-doi-xxxxx")
        assert item is None

    def test_arxiv_resolves_known_id(self):
        ax = vb.arxiv_lookup("2406.00365")
        if ax is None:
            pytest.skip("arXiv API rate-limited or unreachable")
        assert "synthba" in ax["title"].lower()

    def test_arxiv_rejects_placeholder(self):
        ax = vb.arxiv_lookup("2210.xxxxx")
        assert ax is None
