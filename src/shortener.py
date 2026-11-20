"""URL shortener backed by the project's custom hash table."""

from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable


class Shortener:
    def __init__(self, table_kind: str = "chaining", capacity: int = 10) -> None:
        if table_kind == "chaining":
            table_type = HashTable
        elif table_kind == "linear":
            table_type = LinearProbingHashTable
        else:
            raise ValueError(f"unsupported table kind: {table_kind!r}")
        self.table_kind = table_kind
        self.url_to_code = table_type(capacity)
        self.code_to_url = table_type(capacity)
        self.table = self.code_to_url
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
        existing_code = self.url_to_code.get(url)
        if existing_code is not None:
            return existing_code

        if len(self.code_to_url) >= self._capacity:
            raise OverflowError("shortener capacity is full")
        code = encode(self._next_code)
        self.url_to_code.insert(url, code)
        self.code_to_url.insert(code, url)
        self._next_code += 1
        return code

    def resolve(self, code: str) -> str:
        url = self.code_to_url.get(code)
        if url is None:
            raise KeyError(code)
        return url
