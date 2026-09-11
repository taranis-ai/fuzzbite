# Measured benchmarks

Measured on 2026-09-11: Apple M4 Pro (12 logical CPUs), macOS 26.6.2 arm64,
CPython 3.14.7, Rust 1.98.1, uv 0.12.10. Release extension; no CPU affinity
or frequency pinning. Five calibrated samples per measurement. ffuzzy 0.3.16,
PyO3 0.29.2, maturin 1.15.0, ppdeep 20260221, fuzzbite 0.1.0.

Run `uv run --locked python -m benchmarks.run --output benchmark-results.json`.
See [raw samples](../benchmarks/results-macos-arm64.json) for all medians, sample
values, iteration counts, and parameters. Corpus generation and batch splitting
are excluded. Times below include Python/Rust conversion and target preparation
once per search. Default batch size is 100; each search has the stated number of
candidates. An early match stops at the first candidate; a late match is last.

| Candidates | Workload | ppdeep loop (ms) | fuzzbite loop (ms) | Matcher incl. preparation (ms) | vs ppdeep | vs fuzzbite loop |
|---:|---|---:|---:|---:|---:|---:|
| 100 | no_match | 52.302916 | 0.034658 | 0.018959 | 2758.7× | 1.83× |
| 100 | early_match | 0.005451 | 0.000353 | 0.003002 | 1.8× | 0.12× |
| 100 | late_match | 52.622458 | 0.034442 | 0.018880 | 2787.2× | 1.82× |
| 1,000 | no_match | 544.626167 | 0.385541 | 0.207074 | 2630.1× | 1.86× |
| 1,000 | early_match | 0.005623 | 0.000353 | 0.003191 | 1.8× | 0.11× |
| 1,000 | late_match | 553.615083 | 0.373208 | 0.216466 | 2557.5× | 1.72× |
| 10,000 | no_match | 5458.972958 | 3.609805 | 2.072822 | 2633.6× | 1.74× |
| 10,000 | early_match | 0.005425 | 0.000352 | 0.003205 | 1.7× | 0.11× |
| 10,000 | late_match | 5298.328042 | 3.565924 | 2.043997 | 2592.1× | 1.74× |

## Preparation and reuse

A single target preparation took 0.219 µs (median).
The main results include this cost once for each search. The raw report also
records an already prepared target and a fresh target per batch. The following
sweep makes preparation frequency visible: 1,000 compatible nonmatches, five
samples, with all conversion and scanning costs included.

| Batch size | Prepare once (ms) | Prepare every batch (ms) | Reuse speedup |
|---:|---:|---:|---:|
| 1 | 0.284492 | 0.494385 | 1.74× |
| 10 | 0.204985 | 0.221622 | 1.08× |
| 100 | 0.194061 | 0.195962 | 1.01× |

Preparation reuse matters most for very small batches. At batch size 100 its
benefit is small relative to scan/conversion time and normal timing noise.
The larger gain over pairwise calls comes from parsing/preparing the target
once and avoiding a separate Python call and GIL detach/reattach per candidate.

## Hashing (separate measurement)

| Bytes | ppdeep (ms) | fuzzbite (ms) | Speedup |
|---:|---:|---:|---:|
| 1,024 | 0.181301 | 0.004371 | 41.5× |
| 16,384 | 5.841583 | 0.068275 | 85.6× |
| 65,536 | 23.546833 | 0.266170 | 88.5× |

## Interpretation

- The comparison corpus uses valid synthetic digest variants of one article
  fingerprint. Every nonmatch has the same block size as the target and shared
  seven-character substrings in both components. This intentionally exercises
  edit-distance scoring. It is not a production article distribution.
- ppdeep runs nested Python loops for substring and distance calculations, so
  its slowdown here is much larger than on unrelated block sizes or immediate
  equality. The native `ssdeep` wrapper was unavailable and is not represented.
- Immediate matches favor a single fuzzbite.compare call: Matcher copies the
  whole first batch before returning. Increasing the number of *later* batches
  does not change that first-batch cost. Batch size is a consumer tradeoff.
- Scores differ between implementations; correctness checks ensure these
  benchmark cases have the same selected match and score under every measured
  implementation. The compatibility tests cover cases where decisions differ.
- These are workstation microbenchmarks, not throughput promises. Scheduling,
  allocator behavior, batch size, article length, similarity, and database costs
  affect application results. No noisy performance gate runs in CI.
