"""Hash extracted articles and save a labeled all-pairs ssdeep score matrix."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from importlib.metadata import version
from itertools import combinations_with_replacement
from pathlib import Path

import fuzzbite

from scripts.extract_article import download, save


def compare_sources(sources: dict[str, str], content_dir: Path | None = None) -> dict:
    if not sources:
        raise ValueError("Source manifest must not be empty")
    for name, url in sources.items():
        if Path(name).name != name or not name.endswith(".txt"):
            raise ValueError(f"Invalid source filename: {name}")
        if not isinstance(url, str):
            raise ValueError(f"Invalid URL for {name}")
    articles = {}
    for name, url in sources.items():
        data = (
            (content_dir / name).read_bytes()
            if content_dir is not None
            else download(url).encode("utf-8")
        )
        if not data.strip():
            raise ValueError(f"Empty content: {name}")
        articles[name] = {
            "url": url,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "fuzzy_hash": fuzzbite.hash(data),
        }
    scores = {name: {} for name in articles}
    for left, right in combinations_with_replacement(articles, 2):
        score = fuzzbite.compare(
            articles[left]["fuzzy_hash"], articles[right]["fuzzy_hash"]
        )
        scores[left][right] = scores[right][left] = score
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "algorithm": "ssdeep",
        "fuzzbite_version": version("fuzzbite"),
        "trafilatura_version": version("trafilatura"),
        "input": "local_files"
        if content_dir is not None
        else "live_extracted_articles",
        "articles": articles,
        "scores": scores,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources", type=Path, default=Path("testdata/baerbock-columbia/sources.json")
    )
    parser.add_argument("--content-dir", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("testdata/baerbock-columbia/comparison.json"),
    )
    args = parser.parse_args()
    try:
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        if not isinstance(sources, dict):
            raise ValueError("Manifest must map filenames to URLs")
        if args.output.exists():
            raise FileExistsError(f"Output already exists: {args.output}")
        result = compare_sources(sources, args.content_dir)
        save(json.dumps(result, ensure_ascii=False, indent=2) + "\n", args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Comparison failed: {exc}\n")
    count = len(result["articles"])
    pairs = count * (count - 1) // 2
    print(f"Saved {count} hashes and {pairs} pair scores: {args.output}")


if __name__ == "__main__":
    main()
