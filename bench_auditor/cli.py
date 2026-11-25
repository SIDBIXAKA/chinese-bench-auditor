"""Command-line interface for chinese-bench-auditor."""

from __future__ import annotations

import argparse
import json
import sys

from bench_auditor.audit import run_audit
from bench_auditor.model_eval import summarize_eval_sheet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bench_auditor",
        description="Chinese LLM benchmark quality control, leakage, and bad-case auditor",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="Run full DQC audit on a CMMLU-layout directory")
    p_audit.add_argument("--data-dir", required=True, help="Directory containing dev/ and test/ CSVs")
    p_audit.add_argument("--out-dir", required=True, help="Output directory for report and JSONL/CSV")
    p_audit.add_argument("--near-dup-threshold", type=float, default=0.85)
    p_audit.add_argument("--eval-sheet-limit", type=int, default=50)

    p_eval = sub.add_parser("summarize-eval", help="Summarize filled badcase_eval_sheet.csv")
    p_eval.add_argument("--csv", required=True, help="Path to badcase_eval_sheet.csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "audit":
        summary = run_audit(
            data_dir=args.data_dir,
            out_dir=args.out_dir,
            near_dup_threshold=args.near_dup_threshold,
            eval_sheet_limit=args.eval_sheet_limit,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if args.command == "summarize-eval":
        summary = summarize_eval_sheet(args.csv)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
