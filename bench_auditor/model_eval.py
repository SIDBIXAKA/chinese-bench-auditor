"""Optional OpenAI-compatible evaluation runner and offline disagreement scorer."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter

ANSWER_EXTRACT_RE = re.compile(r"\b([ABCD])\b")


def extract_choice(text: str) -> str:
    """Extract normalized option letter A-D from raw model text."""
    cleaned = text.strip().upper()
    if cleaned in {"A", "B", "C", "D"}:
        return cleaned
    matches = ANSWER_EXTRACT_RE.findall(cleaned)
    return matches[0] if matches else "INVALID"


def call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    question: str,
    options: dict[str, str],
    timeout: int = 30,
) -> str:
    """Query an OpenAI-compatible chat completions endpoint for one MCQ item."""
    import requests  # Optional runtime dependency

    prompt = (
        "请阅读以下中文单项选择题。如果题干缺少必要的图片、表格或存在明显条件矛盾，"
        "请直接回答 UNANSWERABLE；否则仅输出唯一正确选项字母（A、B、C 或 D）。\n\n"
        f"题目：{question}\n"
        f"A. {options['A']}\n"
        f"B. {options['B']}\n"
        f"C. {options['C']}\n"
        f"D. {options['D']}\n"
    )
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
    if "UNANSWERABLE" in content.upper():
        return "UNANSWERABLE"
    return extract_choice(content)


def summarize_eval_sheet(csv_path: str) -> dict[str, object]:
    """Summarize benchmark vs multi-model agreement and suspected gold errors."""
    model_cols = ("model_deepseek_ans", "model_qwen_ans", "model_doubao_ans")
    total = 0
    evaluated = 0
    unanimous_disagree = 0
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
                if len(preds) >= 2 and len(set(preds)) == 1 and preds[0] != gold:
                    unanimous_disagree += 1

    return {
        "total_rows": total,
        "evaluated_rows": evaluated,
        "unanimous_disagree_with_gold": unanimous_disagree,
        "human_verdicts": dict(verdict_counts),
    }
