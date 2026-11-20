"""URL shortener backed by the project's custom hash table."""

from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable


class Shortener:
    def __init__(self, table_kind: str = "chaining", capacity: int = 10) -> None:
        if table_kind != "chaining":
            raise ValueError(f"unsupported table kind: {table_kind!r}")
        self.table = HashTable(capacity)
        self._capacity = capacity
        self._next_code = 0

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str) or not url or any(character.isspace() for character in url):
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            parsed.port
        except ValueError as error:
            raise ValueError("url must be a valid absolute HTTP or HTTPS URL") from error
        if parsed.scheme.lower() not in ("http", "https") or not hostname:
            raise ValueError("url must be an absolute HTTP or HTTPS URL with a host")

    def shorten(self, url: str) -> str:
        self._validate_url(url)
        for slot in self.table.inspect():
            for code, stored_url in slot:
                if stored_url == url:
                    return code

        if len(self.table) >= self._capacity:
            raise OverflowError("shortener capacity is full")
        code = encode(self._next_code)
        self._next_code += 1
        self.table.insert(code, url)
        return code

    def resolve(self, code: str) -> str:
        url = self.table.get(code)
        if url is None:
            raise KeyError(code)
        return url
