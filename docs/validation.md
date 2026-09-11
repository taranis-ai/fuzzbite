# Delivery and package checklist

Evidence collected locally on 2026-09-11. No release, PyPI publication, or remote
Git push has been performed. The implementation and both lockfiles are committed
locally; distributions remain ignored build outputs in dist/.

## Completed locally

- `cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings`, and
  `cargo test --locked`: passed with Rust 1.98.1; two Rust tests.
- `uv run --locked ruff check .` and `uv run --locked ruff format --check .`: passed.
- `uv run --locked python -m pytest -q`: 101 passed, including 46 hashing inputs,
  2,116 ordered comparison pairs, explicit ppdeep discrepancies, threshold/order/
  validation behavior, and shared immutable Matcher use from Python threads.
- The complete Python suite passed in isolated uv environments for CPython
  3.10, 3.11, 3.12, 3.13, and 3.14 on macOS arm64.
- Reproducible benchmarks completed for 100 / 1,000 / 10,000 candidates,
  no/early/late matches, separate hashing, and preparation reuse. Five-sample
  medians and environment are in benchmarks/results-macos-arm64.json.
- `uv build` produced an sdist and ABI3 wheel on macOS arm64. The sdist produced
  another working wheel. Both wheels passed clean installed-package smoke tests
  outside the checkout under all five supported Python versions.
- A Linux aarch64 Podman container (Debian trixie, uv 0.12.10, Rust 1.98.1) passed
  Rust lint/tests, Python lint/tests, wheel/sdist builds, and both wheels' clean
  installation smoke tests on CPython 3.10–3.14. This ran natively inside an ARM VM.
- Linux x86_64 wheels were cross-compiled from the ARM Linux container using
  Rust's x86_64-unknown-linux-gnu target and Debian's cross-linker. The original
  and independently sdist-rebuilt wheels passed clean installs on CPython
  3.10–3.14 under x86_64 QEMU emulation. Native x86_64 CI has not yet run.
  The initial attempt to run the x86_64 Rust compiler under QEMU failed with a
  compiler-startup SIGSEGV, before package compilation; cross-compiling avoided
  that emulator/toolchain failure. No code workaround was needed.
- Workflow YAML passed `go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12`.
  Third-party action SHAs were checked against the upstream repositories.

## GitHub Actions status

The public remote taranis-ai/fuzzbite was accessible but had no commits, default
branch, or workflow runs at inspection. The CI and benchmark workflows have been
configured and locally syntax-checked. **There are no successful GitHub Actions
runs to report.** A public initial push requires the user's approval under the
workspace's instruction to ask before public-impact operations.

Once that push is authorized, inspect the native x86_64, ARM64, and macOS artifact
jobs and all five Python check jobs. Download their artifacts and retain failed
logs if a platform-specific issue occurs. The manual benchmark workflow can then
be run without any performance pass/fail gate. No secrets or publishing setup
are needed for these checks.

## Rebuild and inspect artifacts

```sh
uv sync --locked --python 3.14
uv build
uv run --locked python scripts/validate_artifacts.py
```

For native Linux builds, set `MATURIN_PEP517_ARGS='--compatibility linux'` for
both build and validation. The latter inherits this setting when it rebuilds
the sdist. The source archive includes Cargo.lock, uv.lock, Rust and Python
sources, tests, benchmark inputs/results, documentation, and license notices.
Compiled extensions and environment/cache files are excluded from the sdist.

The Python build backend is pinned exactly and Rust's resolver is locked.
Clean-install validation uses `uv run --isolated --no-project --with <wheel>`
in a temporary directory, with `python -I`, and checks import location, native
functionality, metadata, typing, and bundled licensing.

## Remaining limits

- ppdeep and ffuzzy can make different duplicate decisions at threshold 90.
  The measured 90-versus-83 example is an expected upstream behavior difference.
- Linux wheels use honest `linux_*` tags. They are not manylinux/musllinux wheels
  and are only validated in the build/runtime environments described here.
- macOS wheels target 11.0+, but the local runtime tested was macOS 26.6.2.
  Testing an old deployment target is separate from assigning its build tag.
- No native Python ssdeep-wrapper benchmark, production corpus replay, Windows,
  free-threaded Python, alternative interpreter, or Python 3.15 validation.
- Fingerprints with a second digest longer than 32 characters are unsupported.
  Input normalization, short-article rules, database policy, and locking remain
  consumer responsibilities.

## Local x86_64 cross-build fallback

The normal CI build uses native runners. To reproduce the local fallback from an
ARM Debian environment with Rust, uv, and `gcc-x86-64-linux-gnu` installed:

```sh
rustup target add x86_64-unknown-linux-gnu
export CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER=x86_64-linux-gnu-gcc
export PYO3_CROSS_PYTHON_VERSION=3.10
export MATURIN_PEP517_ARGS='--target x86_64-unknown-linux-gnu --compatibility linux'
uv build
uv build --wheel dist/fuzzbite-0.1.0.tar.gz --out-dir dist/rebuilt
```

Install and run scripts/smoke.py against each wheel on an x86_64 Python runtime,
not the ARM build interpreter. Local smoke runs used isolated uv environments
inside an x86_64 Debian trixie container under QEMU. No emulated timings are
included in the benchmark report.
