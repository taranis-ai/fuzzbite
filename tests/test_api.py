from collections import UserList
from concurrent.futures import ThreadPoolExecutor

import fuzzbite
import pytest

REFERENCE = "3:iKFSMPn:rJPn"
LEFT = "12288:+ySwl5P+C5IxJ845HYV5sxOH/cccccccei:+Klhav84a5sxJ"
RIGHT = "12288:+yUwldx+C5IxJ845HYV5sxOH/cccccccex:+glvav84a5sxK"


def test_known_references():
    assert fuzzbite.hash(b"") == "3::"
    assert fuzzbite.hash(b"hello world") == REFERENCE
    assert fuzzbite.compare(LEFT, RIGHT) == 88
    assert fuzzbite.compare(REFERENCE, REFERENCE) == 100
    assert fuzzbite.compare(LEFT, REFERENCE) == 0


@pytest.mark.parametrize("sequence", [list, tuple, UserList])
def test_batch_order_and_reuse(sequence):
    matcher = fuzzbite.Matcher(LEFT)
    assert matcher.find_match(sequence([])) is None
    assert matcher.find_match(sequence([REFERENCE, RIGHT])) is None
    assert matcher.find_match(sequence([REFERENCE, RIGHT, LEFT]), threshold=88) == (
        1,
        88,
    )
    assert matcher.find_match(sequence([RIGHT, LEFT])) == (1, 100)
    assert matcher.find_match(sequence([LEFT, RIGHT]), threshold=88) == (0, 100)


@pytest.mark.parametrize("threshold", [0, 1, 88, 89, 90, 99, 100])
def test_batch_matches_sequential(threshold):
    hashes = [REFERENCE, RIGHT, LEFT, "3::"]
    for target in hashes:
        for batch in ([], hashes, list(reversed(hashes))):
            expected = next(
                (
                    (i, score)
                    for i, item in enumerate(batch)
                    if (score := fuzzbite.compare(target, item)) >= threshold
                ),
                None,
            )
            assert (
                fuzzbite.Matcher(target).find_match(batch, threshold=threshold)
                == expected
            )


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "nonsense",
        "0::",
        "4:abc:abc",
        "-3::",
        "3:a",
        "3:a:b:c",
        "3:é:b",
        "3:a:b\0",
        "3:a:b\n",
        "3:a:b,file",
        "3:" + "a" * 65 + ":",
        "3::" + "a" * 33,
        "6442450944::",
    ],
)
def test_invalid_fingerprints(bad):
    with pytest.raises(ValueError, match="invalid fingerprint"):
        fuzzbite.Matcher(bad)
    with pytest.raises(ValueError, match="invalid fingerprint"):
        fuzzbite.compare(REFERENCE, bad)
    with pytest.raises(ValueError, match="invalid fingerprint"):
        fuzzbite.compare(bad, REFERENCE)
    with pytest.raises(ValueError, match=r"candidates\[0\]"):
        fuzzbite.Matcher(REFERENCE).find_match([bad], threshold=0)


def test_early_exit_validation_contract():
    matcher = fuzzbite.Matcher(REFERENCE)
    assert matcher.find_match([REFERENCE, "invalid"]) == (0, 100)
    with pytest.raises(ValueError, match=r"candidates\[1\]"):
        matcher.find_match([LEFT, "invalid", REFERENCE])
    # Python-to-Rust conversion visits the whole batch, before scoring begins.
    with pytest.raises(TypeError):
        matcher.find_match([REFERENCE, None])


@pytest.mark.parametrize("bad", [None, 1, b"3::"])
def test_wrong_fingerprint_types(bad):
    with pytest.raises(TypeError):
        fuzzbite.Matcher(bad)
    with pytest.raises(TypeError):
        fuzzbite.compare(bad, REFERENCE)
    with pytest.raises(TypeError):
        fuzzbite.compare(REFERENCE, bad)


@pytest.mark.parametrize(
    "bad", [None, "hello", 42, bytearray(b"abc"), memoryview(b"abc")]
)
def test_hash_requires_bytes(bad):
    with pytest.raises(TypeError):
        fuzzbite.hash(bad)


@pytest.mark.parametrize(
    "bad", [None, "3::", b"3::", {REFERENCE}, {REFERENCE: 1}, iter([REFERENCE]), [3]]
)
def test_batch_requires_a_sequence_of_strings(bad):
    with pytest.raises(TypeError):
        fuzzbite.Matcher(REFERENCE).find_match(bad)


@pytest.mark.parametrize("threshold", [-1, 101, -1000, 1000])
def test_threshold_range_even_for_empty_batches(threshold):
    with pytest.raises(ValueError, match="threshold"):
        fuzzbite.Matcher(REFERENCE).find_match([], threshold=threshold)


@pytest.mark.parametrize("threshold", [None, "90", 90.0])
def test_threshold_type(threshold):
    with pytest.raises(TypeError):
        fuzzbite.Matcher(REFERENCE).find_match([], threshold=threshold)


def test_threshold_keyword_only_and_integer_conversion():
    matcher = fuzzbite.Matcher(REFERENCE)
    with pytest.raises(TypeError):
        matcher.find_match([], 90)
    with pytest.raises(OverflowError):
        matcher.find_match([], threshold=2**100)
    assert matcher.find_match([LEFT], threshold=0) == (0, 0)
    assert matcher.find_match([LEFT], threshold=False) == (0, 0)
    assert matcher.find_match([REFERENCE], threshold=100) == (0, 100)


def test_shared_matcher_is_immutable_and_safe_to_reuse():
    matcher = fuzzbite.Matcher(LEFT)
    with pytest.raises(AttributeError):
        matcher.target = RIGHT
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(matcher.find_match, [[RIGHT] * 100 + [LEFT]] * 20))
    assert results == [(100, 100)] * 20
