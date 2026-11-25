# Chinese LLM Benchmark Quality Auditor (`chinese-bench-auditor`)

面向中文大模型评测基准（如 CMMLU 等）的数据质量控制（DQC）、跨集泄露检测与 Bad Case 核查工程工具。零重型外部依赖（仅用 Python 标准库即可完成全量审计，多模型 API 实测可选配 `requests`）。

## 核心能力

1. **Schema 与字段完整性校验** (`loader.py`)：严格核查表头、列宽对齐、空值/占位符及非法答案键值。
2. **七维细粒度 DQC 质检规则** (`checks.py`)：
   - `CHK_INVALID_ANSWER_KEY` / `CHK_EMPTY_OR_NAN_FIELD`：非法答案标签或空/NaN 字段。
   - `CHK_DUPLICATE_OPTIONS`：符号与小数位安全的选项归一化去重（区分 `-0.014` 与 `0.014`、`1.8km` 与 `18km`）。
   - `CHK_MISSING_VISUAL_CONTEXT`：识别在纯文本评测中引用缺失图片/表格的“瞎子题”（如“如图所示”“下表所示”）。
   - `CHK_LATEX_SYNTAX_BROKEN`：未配对 `$` 与花括号失衡扫描。
   - `CHK_KANGXI_OCR_ARTIFACT` / `CHK_HTML_OR_MOJIBAKE`：识别 PDF OCR 残留的康熙部首（`U+2F00..2FDF`，如 `⻄`、`⾯`、`⼀`）与未清洗 HTML 标签（过滤数学不等式误报）。
   - `CHK_CONFLICTING_GOLD_ANSWER` / `CHK_DEV_TEST_LEAKAGE` / `CHK_EXACT_DUPLICATE_ITEM`：基于题干与排序选项哈希，精准区分“同题同答案泄露”与“同题异答案标错冲突”。
   - `CHK_DEV_TEST_NEAR_LEAKAGE`：基于 3-gram 倒排索引加速的 `dev -> test` 高相似度近重复泄露扫描。
3. **交付物导出与多模型对比** (`audit.py`, `model_eval.py`)：一键输出 `audit_report.md`、`findings.jsonl` 与可填入 DeepSeek / Qwen / Doubao 实测结果的 `badcase_eval_sheet.csv`。

## 快速运行

```bash
# 1. 运行自动化单元测试
python -m unittest discover -s tests -v

# 2. 对 CMMLU 数据集执行全量审计
python -m bench_auditor audit --data-dir data/raw/cmmlu --out-dir outputs/cmmlu_v1_0_1

# 3. 汇总人工/多模型核查表
python -m bench_auditor summarize-eval --csv outputs/cmmlu_v1_0_1/badcase_eval_sheet.csv
```
