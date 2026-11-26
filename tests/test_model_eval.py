import csv
import os
import tempfile
import unittest

from bench_auditor.model_eval import (
    classify_disagreement,
    evaluate_eval_sheet,
    export_web_prompts,
    extract_choice,
)


class TestModelEval(unittest.TestCase):
    def test_extract_choice_and_unanswerable(self) -> None:
        self.assertEqual(extract_choice("A"), "A")
        self.assertEqual(extract_choice("答案选 C。"), "C")
        self.assertEqual(extract_choice("缺少图片，UNANSWERABLE"), "UNANSWERABLE")
        self.assertEqual(extract_choice("无法判断"), "INVALID")

    def test_classify_disagreement_buckets(self) -> None:
        self.assertEqual(
            classify_disagreement("CHK_CONFLICTING_GOLD_ANSWER", "C", ["A", "A"]),
            "SUSPECTED_GOLD_ERROR_MODEL_UNANIMOUS",
        )
        self.assertEqual(
            classify_disagreement("CHK_MISSING_VISUAL_CONTEXT", "D", ["B", "UNANSWERABLE"]),
            "BLIND_CONTEXT_HALLUCINATION",
        )
        self.assertEqual(
            classify_disagreement("CHK_MISSING_VISUAL_CONTEXT", "D", ["UNANSWERABLE", "UNANSWERABLE"]),
            "BLIND_CONTEXT_ABSTAINED",
        )

    def test_evaluate_sheet_resume_and_prompt_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "eval.csv")
            md_path = os.path.join(tmp, "summary.md")
            txt_path = os.path.join(tmp, "prompts.txt")
            fieldnames = [
                "uid",
                "split",
                "subject",
                "row_id",
                "severity",
                "check_code",
                "audit_detail",
                "question",
                "A",
                "B",
                "C",
                "D",
                "benchmark_answer",
                "model_deepseek_ans",
                "model_qwen_ans",
                "model_doubao_ans",
                "human_verdict",
                "root_cause_notes",
            ]
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerow(
                    {
                        "uid": "test/high_school_mathematics#128",
                        "split": "test",
                        "subject": "high_school_mathematics",
                        "row_id": "128",
                        "severity": "critical",
                        "check_code": "CHK_CONFLICTING_GOLD_ANSWER",
                        "audit_detail": "conflict",
                        "question": "集合{1,2,3,4}真子集个数",
                        "A": "15",
                        "B": "10",
                        "C": "11",
                        "D": "14",
                        "benchmark_answer": "C",
                        "model_deepseek_ans": "A",
                        "model_qwen_ans": "",
                        "model_doubao_ans": "",
                        "human_verdict": "",
                        "root_cause_notes": "",
                    }
                )

            calls: list[str] = []

            def fake_caller(base_url: str, key: str, model: str, q: str, opts: dict[str, str]) -> str:
                calls.append(model)
                return "A"

            summary = evaluate_eval_sheet(
                csv_path=csv_path,
                api_key="dummy",
                model_map={"model_deepseek_ans": "ds", "model_qwen_ans": "qwen"},
                summary_md_path=md_path,
                caller=fake_caller,
            )
            # DeepSeek already filled -> only Qwen should be called (resume behavior!)
            self.assertEqual(calls, ["qwen"])
            self.assertEqual(
                summary["taxonomy_counts"]["SUSPECTED_GOLD_ERROR_MODEL_UNANIMOUS"], 1
            )
            self.assertTrue(os.path.isfile(md_path))

            exported = export_web_prompts(csv_path, txt_path, limit=5)
            self.assertEqual(exported, 1)
            self.assertTrue(os.path.isfile(txt_path))
