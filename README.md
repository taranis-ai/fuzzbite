# fuzzbite

Fast one-to-many ssdeep/CTPH fingerprint comparisons for Python. Hash an incoming
article once, prepare one `Matcher`, and pass bounded batches of stored
fingerprints to Rust. ffuzzy performs the hashing and scoring; PyO3 exposes three
public entry points. There are no Python runtime dependencies.

**Scores are not interchangeable with ppdeep.** In the checked corpus, one edited
article scores 90 in ppdeep and 83 here, changing rejection at threshold 90. See
[compatibility](#compatibility-with-ppdeep) before migrating a consumer.

## Install and develop

This repository has not been published to PyPI. To use the checkout in an existing
uv project:

```sh
uv add /absolute/path/to/fuzzbite
```

Building from source requires a C linker and Rust. CI and `rust-toolchain.toml`
pin Rust 1.98.1; PyO3's upstream minimum is 1.83. The declared source minimum in
Cargo.toml is 1.83, but this project's checks use 1.98.1. Supported interpreters
are standard, GIL-enabled CPython 3.10–3.14. Free-threaded CPython, PyPy, GraalPy,
Windows, and Python 3.15+ are not currently validated.

```sh
uv sync --locked --python 3.14
# After changing Rust source, explicitly rebuild the editable extension:
uv run --locked maturin develop --release --locked
cargo fmt --check
PYO3_PYTHON="$(uv python find)" cargo clippy --locked --all-targets -- -D warnings
PYO3_PYTHON="$(uv python find)" cargo test --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m pytest -q
```

Use `python -m pytest` as shown so the repository's benchmark corpus is importable.
`uv sync` uses maturin's release profile by default. Both dependency lockfiles are
versioned. `uv sync --locked` / `uv run --locked` check Python resolution;
Cargo checks use `--locked`, and `[tool.maturin] locked = true` applies to PEP 517
builds too. `uv build` has no `--locked` option: its sole build requirement is
pinned exactly to maturin 1.15.0, which has no Python runtime dependencies.

## API

```python
from collections.abc import Sequence

import fuzzbite

fingerprint = fuzzbite.hash(b"article bytes")
score = fuzzbite.compare(fingerprint, fingerprint)  # 100
matcher = fuzzbite.Matcher(fingerprint)
match = matcher.find_match([fingerprint], threshold=90)  # (0, 100)

# Typed signatures (the distribution includes .pyi and py.typed):
# hash(data: bytes) -> str
# compare(left: str, right: str) -> int
# Matcher(fingerprint: str)
# Matcher.find_match(candidates: Sequence[str], *, threshold: int = 90)
#     -> tuple[int, int] | None
```

`find_match` returns the **first qualifying candidate in input order**, with its
index within that batch and the unmodified integer ffuzzy score. It does not
search for the highest score. An immutable `Matcher` retains ffuzzy's prepared
comparison target across calls; it does not retain candidate batches.

A database integration can keep source/time selection, stable ordering, and
concurrency control in the ingestion service. For example, using an existing
DB-API connection and a cursor supporting `fetchmany`:

```python
from datetime import timedelta

import fuzzbite


def find_duplicate(connection, source_id, received_at, normalized_content: bytes):
    fingerprint = fuzzbite.hash(normalized_content)
    matcher = fuzzbite.Matcher(fingerprint)
    cursor = connection.cursor()
    try:
        # Placeholder syntax shown for PostgreSQL DB-API drivers.
        cursor.execute(
            """SELECT id, fingerprint FROM articles
               WHERE source_id = %s AND received_at >= %s AND received_at <= %s
               ORDER BY received_at, id""",
            (source_id, received_at - timedelta(days=30), received_at),
        )
        while rows := cursor.fetchmany(500):
            match = matcher.find_match([row[1] for row in rows], threshold=90)
            if match is not None:
                index, score = match
                return fingerprint, (rows[index][0], score)
        return fingerprint, None
    finally:
        cursor.close()
```

Use a server-side cursor if the driver otherwise buffers the entire result set.
The consumer owns content normalization, minimum article length, SQL/index design,
selection policy, transactions, and locking to prevent concurrent check/insert
races. This package has no database, persistent index, async API, or thread pool.

## Validation and execution semantics

- `hash` requires `bytes`; encode text explicitly. Mutable buffers and memoryviews
  raise `TypeError`. Empty data is valid and hashes to `3::`.
- Fingerprints use `blocksize:first:second`, with ffuzzy's Base64 alphabet,
  block sizes `3 * 2**n` for `0 <= n <= 30`, and raw digest lengths at most 64
  and 32. Empty components are accepted. ffuzzy normalizes runs longer than three
  characters for comparison. Hash generation preserves the raw fingerprint.
- ffuzzy's strict parser checks raw lengths even if normalization would shorten
  them. Filenames/CSV suffixes, trailing data, illegal characters, and invalid
  block sizes raise `ValueError`. Long/non-truncated ssdeep fingerprints with a
  second component over 32 characters are outside this initial API.
- Candidates must be a sequence of strings (for example list, tuple, or
  `collections.UserList`), not a generator, mapping, set, or a single string.
  All elements are copied to owned Rust strings before the GIL is released.
  **A wrong element type anywhere raises `TypeError`, even after an early match.**
- Fingerprint syntax is parsed during the Rust scan. Invalid syntax before the
  first match raises `ValueError` with the batch index. **Malformed strings after
  a match are not parsed.** If no candidate matches, all fingerprints are parsed.
- `threshold` is keyword-only, defaults to 90, and accepts 0 through 100 inclusive.
  Values outside that range raise `ValueError`, including on empty batches.
  Nonintegers raise `TypeError`; integers outside signed 64-bit range raise
  `OverflowError`. PyO3 accepts integer-like `__index__` values, including Python
  booleans (`False=0`, `True=1`).
- An empty batch returns `None`. Threshold 0 accepts the first valid fingerprint,
  even if its score is 0. Threshold 100 requires a score of 100, which does not
  imply byte-for-byte identical content. Identical empty/very short fingerprints
  can score 100: keep article-length rules in the consumer.

Hashing and comparison work use PyO3's `Python::detach`. Hashing borrows immutable
Python bytes whose argument reference keeps them alive; pairwise comparison uses
immutable string views; batch scoring uses owned Rust strings and an immutable
prepared target. No Python API calls occur in the detached scoring loop. The GIL
is held during candidate conversion. Additional batch memory is proportional to
the number and total byte size of the supplied strings, with one parsed candidate
at a time. Early exit saves scoring work but does not avoid copying that batch.

## Compatibility with ppdeep

The pinned baseline is **ppdeep 20260221**. Hash output agrees for all 46 checked
inputs: generated UTF-8 news text, small edits, empty/short inputs, repeated text,
zero bytes, random bytes, and sizes around 192 and 65,536 bytes. This is measured
coverage, not a claim of equality for every possible input.

The tests freeze scores for all **2,116 ordered pairs** from those inputs.
**96 pairs differ** between ffuzzy and ppdeep. Separate fixtures cover scores
88, 90, and 91 and exact threshold inclusion; the scaled score is discrete and
not every integer is produced by edit-distance scoring.

| Difference | ppdeep | fuzzbite / ffuzzy | Effect at threshold 90 |
|---|---|---|---|
| In an article generated with seed 42, replace eight `river` words with `canal` | 90 | 83 | ppdeep rejects; fuzzbite accepts |
| `3:abc:x` vs `3:abc:y` | 100 | 0 | ppdeep rejects; fuzzbite accepts |
| Nonstandard `4:abc:x` compared with itself | 100 | `ValueError` | Invalid stored data must be handled |

ppdeep's Levenshtein implementation assigns substitution cost 1; ffuzzy uses
ssdeep's insertion/deletion distance (substitution cost 2). ppdeep also short-cuts
to 100 when block size and the normalized **first** component agree, without
requiring agreement of the second. Its input validation is more permissive.
These differences are explicitly tested, including cases where the duplicate
decision changes. fuzzbite never adjusts scores to imitate ppdeep. Validate your
consumer's rejection policy on its own corpus before switching implementations.

References: [ppdeep source](https://github.com/elceef/ppdeep/blob/master/ppdeep.py),
[ffuzzy comparison documentation](https://docs.rs/ffuzzy/0.3.16/ssdeep/struct.FuzzyHashCompareTarget.html).

## Benchmarks

```sh
uv sync --locked --python 3.14
uv run --locked maturin develop --release --locked
uv run --locked python -m benchmarks.run --output benchmark-results.json
# Optional: examine smaller/larger consumer batches.
uv run --locked python -m benchmarks.run --batch-size 10 --output batches-10.json
```

The runner uses seed 20260911 and sets of 100, 1,000, and 10,000 candidates,
split into batches of 100 by default. Each size has no-match, first-candidate,
and last-candidate match workloads. All nonmatches share the target's block size
and seven-character substrings in **both** components, forcing edit-distance work.
These are valid synthetic digest variants derived from a generated article's
fingerprint, not claimed hashes of actual modified articles. The compatibility
suite separately exercises hashes of modified article content.

Corpus generation, candidate validation, and batch splitting occur before timing.
Each implementation includes its Python calls, conversions, scoring, and early
return. Results report preparation once per search, an already prepared matcher,
and preparation per batch. A separate batch-size sweep measures the effect of
reusing the prepared target. Hashing is timed separately. Every method checks its
result before timing, warms up/calibrates, then records five samples and their
median. The output includes loop counts, environment and dependency versions;
it imposes no performance thresholds.

Measured results and limitations are in [docs/benchmarks.md](docs/benchmarks.md),
with [raw samples](benchmarks/results-macos-arm64.json). On the initial local run,
full scans took roughly 1.7–1.8× less time than Python iteration over
`fuzzbite.compare`, and over 2,500× less than ppdeep on this intentionally
expensive comparison corpus. Early matches can favor individual Rust calls:
copying a batch has a cost. These ratios are workload-specific, not service-wide
speedup claims.

The optional `ssdeep` native wrapper is automatically measured if available in
the active uv environment. It was not installed locally, so this report has no
native-wrapper baseline. It requires an additional libfuzzy/CFFI setup; it is not
part of the locked required toolchain.

## Distributions and CI

```sh
uv build
uv run --locked python scripts/validate_artifacts.py
# Build ordinary Linux wheels on the corresponding native Linux machine:
MATURIN_PEP517_ARGS='--compatibility linux' uv build
# Install a wheel in a consumer uv project:
uv add /absolute/path/to/fuzzbite-0.1.0-cp310-abi3-linux_x86_64.whl
```

`uv build` builds an sdist and a wheel from it. The validation script independently
builds another wheel from the sdist and installs every wheel into fresh isolated
uv environments, outside the checkout, using CPython 3.10–3.14. It verifies API
behavior, the native import, package metadata, typing files, and license packaging.

| Platform | Artifact / support scope |
|---|---|
| Linux x86_64 | CI configured on native `ubuntu-24.04`; `linux_x86_64` wheel |
| Linux aarch64 | CI configured on native `ubuntu-24.04-arm`; `linux_aarch64` wheel |
| macOS arm64 | Locally verified; CI configured on `macos-14`; `macosx_11_0_arm64` wheel |

Wheels use CPython's `cp310-abi3` ABI, tested on standard CPython 3.10–3.14.
ABI tags can allow installation on newer interpreters even though they are not
yet in the supported/tested matrix. The macOS minimum is the build target, not a
claim that macOS 11 itself was tested. Linux wheels are ordinary native builds,
**not manylinux**; the tag does not promise compatibility across glibc versions
or distributions. Use a matching runtime or build from source. No musllinux,
Windows, or universal macOS wheels are supplied.

PRs and pushes to `main` (also `master` for this initially empty repository) run
locked tests and lint checks. Artifact jobs build on each native platform and
smoke-test every supported Python version. Third-party actions are pinned to
verified commit SHAs; permissions are read-only and superseded runs are cancelled.
The manual **Benchmarks** workflow uploads measured JSON without timing gates.
There is no release or publishing workflow and no publishing credentials.

See [the delivery checklist](docs/validation.md) for local evidence, CI status,
and packaging limitations. GitHub workflows are configured and syntax-checked;
that is distinct from a successful GitHub Actions run.

## Attribution and licensing

fuzzbite is **GPL-2.0-or-later**, consistent with its required
[ffuzzy dependency](https://github.com/a4lg/ffuzzy/tree/v0.3.16). PyO3 and maturin
are MIT OR Apache-2.0; ppdeep is Apache-2.0 and used only for development.
See [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and the
bundled [dependency license texts](licenses/THIRD_PARTY.txt).

Dependency versions, support requirements, and upstream documentation were checked
on 2026-09-11; see [docs/dependencies.md](docs/dependencies.md). No hashing or
matching algorithm is reimplemented here.
