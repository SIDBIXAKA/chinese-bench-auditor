"""OpenAI-compatible evaluation runner, prompt exporter, and disagreement analyzer."""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from typing import Callable

ANSWER_EXTRACT_RE = re.compile(r"\b([ABCD])\b")
DEFAULT_SILICONFLOW_URL = "https://api.siliconflow.cn/v1"

DEFAULT_MODEL_COLUMNS: dict[str, str] = {
    "model_deepseek_ans": "deepseek-ai/DeepSeek-V3",
    "model_qwen_ans": "Qwen/Qwen2.5-7B-Instruct",
}


def extract_choice(text: str) -> str:
    """Extract normalized option letter A-D or UNANSWERABLE from raw model text."""
    cleaned = text.strip().upper()
    if "UNANSWERABLE" in cleaned:
        return "UNANSWERABLE"
    if cleaned in {"A", "B", "C", "D"}:
        return cleaned
    matches = ANSWER_EXTRACT_RE.findall(cleaned)
    return matches[0] if matches else "INVALID"


def build_mcq_prompt(question: str, options: dict[str, str]) -> str:
    """Format one multiple-choice item with explicit unanswerable guard."""
    return (
        "请阅读以下中文单项选择题。如果题干缺少必要的图片、表格或存在明显条件矛盾，"
        "请直接回答 UNANSWERABLE；否则仅输出唯一正确选项字母（A、B、C 或 D）。\n\n"
        f"题目：{question}\n"
        f"A. {options['A']}\n"
        f"B. {options['B']}\n"
        f"C. {options['C']}\n"
        f"D. {options['D']}\n"
    )


def call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    question: str,
    options: dict[str, str],
    timeout: int = 45,
) -> str:
    """Query an OpenAI-compatible chat completions endpoint for one MCQ item."""
    import requests

    prompt = build_mcq_prompt(question, options)
    resp = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        data=json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 128,
            }
        ),
        timeout=timeout,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return extract_choice(content)


def classify_disagreement(check_code: str, gold: str, preds: list[str]) -> str:
    """Assign an actionable Bad Case taxonomy bucket from audit rule and model predictions."""
    clean_preds = [p for p in preds if p and p not in {"INVALID", "ERROR"}]
    if not clean_preds:
        return "UNEVALUATED"
    if check_code == "CHK_MISSING_VISUAL_CONTEXT":
        if any(p in {"A", "B", "C", "D"} for p in clean_preds):
            return "BLIND_CONTEXT_HALLUCINATION"
        return "BLIND_CONTEXT_ABSTAINED"
    if len(set(clean_preds)) == 1 and clean_preds[0] != gold:
        return "SUSPECTED_GOLD_ERROR_MODEL_UNANIMOUS"
    if len(set(clean_preds)) == 1 and clean_preds[0] == gold:
        return "MODELS_AGREE_WITH_GOLD"
    return "MODEL_SPLIT_OR_ERROR"


def evaluate_eval_sheet(
    csv_path: str,
    api_key: str,
    base_url: str = DEFAULT_SILICONFLOW_URL,
    model_map: dict[str, str] | None = None,
    limit: int = 50,
    summary_md_path: str | None = None,
    caller: Callable[[str, str, str, str, dict[str, str]], str] = call_openai_compatible,
) -> dict[str, object]:
    """Run batch evaluation over badcase_eval_sheet.csv with resume support and write summary."""
    active_map = model_map or DEFAULT_MODEL_COLUMNS
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    pending = 0  # rows still needing at least one model answer
    api_calls = 0
    errors = 0

    for row in rows:
        options = {k: row.get(k, "") for k in ("A", "B", "C", "D")}
        needs_work = any(
            not (row.get(col) or "").strip() or (row.get(col) or "").strip() == "ERROR"
            for col in active_map
        )
        if needs_work:
            if pending >= limit:
                break
            pending += 1

        for col, model_id in active_map.items():
            if col not in fieldnames:
                fieldnames.append(col)
            existing = (row.get(col) or "").strip()
            if existing and existing != "ERROR":
                continue
            try:
                row[col] = caller(base_url, api_key, model_id, row.get("question", ""), options)
            except Exception as exc:
                row[col] = "ERROR"
                errors += 1
            api_calls += 1

        preds = [(row.get(c) or "").strip().upper() for c in active_map]
        if not (row.get("human_verdict") or "").strip():
            bucket = classify_disagreement(
                row.get("check_code", ""), (row.get("benchmark_answer") or "").strip().upper(), preds
            )
            if bucket != "UNEVALUATED":
                row["root_cause_notes"] = row.get("root_cause_notes") or f"auto:{bucket}"

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize_eval_sheet(csv_path, model_cols=tuple(active_map.keys()))
    summary["api_calls_made"] = api_calls
    summary["api_errors"] = errors

    if summary_md_path:
        _write_eval_summary_md(summary_md_path, rows, active_map, summary)
        summary["summary_md_path"] = summary_md_path
    return summary


