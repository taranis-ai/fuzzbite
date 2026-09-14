# Packaging and releases

## Supported installations

Future releases target Python 3.12–3.14 using the CPython 3.12 stable ABI.
The published 0.1.1 release still supports Python 3.10–3.14.

Precompiled wheels cover Linux x86_64 and aarch64 (glibc 2.17+) and macOS arm64.
Alpine/musl, other platforms, and installs directly from Git require a source
build with Rust and a C linker.

Linux wheels are available from 0.1.1. To disable source builds in deployments:

```sh
uv pip install --only-binary=:all: fuzzbite
```

## Publishing

The [release workflow](../.github/workflows/release.yml) publishes a source archive
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

