import json
from pathlib import Path

import fuzzbite
import pytest

from scripts.compare_articles import compare_sources

CORPUS = Path(__file__).resolve().parents[1] / "testdata/baerbock-columbia"


@pytest.mark.live
def test_live_articles_match_baseline():
    sources = json.loads((CORPUS / "sources.json").read_text(encoding="utf-8"))
    baseline = json.loads((CORPUS / "comparison.json").read_text(encoding="utf-8"))
    current = compare_sources(sources)
    assert current["scores"] == baseline["scores"], "Live pairwise scores changed"
    assert current["articles"] == baseline["articles"], (
        "Extracted bytes or fingerprints changed even though scores match; "
        "inspect the source/extractor before updating the baseline"
    )


def test_same_event_orf_is_an_expected_zero():
    baseline = json.loads((CORPUS / "comparison.json").read_text(encoding="utf-8"))
    orf = baseline["articles"]["orf.txt"]["fuzzy_hash"]
    assert orf.split(":", 1)[0] == "12"
    for name, article in baseline["articles"].items():
        if name != "orf.txt":
            # ssdeep cannot compare block sizes 12 and 48, despite shared reporting.
            assert article["fuzzy_hash"].split(":", 1)[0] == "48"
            assert fuzzbite.compare(orf, article["fuzzy_hash"]) == 0
            assert baseline["scores"]["orf.txt"][name] == 0


def test_local_comparison_uses_exact_file_bytes(tmp_path):
    contents = {
        "first.txt": b"The weather station measures rainfall every hour. " * 30,
        "duplicate.txt": b"The weather station measures rainfall every hour. " * 30,
        "edited.txt": b"The weather station measures snowfall every hour. " * 30,
    }
    for name, data in contents.items():
        (tmp_path / name).write_bytes(data)
    result = compare_sources(dict.fromkeys(contents, "https://example.com"), tmp_path)
    assert result["input"] == "local_files"
    for left, data in contents.items():
        assert result["articles"][left]["fuzzy_hash"] == fuzzbite.hash(data)
        assert result["articles"][left]["bytes"] == len(data)
        for right, other in contents.items():
            assert result["scores"][left][right] == fuzzbite.compare(
                fuzzbite.hash(data), fuzzbite.hash(other)
            )
    assert result["scores"]["first.txt"]["duplicate.txt"] == 100
    (tmp_path / "edited.txt").write_bytes(b"")
    with pytest.raises(ValueError, match="Empty content"):
        compare_sources(dict.fromkeys(contents, "https://example.com"), tmp_path)


def test_saved_article_scores_can_be_recomputed_offline():
    report = json.loads((CORPUS / "comparison.json").read_text(encoding="utf-8"))
    sources = json.loads((CORPUS / "sources.json").read_text(encoding="utf-8"))
    assert set(report["articles"]) == set(report["scores"]) == set(sources)
    for left, article in report["articles"].items():
        assert article["url"] == sources[left]
        assert set(report["scores"][left]) == set(sources)
        for right, other in report["articles"].items():
            assert report["scores"][left][right] == fuzzbite.compare(
                article["fuzzy_hash"], other["fuzzy_hash"]
            )
