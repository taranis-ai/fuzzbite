# Article download and fuzzy-hash regression pipeline

Seven reports cover the same event: Annalena Baerbock's reported move to
Columbia University. This corpus checks extraction and ssdeep comparisons
against a saved baseline, including a related short report that scores zero.

## Run the tests

Install uv, Rust and a C linker, then:

```sh
git clone https://github.com/taranis-ai/fuzzbite.git
cd fuzzbite
uv sync --all-extras
source .venv/bin/activate
pytest
```

**The default test suite includes live downloads.** No browser or API key is
required. Trafilatura is installed with the locked development dependencies.
Existing CI commands run this live test too.

To run only the live baseline test:

```sh
pytest -m live
```

For an explicitly offline run:

```sh
pytest -m 'not live'
```

## What the pipeline does

1. Read `sources.json`, which maps seven filenames to publisher URLs.
2. Download each page once over HTTP with a 30-second total download deadline,
   including a slowly streaming response body. The bounded Python subprocess
   is terminated on timeout. Progress is printed to stderr before each request.
3. Extract article text using Trafilatura's precision mode and the cleanup in
   `scripts/extract_article.py`. Exclude page furniture and the identified
   publisher footer blocks; retain wording, internal subheadings and summaries.
4. Encode the text as UTF-8, including the final newline, and compute its byte
   count, SHA-256 checksum and `fuzzbite.hash()` ssdeep fingerprint.
5. Compare each pair with `fuzzbite.compare()`: 21 distinct pairs, mirrored into
   a 7×7 matrix with seven self-comparisons.
6. Assert the entire score matrix matches `comparison.json` exactly. Also check
   source URLs, byte counts, SHA-256 checksums and fingerprints against the
   baseline so extraction drift cannot hide behind unchanged scores.

The live test processes full extracted bodies in memory. It does not save article
text, rewrite the score file, silently skip failed sources or update expectations.

## The score file

`comparison.json` is the reviewed baseline. Its fields are:

| Field | Meaning |
| --- | --- |
| `generated_at` | UTC time of baseline generation; not compared during tests. |
| `algorithm` | `ssdeep`, implemented by fuzzbite/ffuzzy. |
| `fuzzbite_version`, `trafilatura_version` | Versions used to generate this baseline; informational. |
| `input` | `live_extracted_articles` for this baseline; the CLI also supports local files. |
| `articles` | Filename-keyed URLs, byte counts, SHA-256 checksums and fuzzy hashes. |
| `scores` | Filename-keyed rows and columns containing integer scores from 0 to 100. |

For example, `scores["sueddeutsche-dpa.txt"]["handelsblatt.txt"]` is **99**;
ZEIT/WELT is **93**. Self-comparisons are **100** in this corpus. These are
algorithm scores, not percentages of shared meaning or guarantees of duplication.
The offline tests independently recompute the saved scores from the fingerprints.

## Expected zero: ORF covers the same event

ORF's brief is correctly extracted: three paragraphs, 89 words, 726 UTF-8 bytes.
The other articles contain 1,877–2,304 bytes. ORF condenses and rewords the report;
it is not unrelated content, and its zero scores do not indicate missing text.

Its fingerprint starts with `12:`, while every other fingerprint starts with
`48:`. This number is the ssdeep block size. The algorithm can compare equal
block sizes or sizes differing by a factor of two. A factor of four (12 versus
48) returns zero before comparing the block hashes. Therefore **all six ORF
pairs are expected to score 0 despite discussing the same event**.

`test_same_event_orf_is_an_expected_zero` records this case explicitly. This is
an example of whole-document fuzzy hashing missing related/abridged reporting,
not a claim that the articles have fundamentally different meanings.

## Failures and baseline updates

Publisher outages, request blocking, HTML changes and editorial updates can fail
the live test. Investigate whether the failure comes from fetching, extraction,
changed input or changed comparison behavior. Do not lower thresholds or silently
replace the baseline to make a failing run pass.

To generate a separate candidate report from the repository root:

```sh
uv run --locked python -m scripts.compare_articles --output testdata/baerbock-columbia/comparison-candidate.json
```

Inspect changed inputs and scores, review the diff against `comparison.json`,
and replace the baseline only when the new result is intentional. Existing
output files are never overwritten by the script. Keep the documented ORF case
consistent with any deliberate baseline change.

The source list and dependency lock reproduce the procedure, but live websites
cannot guarantee immutable inputs. [Extraction notes](../../docs/article-extraction.md)
explain source exclusions and the earlier parser/browser experiments.
