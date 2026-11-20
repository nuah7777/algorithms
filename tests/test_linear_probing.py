import http.client
import threading
import unittest

from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable
from src.server import ShortenerHTTPServer
from src.shortener import Shortener


class LinearProbingHashTableTests(unittest.TestCase):
    def test_hash_and_table_contract_match_chaining(self):
        chaining = HashTable(101, max_load=None)
        linear = LinearProbingHashTable(101, max_load=None)
        for key in ("", "a", "ab", "https://example.com/"):
            with self.subTest(key=key):
                self.assertEqual(
                    linear.hash_details(key),
                    chaining.hash_details(key),
                )

        for method in (
            "insert",
            "get",
            "hash_details",
            "inspect",
            "search_path",
            "search_cost",
        ):
            self.assertTrue(callable(getattr(linear, method)))

    def test_rejects_invalid_capacity(self):
        for capacity in (0, -1, 1.5, True):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    LinearProbingHashTable(capacity)

    def test_empty_key_missing_key_and_empty_inspection(self):
        table = LinearProbingHashTable(2, max_load=None)
        self.assertEqual(table.inspect(), ((), ()))
        self.assertIsNone(table.get("missing"))
        table.insert("", "empty")
        self.assertEqual(table.hash_details("")[0], 0)
        self.assertEqual(table.get(""), "empty")

    def test_collision_update_and_length(self):
        table = LinearProbingHashTable(3, max_load=None)
        table.insert("a", "one")
        table.insert("d", "two")
        table.insert("a", "updated")

        self.assertEqual(table.get("a"), "updated")
        self.assertEqual(table.get("d"), "two")
        self.assertEqual(len(table), 2)
        self.assertEqual(table.inspect()[1], (("a", "updated"),))
        self.assertEqual(table.inspect()[2], (("d", "two"),))

    def test_probe_wraps_from_last_slot_to_zero(self):
        table = LinearProbingHashTable(5, max_load=None)
        keys = []
        candidate = 0
        while len(keys) < 3:
            key = f"wrap-{candidate}"
            if table.hash_details(key)[0] == 4:
                keys.append(key)
            candidate += 1

        for index, key in enumerate(keys):
            table.insert(key, index)

        self.assertEqual(table.search_path(keys[1]), (4, 0))
        self.assertEqual(table.search_path(keys[2]), (4, 0, 1))
        self.assertEqual(table.get(keys[2]), 2)

    def test_full_fixed_table_raises_but_can_update_existing_key(self):
        table = LinearProbingHashTable(2, max_load=None)
        table.insert("first", "one")
        table.insert("second", "two")
        table.insert("first", "updated")

        self.assertEqual(table.get("first"), "updated")
        with self.assertRaises(OverflowError):
            table.insert("third", "three")
        self.assertEqual(len(table), 2)


class LinearProbingShortenerTests(unittest.TestCase):
    def test_shortener_contract_for_both_table_kinds(self):
        for table_kind in ("chaining", "linear"):
            with self.subTest(table_kind=table_kind):
                shortener = Shortener(table_kind=table_kind)
                url = "https://example.com/a"
                code = shortener.shorten(url)

                self.assertEqual(code, "0")
                self.assertEqual(shortener.shorten(url), code)
                self.assertEqual(shortener.resolve(code), url)
                self.assertEqual(
                    shortener.shorten("https://example.org/b"),
                    "1",
                )

    def test_shortener_errors_for_both_table_kinds(self):
        for table_kind in ("chaining", "linear"):
            with self.subTest(table_kind=table_kind):
                shortener = Shortener(table_kind=table_kind, capacity=1)
                for url in (
                    "relative/path",
                    "ftp://example.com",
                    "https:///missing-host",
                ):
                    with self.subTest(url=url):
                        with self.assertRaises(ValueError):
                            shortener.shorten(url)

                code = shortener.shorten("https://example.com")
                with self.assertRaises(OverflowError):
                    shortener.shorten("https://another.example")
                with self.assertRaises(KeyError):
                    shortener.resolve("unknown")
                self.assertEqual(shortener.resolve(code), "https://example.com")

    def test_table_page_shows_linear_probe_path(self):
        shortener = Shortener(table_kind="linear", capacity=4)
        shortener.shorten("https://a.example")
        second_url = "https://e.example"
        shortener.shorten(second_url)
        path = shortener.url_to_code.search_path(second_url)

        server = ShortenerHTTPServer(("127.0.0.1", 0), shortener)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            connection = http.client.HTTPConnection(
                "127.0.0.1", server.server_port
            )
            connection.request("GET", "/table")
            response = connection.getresponse()
            body = response.read().decode("utf-8")
            connection.close()

            self.assertEqual(response.status, 200)
            self.assertIn("linear", body)
            self.assertIn(
                f"탐색한 칸: 칸 {path[0]} → 칸 {path[1]}",
                body,
            )
            self.assertIn("호너 해시 계산 과정", body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
