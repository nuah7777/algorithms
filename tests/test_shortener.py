import unittest

from src.shortener import Shortener


class ShortenerTests(unittest.TestCase):
    def test_shorten_and_resolve_url(self):
        shortener = Shortener()
        code = shortener.shorten("https://example.com/path")
        self.assertEqual(code, "0")
        self.assertEqual(shortener.resolve(code), "https://example.com/path")

    def test_duplicate_url_reuses_code(self):
        shortener = Shortener()
        url = "https://example.com/"
        self.assertEqual(shortener.shorten(url), shortener.shorten(url))

    def test_codes_are_sequential_and_capacity_is_enforced(self):
        shortener = Shortener()
        self.assertEqual(shortener.shorten("https://one.example"), "0")
        self.assertEqual(shortener.shorten("https://two.example"), "1")

        bounded = Shortener(capacity=1)
        bounded.shorten("https://one.example")
        with self.assertRaises(OverflowError):
            bounded.shorten("https://two.example")

    def test_rejects_invalid_urls(self):
        shortener = Shortener()
        for url in ("relative/path", "ftp://example.com", "https:///missing-host"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

    def test_unknown_code_raises_key_error(self):
        with self.assertRaises(KeyError):
            Shortener().resolve("unknown")


if __name__ == "__main__":
    unittest.main()