def export_web_prompts(csv_path: str, out_txt_path: str, limit: int = 20, batch_size: int = 10) -> int:
    """Export curated questions into copy-pasteable web-chat batches (zero API cost fallback)."""
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))[:limit]

    lines = [
        "# 网页端大模型零成本对照测试指令包",
        "# 请将每一批完整粘贴到 DeepSeek / 通义千问 / 豆包网页对话框，要求按行输出 JSON 或编号答案。",
        "",
    ]
    for start in range(0, len(rows), batch_size):
        chunk = rows[start : start + batch_size]
        lines.append(f"## Batch {start // batch_size + 1} (Items {start + 1}-{start + len(chunk)})")
        lines.append(
            "请逐题作答下列选择题。若题干缺失必要图片/表格，请回答 UNANSWERABLE；"
            "否则输出格式为 `uid | 选项字母 | 一句话理由`："
        )
        lines.append("")
        for r in chunk:
            lines.append(f"[{r['uid']}] {r['question']}")
            lines.append(f"A. {r['A']}  B. {r['B']}  C. {r['C']}  D. {r['D']}")
        lines.append("")

    with open(out_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return len(rows)


def summarize_eval_sheet(
    csv_path: str,
    model_cols: tuple[str, ...] = ("model_deepseek_ans", "model_qwen_ans", "model_doubao_ans"),
) -> dict[str, object]:
    """Summarize benchmark vs multi-model agreement and Bad Case taxonomy."""
    total = 0
    evaluated = 0
    taxonomy_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            total += 1
            verdict = (row.get("human_verdict") or "").strip()
            if verdict:
                verdict_counts[verdict] += 1
            preds = [
                (row.get(col) or "").strip().upper()
                for col in model_cols
                if (row.get(col) or "").strip()
            ]
            if preds:
                evaluated += 1
                gold = (row.get("benchmark_answer") or "").strip().upper()
                bucket = classify_disagreement(row.get("check_code", ""), gold, preds)
                taxonomy_counts[bucket] += 1

    return {
        "total_rows": total,
        "evaluated_rows": evaluated,
        "taxonomy_counts": dict(taxonomy_counts),
        "human_verdicts": dict(verdict_counts),
    }


def _write_eval_summary_md(
    path: str,
    rows: list[dict[str, str]],
    model_map: dict[str, str],
    summary: dict[str, object],
) -> None:
    lines = [
        "# 多模型 Bad Case 实测对比汇总报告",
        "",
        f"- 样本总数：{summary['total_rows']} | 已实测条数：{summary['evaluated_rows']}",
        f"- 参与模型：{', '.join(f'{k}={v}' for k, v in model_map.items())}",
        "",
        "## 一、分歧归因分类统计",
        "",
        "| 归因类别 | 样本数 | 含义 |",
        "| :--- | ---: | :--- |",
    ]
    labels = {
        "SUSPECTED_GOLD_ERROR_MODEL_UNANIMOUS": "多模型一致答案且不同于题库金标（高度疑似题库标错）",
        "BLIND_CONTEXT_HALLUCINATION": "缺失图片/表格上下文，但模型仍强行瞎猜作答（模型幻觉）",
        "BLIND_CONTEXT_ABSTAINED": "缺失图片/表格上下文，模型正确识别并拒答 UNANSWERABLE",
        "MODELS_AGREE_WITH_GOLD": "多模型作答与原金标一致",
        "MODEL_SPLIT_OR_ERROR": "模型之间存在分歧或部分模型推理错误",
    }
    for bucket, cnt in summary.get("taxonomy_counts", {}).items():  # type: ignore[union-attr]
        lines.append(f"| `{bucket}` | {cnt} | {labels.get(bucket, '')} |")

    lines.extend(["", "## 二、典型案例明晰（前 15 条已测记录）", ""])
    cols = list(model_map.keys())
    shown = 0
    for row in rows:
        preds = [row.get(c, "").strip() for c in cols if row.get(c, "").strip()]
        if not preds:
            continue
        shown += 1
        if shown > 15:
            break
        pred_str = ", ".join(f"{c}={row.get(c, '').strip()}" for c in cols if row.get(c, "").strip())
        lines.append(
            f"- **`{row['uid']}`** (`{row['check_code']}`) | 原金标: `{row['benchmark_answer']}` | {pred_str}  \n"
            f"  题干：{row['question'][:90]}"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
