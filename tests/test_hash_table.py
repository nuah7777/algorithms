import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_rejects_zero_capacity(self):
        with self.assertRaises(ValueError):
            HashTable(0)

    def test_capacity_one_and_empty_key(self):
        table = HashTable(1)
        table.insert("", "empty")
        self.assertEqual(table.get(""), "empty")
        self.assertEqual(table.hash_details("")[0], 0)

    def test_collisions_are_retrievable_and_updates_do_not_grow_table(self):
        table = HashTable(1)
        table.insert("first", "one")
        table.insert("second", "two")
        table.insert("first", "updated")

        self.assertEqual(table.get("first"), "updated")
        self.assertEqual(table.get("second"), "two")
        self.assertEqual(len(table), 2)
        self.assertCountEqual(
            table.inspect()[0],
            (("first", "updated"), ("second", "two")),
        )

    def test_missing_key_and_empty_inspection(self):
        table = HashTable(2)
        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.inspect(), ((), ()))

    def test_horner_hash_details(self):
        table = HashTable(101)
        index, steps = table.hash_details("ab")
        self.assertEqual(index, 75)
        self.assertEqual(
            steps,
            (("a", 97, 0, 97), ("b", 98, 97, 75)),
        )


if __name__ == "__main__":
    unittest.main()
