import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero_as_zero(self):
        self.assertEqual(encode(0), "0")

    def test_round_trip(self):
        for number in (1, 61, 62, 3844, 123456789):
            with self.subTest(number=number):
                self.assertEqual(decode(encode(number)), number)

    def test_encode_rejects_negative_numbers(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_decode_rejects_invalid_characters(self):
        with self.assertRaises(ValueError):
            decode("a!")


if __name__ == "__main__":
    unittest.main()
