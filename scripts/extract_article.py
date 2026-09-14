"""Download an article body to a UTF-8 text file; run with uv."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit

from trafilatura import extract


def article_text(html: bytes) -> str:
    text = extract(
        html,
        include_comments=False,
        include_tables=False,
        with_metadata=False,
        favor_precision=True,
        prune_xpath="//h1 | //figure | //figcaption | //nav | //footer | //aside",
    )
    if not text or not text.strip():
        raise ValueError("No article body found; output was not written")
    # Remove the observed publisher footer blocks, without changing body wording.
    text = re.sub(r"(?m)^© dpa-infocom[^\n]*$", "", text)
    text = re.sub(
        r"\n- showPaywall:\n- (?:true|false)\n- isSubscriber:\n- (?:true|false)"
        r"\n- isPaid:\n- (?:true|false)\s*$",
        "",
        text,
    )
    text = re.sub(r"\s*\(dpa, AFP, Tsp\)\s*$", "", text)
    if not text.strip():
        raise ValueError("No article body found; output was not written")
    return text.strip() + "\n"


def download(url: str, timeout: float = 30) -> str:
    if urlsplit(url).scheme not in {"https", "http"}:
        raise ValueError("URL must use HTTP or HTTPS")
    # A child process bounds DNS, redirects and trickling response bodies together.
    # Socket timeouts alone only limit inactivity and can wait indefinitely.
    code = """
import sys
from urllib.request import Request, urlopen
request = Request(sys.argv[1], headers={"User-Agent": "fuzzbite-example/0.1"})
with urlopen(request, timeout=float(sys.argv[2])) as response:
    if response.headers.get_content_type() != "text/html":
        raise ValueError("Expected an HTML page")
    sys.stdout.buffer.write(response.read())
"""
    print(f"Downloading {url} (deadline {timeout:g}s)", file=sys.stderr, flush=True)
    try:
        response = subprocess.run(
            [sys.executable, "-c", code, url, str(timeout)],
            capture_output=True,
            check=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Download exceeded {timeout:g}s: {url}") from None
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise OSError(detail[-1] if detail else f"Download failed: {url}") from None
    return article_text(response.stdout)


def save(content: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def batch(sources: Path, output_dir: Path, check_only: bool) -> bool:
    entries = json.loads(sources.read_text(encoding="utf-8"))
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Manifest must map filenames to URLs")
    for name, url in entries.items():
        if Path(name).name != name or not name.endswith(".txt"):
            raise ValueError(f"Invalid output filename: {name}")
        if not isinstance(url, str):
            raise ValueError(f"Invalid URL for {name}")
    success = True
    for name, url in entries.items():
        result = {"file": name, "url": url}
        try:
            output = output_dir / name
            if not check_only and output.is_file():
                result.update(status="skipped", reason="file already exists")
                print(json.dumps(result, ensure_ascii=False), flush=True)
                continue
            content = download(url)
            markers = [
                marker
                for marker in (
                    "cookie",
                    "abonnieren",
                    "anmelden",
                    "datenschutz",
                    "redaktionell nicht bearbeitet",
                    "dpa-infocom",
                    "red, orf.at",
                    "©",
                    "showpaywall",
                    "issubscriber",
                    "ispaid",
                    "google-quelle",
                    "(apa/dpa)",
                    "(dpa, afp, tsp)",
                )
                if marker in content.lower()
            ]
            result.update(
                status="checked" if check_only else "saved",
                words=len(content.split()),
                paragraphs=len(content.splitlines()),
                event_terms_present=all(
                    term in content.lower() for term in ("baerbock", "columbia")
                ),
                possible_boilerplate=markers,
            )
            if not check_only:
                save(content, output_dir / name)
        except (OSError, URLError, ValueError) as exc:
            result.update(status="error", error=str(exc))
            success = False
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return success


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?")
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--sources", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("testdata/baerbock-columbia/local"),
    )
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.sources:
        if args.url or args.output:
            parser.error("--sources cannot be combined with positional arguments")
        try:
            success = batch(args.sources, args.output_dir, args.check_only)
        except (OSError, ValueError) as exc:
            parser.exit(1, f"Manifest failed: {exc}\n")
        parser.exit(0 if success else 1)
    if args.check_only:
        parser.error("--check-only requires --sources")
    if not args.url or not args.output:
        parser.error("provide a URL and output .txt path")
    if urlsplit(args.url).scheme not in {"https", "http"}:
        parser.error("URL must use HTTP or HTTPS")
    try:
        content = download(args.url)
        save(content, args.output)
    except (OSError, URLError, ValueError) as exc:
        parser.exit(1, f"Extraction failed: {exc}\n")
    print(f"Saved {len(content.encode('utf-8'))} bytes to {args.output}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted; rerun to resume saved files.", file=sys.stderr)
        raise SystemExit(130) from None
