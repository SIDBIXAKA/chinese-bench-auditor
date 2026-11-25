"""Calibrated DQC, leakage, formatting, and consistency checks for benchmarks."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass

from bench_auditor.loader import OPTION_KEYS, QuestionRecord

VALID_ANSWERS = frozenset(OPTION_KEYS)
PLACEHOLDER_LITERALS = frozenset({"nan", "none", "null", "n/a"})

# Visual/table context cues that indicate an unanswerable question without external media
VISUAL_CONTEXT_RE = re.compile(
    r"(如图所示|如下[图表]所示|见[图表]|下[图表]所?示|上[图表]所?示|左图|右图|以下图|"
    r"(?<![代发外手列])表\s*[0-9一二三四五六七八九十]+|图\s*[0-9一二三四五六七八九十]+)"
)
# Exclude false positives where markdown table pipes or inline choices carry the data
EMBEDDED_TABLE_RE = re.compile(r"\|.+\|.+\n\|[-: |]+\|")

# Genuine HTML markup or encoding artifacts (require tag terminator/space so <P(A)<1 never matches)
HTML_ARTIFACT_RE = re.compile(
    r"(</?(?:br|p|div|span|img|table|tr|td|th|b|strong|i|em|sup|sub|font|ul|ol|li|a)(?=[\s/>])[^>]*>|"
    r"&(?:nbsp|lt|gt|amp|quot);|\ufffd)",
    re.IGNORECASE,
)

# Unicode Kangxi Radicals (U+2F00-U+2FDF) & CJK Radicals Supplement (U+2E80-U+2EFF) from PDF OCR
KANGXI_RADICAL_RE = re.compile(r"[\u2e80-\u2eff\u2f00-\u2fdf]")

# Unescaped LaTeX inline math delimiter
UNESCAPED_DOLLAR_RE = re.compile(r"(?<!\\)\$")

TRUNCATION_TAIL_RE = re.compile(r"(?:[=+\-*/\\]$|\.\.\.$|…$)")


@dataclass(frozen=True)
class AuditFinding:
    """Single quality defect or leakage finding tied to a benchmark record."""

    uid: str
    split: str
    subject: str
    row_id: str
    check_code: str
    severity: str  # critical | high | medium | low
    detail: str
    evidence: str


@dataclass(frozen=True)
class SubjectHealthSummary:
    """Aggregate quality and answer-distribution metrics for one split/subject."""

    split: str
    subject: str
    total_items: int
    flagged_items: int
    critical_or_high_items: int
    answer_counts: dict[str, int]
    max_answer_share: float
    answer_entropy_bits: float


def normalize_stem(text: str) -> str:
    """Normalize text for duplicate stem matching while keeping digits and semantic words."""
    nfkc = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[\s，。、；：！？\"'“”‘’（）()\[\]【】{}.,;:!?_]+", "", nfkc)


def normalize_option(text: str) -> str:
    """Normalize an option while preserving case (e.g., GG vs gg, FILE vs file), signs, and decimals."""
    nfkc = unicodedata.normalize("NFKC", text).strip()
    cleaned = re.sub(r"\s+", "", nfkc)
    return cleaned.strip("。；，、.")


def char_ngrams(text: str, n: int = 3) -> set[str]:
    """Generate character n-grams for Jaccard similarity checks."""
    if len(text) < n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two n-gram sets."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / (len(a) + len(b) - inter)


def _count_unescaped_dollars(text: str) -> int:
    return len(UNESCAPED_DOLLAR_RE.findall(text))


def _brace_balance_delta(text: str) -> int:
    """Return abs(unclosed '{' - '}') ignoring escaped braces."""
    cleaned = text.replace(r"\{", "").replace(r"\}", "")
    return abs(cleaned.count("{") - cleaned.count("}"))


def check_item_level(record: QuestionRecord) -> list[AuditFinding]:
    """Run all single-record DQC rules on one benchmark item."""
    findings: list[AuditFinding] = []
    q = record.question.strip()

    # 1. Invalid answer key or missing/placeholder text fields
    if record.answer not in VALID_ANSWERS:
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_INVALID_ANSWER_KEY",
                "critical",
                f"Answer key {record.answer!r} is not in A/B/C/D",
                q[:80],
            )
        )

    bad_fields = [
        name
        for name, val in [("Question", q), *[(k, record.options[k].strip()) for k in OPTION_KEYS]]
        if not val or val.lower() in PLACEHOLDER_LITERALS
    ]
    if bad_fields:
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_EMPTY_OR_NAN_FIELD",
                "critical",
                f"Empty or placeholder fields: {', '.join(bad_fields)}",
                q[:80],
            )
        )

    # 2. Duplicate options (after sign/decimal-safe normalization)
    opt_norms = {k: normalize_option(record.options[k]) for k in OPTION_KEYS}
    non_empty_norms = [v for v in opt_norms.values() if v]
    if len(set(non_empty_norms)) < len(non_empty_norms):
        dup_pairs = [
            f"{k1}={k2}({record.options[k1]!r})"
            for i, k1 in enumerate(OPTION_KEYS)
            for k2 in OPTION_KEYS[i + 1 :]
            if opt_norms[k1] and opt_norms[k1] == opt_norms[k2]
        ]
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_DUPLICATE_OPTIONS",
                "critical",
                f"Identical normalized options: {'; '.join(dup_pairs)}",
                q[:80],
            )
        )

    # 3. Missing visual or table context ("blind" multimodal/tabular questions)
    vis_match = VISUAL_CONTEXT_RE.search(q)
    if vis_match and not EMBEDDED_TABLE_RE.search(q):
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_MISSING_VISUAL_CONTEXT",
                "high",
                f"References missing figure/table ({vis_match.group(1)!r}) in text-only CSV",
                q[:120],
            )
        )

    # 4. LaTeX corruption (unpaired '$' or severe brace mismatch)
    full_text = " ".join([q, *(record.options[k] for k in OPTION_KEYS)])
    q_dollars = _count_unescaped_dollars(q)
    if q_dollars % 2 == 1:
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_LATEX_SYNTAX_BROKEN",
                "medium",
                f"Odd count of unescaped '$' ({q_dollars}) in question stem",
                q[:120],
            )
        )
    elif "$" in full_text and _brace_balance_delta(q) > 0:
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_LATEX_SYNTAX_BROKEN",
                "medium",
                f"Unbalanced curly braces inside math question (delta={_brace_balance_delta(q)})",
                q[:120],
            )
        )

    # 5. Kangxi radicals from PDF OCR & HTML/replacement-char artifacts
    kangxi_chars = sorted(set(KANGXI_RADICAL_RE.findall(full_text)))
    if kangxi_chars:
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_KANGXI_OCR_ARTIFACT",
                "medium",
                f"Contains {len(kangxi_chars)} PDF-OCR Kangxi/CJK radical chars: {''.join(kangxi_chars[:8])}",
                q[:100],
            )
        )

    html_hit = HTML_ARTIFACT_RE.search(full_text)
    if html_hit:
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_HTML_OR_MOJIBAKE",
                "medium",
                f"Contains raw HTML/mojibake token: {html_hit.group(0)!r}",
                q[:100],
            )
        )

    # 6. Truncated / suspiciously short stems
    if 0 < len(q) < 6 or TRUNCATION_TAIL_RE.search(q):
        findings.append(
            AuditFinding(
                record.uid,
                record.split,
                record.subject,
                record.row_id,
                "CHK_TRUNCATED_STEM",
                "low",
                f"Suspicious short or cut-off stem (len={len(q)})",
                q[:100],
            )
        )

    return findings


def _item_signature(record: QuestionRecord) -> str:
    """Hash stem + option set + gold option text to identify identical MCQ duplicates."""
    stem_n = normalize_stem(record.question)
    opts_sorted = sorted(normalize_option(record.options[k]) for k in OPTION_KEYS)
    payload = stem_n + "||" + "||".join(opts_sorted)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def check_dataset_level(
    records: list[QuestionRecord], near_dup_threshold: float = 0.85
) -> list[AuditFinding]:
    """Detect exact duplicates, dev->test leakage, conflicting labels, and near-duplicates."""
    findings: list[AuditFinding] = []

    # Exact MCQ signature groups (same stem + same 4 options regardless of A/B/C/D order)
    by_exact_sig: dict[str, list[QuestionRecord]] = defaultdict(list)
    by_stem: dict[str, list[QuestionRecord]] = defaultdict(list)
    for rec in records:
        by_exact_sig[_item_signature(rec)].append(rec)
        stem_n = normalize_stem(rec.question)
        if len(stem_n) >= 8:
            by_stem[stem_n].append(rec)

    # Group 1: Exact MCQ duplicates & conflicting gold-answer text
    for sig, grp in by_exact_sig.items():
        if len(grp) < 2:
            continue
        splits = {r.split for r in grp}
        gold_texts = {
            normalize_option(r.options[r.answer])
            for r in grp
            if r.answer in VALID_ANSWERS
        }
        has_conflict = len(gold_texts) > 1
        has_leakage = "dev" in splits and "test" in splits
        peers = ", ".join(r.uid for r in grp)

        for r in grp:
            if has_conflict:
                findings.append(
                    AuditFinding(
                        r.uid,
                        r.split,
                        r.subject,
                        r.row_id,
                        "CHK_CONFLICTING_GOLD_ANSWER",
                        "critical",
                        f"Identical question & options have conflicting gold answers across [{peers}]",
                        r.question[:100],
                    )
                )
            elif has_leakage:
                findings.append(
                    AuditFinding(
                        r.uid,
                        r.split,
                        r.subject,
                        r.row_id,
                        "CHK_DEV_TEST_LEAKAGE",
                        "high",
                        f"Exact dev/test split leakage across [{peers}] (sig={sig})",
                        r.question[:100],
                    )
                )
            else:
                findings.append(
                    AuditFinding(
                        r.uid,
                        r.split,
                        r.subject,
                        r.row_id,
                        "CHK_EXACT_DUPLICATE_ITEM",
                        "medium",
                        f"Exact duplicate item across [{peers}] (sig={sig})",
                        r.question[:100],
                    )
                )

    # Group 2: Dev->Test stem near-duplicates via 3-gram Jaccard with shared bucket pre-filtering
    dev_recs = [r for r in records if r.split == "dev" and len(normalize_stem(r.question)) >= 12]
    test_recs = [r for r in records if r.split == "test" and len(normalize_stem(r.question)) >= 12]
    exact_pairs_seen = {
        (a.uid, b.uid)
        for grp in by_exact_sig.values()
        if len(grp) > 1
        for a in grp
        for b in grp
        if a.uid != b.uid
    }

    # Index dev items by 3-gram to avoid O(N*M) full scan
    dev_ngrams: dict[str, set[str]] = {}
    inverted_index: dict[str, list[QuestionRecord]] = defaultdict(list)
    for d in dev_recs:
        grams = char_ngrams(normalize_stem(d.question), n=3)
        dev_ngrams[d.uid] = grams
        for g in grams:
            inverted_index[g].append(d)

    for t in test_recs:
        t_grams = char_ngrams(normalize_stem(t.question), n=3)
        candidate_hits: Counter[str] = Counter()
        dev_lookup: dict[str, QuestionRecord] = {}
        for g in t_grams:
            for d in inverted_index.get(g, ()):
                candidate_hits[d.uid] += 1
                dev_lookup[d.uid] = d
        for d_uid, overlap in candidate_hits.items():
            # Exact necessary upper-bound condition: |A∩B|/|A| >= |A∩B|/|A∪B| >= threshold
            if overlap / max(len(t_grams), 1) < near_dup_threshold:
                continue
            d = dev_lookup[d_uid]
            if (d.uid, t.uid) in exact_pairs_seen:
                continue
            sim = jaccard_similarity(dev_ngrams[d.uid], t_grams)
            if sim >= near_dup_threshold:
                findings.append(
                    AuditFinding(
                        t.uid,
                        t.split,
                        t.subject,
                        t.row_id,
                        "CHK_DEV_TEST_NEAR_LEAKAGE",
                        "high",
                        f"3-gram Jaccard={sim:.3f} (>= {near_dup_threshold}) with {d.uid}",
                        t.question[:100],
                    )
                )

    return findings


def summarize_subjects(
    records: list[QuestionRecord], findings: list[AuditFinding]
) -> list[SubjectHealthSummary]:
    """Compute per-(split, subject) quality metrics and answer distribution skew."""
    by_key: dict[tuple[str, str], list[QuestionRecord]] = defaultdict(list)
    for r in records:
        by_key[(r.split, r.subject)].append(r)

    flagged_uids_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    high_uids_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    for f in findings:
        key = (f.split, f.subject)
        flagged_uids_by_key[key].add(f.uid)
        if f.severity in ("critical", "high"):
            high_uids_by_key[key].add(f.uid)

    summaries: list[SubjectHealthSummary] = []
    for key in sorted(by_key):
        split, subject = key
        items = by_key[key]
        counts = Counter(r.answer for r in items if r.answer in VALID_ANSWERS)
        total = len(items)
        max_share = max(counts.values()) / total if total and counts else 0.0
        entropy = 0.0
        if total and counts:
            for cnt in counts.values():
                p = cnt / total
                entropy -= p * math.log2(p)
        summaries.append(
            SubjectHealthSummary(
                split=split,
                subject=subject,
                total_items=total,
                flagged_items=len(flagged_uids_by_key[key]),
                critical_or_high_items=len(high_uids_by_key[key]),
                answer_counts={k: counts.get(k, 0) for k in OPTION_KEYS},
                max_answer_share=max_share,
                answer_entropy_bits=entropy,
            )
        )
    return summaries
