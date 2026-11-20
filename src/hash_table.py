"""Separate-chaining hash table with Horner hashing."""

from __future__ import annotations

import math
from typing import Any


class _Node:
    def __init__(self, key: str, value: Any, next_node: _Node | None = None) -> None:
        self.key = key
        self.value = value
        self.next = next_node


class HashTable:
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
        self._buckets: list[_Node | None] = [None] * capacity
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
        index, _ = self.hash_details(key)
        path = []
        node = self._buckets[index]
        while node is not None:
            path.append(index)
            if node.key == key:
                break
            node = node.next
        return tuple(path)

    def search_cost(self, key: str) -> int:
        return len(self.search_path(key))

    def insert(self, key: str, value: Any) -> None:
        self._validate_key(key)
        index, _ = self.hash_details(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self._buckets[index] = _Node(key, value, self._buckets[index])
        self._length += 1
        while (
            self.max_load is not None
            and self._length / self.capacity > self.max_load
        ):
            self._resize()

    def _resize(self) -> None:
        old_buckets = self._buckets
        self.capacity *= 2
        self._buckets = [None] * self.capacity

        for bucket in old_buckets:
            node = bucket
            while node is not None:
                next_node = node.next
                index, _ = self.hash_details(node.key)
                node.next = self._buckets[index]
                self._buckets[index] = node
                node = next_node

    def get(self, key: str) -> Any | None:
        self._validate_key(key)
        index, _ = self.hash_details(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next
        return None

    def inspect(self) -> tuple[tuple[tuple[str, Any], ...], ...]:
        slots = []
        for bucket in self._buckets:
            entries = []
            node = bucket
            while node is not None:
                entries.append((node.key, node.value))
                node = node.next
            slots.append(tuple(entries))
        return tuple(slots)

    def __len__(self) -> int:
        return self._length
