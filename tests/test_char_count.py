import unittest

from cogs.char_count import count_chars


class CountCharsTest(unittest.TestCase):
    def test_mixed(self):
        r = count_chars("Abc あい\nカタカナー漢字12")
        self.assertEqual(r["total"], 16)
        self.assertEqual(r["no_newline"], 15)
        self.assertEqual(r["no_space"], 14)
        self.assertEqual(r["alpha"], 3)
        self.assertEqual(r["hiragana"], 2)
        self.assertEqual(r["katakana"], 5)
        self.assertEqual(r["kanji"], 2)
        self.assertEqual(r["digit"], 2)

    def test_crlf_counts_as_one(self):
        r = count_chars("a\r\nb")
        self.assertEqual(r["total"], 3)
        self.assertEqual(r["no_newline"], 2)

    def test_empty(self):
        self.assertTrue(all(v == 0 for v in count_chars("").values()))


if __name__ == "__main__":
    unittest.main()
