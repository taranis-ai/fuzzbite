"""Build a wheel from the sdist, then smoke every wheel in clean uv environments."""

import argparse
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path


def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--python", nargs="+", default=["3.12", "3.13", "3.14"])
    args = parser.parse_args()
    distributions = args.dist.resolve()
    sdists = list(distributions.glob("*.tar.gz"))
    wheels = list(distributions.glob("*.whl"))
    assert len(sdists) == 1 and wheels, "expected one sdist and at least one wheel"
    with tarfile.open(sdists[0]) as archive:
        names = {name.split("/", 1)[-1] for name in archive.getnames()}
        assert {"Cargo.lock", "uv.lock", "src/lib.rs", "tests/scores.json"} <= names
    with tempfile.TemporaryDirectory(prefix="fuzzbite-artifacts-") as temporary:
        work = Path(temporary)
        smoke = work / "smoke.py"
        shutil.copyfile(Path(__file__).with_name("smoke.py"), smoke)
        rebuilt = work / "rebuilt"
        run(
            "uv",
            "build",
            "--wheel",
            str(sdists[0]),
            "--out-dir",
            str(rebuilt),
            "--python",
            args.python[0],
            cwd=work,
        )
        rebuilt_wheels = list(rebuilt.glob("*.whl"))
        assert rebuilt_wheels, "sdist did not produce a wheel"
        for wheel in wheels + rebuilt_wheels:
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())
                assert {"fuzzbite/py.typed", "fuzzbite/_native.pyi"} <= names
                assert any(name.endswith("/licenses/LICENSE") for name in names)
            for version in args.python:
                print(f"Smoke: {wheel.name}, Python {version}", flush=True)
                run(
                    "uv",
                    "run",
                    "--isolated",
                    "--no-project",
                    "--python",
                    version,
                    "--with",
                    str(wheel),
                    "python",
                    "-I",
                    str(smoke),
                    cwd=work,
                )
    print("All distribution checks passed.")


if __name__ == "__main__":
    main()
