# fuzzbite

Fast fuzzy hashing and one-to-many fingerprint comparisons for Python, powered
by [ffuzzy](https://github.com/a4lg/ffuzzy) and Rust.

Use ssdeep/CTPH fingerprints to find similar content. Hash a document once, then
reuse a `Matcher` to search batches of stored fingerprints. No Python runtime
dependencies.

## Installation

Install from PyPI with [uv](https://docs.astral.sh/uv/):

```sh
uv add fuzzbite
```

The release workflow builds precompiled wheels for Linux x86_64 and aarch64
(glibc 2.17+, including Debian/Ubuntu containers), and macOS arm64, with standard
CPython 3.10–3.14. Wheel installs require no Rust, Cargo, or C compiler.
Alpine/musl, other platforms, and installs directly from Git require a source
build with Rust and a C linker.

Linux wheels are available starting with **0.1.1**; 0.1.0 only has a macOS wheel.
To prevent silent source builds in a deployment, use
`uv pip install --only-binary=:all: fuzzbite`.

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

Reuse the matcher across batches. Each result contains the candidate's index
within that batch and its score, or `None` if nothing meets the threshold.
Matching stops at the first qualifying candidate; it does not find the best match.

## API

| Function | Returns |
| --- | --- |
| `hash(data: bytes)` | An ssdeep fingerprint string |
| `compare(left: str, right: str)` | An integer similarity score from 0 to 100 |
| `Matcher(fingerprint: str)` | A reusable comparison target |
| `matcher.find_match(candidates, *, threshold=90)` | `(index, score)` or `None` |

- Encode text to `bytes` before hashing.
- Pass candidates as a sequence of strings, such as a list or tuple. Generators
  are not accepted.
- Thresholds range from 0 to 100, inclusive. An empty batch returns `None`.
- Fingerprints must use `blocksize:first:second`, with valid ssdeep block sizes
  and digest lengths of at most 64 and 32 characters. Invalid fingerprints raise
  `ValueError`; filename suffixes and long-form second digests are not supported.
- Candidate types are checked for the entire batch. Fingerprint syntax is checked
  only up to the first match, so malformed strings after a match are not parsed.

Hashing and scoring release the GIL. Candidate batches are copied before scanning,
so use bounded batches for large collections. Content normalization, minimum
content length, and storage are handled by the caller. A score of 100 does not
prove that the original content is identical.

## Compatibility

fuzzbite uses ffuzzy's ssdeep scoring. **Scores can differ from ppdeep**, so test
your similarity threshold before switching implementations.

The compatibility suite compares 46 inputs and 2,116 ordered pairs against
ppdeep 20260221. Hashes agree for those inputs; scores differ for 96 pairs.
For example, one edited article scores 90 with ppdeep and 83 with fuzzbite.
ffuzzy also validates fingerprints more strictly than ppdeep.

## Benchmarks

On the included synthetic comparison corpus, full scans with `Matcher` took
roughly 1.7–1.8× less time than a Python loop over `fuzzbite.compare`. Immediate
matches can be faster with a single comparison because batching copies candidates.

See [benchmark results and methodology](docs/benchmarks.md) for timings,
ppdeep comparisons, and workload details. To run the benchmarks:

```sh
uv run --locked python -m benchmarks.run --output benchmark-results.json
```

## Development

```sh
git clone https://github.com/taranis-ai/fuzzbite.git
cd fuzzbite
uv sync --locked --python 3.14
```

After changing Rust code, rebuild the extension:

```sh
uv run --locked maturin develop --release --locked
```

Run checks:

```sh
cargo fmt --check
PYO3_PYTHON="$(uv python find)" cargo clippy --locked --all-targets -- -D warnings
PYO3_PYTHON="$(uv python find)" cargo test --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m pytest -q
```

Build and verify distributions:

```sh
uv build
uv run --locked python scripts/validate_artifacts.py
```

On Linux, set `MATURIN_PEP517_ARGS='--compatibility linux'` for both commands.
These local Linux wheels are platform-specific and cannot be uploaded to PyPI.
CI checks all supported Python versions plus the latest stable Python. Linux
wheels are built in manylinux2014 containers and installed with source builds
disabled into compiler-free Python 3.10–3.14 slim containers on both architectures.
The same Linux workflow runs before publishing. Workflows follow upstream action
branches, latest uv, and stable Rust. Ubuntu x86_64 and macOS use `-latest` runners; Ubuntu ARM uses
`ubuntu-26.04-arm` because GitHub does not provide a `ubuntu-latest-arm` label.

## Publishing

The [release workflow](.github/workflows/release.yml) publishes a source archive
and macOS arm64 and manylinux2014 x86_64/aarch64 wheels when a GitHub release is
published. Publishing waits for every build and installation check to pass.

Configure PyPI Trusted Publishing with these values:

| Field | Value |
| --- | --- |
| PyPI project name | `fuzzbite` |
| Owner | `taranis-ai` |
| Repository name | `fuzzbite` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Create the `pypi` environment in the repository's GitHub settings and configure
required reviewers to approve uploads. No PyPI API token is needed. The workflow
must be committed before creating a release. Keep versions in `pyproject.toml`
and `Cargo.toml` aligned, and use a matching tag such as `v0.1.1`.

Release checklist:

1. Update the version in `pyproject.toml`, `Cargo.toml`, and `scripts/smoke.py`,
   and regenerate `uv.lock` and `Cargo.lock`.
2. Run CI, publish the matching GitHub release, and approve the PyPI upload.
3. Verify binary-only installation from PyPI on both Linux architectures.
4. Update consumers' version pins and refresh their lockfiles so they include
   the new wheels. Advance any `exclude-newer-package` cutoff past the upload
   time; an older cutoff can hide the wheels. Then remove compiler installation
   workarounds and verify their container builds.

## License

[GPL-2.0-or-later](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md)
for dependency licenses.
