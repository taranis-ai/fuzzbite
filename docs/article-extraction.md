# Article extraction example

The event is Baerbock's reported move to Columbia University, covered on
24–25 August 2026. Sources were located on 14 September 2026.

The source manifest and saved fingerprints/scores live in
`testdata/baerbock-columbia/`. Tests download article bodies in memory.

## Sources

| Source filename | Publisher |
| --- | --- |
| `zeit.txt` | [ZEIT](https://www.zeit.de/news/2026-08/24/kreise-baerbock-wechselt-an-new-yorker-columbia-universitaet) |
| `sueddeutsche-dpa.txt` | [SZ dpa](https://www.sueddeutsche.de/panorama/auf-un-posten-folgt-professur-kreise-baerbock-wechselt-an-new-yorker-columbia-universitaet-dpa.urn-newsml-dpa-com-20090101-260824-930-577201) |
| `sueddeutsche-edited.txt` | [SZ edited](https://www.sueddeutsche.de/politik/annalena-baerbock-professorin-columbia-universitaet-new-york-li.3536303) |
| `handelsblatt.txt` | [Handelsblatt](https://www.handelsblatt.com/politik/deutschland/auf-un-posten-folgt-professur-kreise-baerbock-wechselt-an-new-yorker-columbia-universitaet/100249404.html) |
| `tagesspiegel.txt` | [Tagesspiegel](https://www.tagesspiegel.de/internationales/nach-ende-ihres-un-jobs-baerbock-wechselt-an-new-yorker-columbia-universitat-15977593.html) |
| `welt.txt` | [WELT](https://www.welt.de/newsticker/dpa_nt/infoline_nt/Politik__Inland_/article6a8ca1fa511d4fd3bc4e2b2d/kreise-baerbock-wechselt-an-new-yorker-columbia-universitaet.html) |
| `orf.txt` | [ORF.at](https://orf.at/stories/3440133/) |

## Setup and tests

With uv, Rust and a C linker installed:

```sh
uv sync --all-extras
source .venv/bin/activate
pytest
```

Trafilatura is a locked dev dependency. The default suite downloads the seven
articles and checks their scores and input fingerprints against the saved
baseline, alongside synthetic offline tests. No browser or API key is required.
See the [test pipeline README](../testdata/baerbock-columbia/README.md) for details
and the explicit offline command.

## Download body text

`testdata/baerbock-columbia/sources.json` maps the seven retained filenames to
source URLs. Run the batch, or inspect results without saving full article text:

```sh
uv run --locked python scripts/extract_article.py --sources testdata/baerbock-columbia/sources.json
uv run --locked python scripts/extract_article.py --sources testdata/baerbock-columbia/sources.json --check-only
```

Use this for content you are entitled to download and use. Outputs default to
`testdata/baerbock-columbia/local/` (gitignored); `--output-dir` changes this.
Batch downloads skip existing files before making a request, so rerunning the
same command resumes missing files. To inspect a fresh extraction, choose a new
output directory. Check-only mode always downloads each source. Single-file
downloads still refuse to overwrite their output.
Each source produces a JSON status line;
failures do not stop the batch, but cause exit status 1. A single URL and output
path can also be passed as positional arguments.

Download progress goes to stderr before each request. A 30-second total download
deadline covers connection, redirects and the entire response body, including
servers that keep trickling data. Downloads run in a short-lived Python child
process which is terminated on timeout; no additional dependency is needed.
Timed-out sources report an error and the batch continues. Ctrl-C exits cleanly;
previously saved files remain available for the next run.

Extraction uses HTTP and Trafilatura's precision mode, excludes common page
furniture, and removes the observed dpa copyright footer, Tagesspiegel agency
credit and trailing internal paywall flags. Body wording, internal subheadings
and introductory summaries are preserved. Output is UTF-8 with a final newline.
`checked` means extraction succeeded, not a guarantee of completeness.

The stored manifest and locked dependencies make the procedure repeatable;
changing live pages prevent guaranteed byte-for-byte recreation.

## Fuzzy hashes and pairwise scores

`testdata/baerbock-columbia/comparison.json` contains seven ssdeep fingerprints
and a labeled 7×7 score matrix, including 21 distinct pairs and self-comparisons.
These fingerprints were calculated from live extracted article bodies in memory.
No full article text is stored in the report.

```sh
uv run --locked python -m scripts.compare_articles --output testdata/baerbock-columbia/comparison-new.json
```

For previously downloaded local files, pass
`--content-dir testdata/baerbock-columbia/local`. Only filenames listed in the
source manifest are read. Files are hashed as exact bytes; live text is encoded
as UTF-8 including the extractor's final newline. No further normalization is
applied. An empty file or failed source aborts the run without saving a partial
report. Existing reports are never overwritten.

The JSON includes source URLs, byte counts, SHA-256 checksums, fuzzy hashes,
generation time and library versions. Checksums help identify changed input on
future downloads. Scores can be recomputed offline from the stored fingerprints;
the normal pytest suite verifies every saved score and the source labels.

In this run, SZ dpa/Handelsblatt scored 99 and ZEIT/WELT scored 93. All comparisons
with ORF scored 0. Scores range from 0 to 100 but are not percentages of shared
meaning: the same event can receive a zero score. These seven articles are an
example, not enough data to calibrate a general duplicate-detection threshold.

## Verification and excluded sources: 14 September 2026

Playwright was removed from the project, including its browser mode and tests.
It did not recover the two incomplete articles and introduced duplicate
Handelsblatt paragraphs. The project no longer requires a browser installation.
Shared browser caches used by other projects were left alone.

Also tried Readability (`readability-lxml`) in a temporary uv environment and
Trafilatura's recall mode; neither was added as a new project dependency or
fallback. Inspected HTML for explicit `articleBody` containers as well.

| Excluded source | Result |
| --- | --- |
| Der Standard | Precision mode returned 54 words; recall returned 83 and Readability 74, adding headline/summary rather than recovering the body. |
| Kleine Zeitung | Precision mode returned 59 words; recall returned 67 and Readability 90, adding headline/caption/promotion rather than recovering the body. |
| VOL.at | HTTP extraction intermittently returned nothing. Readability returned 198 words but omitted the article opening. |

These three sources are removed from the active corpus.
ZEIT, both SZ versions, Handelsblatt, Tagesspiegel, WELT and ORF remain. ORF is a
short complete brief, so a universal minimum word count would reject it wrongly.
The final check-only results are in
`testdata/baerbock-columbia/extraction-report.jsonl`. Full article bodies were
inspected in memory in earlier checks; no full copyrighted article fixtures
were saved.
