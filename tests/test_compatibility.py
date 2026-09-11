"""ppdeep is a differential baseline, not a score oracle for ffuzzy."""

import json
from pathlib import Path

import fuzzbite
import ppdeep
import pytest

from benchmarks.corpus import article, compatibility_inputs


@pytest.mark.parametrize(
    "data", compatibility_inputs(), ids=lambda data: f"{len(data)}B"
)
def test_hashes_match_ppdeep(data):
    assert fuzzbite.hash(data) == ppdeep.hash(data)


def test_article_edits_include_a_duplicate_decision_change():
    data = article(42)
    target = fuzzbite.hash(data)
    # ppdeep uses substitution cost 1; ssdeep/ffuzzy uses insertion/deletion cost 2.
    for count, rust_score, python_score in [
        (1, 99, 100),
        (2, 97, 99),
        (4, 93, 96),
        (8, 83, 90),
        (16, 60, 75),
    ]:
        candidate = fuzzbite.hash(data.replace(b"river", b"canal", count))
        assert fuzzbite.compare(target, candidate) == rust_score
        assert ppdeep.compare(target, candidate) == python_score
        match = fuzzbite.Matcher(target).find_match([candidate])
        assert (match is not None) == (rust_score >= 90)
        if count == 8:
            assert python_score >= 90 and match is None


def test_ppdeep_shortcut_ignores_second_component():
    left, right = "3:abc:x", "3:abc:y"
    assert ppdeep.compare(left, right) == 100
    assert fuzzbite.compare(left, right) == 0
    assert fuzzbite.Matcher(left).find_match([right]) is None


def test_ppdeep_accepts_nonstandard_hashes_that_fuzzbite_rejects():
    for value in ("4:abc:x", "3:!!!:x", "3:" + "a" * 65 + ":"):
        assert ppdeep.compare(value, value) == 100
        with pytest.raises(ValueError):
            fuzzbite.compare(value, value)


def test_reference_score_matrix():
    # Frozen outputs of both pinned upstream implementations, over real hashes.
    # Includes empty/short/repeated content and same/double/distant block sizes.
    fixture = json.loads((Path(__file__).parent / "scores.json").read_text())
    hashes = [fuzzbite.hash(data) for data in compatibility_inputs()]
    assert hashes == fixture["hashes"]
    for i, left in enumerate(hashes):
        for j, right in enumerate(hashes):
            assert fuzzbite.compare(left, right) == fixture["ffuzzy"][i][j]
            assert ppdeep.compare(left, right) == fixture["ppdeep"][i][j]


def test_threshold_neighborhood():
    fixture = json.loads((Path(__file__).parent / "scores.json").read_text())
    for case in fixture["threshold_cases"]:
        left, right, score, baseline = case
        assert fuzzbite.compare(left, right) == score
        assert ppdeep.compare(left, right) == baseline
        assert fuzzbite.Matcher(left).find_match([right], threshold=score) == (0, score)
        assert fuzzbite.Matcher(left).find_match([right], threshold=score + 1) is None
