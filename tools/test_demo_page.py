"""Browser test for docs/index.html: snapshot table, id lookup, pasted source parsing."""

import http.server
import socketserver
import threading
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

DOCS = Path(r"C:\Users\User\AppData\Local\Temp\opencode\hh-vacancy-check\docs")
FIXTURES = Path(r"C:\Users\User\AppData\Local\Temp\opencode\hh-vacancy-check\tests\fixtures")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve() -> tuple[socketserver.TCPServer, int]:
    handler = partial(Quiet, directory=str(DOCS))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def main() -> int:
    server, port = serve()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")

            rows = page.locator("#rows tr").count()
            print("snapshot rows:", rows)
            print("snapshot note:", page.locator("#snapshot-note").inner_text()[:90])

            page.fill("#vid", "https://hh.ru/vacancy/139441388?query=x")
            page.click("#check")
            verdict = page.locator("#verdict").inner_text()
            print("id lookup:", " ".join(verdict.split())[:110])

            page.fill("#html", (FIXTURES / "open.html").read_text(encoding="utf-8"))
            page.click("#parse")
            parsed_open = page.locator("#parsed").inner_text()
            print("pasted open:", " ".join(parsed_open.split())[:110])

            page.fill("#html", (FIXTURES / "archived.html").read_text(encoding="utf-8"))
            page.click("#parse")
            parsed_archived = page.locator("#parsed").inner_text()
            print("pasted archived:", " ".join(parsed_archived.split())[:110])

            page.fill("#html", "")
            page.fill("#vid", "not-an-id")
            page.click("#check")
            bad_id = page.locator("#verdict").inner_text()
            print("bad id:", " ".join(bad_id.split())[:90])

            page.screenshot(path=str(DOCS.parent / "docs" / "demo.png"), full_page=True)
            print("console errors:", errors)
            browser.close()
    finally:
        server.shutdown()

    ok = (
        rows >= 5
        and "OPEN" in verdict
        and "OPEN" in parsed_open
        and "Блока JobPosting нет" in parsed_archived
        and "Не вижу id" in bad_id
    )
    print("RESULT:", "pass" if ok else "fail")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
