"""Command-line interface for chinese-bench-auditor."""

from __future__ import annotations

import argparse
import json
import os
import sys

from bench_auditor.audit import run_audit
from bench_auditor.model_eval import (
    DEFAULT_MODEL_COLUMNS,
    DEFAULT_SILICONFLOW_URL,
    evaluate_eval_sheet,
    export_web_prompts,
    summarize_eval_sheet,
)


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

    p_run = sub.add_parser("run-eval", help="Evaluate badcase_eval_sheet.csv via OpenAI-compatible API")
    p_run.add_argument("--csv", required=True, help="Path to badcase_eval_sheet.csv")
    p_run.add_argument("--api-key", default="", help="API key (defaults to SILICONFLOW_API_KEY env)")
    p_run.add_argument("--base-url", default=DEFAULT_SILICONFLOW_URL)
    p_run.add_argument("--limit", type=int, default=50)
    p_run.add_argument("--summary-md", default="", help="Optional path to write Markdown eval summary")

    p_prompts = sub.add_parser("export-prompts", help="Export copy-paste web chat prompt batches")
    p_prompts.add_argument("--csv", required=True, help="Path to badcase_eval_sheet.csv")
    p_prompts.add_argument("--out", required=True, help="Output txt file path")
    p_prompts.add_argument("--limit", type=int, default=20)

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

    if args.command == "run-eval":
        api_key = args.api_key or os.environ.get("SILICONFLOW_API_KEY", "")
        if not api_key:
            print("Error: provide --api-key or set SILICONFLOW_API_KEY", file=sys.stderr)
            return 2
        summary = evaluate_eval_sheet(
            csv_path=args.csv,
            api_key=api_key,
            base_url=args.base_url,
            model_map=DEFAULT_MODEL_COLUMNS,
            limit=args.limit,
            summary_md_path=args.summary_md or None,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-prompts":
        count = export_web_prompts(args.csv, args.out, limit=args.limit)
        print(json.dumps({"exported_items": count, "out": args.out}, ensure_ascii=False))
        return 0

    if args.command == "summarize-eval":
        summary = summarize_eval_sheet(args.csv)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
