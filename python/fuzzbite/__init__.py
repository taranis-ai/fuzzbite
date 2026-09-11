"""Fast ssdeep hashing and deterministic batched fingerprint matching."""

from ._native import Matcher, compare, hash

__all__ = ["Matcher", "compare", "hash"]
