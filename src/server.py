"""HTTP server for the URL shortener."""

from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, unquote, urlsplit, quote

from src.shortener import Shortener

PORT = 8000
MAX_FORM_BYTES = 1_048_576


def _page(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; line-height: 1.5; margin: 2rem auto; max-width: 900px; padding: 0 1rem; }}
    input[type=url] {{ box-sizing: border-box; max-width: 100%; padding: .6rem; width: 36rem; }}
    button {{ cursor: pointer; padding: .6rem 1rem; }}
    .result, .error, .bucket, .node {{ border: 1px solid #bbb; border-radius: .4rem; margin: 1rem 0; padding: 1rem; }}
    .error {{ border-color: #b22; color: #900; }}
    .bucket {{ background: #f7f8fa; }}
    .node {{ background: white; overflow-wrap: anywhere; }}
    .arrow {{ color: #555; font-size: 1.5rem; line-height: 1; text-align: center; }}
    .field {{ margin: .4rem 0; }}
    code {{ overflow-wrap: anywhere; }}
    details {{ margin-top: .8rem; }}
    pre {{ overflow-x: auto; }}
  </style>
</head>
<body>
{content}
</body>
</html>"""


def _short_path(code: str) -> str:
    return f"/s/{quote(code, safe='')}"


def _render_home(url: str = "", error: str | None = None, code: str | None = None) -> str:
    error_content = (
        f'<p class="error">{escape(error)}</p>' if error is not None else ""
    )
    result_content = ""
    if code is not None:
        short_path = _short_path(code)
        result_content = (
            '<section class="result"><h2>짧은 링크</h2>'
            f'<p><a href="{escape(short_path, quote=True)}">'
            f"{escape(short_path)}</a></p>"
            f"<p>원본 URL: <code>{escape(url)}</code></p></section>"
        )
    content = (
        "<h1>URL 단축기</h1>"
        "<p>긴 URL을 입력하면 짧은 링크를 만들어 드립니다.</p>"
        f"{error_content}"
        '<form action="/" method="post">'
        '<label for="url">원본 URL</label><br>'
        f'<input id="url" name="url" type="url" required value="{escape(url, quote=True)}">'
        '<button type="submit">줄이기</button></form>'
        f"{result_content}"
        '<p><a href="/table">해시 테이블 보기</a></p>'
    )
    return _page("URL 단축기", content)


def _render_table(shortener: Shortener) -> str:
    table = shortener.url_to_code
    buckets = []
    for bucket_index, entries in enumerate(table.inspect()):
        nodes = []
        for node_index, (url, code) in enumerate(entries):
            hash_index, steps = table.hash_details(url)
            search_path = table.search_path(url)
            calculations = "".join(
                "<li>"
                f"h = (31 × {previous} + {codepoint}) mod {table.capacity} "
                f"= {value}; 문자 '{escape(character)}'</li>"
                for character, codepoint, previous, value in steps
            )
            short_path = _short_path(code)
            probe_details = ""
            if shortener.table_kind == "linear":
                visited_slots = " → ".join(f"칸 {index}" for index in search_path)
                probe_details = f"<p>탐색한 칸: {visited_slots}</p>"
                location_label = "시작 칸"
            else:
                location_label = "버킷"
            nodes.append(
                '<article class="node">'
                f'<div class="field"><strong>URL 키:</strong> <code>{escape(url)}</code></div>'
                f'<div class="field"><strong>짧은 코드:</strong> <code>{escape(code)}</code></div>'
                '<div class="field"><strong>짧은 링크:</strong> '
                f'<a href="{escape(short_path, quote=True)}">{escape(short_path)}</a></div>'
                f"<p>{location_label} {hash_index}</p>"
                f"{probe_details}"
                "<details><summary>호너 해시 계산 과정</summary>"
                f"<ol>{calculations}</ol></details>"
                "</article>"
            )
            if node_index < len(entries) - 1:
                nodes.append('<div class="arrow" aria-hidden="true">↓</div>')

        bucket_content = "".join(nodes) if nodes else "<p>비어 있음</p>"
        buckets.append(
            '<section class="bucket">'
            f"<h2>칸 {bucket_index}</h2>{bucket_content}</section>"
        )

    content = (
        f"<h1>현재 해시 테이블 ({escape(shortener.table_kind)})</h1>"
        f"<p>{len(table)}개 URL · {table.capacity}칸</p>"
        f'{"".join(buckets)}'
        '<p><a href="/">URL 단축하기</a></p>'
    )
    return _page("해시 테이블", content)


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    @property
    def shortener(self) -> Shortener:
        server = self.server
        if not isinstance(server, ShortenerHTTPServer):
            raise RuntimeError("request handler requires ShortenerHTTPServer")
        return server.shortener

    def _send_html(
        self, content: str, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            path = urlsplit(self.path).path
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid request path")
            return

        if path == "/":
            self._send_html(_render_home())
            return
        if path == "/table":
            self._send_html(_render_table(self.shortener))
            return
        if path.startswith("/s/"):
            code = unquote(path[len("/s/"):])
            if not code or "/" in code:
                self.send_error(HTTPStatus.NOT_FOUND, "Short link not found")
                return
            try:
                url = self.shortener.resolve(code)
            except KeyError:
                self.send_error(HTTPStatus.NOT_FOUND, "Short link not found")
                return

            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Page not found")

    def do_POST(self) -> None:
        try:
            path = urlsplit(self.path).path
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid request path")
            return
        if path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")
            return
        if self.headers.get_content_type() != "application/x-www-form-urlencoded":
            self.send_error(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "Expected a URL-encoded form",
            )
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid content length")
            return
        if content_length < 0:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid content length")
            return
        if content_length > MAX_FORM_BYTES:
            self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Form is too large")
            return

        try:
            form_body = self.rfile.read(content_length).decode("utf-8")
            form = parse_qs(form_body, keep_blank_values=True, max_num_fields=10)
        except (UnicodeDecodeError, ValueError):
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid form data")
            return

        url_values = form.get("url")
        url = url_values[0] if url_values else ""
        try:
            code = self.shortener.shorten(url)
        except (ValueError, OverflowError) as error:
            self._send_html(
                _render_home(url=url, error=str(error)),
                HTTPStatus.BAD_REQUEST,
            )
            return
        self._send_html(_render_home(url=url, code=code))


class ShortenerHTTPServer(HTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        shortener: Shortener,
    ) -> None:
        self.shortener = shortener
        super().__init__(server_address, ShortenerRequestHandler)


def main() -> None:
    with ShortenerHTTPServer(("0.0.0.0", PORT), Shortener()) as server:
        print(f"URL shortener listening on port {PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")


if __name__ == "__main__":
    main()
