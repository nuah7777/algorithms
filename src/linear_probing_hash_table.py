"""Linear-probing hash table with Horner hashing."""

from __future__ import annotations

import math
from typing import Any


class _Entry:
    def __init__(self, key: str, value: Any) -> None:
        self.key = key
        self.value = value


class LinearProbingHashTable:
    def __init__(
        self, capacity: int = 10, *, max_load: float | None = 2
    ) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if max_load is not None and (
            isinstance(max_load, bool)
            or not isinstance(max_load, (int, float))
            or not math.isfinite(max_load)
            or max_load <= 0
        ):
            raise ValueError("max_load must be a positive finite number or None")
        self.capacity = capacity
        self.max_load = max_load
        self._slots: list[_Entry | None] = [None] * capacity
        self._length = 0

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def hash_details(
        self, key: str
    ) -> tuple[int, tuple[tuple[str, int, int, int], ...]]:
        self._validate_key(key)
        value = 0
        steps = []
        for character in key:
            previous = value
            value = (31 * value + ord(character)) % self.capacity
            steps.append((character, ord(character), previous, value))
        return value, tuple(steps)

    def search_path(self, key: str) -> tuple[int, ...]:
        start, _ = self.hash_details(key)
        path = []
        for offset in range(self.capacity):
            index = (start + offset) % self.capacity
            path.append(index)
            entry = self._slots[index]
            if entry is None or entry.key == key:
                break
        return tuple(path)

    def search_cost(self, key: str) -> int:
        return len(self.search_path(key))

    def insert(self, key: str, value: Any) -> None:
        start, _ = self.hash_details(key)
        for offset in range(self.capacity):
            index = (start + offset) % self.capacity
            entry = self._slots[index]
            if entry is None:
                self._slots[index] = _Entry(key, value)
                self._length += 1
                self._grow_to_threshold()
                return
            if entry.key == key:
                entry.value = value
                return

        if self.max_load is None:
            raise OverflowError("linear-probing table is full")
        self._resize()
        self.insert(key, value)

    def _grow_to_threshold(self) -> None:
        while (
            self.max_load is not None
            and self._length / self.capacity > self.max_load
        ):
            self._resize()

    def _resize(self) -> None:
        old_slots = self._slots
        self.capacity *= 2
        self._slots = [None] * self.capacity
        self._length = 0
        for entry in old_slots:
            if entry is not None:
                self._insert_existing(entry)

    def _insert_existing(self, entry: _Entry) -> None:
        start, _ = self.hash_details(entry.key)
        for offset in range(self.capacity):
            index = (start + offset) % self.capacity
            if self._slots[index] is None:
                self._slots[index] = entry
                self._length += 1
                return
        raise OverflowError("linear-probing table is full while resizing")

    def get(self, key: str) -> Any | None:
        for index in self.search_path(key):
            entry = self._slots[index]
            if entry is None:
                return None
            if entry.key == key:
                return entry.value
        return None

    def inspect(self) -> tuple[tuple[tuple[str, Any], ...], ...]:
        return tuple(
            () if entry is None else ((entry.key, entry.value),)
            for entry in self._slots
        )

    def __len__(self) -> int:
        return self._length
