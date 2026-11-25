import csv
import json
import os
import tempfile
import unittest

from bench_auditor.audit import run_audit
from bench_auditor.model_eval import summarize_eval_sheet


class TestAuditE2E(unittest.TestCase):
    def test_end_to_end_pipeline_and_eval_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = os.path.join(tmp, "data")
            out_dir = os.path.join(tmp, "out")
            os.makedirs(os.path.join(data_dir, "dev"))
            os.makedirs(os.path.join(data_dir, "test"))

            with open(os.path.join(data_dir, "dev", "demo.csv"), "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["", "Question", "A", "B", "C", "D", "Answer"])
                w.writerow(["0", "如图所示，小车从斜面滑下的加速度为多少？", "1m/s2", "2m/s2", "3m/s2", "4m/s2", "B"])

            with open(os.path.join(data_dir, "test", "demo.csv"), "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["", "Question", "A", "B", "C", "D", "Answer"])
                w.writerow(["0", "如图所示，小车从斜面滑下的加速度为多少？", "1m/s2", "2m/s2", "3m/s2", "4m/s2", "B"])
                w.writerow(["1", "正常单选测试题：地球绕太阳公转周期约为？", "1天", "1个月", "1年", "10年", "C"])

            summary = run_audit(data_dir=data_dir, out_dir=out_dir)
            self.assertEqual(summary["total_records"], 3)
            self.assertGreaterEqual(summary["total_findings"], 2)
            self.assertTrue(os.path.isfile(summary["report_path"]))
            self.assertTrue(os.path.isfile(summary["findings_path"]))
            self.assertTrue(os.path.isfile(summary["eval_sheet_path"]))

            with open(summary["findings_path"], "r", encoding="utf-8") as f:
                loaded = [json.loads(line) for line in f if line.strip()]
            self.assertTrue(any(x["check_code"] == "CHK_DEV_TEST_LEAKAGE" for x in loaded))

            eval_summary = summarize_eval_sheet(summary["eval_sheet_path"])
            self.assertGreaterEqual(eval_summary["total_rows"], 1)
