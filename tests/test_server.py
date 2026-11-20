import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.server import ShortenerHTTPServer
from src.shortener import Shortener


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = ShortenerHTTPServer(
            ("127.0.0.1", 0),
            Shortener(capacity=2),
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port
        )
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        response_headers = response.headers
        connection.close()
        return response.status, response_headers, response_body

    def test_home_page_has_url_form(self):
        status, _, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn('<form action="/" method="post">', body)
        self.assertIn('name="url"', body)

    def test_form_displays_short_link_and_redirects_to_original(self):
        url = "https://example.com/a?x=1&y=two"
        body = urlencode({"url": url})
        status, _, result_page = self.request(
            "POST",
            "/",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        self.assertEqual(status, 200)
        self.assertIn('href="/s/0"', result_page)

        status, headers, _ = self.request("GET", "/s/0")
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("Location"), url)

    def test_invalid_url_is_shown_on_form(self):
        body = urlencode({"url": "relative/path"})
        status, _, response_body = self.request(
            "POST",
            "/",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        self.assertEqual(status, 400)
        self.assertIn("absolute HTTP or HTTPS URL", response_body)

    def test_table_shows_chained_nodes_and_hash_details(self):
        self.server.shortener.shorten("https://a.example")
        self.server.shortener.shorten("https://c.example")

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("URL 키:", body)
        self.assertIn("짧은 코드:", body)
        self.assertIn("짧은 링크:", body)
        self.assertIn("호너 해시 계산 과정", body)
        self.assertIn('class="arrow"', body)
        self.assertEqual(body.count("<details>"), 2)


if __name__ == "__main__":
    unittest.main()
