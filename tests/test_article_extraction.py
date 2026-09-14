import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError

import pytest

from scripts import extract_article

PARAGRAPH = (
    "The research team measured river levels at three stations every morning. "
    "Their report describes seasonal changes and compares the observations "
    "with measurements from previous years."
)


def test_extracts_body_without_page_furniture():
    html = (
        "<html><head><title>PAGE TITLE</title></head><body>"
        "<nav>NAVIGATION</nav><article><h1>ARTICLE TITLE</h1>"
        f"<p>{PARAGRAPH}</p><figure><figcaption>PHOTO CREDIT</figcaption></figure>"
        f"<p>{PARAGRAPH.replace('river', 'lake')}</p></article>"
        "<footer>FOOTER</footer></body></html>"
    )
    assert extract_article.article_text(html.encode()) == (
        PARAGRAPH + "\n" + PARAGRAPH.replace("river", "lake") + "\n"
    )
    with pytest.raises(ValueError, match="No article body"):
        extract_article.article_text(b"<html><body></body></html>")


def test_batch_check_save_and_no_overwrite(tmp_path, monkeypatch, capsys):
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps({"example.txt": "https://example.com"}))
    content = PARAGRAPH + "\n"
    monkeypatch.setattr(extract_article, "download", lambda url: content)
    output = tmp_path / "output"
    assert extract_article.batch(sources, output, check_only=True)
    assert not output.exists()
    assert extract_article.batch(sources, output, check_only=False)
    monkeypatch.setattr(extract_article, "download", lambda url: pytest.fail(url))
    assert extract_article.batch(sources, output, check_only=False)
    assert (output / "example.txt").read_bytes() == content.encode("utf-8")
    reports = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [report["status"] for report in reports] == ["checked", "saved", "skipped"]


@pytest.mark.parametrize(
    "error", [URLError("offline failure"), TimeoutError("deadline")]
)
def test_batch_continues_after_download_failure(tmp_path, monkeypatch, capsys, error):
    sources = tmp_path / "sources.json"
    sources.write_text(
        json.dumps(
            {
                "failed.txt": "https://example.com/failed",
                "ok.txt": "https://example.com/ok",
            }
        )
    )

    def download(url):
        if url.endswith("failed"):
            raise error
        return PARAGRAPH + "\n"

    monkeypatch.setattr(extract_article, "download", download)
    assert not extract_article.batch(sources, tmp_path / "output", check_only=False)
    assert not (tmp_path / "output/failed.txt").exists()
    assert (tmp_path / "output/ok.txt").exists()
    reports = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [report["status"] for report in reports] == ["error", "saved"]


def test_manifest_rejects_path_traversal_before_downloading(tmp_path, monkeypatch):
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps({"../escape.txt": "https://example.com"}))
    monkeypatch.setattr(extract_article, "download", lambda url: pytest.fail(url))
    with pytest.raises(ValueError, match="Invalid output filename"):
        extract_article.batch(sources, tmp_path, check_only=False)


def test_removes_observed_publisher_footers(monkeypatch):
    text = (
        PARAGRAPH + " (dpa, AFP, Tsp)\n"
        "- showPaywall:\n- false\n- isSubscriber:\n- false\n- isPaid:\n- false"
    )
    monkeypatch.setattr(extract_article, "extract", lambda *a, **kw: text)
    assert extract_article.article_text(b"unused") == PARAGRAPH + "\n"
    text = PARAGRAPH + "\n© dpa-infocom, example"
    assert extract_article.article_text(b"unused") == PARAGRAPH + "\n"
    text = "© dpa-infocom, example"
    with pytest.raises(ValueError, match="No article body"):
        extract_article.article_text(b"unused")


def test_total_deadline_stops_trickling_chunked_response():
    stop = threading.Event()
    requested = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requested.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                while not stop.wait(0.02):
                    self.wfile.write(b"1\r\nx\r\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError, match="Download exceeded"):
            extract_article.download(
                f"http://127.0.0.1:{server.server_port}/", timeout=1
            )
        assert requested.is_set()
        assert time.monotonic() - started < 4
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join()
