"""Unit coverage for the existing normalization contract."""

import unittest

from service import normalize


class NormalizeTests(unittest.TestCase):
    def test_lowercases_words(self):
        self.assertEqual(normalize("Hello WORLD"), "hello-world")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize("  Hello\t\n  World  "), "hello-world")

    def test_blank_value(self):
        self.assertEqual(normalize(" \t\n "), "")

    def test_empty_value(self):
        self.assertEqual(normalize(""), "")

    def test_preserves_punctuation(self):
        self.assertEqual(normalize("Hello, World!"), "hello,-world!")

    def test_unicode_case(self):
        self.assertEqual(normalize("CAFÉ Label"), "café-label")


if __name__ == "__main__":
    unittest.main()
