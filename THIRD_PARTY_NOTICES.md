# Third-party notices

fuzzbite is distributed under GPL-2.0-or-later (see LICENSE). Its compiled
extension incorporates ffuzzy by Tsukasa OI, licensed GPL-2.0-or-later.
The project uses ffuzzy's existing hashing and comparison algorithms unchanged.

- ffuzzy 0.3.16: https://github.com/a4lg/ffuzzy/tree/v0.3.16
- PyO3 0.29.2 (and its build, FFI, macro and runtime components):
  https://github.com/PyO3/pyo3/tree/v0.29.2 — MIT OR Apache-2.0; MIT selected.
- cfg-if, static_assertions, libc, once_cell, target-lexicon, proc-macro2,
  quote, syn, unicode-ident, portable-atomic, heck and version_check: see Cargo.lock for exact
  versions and the accompanying licenses/ directory for upstream license text.
  Some are build dependencies rather than linked runtime components.

Upstream license files are retained verbatim in licenses/. Where a crate offers
MIT OR Apache-2.0, the MIT alternative is selected. unicode-ident additionally
requires Unicode-3.0 attribution; its Unicode license is included. target-lexicon
uses Apache-2.0 WITH LLVM-exception; both texts are included.

Development-only tools, not included in the installed Python package:

- maturin 1.15.0: MIT OR Apache-2.0, https://github.com/PyO3/maturin
- ppdeep 20260221: Apache-2.0, Marcin Ulikowski,
  https://github.com/elceef/ppdeep (differential test and benchmark baseline)
- pytest 9.1.1: MIT, https://github.com/pytest-dev/pytest
- Ruff 0.16.7: MIT, https://github.com/astral-sh/ruff
- uv 0.12.10: MIT OR Apache-2.0, https://github.com/astral-sh/uv

ppdeep is not a runtime dependency and its implementation is not copied into
fuzzbite. The corpus contains generated text, not third-party news articles.
