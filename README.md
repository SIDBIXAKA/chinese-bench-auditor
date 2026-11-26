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

# 3. 方式A：使用硅基流动等 OpenAI 兼容 API 一键批量测试高危 Bad Case（支持断点续跑）
python -m bench_auditor run-eval --csv outputs/cmmlu_v1_0_1/badcase_eval_sheet.csv --api-key sk-xxx --summary-md outputs/cmmlu_v1_0_1/eval_summary.md

# 4. 方式B：零 API 成本导出网页端批次测试题（可直接贴入 DeepSeek / 豆包 / 通义网页）
python -m bench_auditor export-prompts --csv outputs/cmmlu_v1_0_1/badcase_eval_sheet.csv --out outputs/cmmlu_v1_0_1/web_eval_prompts.txt --limit 20

# 5. 汇总人工/多模型核查表（可重新渲染 Markdown 报告）
python -m bench_auditor summarize-eval --csv outputs/cmmlu_v1_0_1/badcase_eval_sheet.csv --summary-md outputs/cmmlu_v1_0_1/eval_summary.md
```

## 实证战果（CMMLU v1.0.1 全量审计与多模型对比）

- **全量数据审计**：扫描 CMMLU 11,917 条样本，检出 772 条缺陷条目（819 次规则命中），包含 12 组同题金标冲突、1 处重复选项、3 处纯文本缺失图表“瞎子题”及 4 对 `dev -> test` 精确泄露。
- **上游开源社区贡献**：
  - 提交官方 Issue：[haonan-li/CMMLU#94](https://github.com/haonan-li/CMMLU/issues/94)
  - 提交修复 Pull Request：修正 `data/test/high_school_mathematics.csv` 第 130 行（`id=128`）集合真子集金标错标（`C -> A`）。
- **多模型 Bad Case 实测（50 条高危样本，`DeepSeek-V3` vs `Qwen2.5-7B-Instruct`）**：
  - `MODELS_AGREE_WITH_GOLD`：24 条
  - `MODEL_SPLIT_OR_ERROR`：14 条
  - `SUSPECTED_GOLD_ERROR_MODEL_UNANIMOUS`：7 条（两模型一致且与原金标冲突，高度疑似题库错标）
  - `BLIND_CONTEXT_HALLUCINATION`：4 条（缺失图表上下文时模型仍强行作答）
  - `BLIND_CONTEXT_ABSTAINED`：1 条（模型正确拒答 `UNANSWERABLE`）
- **人工抽检最终裁决（已核查 10 条高危分歧样本）**：
  - 实锤题库错标（`GOLD_ERROR`）：4 条（含 `test/high_school_mathematics#128`、`test/logical#84`、`test/education#114`、`test/sociology#1`）
  - 题库正确且模型集体翻车（`MODEL_ERROR_GOLD_CORRECT`）：3 条（含高等数学可去间断点 2 题与社会学默顿理论 1 题）
  - 题库正确对照组（`GOLD_CORRECT`）：3 条
  - 详细实证报告见 [`outputs/cmmlu_v1_0_1/eval_summary.md`](outputs/cmmlu_v1_0_1/eval_summary.md)
