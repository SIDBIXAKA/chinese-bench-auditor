"""Dataset loaders and schema validation for benchmark CSV/JSONL files."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from typing import Iterable

EXPECTED_CMMLU_HEADER = ["", "Question", "A", "B", "C", "D", "Answer"]
OPTION_KEYS = ("A", "B", "C", "D")


@dataclass(frozen=True)
class QuestionRecord:
    """Normalized multiple-choice benchmark item."""

    uid: str
    split: str
    subject: str
    row_id: str
    question: str
    options: dict[str, str]
    answer: str
    source_file: str


@dataclass(frozen=True)
class SchemaIssue:
    """File-level or row-level schema parsing anomaly."""

    split: str
    subject: str
    line_no: int
    source_file: str
    detail: str


def load_csv_file(
    file_path: str, split: str, subject: str
) -> tuple[list[QuestionRecord], list[SchemaIssue]]:
    """Load one CMMLU-format CSV file and collect schema issues."""
    records: list[QuestionRecord] = []
    issues: list[SchemaIssue] = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            issues.append(SchemaIssue(split, subject, 0, file_path, "Empty CSV file"))
            return records, issues
        if header != EXPECTED_CMMLU_HEADER:
            issues.append(
                SchemaIssue(
                    split,
                    subject,
                    1,
                    file_path,
                    f"Unexpected header {header!r}, expected {EXPECTED_CMMLU_HEADER!r}",
                )
            )
            return records, issues

        for line_no, row in enumerate(reader, start=2):
            if len(row) != 7:
                issues.append(
                    SchemaIssue(
                        split,
                        subject,
                        line_no,
                        file_path,
                        f"Expected 7 columns, got {len(row)}",
                    )
                )
                continue
            row_id = row[0].strip()
            uid = f"{split}/{subject}#{row_id}"
            records.append(
                QuestionRecord(
                    uid=uid,
                    split=split,
                    subject=subject,
                    row_id=row_id,
                    question=row[1],
                    options={"A": row[2], "B": row[3], "C": row[4], "D": row[5]},
                    answer=row[6].strip(),
                    source_file=file_path,
                )
            )
    return records, issues


def load_cmmlu_dir(
    root_dir: str, splits: Iterable[str] = ("dev", "test")
) -> tuple[list[QuestionRecord], list[SchemaIssue]]:
    """Load all subject CSV files across splits under a CMMLU directory."""
    records: list[QuestionRecord] = []
    issues: list[SchemaIssue] = []

    for split in splits:
        split_dir = os.path.join(root_dir, split)
        if not os.path.isdir(split_dir):
            issues.append(
                SchemaIssue(split, "*", 0, split_dir, f"Missing split directory: {split_dir}")
            )
            continue
        for fname in sorted(os.listdir(split_dir)):
            if not fname.endswith(".csv"):
                continue
            subject = fname[:-4]
            fpath = os.path.join(split_dir, fname)
            recs, errs = load_csv_file(fpath, split=split, subject=subject)
            records.extend(recs)
            issues.extend(errs)
    return records, issues


def load_jsonl_file(
    file_path: str, split: str = "custom", subject: str = "custom"
) -> tuple[list[QuestionRecord], list[SchemaIssue]]:
    """Load generic JSONL multiple-choice records with Question/A-D/Answer fields."""
    records: list[QuestionRecord] = []
    issues: list[SchemaIssue] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(
                    SchemaIssue(split, subject, line_no, file_path, f"Invalid JSON: {exc}")
                )
                continue
            row_id = str(obj.get("id", line_no - 1))
            rec_split = str(obj.get("split", split))
            rec_subj = str(obj.get("subject", subject))
            records.append(
                QuestionRecord(
                    uid=f"{rec_split}/{rec_subj}#{row_id}",
                    split=rec_split,
                    subject=rec_subj,
                    row_id=row_id,
                    question=str(obj.get("question") or obj.get("Question") or ""),
                    options={k: str(obj.get(k, "")) for k in OPTION_KEYS},
                    answer=str(obj.get("answer") or obj.get("Answer") or "").strip(),
                    source_file=file_path,
                )
            )
    return records, issues
