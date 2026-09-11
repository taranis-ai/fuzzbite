"""Run with uv run --locked python -m benchmarks.run --output results.json."""

import argparse
import importlib.metadata
import json
import os
import platform
import random
import statistics
import subprocess
import time
from pathlib import Path

import fuzzbite
import ppdeep

from benchmarks.corpus import article


def timed(function, repeats, minimum_seconds=0.025):
    """Calibrate outside recorded samples; retain per-operation sample medians."""
    start = time.perf_counter()
    function()
    elapsed = time.perf_counter() - start
    loops = min(10000, max(1, int(minimum_seconds / max(elapsed, 1e-9))))
    samples = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        for _ in range(loops):
            function()
        samples.append((time.perf_counter_ns() - start) / loops / 1e6)
    return {
        "median_ms": statistics.median(samples),
        "samples_ms": samples,
        "loops": loops,
    }


def sequential(compare, target, batches):
    for batch_index, batch in enumerate(batches):
        for index, item in enumerate(batch):
            score = compare(target, item)
            if score >= 90:
                return batch_index, index, score
    return None


def batched(matcher, batches):
    for batch_index, batch in enumerate(batches):
        if (match := matcher.find_match(batch)) is not None:
            return batch_index, *match
    return None


def fresh_per_batch(target, batches):
    for batch_index, batch in enumerate(batches):
        if (match := fuzzbite.Matcher(target).find_match(batch)) is not None:
            return batch_index, *match
    return None


def candidate_pool(target, count):
    """Valid synthetic digest variants with shared substrings and the same block size.

    Derived from an article fingerprint, not hashes of modified articles. Force
    real edit-distance work in both components, rather than size/substring rejection.
    """
    rng = random.Random(20260911)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    block, first, second = target.split(":")
    pool = []
    while len(pool) < count:
        candidate = ":".join(
            [
                block,
                first[:14] + "".join(rng.choices(alphabet, k=len(first) - 14)),
                second[:7] + "".join(rng.choices(alphabet, k=len(second) - 7)),
            ]
        )
        if (
            fuzzbite.compare(target, candidate) < 90
            and ppdeep.compare(target, candidate) < 90
        ):
            pool.append(candidate)
    return pool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("benchmark-results.json"))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if args.repeats < 3 or args.batch_size < 1:
        parser.error("use at least 3 repeats and a positive batch size")

    data = article(42)
    target = fuzzbite.hash(data)
    matcher = fuzzbite.Matcher(target)
    baselines = {"ppdeep_loop": ppdeep.compare, "fuzzbite_loop": fuzzbite.compare}
    try:
        import ssdeep
    except ImportError:
        native = "not installed (optional libfuzzy + ssdeep wrapper baseline)"
    else:
        baselines["ssdeep_loop"] = ssdeep.compare
        native = importlib.metadata.version("ssdeep")

    print("Generating and validating 10,000 compatible nonmatches...", flush=True)
    pool = candidate_pool(target, 10000)
    result = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
            "uv": subprocess.check_output(["uv", "--version"], text=True).strip(),
            "versions": {
                name: importlib.metadata.version(name)
                for name in ("fuzzbite", "ppdeep", "maturin")
            },
            "ffuzzy": "0.3.16",
            "pyo3": "0.29.2",
            "ssdeep": native,
            "build_profile": "release (uv sync / uv build default)",
        },
        "parameters": {
            "seed": 20260911,
            "repeats": args.repeats,
            "batch_size": args.batch_size,
            "threshold": 90,
            "target": target,
            "article_bytes": len(data),
        },
        "preparation": timed(lambda: fuzzbite.Matcher(target), args.repeats),
        "hashing": {},
        "comparisons": [],
    }
    result["reuse_sweep"] = []
    for batch_size in (1, 10, 100):
        batches = [pool[i : i + batch_size] for i in range(0, 1000, batch_size)]
        once = timed(
            lambda batches=batches: batched(fuzzbite.Matcher(target), batches),
            args.repeats,
            minimum_seconds=0.1,
        )
        each = timed(
            lambda batches=batches: fresh_per_batch(target, batches),
            args.repeats,
            minimum_seconds=0.1,
        )
        result["reuse_sweep"].append(
            {
                "candidates": 1000,
                "batch_size": batch_size,
                "prepare_once": once,
                "prepare_each_batch": each,
                "speedup": each["median_ms"] / once["median_ms"],
            }
        )
    for size in (1024, 16384, 65536):
        content = (data * (size // len(data) + 1))[:size]
        result["hashing"][str(size)] = {
            "ppdeep": timed(lambda content=content: ppdeep.hash(content), args.repeats),
            "fuzzbite": timed(
                lambda content=content: fuzzbite.hash(content), args.repeats
            ),
        }
    for size in (100, 1000, 10000):
        for workload in ("no_match", "early_match", "late_match"):
            candidates = pool[:size]
            if workload == "early_match":
                candidates[0] = target
            elif workload == "late_match":
                candidates[-1] = target
            batches = [
                candidates[i : i + args.batch_size]
                for i in range(0, size, args.batch_size)
            ]
            methods = {
                name: (
                    lambda compare=compare, batches=batches: sequential(
                        compare, target, batches
                    )
                )
                for name, compare in baselines.items()
            }
            # Both one-preparation-per-search and steady-state reuse are measured.
            methods["matcher_prepare_once"] = lambda batches=batches: batched(
                fuzzbite.Matcher(target), batches
            )
            methods["matcher_reused"] = lambda batches=batches: batched(
                matcher, batches
            )
            methods["matcher_prepare_each_batch"] = lambda batches=batches: (
                fresh_per_batch(target, batches)
            )
            expected = sequential(fuzzbite.compare, target, batches)
            for name, function in methods.items():
                assert function() == expected, (name, workload)
            timings = {
                name: timed(function, args.repeats)
                for name, function in methods.items()
            }
            batch_ms = timings["matcher_prepare_once"]["median_ms"]
            row = {
                "size": size,
                "workload": workload,
                "timings": timings,
                "speedup_vs_ppdeep": timings["ppdeep_loop"]["median_ms"] / batch_ms,
                "speedup_vs_fuzzbite_loop": timings["fuzzbite_loop"]["median_ms"]
                / batch_ms,
                "reuse_vs_prepare_each_batch": (
                    timings["matcher_prepare_each_batch"]["median_ms"]
                    / timings["matcher_prepare_once"]["median_ms"]
                ),
            }
            result["comparisons"].append(row)
            print(
                f"{size:5} {workload:11} {batch_ms:.4f} ms; "
                f"{row['speedup_vs_ppdeep']:.1f}x ppdeep, "
                f"{row['speedup_vs_fuzzbite_loop']:.2f}x per-call Rust",
                flush=True,
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
