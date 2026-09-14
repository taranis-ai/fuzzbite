# Development

Source builds require Rust and a C linker.

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
CI checks Python 3.12, 3.13, and 3.14. Linux
wheels are built in manylinux2014 containers and installed with source builds
disabled into compiler-free Python 3.12–3.14 slim containers on both architectures.
The same Linux workflow runs before publishing. Workflows follow upstream action
branches, latest uv, and stable Rust. Ubuntu x86_64 and macOS use `-latest` runners; Ubuntu ARM uses
`ubuntu-26.04-arm` because GitHub does not provide a `ubuntu-latest-arm` label.

