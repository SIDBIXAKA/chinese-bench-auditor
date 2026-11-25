import os
import tempfile
import unittest

from bench_auditor.loader import load_cmmlu_dir, load_csv_file


class TestLoader(unittest.TestCase):
    def test_load_csv_valid_and_bad_row_width(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "sample.csv")
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                f.write(",Question,A,B,C,D,Answer\n")
                f.write("0,1+1=?,1,2,3,4,B\n")
                f.write("1,broken_row,only_two\n")
            records, issues = load_csv_file(p, split="test", subject="math")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].uid, "test/math#0")
            self.assertEqual(records[0].answer, "B")
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].line_no, 3)

    def test_load_cmmlu_missing_split_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            records, issues = load_cmmlu_dir(tmp, splits=("dev", "test"))
            self.assertEqual(records, [])
            self.assertEqual(len(issues), 2)
