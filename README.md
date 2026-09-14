# fuzzbite

Fast ssdeep-compatible fuzzy hashing and batch comparisons for Python, powered
by [ffuzzy](https://github.com/a4lg/ffuzzy) and Rust. No Python runtime dependencies.

## Installation

```sh
uv add fuzzbite
```

Supports Python 3.12–3.14.

## Quick start

```python
import fuzzbite

content = b"The river monitoring station reports water levels every morning. " * 20
fingerprint = fuzzbite.hash(content)

# Compare two fingerprints: scores range from 0 to 100.
score = fuzzbite.compare(fingerprint, fingerprint)  # 100

# Find the first candidate scoring at least 90.
matcher = fuzzbite.Matcher(fingerprint)
match = matcher.find_match([fingerprint], threshold=90)  # (0, 100)
```

Reuse the matcher across batches. Results contain the candidate's index within
that batch and its score, or `None` if nothing matches. It returns the first
qualifying match, not necessarily the best one.

## API

| Function | Returns |
| --- | --- |
| `hash(data: bytes)` | An ssdeep fingerprint string |
| `compare(left: str, right: str)` | A similarity score from 0 to 100 |
| `Matcher(fingerprint: str)` | A reusable comparison target |
| `matcher.find_match(candidates, *, threshold=90)` | `(index, score)` or `None` |

- Encode text to bytes before hashing: `fuzzbite.hash(text.encode("utf-8"))`.
- Pass candidates as a list or tuple of fingerprints. Use bounded batches for
  large collections.
- Thresholds must be between 0 and 100. Empty batches return `None`.
- Malformed fingerprints raise `ValueError` when parsed. Filename suffixes and
  long-form ssdeep digests are unsupported.
- A score of 100 does not guarantee identical content. **Scores can differ from
  ppdeep**, so check your threshold when switching.

[Benchmarks](docs/benchmarks.md) · [GPL-2.0-or-later](LICENSE) ·
[Third-party licenses](THIRD_PARTY_NOTICES.md)
