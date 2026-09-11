# Dependency selection (2026-09-11)

The runtime Rust dependencies are exactly ffuzzy 0.3.16 and PyO3 0.29.2; the
Python package has no runtime requirements. The versions below were checked
against upstream Cargo/PyPI metadata and documentation, not inferred from an
older example. Transitive versions and package hashes are in Cargo.lock and uv.lock.

| Dependency | Selected | Upstream support / license | Verification |
|---|---|---|---|
| ffuzzy | 0.3.16 | Rust 1.56+, GPL-2.0-or-later | `cargo info ffuzzy`, [docs](https://docs.rs/ffuzzy/0.3.16/ssdeep/) |
| PyO3 | 0.29.2 | Rust 1.83+, CPython 3.8+, MIT OR Apache-2.0 | `cargo info pyo3`, [guide](https://pyo3.rs/v0.29.0/) |
| maturin | 1.15.0 | Python 3.7+, MIT OR Apache-2.0 | [PyPI version metadata](https://pypi.org/pypi/maturin/1.15.0/json), [configuration](https://www.maturin.rs/config) |
| ppdeep | 20260221 | Pure Python, no declared Requires-Python; Apache-2.0 | [PyPI metadata](https://pypi.org/pypi/ppdeep/20260221/json), [source](https://github.com/elceef/ppdeep) |
| pytest | 9.1.1 | Python 3.10+, MIT | [PyPI metadata](https://pypi.org/pypi/pytest/9.1.1/json) |
| Ruff | 0.16.7 | Python 3.7+, MIT | [PyPI metadata](https://pypi.org/pypi/ruff/0.16.7/json) |
| uv | 0.12.10 | MIT OR Apache-2.0 | Installed CLI and [build guide](https://docs.astral.sh/uv/guides/package/) |
| Rust | 1.98.1 | MIT OR Apache-2.0 | Installed compiler and [stable manifest](https://static.rust-lang.org/dist/channel-rust-stable.toml) |

ffuzzy's `FuzzyHashCompareTarget` directly implements the required reusable target.
Its strict-parser feature rejects raw digest overflow instead of accepting it
only because run normalization shortens the digest. The wrapper requires full
parser consumption to disallow ssdeep CSV filename suffixes. PyO3's supported
[`Python::detach`](https://pyo3.rs/v0.29.0/parallelism.html) API releases the GIL.

The initial Python support policy deliberately covers standard CPython 3.10–3.14.
It is narrower than PyO3's upstream interpreter support. ABI3 avoids separate
wheels for each of those interpreter versions. Linux native tags are explicitly
selected; no manylinux certification is assumed from successful compilation.

Actions were resolved with `git ls-remote` and verified using GitHub's commit API.
Annotated version tags were peeled to commits before pinning (in particular
setup-uv's floating v7 ref points to a tag object, not an action commit).

| Action | Verified commit |
|---|---|
| actions/checkout v6 | `d23441a48e516b6c34aea4fa41551a30e30af803` |
| astral-sh/setup-uv v7.6.0 | `37802adc94f370d6bfd71619e3f0bf239e1f3b78` |
| dtolnay/rust-toolchain stable action | `6bed0761d98439e5a578e2877258200ad565ba87` |
| actions/cache v4 | `0057852bfaa89a56745cba8c7296529d2fc39830` |
| actions/upload-artifact v6 | `b7c566a772e6b6bfb58ed0dc250532a479d7789f` |

The toolchain action receives the explicit Rust version. uv is also pinned.
Actionlint 1.7.12 was used locally after checking its upstream release metadata;
it is a validation tool, not a project dependency.
