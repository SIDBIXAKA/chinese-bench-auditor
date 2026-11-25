import unittest

from bench_auditor.checks import (
    check_dataset_level,
    check_item_level,
    normalize_option,
)
from bench_auditor.loader import QuestionRecord


def _make_record(
    uid: str = "test/subj#0",
    split: str = "test",
    subject: str = "subj",
    row_id: str = "0",
    question: str = "以下哪个城市是中国的首都？",
    options: dict[str, str] | None = None,
    answer: str = "A",
) -> QuestionRecord:
    return QuestionRecord(
        uid=uid,
        split=split,
        subject=subject,
        row_id=row_id,
        question=question,
        options=options or {"A": "北京", "B": "上海", "C": "广州", "D": "深圳"},
        answer=answer,
        source_file="dummy.csv",
    )


class TestChecks(unittest.TestCase):
    def test_numeric_and_signed_options_not_falsely_merged(self) -> None:
        rec = _make_record(
            question="计算下列数值。",
            options={"A": "-0.014", "B": "0.014", "C": "1.8km", "D": "18km"},
            answer="A",
        )
        codes = {f.check_code for f in check_item_level(rec)}
        self.assertNotIn("CHK_DUPLICATE_OPTIONS", codes)

    def test_true_duplicate_options_caught(self) -> None:
        rec = _make_record(
            options={"A": "北京 ", "B": "北京", "C": "上海", "D": "广州"},
        )
        codes = {f.check_code for f in check_item_level(rec)}
        self.assertIn("CHK_DUPLICATE_OPTIONS", codes)

    def test_missing_visual_context_and_kangxi_and_latex(self) -> None:
        rec = _make_record(
            question="如图所示，已知$f(x)=x^2，在平⾯直角坐标系中求面积",
        )
        codes = {f.check_code for f in check_item_level(rec)}
        self.assertIn("CHK_MISSING_VISUAL_CONTEXT", codes)
        self.assertIn("CHK_LATEX_SYNTAX_BROKEN", codes)
        self.assertIn("CHK_KANGXI_OCR_ARTIFACT", codes)

    def test_math_inequality_not_flagged_as_html(self) -> None:
        rec = _make_record(question="设 $0<x<100$ 且 $0<P(A)<1$，又 y>0 且代表六亿人，则？")
        codes = {f.check_code for f in check_item_level(rec)}
        self.assertNotIn("CHK_HTML_OR_MOJIBAKE", codes)
        self.assertNotIn("CHK_MISSING_VISUAL_CONTEXT", codes)

    def test_case_sensitive_biology_and_c_options_preserved(self) -> None:
        rec = _make_record(
            question="基因型组合判断",
            options={"A": "GG", "B": "Gg", "C": "gg", "D": "FILE *c"},
        )
        codes = {f.check_code for f in check_item_level(rec)}
        self.assertNotIn("CHK_DUPLICATE_OPTIONS", codes)

    def test_conflicting_gold_answer_and_dev_test_leakage(self) -> None:
        r_dev = _make_record(
            uid="dev/law#0",
            split="dev",
            subject="law",
            row_id="0",
            question="下列哪项属于邻接权的保护客体？",
            answer="A",
        )
        r_test_conflict = _make_record(
            uid="test/law#9",
            split="test",
            subject="law",
            row_id="9",
            question="下列哪项属于邻接权的保护客体？",
            answer="B",
        )
        findings = check_dataset_level([r_dev, r_test_conflict])
        codes = {f.check_code for f in findings}
        self.assertIn("CHK_CONFLICTING_GOLD_ANSWER", codes)

        r_dev_long = _make_record(
            uid="dev/law#1",
            split="dev",
            subject="law",
            row_id="1",
            question="根据我国现行著作权法规定，下列哪项属于邻接权的法定保护客体？",
            answer="A",
        )
        r_test_near = _make_record(
            uid="test/law#10",
            split="test",
            subject="law",
            row_id="10",
            question="根据我国现行著作权法规定，下列哪项属于邻接权的法定保护客体之一？",
            options={"A": "专利", "B": "商标", "C": "著作邻接", "D": "商业秘密"},
            answer="C",
        )
        findings_near = check_dataset_level([r_dev_long, r_test_near], near_dup_threshold=0.80)
        self.assertIn("CHK_DEV_TEST_NEAR_LEAKAGE", {f.check_code for f in findings_near})

    def test_normalize_option_preserves_decimals_and_nfkc(self) -> None:
        self.assertEqual(normalize_option(" 1.8 km "), "1.8km")
        self.assertNotEqual(normalize_option("-0.014"), normalize_option("0.014"))
