"""Deterministic synthetic news text; no network or private article data."""

import random

WORDS = (
    "council residents river district research transport energy public report "
    "announced market project schools regional funding workers community "
    "Vienna München café climate evidence growth plan budget September"
).split()


def article(seed: int, words: int = 600) -> bytes:
    rng = random.Random(seed)
    paragraphs = [
        " ".join(rng.choices(WORDS, k=50)).capitalize() + "."
        for _ in range((words + 49) // 50)
    ]
    return ("Regional news update\n\n" + "\n\n".join(paragraphs)).encode()


def compatibility_inputs() -> list[bytes]:
    base = article(42)
    inputs = [b"", b"hello world", "Grüße aus Wien — 東京 📰".encode()]
    inputs += [base[:size] for size in (1, 6, 7, 31, 64, 191, 192, 193, 512, 1024)]
    inputs += [article(seed) for seed in range(5)]
    inputs += [base]
    inputs += [base.replace(b"river", b"canal", count) for count in (1, 2, 4, 8, 16)]
    inputs += [base[:i] + b" Updated." + base[i:] for i in (0, 100, 1000)]
    inputs += [base * count for count in (2, 4, 16)]
    inputs += [b"a" * size for size in (1, 7, 64, 1000, 65537)]
    inputs += [b"\0" * size for size in (1, 7, 192, 1000)]
    inputs += [
        random.Random(size).randbytes(size)
        for size in (3, 65, 193, 4096, 65535, 65536, 65537)
    ]
    return inputs
