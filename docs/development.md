# Development

Install uv, Rust and a C linker first. Then clone, install the locked development
dependencies (included by default), and run the test suite (including live article downloads):

```sh
git clone https://github.com/taranis-ai/fuzzbite.git
cd fuzzbite
uv sync --all-extras
source .venv/bin/activate
pytest
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
pytest
```

The [article test pipeline](../testdata/baerbock-columbia/README.md) downloads
seven publisher pages, extracts and hashes their bodies, and checks all scores
and input fingerprints against the current baseline. This runs by default,
including in CI, and requires internet access. Source availability or changed
content can fail the test; expectations are never updated automatically.
Synthetic extraction and comparison tests also run normally.
The downloader reports progress and has a 30-second total download deadline.
Manual batch downloads resume by skipping existing files; live tests always fetch
fresh content and fail on download errors.

For an explicitly offline run, use
`pytest -m 'not live'`.

Build and verify distributions:

```sh
uv build
uv run --locked python scripts/validate_artifacts.py
```

On Linux, set `MATURIN_PEP517_ARGS='--compatibility linux'` for both commands.
These local Linux wheels are platform-specific and cannot be uploaded to PyPI.
CI checks Python 3.12, 3.13, and 3.14. Linux
wheels are built in manylinux2014 containers and installed with source builds
disabled into compiler-free Python 3.12–3.14 slim containers on both architectures.
The same Linux workflow runs before publishing. Workflows follow upstream action
branches, latest uv, and stable Rust. Ubuntu x86_64 and macOS use `-latest` runners; Ubuntu ARM uses
`ubuntu-26.04-arm` because GitHub does not provide a `ubuntu-latest-arm` label.
