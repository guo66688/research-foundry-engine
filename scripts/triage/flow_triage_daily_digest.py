from __future__ import annotations

import argparse
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.shared.flow_common import ensure_dir, load_yaml, parse_timestamp, read_json  # noqa: E402

LOGGER = logging.getLogger("flow_triage_daily_digest")

TOPIC_RULES = [
    (["chain-of-agents", "multi-agent", "agentic", "agents", "agent system"], "多智能体 / Agent 系统"),
    (["evaluation", "benchmark", "benchmarking", "benchresolve", "nl2bench", "eval"], "评测与 Benchmark"),
    (["retrieval-augmented generation", "rag", "knowledge retrieval", "retrieval"], "检索增强 / 知识检索"),
    (["long-context", "long context", "chunk ordering", "chunk", "bounded shared memory"], "长上下文推理"),
    (["fine-tuning", "continual", "replay", "catastrophic forgetting"], "持续学习 / 微调"),
    (["safety", "hallucination", "preference", "jailbreak", "risk"], "安全 / 风险 / 可靠性"),
    (["inference", "serving", "latency", "throughput", "scheduler"], "推理 / 系统优化"),
    (["multimodal", "vision-language", "medical"], "多模态应用"),
    (["reasoning"], "推理方法"),
]

DOMAIN_RULES = [
    (["medical", "clinical", "diagnostic", "disease"], "医疗场景"),
    (["physics", "cern", "scientific collaborations"], "科研知识库 / 物理协作"),
    (["spoken", "speech", "audio"], "语音场景"),
    (["video", "egocentric"], "视频场景"),
    (["political", "persuasion"], "政治风险场景"),
]


def note_date(raw_value: str) -> str:
    parsed = parse_timestamp(raw_value)
    if parsed is None:
        return datetime.now().date().isoformat()
    return parsed.astimezone().date().isoformat()


def default_output_path(workflow: Dict[str, Any], triage_payload: Dict[str, Any]) -> Path:
    workspace = workflow.get("workspace", {})
    notes_root = Path(workspace.get("notes_root", ""))
    inbox_dir = Path(workspace.get("inbox_dir", "research/inbox"))
    digest_date = note_date(str(triage_payload.get("generated_at", "")))
    return notes_root / inbox_dir / "daily-recommendations" / digest_date[:4] / f"{digest_date}-{triage_payload['profile_id']}.md"


def yaml_quote(text: str) -> str:
    return text.replace('"', "'")


def join_values(values: Iterable[Any], separator: str = "、", fallback: str = "未明确") -> str:
    cleaned = [str(value) for value in values if value]
    return separator.join(cleaned) if cleaned else fallback


def normalize_text(item: Dict[str, Any]) -> str:
    title = str(item.get("title", "")).lower()
    abstract = str(item.get("abstract", "")).lower()
    return f"{title}\n{abstract}"


