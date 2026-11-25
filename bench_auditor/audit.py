"""Audit pipeline orchestration and artifact exporters (Markdown, JSONL, CSV)."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from dataclasses import asdict
from datetime import datetime

from bench_auditor.checks import (
    AuditFinding,
    SubjectHealthSummary,
    check_dataset_level,
    check_item_level,
    summarize_subjects,
)
from bench_auditor.loader import QuestionRecord, SchemaIssue, load_cmmlu_dir

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def run_audit(
    data_dir: str,
    out_dir: str,
    near_dup_threshold: float = 0.85,
    eval_sheet_limit: int = 50,
) -> dict[str, object]:
    """Execute full benchmark DQC audit and write structured deliverables."""
    os.makedirs(out_dir, exist_ok=True)
    records, schema_issues = load_cmmlu_dir(data_dir)

    findings: list[AuditFinding] = []
    for rec in records:
        findings.extend(check_item_level(rec))
    findings.extend(check_dataset_level(records, near_dup_threshold=near_dup_threshold))
    findings.sort(key=lambda x: (SEVERITY_RANK.get(x.severity, 9), x.check_code, x.uid))

    summaries = summarize_subjects(records, findings)
    rec_by_uid = {r.uid: r for r in records}

    findings_path = os.path.join(out_dir, "findings.jsonl")
    with open(findings_path, "w", encoding="utf-8") as f:
        for item in findings:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")

    eval_sheet_path = os.path.join(out_dir, "badcase_eval_sheet.csv")
    _write_eval_sheet(eval_sheet_path, findings, rec_by_uid, limit=eval_sheet_limit)

    report_path = os.path.join(out_dir, "audit_report.md")
    _write_markdown_report(report_path, data_dir, records, schema_issues, findings, summaries)

    return {
        "total_records": len(records),
        "schema_issues": len(schema_issues),
        "total_findings": len(findings),
        "unique_flagged_items": len({f.uid for f in findings}),
        "severity_counts": dict(Counter(f.severity for f in findings)),
        "check_counts": dict(Counter(f.check_code for f in findings)),
        "report_path": report_path,
        "findings_path": findings_path,
        "eval_sheet_path": eval_sheet_path,
    }


def _write_eval_sheet(
    path: str,
    findings: list[AuditFinding],
    rec_by_uid: dict[str, QuestionRecord],
    limit: int,
) -> None:
    """Export curated high-priority suspect items for multi-model verification."""
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
    seen_uids: set[str] = set()
    rows_written = 0

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in findings:
            if item.uid in seen_uids:
                continue
            if item.severity not in ("critical", "high") and rows_written >= limit:
                continue
            rec = rec_by_uid.get(item.uid)
            if rec is None:
                continue
            seen_uids.add(item.uid)
            writer.writerow(
                {
                    "uid": rec.uid,
                    "split": rec.split,
                    "subject": rec.subject,
                    "row_id": rec.row_id,
                    "severity": item.severity,
                    "check_code": item.check_code,
                    "audit_detail": item.detail,
                    "question": rec.question,
                    "A": rec.options["A"],
                    "B": rec.options["B"],
                    "C": rec.options["C"],
                    "D": rec.options["D"],
                    "benchmark_answer": rec.answer,
                    "model_deepseek_ans": "",
                    "model_qwen_ans": "",
                    "model_doubao_ans": "",
                    "human_verdict": "",
                    "root_cause_notes": "",
                }
            )
            rows_written += 1
            if rows_written >= limit:
                break


def _write_markdown_report(
    path: str,
    data_dir: str,
    records: list[QuestionRecord],
    schema_issues: list[SchemaIssue],
    findings: list[AuditFinding],
    summaries: list[SubjectHealthSummary],
) -> None:
    """Render an auditable Markdown summary report with real trace evidence."""
    dev_n = sum(1 for r in records if r.split == "dev")
    test_n = sum(1 for r in records if r.split == "test")
    flagged_uids = {f.uid for f in findings}
    sev_counts = Counter(f.severity for f in findings)
    chk_counts = Counter(f.check_code for f in findings)

    top_dirty_test = sorted(
        (s for s in summaries if s.split == "test"),
        key=lambda s: (s.critical_or_high_items, s.flagged_items),
        reverse=True,
    )[:15]

    lines = [
        "# CMMLU 公开基准数据集质量审计报告",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"> 审计目录：`{data_dir}`  ",
        f"> 覆盖样本：**{len(records):,}** 条（`dev`: {dev_n:,}，`test`: {test_n:,}）  ",
        f"> 检出风险条目：**{len(flagged_uids):,}** 条（占比 {len(flagged_uids)/max(len(records),1):.2%}），累计触发规则 **{len(findings):,}** 次，Schema 异常 **{len(schema_issues)}** 项",
        "",
        "## 一、缺陷分级与规则分布",
        "",
        "| 严重级别 | 命中次数 | 说明 |",
        "| :--- | ---: | :--- |",
        f"| critical | {sev_counts.get('critical', 0)} | 冲突标准答案 / 重复选项 / 缺失必填字段 |",
        f"| high | {sev_counts.get('high', 0)} | 残缺图表上下文（瞎子题） / dev-test 精确或近似泄露 |",
        f"| medium | {sev_counts.get('medium', 0)} | 康熙部首 OCR 污染 / LaTeX 语法断裂 / HTML 残留 / 跨题重复 |",
        f"| low | {sev_counts.get('low', 0)} | 题干过短或截断风险 |",
        "",
        "| 规则编号 | 命中次数 |",
        "| :--- | ---: |",
    ]
    for code, cnt in chk_counts.most_common():
        lines.append(f"| `{code}` | {cnt} |")

    lines.extend(
        [
            "",
            "## 二、问题最集中学科排行（Test 集 Top 15）",
            "",
            "| 学科 | 总题数 | 高危/致命题数 | 累计命中题数 | 最大单选项占比 |",
            "| :--- | ---: | ---: | ---: | ---: |",
        ]
    )
    for s in top_dirty_test:
        lines.append(
            f"| `{s.subject}` | {s.total_items} | {s.critical_or_high_items} | {s.flagged_items} | {s.max_answer_share:.1%} |"
        )

    lines.extend(
        [
            "",
            "## 三、高置信真实缺陷样本摘录（供人工复核与模型 Bad Case 实测）",
            "",
        ]
    )
    shown_codes: Counter[str] = Counter()
    for item in findings:
        if item.severity not in ("critical", "high", "medium"):
            continue
        if shown_codes[item.check_code] >= 5:
            continue
        shown_codes[item.check_code] += 1
        lines.append(
            f"- **[{item.severity.upper()}] `{item.uid}`** (`{item.check_code}`): {item.detail}  \n"
            f"  题干摘录：`{item.evidence.replace('`', '')}`"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