def keyword_in_text(text: str, needle: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def has_any(text: str, needles: Iterable[str]) -> bool:
    return any(keyword_in_text(text, needle) for needle in needles)


def detect_topics(item: Dict[str, Any]) -> List[str]:
    text = normalize_text(item)
    scored_topics: List[tuple[int, int, str]] = []
    for index, (needles, label) in enumerate(TOPIC_RULES):
        score = sum(1 for needle in needles if keyword_in_text(text, needle))
        if score > 0:
            scored_topics.append((score, -index, label))
    scored_topics.sort(reverse=True)
    topics = [label for _score, _index, label in scored_topics]
    return topics or ["通用机器学习 / AI 方法"]


def detect_domain(item: Dict[str, Any]) -> str:
    text = normalize_text(item)
    for needles, label in DOMAIN_RULES:
        if has_any(text, needles):
            return label
    return ""


def infer_contribution(item: Dict[str, Any]) -> str:
    text = normalize_text(item)
    if has_any(text, ["benchmark", "benchmarking", "evaluation", "eval"]) and has_any(text, ["framework", "platform", "system"]):
        return "提出一个面向该方向的评测 / 基准框架"
    if has_any(text, ["retrieval-augmented generation", "rag", "knowledge retrieval", "retrieval"]):
        return "构建一个面向专门知识库的检索增强系统"
    if has_any(text, ["long-context", "long context", "chunk ordering", "ordering"]):
        return "研究长上下文推理里的信息组织与排序策略"
    if has_any(text, ["fine-tuning", "continual", "replay", "catastrophic forgetting"]):
        return "提出持续微调时缓解遗忘的训练 / 回放策略"
    if has_any(text, ["framework", "platform", "system", "toolkit"]):
        return "提出一个较完整的系统或框架"
    if has_any(text, ["analysis", "study", "we investigate"]):
        return "对一个关键问题做系统分析"
    return "围绕该方向提出新的方法或实践方案"


def infer_validation_signal(item: Dict[str, Any]) -> str:
    text = normalize_text(item)
    signals: List[str] = []
    if has_any(text, ["benchmark", "evaluation", "experiments", "extensive experiments"]):
        signals.append("带有实验或基准验证")
    if has_any(text, ["ablation", "trade-off", "analysis"]):
        signals.append("包含一定分析或消融")
    return "；".join(signals)


def paper_overview(item: Dict[str, Any]) -> str:
    topics = detect_topics(item)
    contribution = infer_contribution(item)
    domain = detect_domain(item)
    validation = infer_validation_signal(item)

    parts = [f"这篇主要属于{join_values(topics[:2])}方向", contribution]
    if domain:
        parts.append(f"应用场景偏{domain}")
    if validation:
        parts.append(validation)
    return "，".join(parts) + "。"


def tier_label(tier: str) -> str:
    mapping = {
        "priority": "优先读",
        "watch": "跟踪看",
        "discard": "不进入 shortlist",
    }
    return mapping.get(tier, tier or "未标注")


def score_band(value: float, *, high: float, medium: float) -> str:
    if value >= high:
        return "高"
    if value >= medium:
        return "中"
    return "低"


def human_signal_summary(item: Dict[str, Any]) -> str:
    components = item.get("score_breakdown") or item.get("scores", {}).get("components", {})
    if not isinstance(components, dict) or not components:
        return "暂无评分拆解"

    topical_fit = float(components.get("topical_fit", 0.0) or 0.0)
    freshness = float(components.get("freshness", 0.0) or 0.0)
    impact = float(components.get("impact", 0.0) or 0.0)
    method_signal = float(components.get("method_signal", 0.0) or 0.0)

    impact_text = "较早期，引用信号尚弱"
    if impact >= 0.5:
        impact_text = "已有较强影响力"
    elif impact >= 0.2:
        impact_text = "已有一定影响力"

    freshness_text = "很新"
    if freshness < 0.7:
        freshness_text = "较新"
    if freshness < 0.4:
        freshness_text = "时效性一般"

    return (
        f"主题契合度{score_band(topical_fit, high=0.35, medium=0.15)}，"
        f"新近性{freshness_text}，"
        f"方法信号{score_band(method_signal, high=0.75, medium=0.4)}，"
        f"{impact_text}"
    )


def decision_reason_text(item: Dict[str, Any]) -> str:
    raw_reasons = list(item.get("decision_reasons") or [])
    mapping = {
        "rank_within_shortlist": "综合得分进入本轮 shortlist",
        "duplicate_record": "与组内更高分候选重复",
        "lower_than_group_best": "同组中不是最佳条目",
        "below_shortlist_threshold": "综合得分未进入 shortlist 阈值",
    }
    translated = [mapping.get(reason, reason) for reason in raw_reasons]
    return join_values(translated, separator="；", fallback="未提供")


def recommendation_reason(item: Dict[str, Any]) -> str:
    components = item.get("score_breakdown") or item.get("scores", {}).get("components", {})
    topical_fit = float(components.get("topical_fit", 0.0) or 0.0)
    freshness = float(components.get("freshness", 0.0) or 0.0)
    method_signal = float(components.get("method_signal", 0.0) or 0.0)
    profile_hits = list(item.get("profile_hits") or [])
    reasons: List[str] = []

    if profile_hits:
        reasons.append(f"与画像直接相关，命中关键词 {join_values(profile_hits, separator='、')}")
    elif topical_fit >= 0.15:
        reasons.append("和研究画像有一定主题相关性")

    if freshness >= 0.7:
        reasons.append("发布时间很新，适合做当日扫描")
    if method_signal >= 0.75:
        reasons.append("摘要里有较强的方法 / 基准 / 消融信号")
    elif method_signal >= 0.4:
        reasons.append("方法设计和实验设置比较明确")

    if item.get("tier") == "priority":
        reasons.append("综合排位靠前，建议优先阅读")
    else:
        reasons.append("进入 shortlist，但更适合放入跟踪队列")

    return "；".join(reasons) + "。"


def source_overview(manifest_payload: Dict[str, Any]) -> List[str]:
    source_status = manifest_payload.get("source_status", {}) or {}
    warnings = manifest_payload.get("warnings", []) or []
    if not source_status and not warnings:
        return []

    lines = ["## Source 状态", ""]
    for source_name, payload in source_status.items():
        lines.append(
            f"- `{source_name}`：状态 `{payload.get('status', 'unknown')}`，返回候选 `{payload.get('candidate_count', 0)}` 篇"
        )
    if warnings:
        lines.extend(["", "### Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    return lines


def digest_highlights(items: List[Dict[str, Any]]) -> List[str]:
    topic_counter: Counter[str] = Counter()
    priority_count = 0
    for item in items:
        detected = detect_topics(item)
        if detected:
            topic_counter[detected[0]] += 1
        if item.get("tier") == "priority":
            priority_count += 1

    main_topics = [topic for topic, _count in topic_counter.most_common(3)]
    lines = [
        "## 今天值得看什么",
        "",
        f"- 主线方向：`{join_values(main_topics, separator=' / ', fallback='通用机器学习 / AI 方法')}`",
        f"- 阅读顺序：先看 `priority` 档 `{priority_count}` 篇，再按兴趣补 `watch` 档。",
        "- 判断原则：这里只基于 triage 阶段的标题、摘要和打分信号做快读，不代表 dossier 级结论。",
        "",
    ]
    return lines


def build_top_section(items: List[Dict[str, Any]], top_k: int) -> List[str]:
    lines = [f"## 最值得先看的 {top_k} 篇", ""]
    for index, item in enumerate(items[:top_k], start=1):
        source_url = item.get("source_url", "") or ""
        pdf_url = item.get("pdf_url", "") or ""

        lines.append(f"### {index}. {item.get('title', 'Untitled Paper')}")
        lines.append(f"- 研究方向：`{join_values(detect_topics(item)[:2])}`")
        lines.append(f"- 这篇在做什么：{paper_overview(item)}")
        lines.append(f"- 为什么推荐：{recommendation_reason(item)}")
        lines.append(f"- 推荐判断：{decision_reason_text(item)}")
        lines.append(f"- 信号概览：{human_signal_summary(item)}")
        lines.append(
            f"- 原始信息：paper_id=`{item.get('paper_id', 'n/a')}`，score=`{item.get('scores', {}).get('total', 'n/a')}`，建议=`{tier_label(str(item.get('tier', '')))}'"
        )
        if source_url and pdf_url:
            lines.append(f"- 链接：[Abstract]({source_url}) | [PDF]({pdf_url})")
        elif source_url:
            lines.append(f"- 链接：[Abstract]({source_url})")
        elif pdf_url:
            lines.append(f"- 链接：[PDF]({pdf_url})")
        lines.append("")
    return lines


def build_shortlist_table(items: List[Dict[str, Any]]) -> List[str]:
    lines = [
        "## 完整 Shortlist",
        "",
        "| 排名 | paper_id | 方向 | 建议 | score | title |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for index, item in enumerate(items, start=1):
        title = str(item.get("title", "Untitled Paper")).replace("|", "\\|")
        topic_text = join_values(detect_topics(item)[:1])
        lines.append(
            f"| {index} | `{item.get('paper_id', 'n/a')}` | {topic_text} | {tier_label(str(item.get('tier', '')))} | "
            f"{item.get('scores', {}).get('total', 'n/a')} | {title} |"
        )
    lines.append("")
    return lines


def build_runtime_section(candidate_path: Path, triage_path: Path, queue_path: Path) -> List[str]:
    return [
        "## 运行产物",
        "",
        f"- candidate_pool: `{candidate_path}`",
        f"- triage_result: `{triage_path}`",
        f"- reading_queue: `{queue_path}`",
        "",
    ]


def build_digest_markdown(
    triage_payload: Dict[str, Any],
    manifest_payload: Dict[str, Any],
    candidate_path: Path,
    triage_path: Path,
    queue_path: Path,
    top_k: int,
) -> str:
    selected = list(triage_payload.get("selected", []))
    if not selected:
        raise ValueError("triage_result has no selected papers")

    generated_at = str(triage_payload.get("generated_at", ""))
    digest_date = note_date(generated_at)
    stats = triage_payload.get("stats", {}) or {}
    sources = sorted({str(item.get("source", "unknown")) for item in selected})

    lines = [
        "---",
        'type: "daily-paper-recommendation"',
        f'date: "{digest_date}"',
        f'profile_id: "{yaml_quote(str(triage_payload.get("profile_id", "unknown")))}"',
        f'run_id: "{yaml_quote(str(triage_payload.get("run_id", "unknown")))}"',
        f'candidate_count: {int(stats.get("input_count", 0))}',
        f'shortlist_count: {int(stats.get("selected_count", 0))}',
        "tags:",
        "  - research-foundry",
        "  - daily-recommendation",
        f'  - {triage_payload.get("profile_id", "unknown")}',
        "---",
        "",
        f"# 每日论文推荐 | {digest_date}",
        "",
        "> 本文档只包含 source-intake 与 candidate-triage 结果，不包含 dossier、synthesis、registry。",
        "",
        "## 今日概览",
        "",
        f"- 研究画像：`{triage_payload.get('profile_id', 'unknown')}`",
        f"- 运行批次：`{triage_payload.get('run_id', 'unknown')}`",
        f"- 生成时间：`{generated_at or 'n/a'}`",
        f"- 候选总数：`{stats.get('input_count', 0)}`",
        f"- 去重后候选：`{stats.get('deduped_count', 0)}`",
        f"- shortlist：`{stats.get('selected_count', 0)}`",
        f"- 数据源：`{join_values(sources, separator=' / ', fallback='unknown')}`",
        "",
    ]
    lines.extend(digest_highlights(selected))
    lines.extend(source_overview(manifest_payload))
    lines.extend(build_top_section(selected, top_k))
    lines.extend(build_shortlist_table(selected))
    lines.extend(build_runtime_section(candidate_path, triage_path, queue_path))
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a readable Chinese Obsidian digest from triage results.")
    parser.add_argument("--config", required=True, help="Path to workflow config")
    parser.add_argument("--triage-file", required=True, help="Path to triage_result.json")
    parser.add_argument("--output", default="", help="Optional output markdown path")
    parser.add_argument("--top-k", type=int, default=5, help="How many top papers to expand")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    workflow = load_yaml(Path(args.config))
    triage_path = Path(args.triage_file).resolve()
    triage_payload = read_json(triage_path, default={}) or {}
    if not triage_payload:
        raise SystemExit("triage_result is missing or empty")
    selected = list(triage_payload.get("selected", []))
    if not selected:
        raise SystemExit("triage_result has no selected papers")

    run_dir = triage_path.parent
    candidate_path = run_dir / "candidate_pool.jsonl"
    manifest_path = run_dir / "run_manifest.json"
    queue_path = Path(workflow.get("runtime", {}).get("artifact_dir", "runtime/artifacts")).resolve() / (
        f"reading_queue-{triage_payload.get('run_id', 'unknown')}.md"
    )
    manifest_payload = read_json(manifest_path, default={}) or {}

    output_path = Path(args.output) if args.output else default_output_path(workflow, triage_payload)
    ensure_dir(output_path.parent)
    output_path.write_text(
        build_digest_markdown(
            triage_payload,
            manifest_payload,
            candidate_path,
            triage_path,
            queue_path,
            max(args.top_k, 1),
        ),
        encoding="utf-8",
    )

    LOGGER.info("daily_digest=%s", output_path)
    LOGGER.info("expanded_top_k=%d", max(args.top_k, 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
