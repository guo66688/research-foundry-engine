from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests
import yaml


PAPER_ID_PATTERN = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")

PHASE_SCRIPT_RELATIVE = {
    "source-intake": Path("scripts/intake/flow_intake_fetch.py"),
    "candidate-triage": Path("scripts/triage/flow_triage_rank.py"),
    "evidence-dossier": Path("scripts/dossier/flow_dossier_build.py"),
    "knowledge-synthesis": Path("scripts/synthesis/flow_synthesis_link.py"),
    "run-registry": Path("scripts/registry/flow_registry_update.py"),
    "figure-extraction": Path("scripts/dossier/flow_dossier_figures.py"),
}

STANDALONE_SCRIPT_RELATIVE = {
    "source-intake": Path("source-intake/scripts/flow_intake_fetch.py"),
    "candidate-triage": Path("candidate-triage/scripts/flow_triage_rank.py"),
    "evidence-dossier": Path("evidence-dossier/scripts/flow_dossier_build.py"),
    "knowledge-synthesis": Path("knowledge-synthesis/scripts/flow_synthesis_link.py"),
    "run-registry": Path("run-registry/scripts/flow_registry_update.py"),
    "figure-extraction": Path("evidence-dossier/scripts/rf_standalone/flow_dossier_figures.py"),
}

TOPIC_RULES = [
    (["agentic", "agent", "multi-agent", "chain-of-agents"], "Agent 系统"),
    (["benchmark", "evaluation", "eval"], "评测与 Benchmark"),
    (["rag", "retrieval", "knowledge retrieval"], "检索增强"),
    (["long-context", "long context"], "长上下文推理"),
    (["fine-tuning", "continual", "replay"], "持续学习与微调"),
    (["multimodal", "vision-language", "medical"], "多模态应用"),
    (["reasoning"], "推理方法"),
]

STOP_WORDS = {
    "with",
    "from",
    "that",
    "this",
    "into",
    "paper",
    "results",
    "using",
    "their",
    "there",
    "these",
    "which",
    "have",
    "been",
    "model",
    "models",
    "based",
    "large",
    "language",
}


@dataclass
class Backend:
    mode: str
    repo_root: Optional[Path]
    skills_root: Optional[Path]
    support_root: Path

    def phase_script(self, phase_name: str) -> Path:
        if self.mode == "external":
            if self.repo_root is None:
                raise RuntimeError("external backend missing repo root")
            path = self.repo_root / PHASE_SCRIPT_RELATIVE[phase_name]
        else:
            if self.skills_root is None:
                raise RuntimeError("standalone backend missing skills root")
            path = self.skills_root / STANDALONE_SCRIPT_RELATIVE[phase_name]
        if not path.exists():
            raise FileNotFoundError(f"missing phase script for {phase_name}: {path}")
        return path

    def phase_python(self, phase_name: str) -> str:
        if self.mode == "external":
            return sys.executable
        if self.skills_root is None:
            return sys.executable
        if phase_name == "figure-extraction":
            runtime_file = self.skills_root / "evidence-dossier" / ".runtime" / "python.txt"
        else:
            runtime_file = self.skills_root / phase_name / ".runtime" / "python.txt"
        if runtime_file.exists():
            recorded = runtime_file.read_text(encoding="utf-8").lstrip("\ufeff").strip()
            if recorded:
                return recorded
        return sys.executable

    def template_path(self, template_name: str) -> Path:
        if self.mode == "external":
            if self.repo_root is None:
                raise RuntimeError("external backend missing repo root")
            path = self.repo_root / "templates" / template_name
        else:
            path = self.support_root.parent / "templates" / template_name
        if not path.exists():
            raise FileNotFoundError(f"missing template: {path}")
        return path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def write_json_file(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_yaml(path: Path) -> Dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"expected mapping in {path}")
    return payload


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_paper_id(value: str) -> str:
    match = PAPER_ID_PATTERN.search(value)
    if match:
        return match.group(1)
    return slugify(value, max_length=48)


def slugify(text: str, max_length: int = 80) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    compact = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if not compact:
        compact = "item"
    return compact[:max_length].rstrip("-")


def parse_frontmatter(text: str) -> Dict[str, Any]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    payload = yaml.safe_load(match.group(1)) or {}
    return payload if isinstance(payload, dict) else {}


def normalize_text(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", ascii_text).strip()


def important_terms(text: str) -> List[str]:
    candidates = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text.lower())
    unique: List[str] = []
    seen = set()
    for item in candidates:
        if item in STOP_WORDS or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def detect_topics(record: Dict[str, Any]) -> List[str]:
    text = normalize_text(f"{record.get('title', '')}\n{record.get('abstract', '')}")
    hits: List[str] = []
    for needles, label in TOPIC_RULES:
        if any(needle in text for needle in needles):
            hits.append(label)
    return hits or ["通用 AI 研究"]


def profile_reasons(record: Dict[str, Any]) -> List[str]:
    hits = list(record.get("profile_hits") or [])
    if hits:
        return [f"命中研究画像关键词：{', '.join(hits)}"]
    scores = record.get("score_breakdown") or record.get("scores", {}).get("components", {})
    topical_fit = float(scores.get("topical_fit", 0.0) or 0.0)
    if topical_fit >= 0.2:
        return ["与当前研究画像有明确主题重合"]
    if topical_fit > 0:
        return ["与当前研究画像存在一定主题关联"]
    return ["与当前研究画像关联较弱，但进入了当前筛选结果"]


def contribution_summary(record: Dict[str, Any]) -> str:
    text = normalize_text(f"{record.get('title', '')}\n{record.get('abstract', '')}")
    if "benchmark" in text or "evaluation" in text:
        return "核心贡献偏向评测框架、基准设计或系统化验证。"
    if "framework" in text or "system" in text or "platform" in text:
        return "核心贡献偏向提出一个完整系统或方法框架。"
    if "retrieval" in text or "rag" in text:
        return "核心贡献偏向检索增强或知识获取链路。"
    if "fine-tuning" in text or "continual" in text or "replay" in text:
        return "核心贡献偏向训练策略、持续学习或微调方法。"
    if "reasoning" in text:
        return "核心贡献偏向推理链路、上下文组织或推理性能提升。"
    return "核心贡献偏向提出新的方法或应用方案。"


def evidence_summary(record: Dict[str, Any]) -> str:
    abstract = normalize_text(str(record.get("abstract", "")))
    signals: List[str] = []
    if "benchmark" in abstract or "experiments" in abstract:
        signals.append("包含实验或基准验证")
    if "ablation" in abstract:
        signals.append("提到消融分析")
    if "outperform" in abstract or "improves" in abstract or "improvement" in abstract:
        signals.append("摘要中声明了性能提升")
    if not signals:
        signals.append("摘要中的实验信号较弱，仍需通读正文确认")
    return "；".join(signals) + "。"


def split_sentences(text: str) -> List[str]:
    compact = " ".join(str(text).split())
    if not compact:
        return []
    parts = re.split(r"(?<=[\.\!\?])\s+", compact)
    return [part.strip() for part in parts if part.strip()]


def first_sentence_with_keywords(text: str, keywords: Sequence[str]) -> str:
    for sentence in split_sentences(text):
        lowered = normalize_text(sentence)
        if any(keyword in lowered for keyword in keywords):
            return sentence.strip()
    return ""


def artifact_label(record: Dict[str, Any]) -> str:
    title_text = normalize_text(str(record.get("title", "")))
    abstract_text = normalize_text(str(record.get("abstract", "")))
    text = f"{title_text}\n{abstract_text}"
    if "fine-tuning" in title_text or "continual" in title_text or "replay" in title_text or "alignment" in title_text:
        return "训练/微调型工作"
    if "retrieval" in title_text or "rag" in title_text or "search" in title_text:
        return "检索增强型工作"
    if "ordering" in title_text or "reasoning" in title_text or "planner" in title_text or "planning" in title_text:
        return "推理/规划型工作"
    if "framework" in title_text or "platform" in title_text or "system" in title_text or "assistant" in title_text:
        return "系统/框架型工作"
    if "dataset" in title_text or "corpus" in title_text or "benchmark" in title_text:
        return "数据集型工作"
    if "benchmark" in text or "evaluation" in text or "evaluator" in text:
        return "评测/基准型工作"
    if "dataset" in text or "corpus" in text:
        return "数据集型工作"
    if "framework" in text or "platform" in text or "system" in text or "assistant" in text:
        return "系统/框架型工作"
    if "retrieval" in text or "rag" in text or "search" in text:
        return "检索增强型工作"
    if "fine-tuning" in text or "tuning" in text or "continual" in text or "replay" in text or "alignment" in text:
        return "训练/微调型工作"
    if "reasoning" in text or "planner" in text or "planning" in text:
        return "推理/规划型工作"
    return "方法型工作"


def domain_label(record: Dict[str, Any]) -> str:
    text = normalize_text(f"{record.get('title', '')}\n{record.get('abstract', '')}")
    if "medical" in text or "clinical" in text:
        return "医疗场景"
    if "physics" in text:
        return "科研知识检索场景"
    if "political" in text:
        return "政治风险评估场景"
    if "cardiac" in text:
        return "心脏影像场景"
    if "egocentric" in text or "video" in text:
        return "视频理解场景"
    if "spoken" in text or "speech" in text:
        return "语音交互场景"
    if "multimodal" in text or "vision-language" in text:
        return "多模态场景"
    if "agent" in text:
        return "Agent 系统场景"
    if "large language model" in text or "llm" in text:
        return "大模型系统场景"
    return "通用 AI 场景"


def problem_summary(record: Dict[str, Any], text_context: Optional[Dict[str, Any]] = None) -> str:
    sections = (text_context or {}).get("sections", {}) if text_context else {}
    intro_text = "\n".join(
        filter(
            None,
            [
                sections.get("introduction", ""),
                sections.get("background", ""),
                sections.get("motivation", ""),
            ],
        )
    )
    matched_from_fulltext = sentence_with_keywords(
        intro_text,
        ["challenge", "problem", "limited", "lack", "hinder", "suffer", "fragility", "gap"],
    )
    if matched_from_fulltext:
        return f"从正文前半部分看，作者首先强调的瓶颈是：{abstract_snapshot(matched_from_fulltext, length=180)}"
    abstract = str(record.get("abstract", ""))
    text = normalize_text(abstract)
    if "lack of standardized" in text or "lack of standard" in text:
        return "作者认为当前方向的主要问题是缺少统一标准，导致不同方法难以直接比较。"
    if "fragment" in text or "heterogeneous" in text or "non-uniform" in text:
        return "作者试图解决现有方案碎片化、数据或流程不统一的问题。"
    if "cost-performance trade-offs" in text or "trade-off" in text:
        return "论文关心的不只是性能，还包括性能与成本之间的实际权衡。"
    if "long-context" in text or "long context" in text:
        return "论文聚焦长上下文条件下的信息组织与推理稳定性问题。"
    if "retrieval" in text or "knowledge retrieval" in text:
        return "论文试图解决知识获取和外部信息接入效率不足的问题。"
    if "continual" in text or "catastrophic forgetting" in text or "replay" in text:
        return "论文关注持续学习中的遗忘、数据选择或训练稳定性问题。"
    matched = first_sentence_with_keywords(
        abstract,
        ["challenge", "problem", "limited", "lack", "hinder", "suffer", "fragility", "gap"],
    )
    if matched:
        return f"从摘要看，作者首先指出了一个现实瓶颈：{abstract_snapshot(matched, length=140)}"
    first = split_sentences(abstract)
    if first:
        return f"从摘要开头看，论文首先在界定问题背景：{abstract_snapshot(first[0], length=140)}"
    return "摘要没有明显展开问题背景，建议通读引言确认作者想解决的核心瓶颈。"


def feature_bullets(record: Dict[str, Any]) -> List[str]:
    text = normalize_text(f"{record.get('title', '')}\n{record.get('abstract', '')}")
    features: List[str] = []
    if "protocol" in text or "communication" in text:
        features.append("定义了更统一的交互或通信方式，方便把不同模块接到同一流程里。")
    if "framework" in text or "platform" in text or "system" in text:
        features.append("提供了一个可复用的系统框架或实验平台，而不是只给单点技巧。")
    if "benchmark" in text or "benchmarking" in text or "dataset" in text:
        features.append("把任务、数据或评价标准整理成可复用的基准，便于横向比较。")
    if "evaluator" in text or "evaluation" in text:
        features.append("设计了自动化评估或验证流程，重点不只是提出方法，也包括如何可靠地测。")
    if "retrieval" in text or "rag" in text or "knowledge retrieval" in text:
        features.append("核心路径包含检索或知识接入，强调把外部信息有效接入系统。")
    if "memory" in text:
        features.append("显式处理记忆或历史信息，重点改善跨轮次或跨阶段的信息保留。")
    if "ordering" in text or "planner" in text or "planning" in text:
        features.append("重点优化步骤编排或推理顺序，属于流程组织能力的改进。")
    if "fine-tuning" in text or "continual" in text or "replay" in text or "alignment" in text:
        features.append("方法上更偏训练策略或调优机制，而不是单纯换模型。")
    if "ablation" in text:
        features.append("摘要明确提到消融，说明作者有在拆解关键机制是否真的有效。")
    return features[:3]


def method_summary(record: Dict[str, Any], text_context: Optional[Dict[str, Any]] = None) -> str:
    sections = (text_context or {}).get("sections", {}) if text_context else {}
    method_text = "\n".join(
        filter(
            None,
            [
                sections.get("method", ""),
                sections.get("methods", ""),
                sections.get("approach", ""),
                sections.get("framework", ""),
                sections.get("system", ""),
                sections.get("architecture", ""),
            ],
        )
    )
    matched_from_fulltext = sentence_with_keywords(
        method_text,
        ["we propose", "we present", "we introduce", "our method", "our framework", "our system"],
    )
    if matched_from_fulltext:
        return f"正文里的方法主线可以概括为：{abstract_snapshot(matched_from_fulltext, length=180)}"
    features = feature_bullets(record)
    if features:
        return features[0]
    abstract = str(record.get("abstract", ""))
    matched = first_sentence_with_keywords(
        abstract,
        ["we present", "we propose", "we introduce", "we develop", "we provide", "this paper"],
    )
    if matched:
        return f"摘要中的方法主句是：{abstract_snapshot(matched, length=160)}"
    return contribution_summary(record)


def results_summary(record: Dict[str, Any], text_context: Optional[Dict[str, Any]] = None) -> str:
    sections = (text_context or {}).get("sections", {}) if text_context else {}
    result_text = "\n".join(
        filter(
            None,
            [
                sections.get("experiment", ""),
                sections.get("experiments", ""),
                sections.get("evaluation", ""),
                sections.get("results", ""),
                sections.get("analysis", ""),
                sections.get("conclusion", ""),
            ],
        )
    )
    matched_from_fulltext = sentence_with_keywords(
        result_text,
        ["outperform", "improve", "better", "gain", "reveal", "show", "trade-off"],
    )
    if matched_from_fulltext:
        return f"从正文实验和结论部分看，作者最想强调的是：{abstract_snapshot(matched_from_fulltext, length=200)}"
    abstract = str(record.get("abstract", ""))
    text = normalize_text(abstract)
    parts: List[str] = []
    if "benchmark" in text or "experiments" in text or "evaluation" in text:
        parts.append("论文给出了实验或基准验证，不只是概念性提案。")
    if "ablation" in text:
        parts.append("作者做了消融或机制拆解，便于判断哪些设计真的起作用。")
    if "outperform" in text or "improves" in text or "improvement" in text or "better than" in text:
        parts.append("摘要声称相比基线有性能提升，但具体幅度仍需回到正文核对。")
    if "trade-off" in text or "cost" in text:
        parts.append("结果不仅看效果，也在讨论成本或效率权衡。")
    if "reveal" in text or "shows that" in text or "our evaluation reveals" in text:
        parts.append("除了报分，论文还试图总结某类系统在什么条件下会失效或表现不稳。")
    if parts:
        return " ".join(parts)
    return "摘要里的结果信号不算弱，但更像方向性结论，是否稳健还要结合实验部分细看。"


def audience_summary(record: Dict[str, Any]) -> str:
    artifact = artifact_label(record)
    if artifact == "评测/基准型工作":
        return "适合想搭评测协议、比较不同方案，或判断这个方向到底该怎么测的人先看。"
    if artifact == "数据集型工作":
        return "适合想找任务设置、数据资源或 benchmark 入口的人先看。"
    if artifact == "系统/框架型工作":
        return "适合想看系统怎么搭、模块怎么拼、工程边界怎么划分的人先看。"
    if artifact == "检索增强型工作":
        return "适合关心知识接入、检索链路和问答系统落地方式的人先看。"
    if artifact == "训练/微调型工作":
        return "适合关心训练策略、数据选择、稳定性和持续学习问题的人先看。"
    if artifact == "推理/规划型工作":
        return "适合关心推理链路、上下文组织和多步决策的人先看。"
    return "适合作为当前方向的近期样本来快速补齐认知。"


def recommendation_summary(record: Dict[str, Any]) -> str:
    reasons = profile_reasons(record)
    method_summary_text = method_signal_summary(record).rstrip("。")
    domain = domain_label(record)
    artifact = artifact_label(record)
    core = reasons[0] if reasons else "与当前画像存在一定关系"
    return f"{core}；论文本身属于{domain}中的{artifact}，而且{method_summary_text}。"


def paper_glance(record: Dict[str, Any]) -> str:
    domain = domain_label(record)
    artifact = artifact_label(record)
    topics = detect_topics(record)
    topic_text = " / ".join(topics[:2]) if topics else "当前研究方向"
    if artifact == "评测/基准型工作":
        focus = "重点在怎么把任务、指标和比较方式整理成可复用的评测方案"
    elif artifact == "数据集型工作":
        focus = "重点在任务设置、数据覆盖范围以及后续能否成为公共入口"
    elif artifact == "系统/框架型工作":
        focus = "重点在系统组织方式、模块协作和整体工作流设计"
    elif artifact == "检索增强型工作":
        focus = "重点在如何把检索或外部知识真正接进系统"
    elif artifact == "训练/微调型工作":
        focus = "重点在训练策略、调优机制和稳定性改进"
    elif artifact == "推理/规划型工作":
        focus = "重点在推理顺序、上下文组织和决策流程"
    else:
        focus = "重点在提出新的方法思路并验证其有效性"
    return f"面向{domain}，这篇更像一项{artifact}；主题靠近 {topic_text}，{focus}。"


def reading_focus_summary(record: Dict[str, Any]) -> str:
    artifact = artifact_label(record)
    if artifact == "评测/基准型工作":
        return "建议先看 benchmark 覆盖范围、评测协议和 baseline 是否公平。"
    if artifact == "数据集型工作":
        return "建议先看任务定义、数据规模和数据分布是否真的补上了现有空缺。"
    if artifact == "系统/框架型工作":
        return "建议先看系统结构图、模块边界，以及作者到底统一了哪些原本分散的流程。"
    if artifact == "检索增强型工作":
        return "建议先看检索来源、召回方式，以及检索和生成是如何耦合的。"
    if artifact == "训练/微调型工作":
        return "建议先看训练目标、数据选择策略和与基线相比提升是否稳定。"
    if artifact == "推理/规划型工作":
        return "建议先看推理流程、排序/规划机制和失败案例。"
    return "建议先看方法主线，再回到实验确认作者声称的提升是否成立。"


def method_signal_summary(record: Dict[str, Any]) -> str:
    scores = record.get("score_breakdown") or record.get("scores", {}).get("components", {})
    freshness = float(scores.get("freshness", 0.0) or 0.0)
    method_signal = float(scores.get("method_signal", 0.0) or 0.0)
    impact = float(scores.get("impact", 0.0) or 0.0)
    parts: List[str] = []
    if freshness >= 0.7:
        parts.append("发布时间较新")
    if method_signal >= 0.75:
        parts.append("摘要中方法和实验信号较强")
    elif method_signal >= 0.4:
        parts.append("方法路径相对明确")
    if impact > 0.2:
        parts.append("已有一定引用或影响力信号")
    elif impact == 0:
        parts.append("仍处于早期阶段，影响力信号有限")
    return "，".join(parts) + "。"


def parse_logged_value(output: str, key: str) -> str:
    pattern = re.compile(rf"{re.escape(key)}=(.+)")
    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            return match.group(1).strip()
    return ""


def run_script(python_exe: str, script_path: Path, args: Sequence[str]) -> str:
    completed = subprocess.run(
        [python_exe, str(script_path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {script_path}\n{output.strip()}")
    return output


def detect_repo_root(current_file: Path) -> Optional[Path]:
    candidate = current_file.parents[2]
    if (candidate / "scripts" / "intake" / "flow_intake_fetch.py").exists():
        return candidate
    return None


def detect_skills_root(current_file: Path) -> Optional[Path]:
    for parent in current_file.parents:
        if parent.name == "skills" and (parent / "source-intake").exists():
            return parent
    default_root = Path.home() / ".codex" / "skills"
    if (default_root / "source-intake").exists():
        return default_root
    return None


def resolve_backend(mode: str = "auto") -> Backend:
    current_file = Path(__file__).resolve()
    repo_root = detect_repo_root(current_file)
    skills_root = detect_skills_root(current_file)
    if mode == "external":
        if repo_root is None:
            raise RuntimeError("external backend requested but repo scripts are unavailable")
        return Backend(mode="external", repo_root=repo_root, skills_root=skills_root, support_root=current_file.parent)
    if mode == "standalone":
        if skills_root is None:
            raise RuntimeError("standalone backend requested but installed skills are unavailable")
        return Backend(mode="standalone", repo_root=None, skills_root=skills_root, support_root=current_file.parent)
    if repo_root is not None:
        return Backend(mode="external", repo_root=repo_root, skills_root=skills_root, support_root=current_file.parent)
    if skills_root is not None:
        return Backend(mode="standalone", repo_root=None, skills_root=skills_root, support_root=current_file.parent)
    raise RuntimeError("no execution backend available")


def runtime_run_root(workflow: Dict[str, Any]) -> Path:
    return Path(workflow.get("runtime", {}).get("run_dir", "runtime/runs"))


def runtime_artifact_root(workflow: Dict[str, Any]) -> Path:
    return Path(workflow.get("runtime", {}).get("artifact_dir", "runtime/artifacts"))


def runtime_cache_root(workflow: Dict[str, Any]) -> Path:
    return Path(workflow.get("runtime", {}).get("cache_dir", "runtime/cache"))


def resolve_notes_root(workflow: Dict[str, Any], override: str = "") -> Path:
    return Path(override) if override else Path(workflow.get("workspace", {}).get("notes_root", "."))


def daily_note_path(notes_root: Path, profile_id: str, date_value: str) -> Path:
    note_date = date_value[:10]
    return notes_root / "research" / "inbox" / "daily-recommendations" / note_date[:4] / f"{note_date}-{profile_id}.md"


def paper_note_path(notes_root: Path, paper_id: str) -> Path:
    return notes_root / "research" / "papers" / f"{paper_id}.md"


def paper_image_dir(notes_root: Path, paper_id: str) -> Path:
    return notes_root / "research" / "papers" / paper_id / "images"


def image_index_path(notes_root: Path, paper_id: str) -> Path:
    return notes_root / "research" / "papers" / f"{paper_id}-figures.md"


def paper_text_artifact_path(workflow: Dict[str, Any], paper_id: str) -> Path:
    return runtime_artifact_root(workflow) / f"paper_text-{paper_id}.txt"


def deepread_context_path(workflow: Dict[str, Any], paper_id: str) -> Path:
    return runtime_artifact_root(workflow) / f"deepread_context-{paper_id}.json"


def daily_context_path(workflow: Dict[str, Any], run_id: str) -> Path:
    return runtime_artifact_root(workflow) / f"daily_context-{run_id}.json"


def list_recent_runs(run_root: Path) -> List[Path]:
    if not run_root.exists():
        return []
    runs = [path for path in run_root.iterdir() if path.is_dir() and path.name.startswith("run-")]
    runs.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return runs


def find_best_title_match(query: str, records: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    normalized_query = normalize_text(query)
    query_terms = set(important_terms(query))
    best: Optional[Dict[str, Any]] = None
    best_score = -1
    for record in records:
        title = str(record.get("title", ""))
        normalized_title = normalize_text(title)
        score = 0
        if normalized_title == normalized_query:
            score += 100
        if normalized_query and normalized_query in normalized_title:
            score += 30
        score += len(query_terms & set(important_terms(title))) * 5
        if score > best_score:
            best_score = score
            best = record
    return best if best_score > 0 else None


def resolve_paper_record(query: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
    run_root = runtime_run_root(workflow)
    normalized_id = canonical_paper_id(query)
    query_is_id = bool(PAPER_ID_PATTERN.search(query))
    for run_dir in list_recent_runs(run_root):
        triage_path = run_dir / "triage_result.json"
        candidate_path = run_dir / "candidate_pool.jsonl"
        if triage_path.exists():
            triage_payload = read_json(triage_path, default={}) or {}
            triage_records = list(triage_payload.get("selected", [])) + list(triage_payload.get("rejected", []))
            if query_is_id:
                for record in triage_records:
                    if canonical_paper_id(str(record.get("paper_id", ""))) == normalized_id:
                        bundle = dict(record)
                        bundle["_triage_file"] = str(triage_path)
                        bundle["_candidate_file"] = str(candidate_path)
                        bundle["_run_id"] = str(triage_payload.get("run_id", run_dir.name))
                        return bundle
            else:
                matched = find_best_title_match(query, triage_records)
                if matched is not None:
                    bundle = dict(matched)
                    bundle["_triage_file"] = str(triage_path)
                    bundle["_candidate_file"] = str(candidate_path)
                    bundle["_run_id"] = str(triage_payload.get("run_id", run_dir.name))
                    return bundle
        if candidate_path.exists():
            candidates = read_jsonl(candidate_path)
            if query_is_id:
                for record in candidates:
                    if canonical_paper_id(str(record.get("paper_id", ""))) == normalized_id:
                        bundle = dict(record)
                        bundle["_candidate_file"] = str(candidate_path)
                        bundle["_run_id"] = run_dir.name
                        return bundle
            else:
                matched = find_best_title_match(query, candidates)
                if matched is not None:
                    bundle = dict(matched)
                    bundle["_candidate_file"] = str(candidate_path)
                    bundle["_run_id"] = run_dir.name
                    return bundle
    raise KeyError(f"paper not found in recent runtime artifacts: {query}")


def copy_figure_items(manifest: Dict[str, Any], destination_dir: Path) -> List[Dict[str, Any]]:
    ensure_dir(destination_dir)
    copied: List[Dict[str, Any]] = []
    for item in list(manifest.get("items", [])):
        source_path = Path(str(item.get("path", "")))
        if not source_path.exists():
            continue
        destination_path = destination_dir / source_path.name
        destination_path.write_bytes(source_path.read_bytes())
        copied.append(
            {
                "name": destination_path.name,
                "path": str(destination_path),
                "source": item.get("source", ""),
                "format": item.get("format", ""),
            }
        )
    return copied


def render_image_index(record: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    paper_id = canonical_paper_id(str(record.get("paper_id", "")))
    title = str(record.get("title", paper_id)).replace('"', "'")
    lines = [
        "---",
        'type: "paper-figures"',
        f'paper_id: "{paper_id}"',
        f'title: "{title}"',
        f'generated_at: "{utc_timestamp()}"',
        "---",
        "",
        f"# 配图索引｜{record.get('title', paper_id)}",
        "",
    ]
    if not items:
        lines.extend(["未提取到可用配图。", ""])
        return "\n".join(lines)
    for index, item in enumerate(items, start=1):
        image_file = Path(str(item["path"])).name
        image_link = f"{paper_id}/images/{image_file}"
        lines.extend(
            [
                f"## 图 {index}",
                "",
                f"- 来源：`{item.get('source', 'unknown')}`",
                f"- 文件：`{image_file}`",
                "",
                f"![[{image_link}]]",
                "",
            ]
        )
    return "\n".join(lines)


def scan_markdown_notes(notes_root: Path) -> List[Dict[str, Any]]:
    notes: List[Dict[str, Any]] = []
    if not notes_root.exists():
        return notes
    candidate_roots = [
        notes_root / "research" / "papers",
        notes_root / "research" / "inbox",
        notes_root / "research" / "links",
    ]
    markdown_paths: List[Path] = []
    for root in candidate_roots:
        if root.exists():
            markdown_paths.extend(root.rglob("*.md"))
    for path in markdown_paths:
        try:
            content = read_text(path)
        except OSError:
            continue
        frontmatter = parse_frontmatter(content)
        tags = frontmatter.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        notes.append(
            {
                "path": str(path),
                "title": str(frontmatter.get("title") or path.stem),
                "authors": frontmatter.get("authors") or [],
                "tags": [str(item) for item in tags],
                "content": content,
                "modified_at": path.stat().st_mtime,
            }
        )
    return notes


def search_notes(notes_root: Path, query_text: str, limit: int = 10, exclude_paths: Optional[Sequence[Path]] = None) -> List[Dict[str, Any]]:
    exclude_set = {str(path.resolve()) for path in exclude_paths or []}
    query_terms = set(important_terms(query_text))
    normalized_query = normalize_text(query_text)
    results: List[Dict[str, Any]] = []
    for note in scan_markdown_notes(notes_root):
        resolved_path = str(Path(note["path"]).resolve())
        if resolved_path in exclude_set:
            continue
        title = str(note["title"])
        body = str(note["content"])
        tags = " ".join(note.get("tags", []))
        authors = " ".join(str(item) for item in note.get("authors", []))
        combined = normalize_text(f"{title}\n{tags}\n{authors}\n{body}")
        score = 0.0
        overlaps: List[str] = []
        if normalized_query and normalized_query in normalize_text(title):
            score += 8.0
        if normalized_query and normalized_query in combined:
            score += 3.0
        for term in query_terms:
            if term in normalize_text(title):
                score += 3.0
                overlaps.append(term)
            elif term in tags:
                score += 2.0
                overlaps.append(term)
            elif term in authors.lower():
                score += 2.0
                overlaps.append(term)
            elif term in combined:
                score += 1.0
                overlaps.append(term)
        if score <= 0:
            continue
        results.append(
            {
                "title": title,
                "path": note["path"],
                "score": round(score, 2),
                "overlaps": sorted(set(overlaps))[:10],
                "modified_at": note.get("modified_at", 0),
            }
        )
    results.sort(key=lambda item: (float(item["score"]), float(item.get("modified_at", 0))), reverse=True)
    return results[:limit]


def markdown_link(path: Path, notes_root: Path) -> str:
    return str(path.relative_to(notes_root)).replace("\\", "/")


def abstract_snapshot(text: str, length: int = 520) -> str:
    compact = " ".join(text.split())
    if len(compact) <= length:
        return compact
    return compact[: length - 3].rstrip() + "..."


def _require_fitz():
    try:
        import fitz  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError("PyMuPDF is required for full-text extraction.") from error
    return fitz


def cached_pdf_path(workflow: Dict[str, Any], paper_id: str) -> Path:
    return runtime_cache_root(workflow) / "pdfs" / f"{paper_id}.pdf"


def fetch_pdf(record: Dict[str, Any], workflow: Dict[str, Any]) -> Optional[Path]:
    paper_id = canonical_paper_id(str(record.get("paper_id", "")))
    target = cached_pdf_path(workflow, paper_id)
    if target.exists() and target.stat().st_size > 0:
        return target
    pdf_url = str(record.get("pdf_url", "")).strip()
    if not pdf_url and paper_id:
        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
    if not pdf_url:
        return None
    timeout = int(workflow.get("runtime", {}).get("request_timeout_seconds", 20))
    retry_limit = int(workflow.get("runtime", {}).get("retry_limit", 3))
    last_error: Optional[Exception] = None
    for _ in range(max(retry_limit, 1)):
        try:
            response = requests.get(pdf_url, timeout=timeout)
            response.raise_for_status()
            ensure_dir(target.parent)
            target.write_bytes(response.content)
            return target
        except Exception as error:
            last_error = error
    if last_error is not None:
        raise RuntimeError(f"failed to download pdf: {pdf_url}") from last_error
    return None


def extract_pdf_text(pdf_path: Path) -> str:
    fitz = _require_fitz()
    document = fitz.open(pdf_path)
    pages: List[str] = []
    try:
        for page in document:
            pages.append(page.get_text("text"))
    finally:
        document.close()
    return "\n".join(pages)


def normalize_heading(text: str) -> str:
    return re.sub(r"[^a-z]+", "", normalize_text(text))


def section_map_from_text(text: str) -> Dict[str, str]:
    known = {
        "abstract",
        "introduction",
        "background",
        "motivation",
        "relatedwork",
        "method",
        "methods",
        "approach",
        "framework",
        "system",
        "architecture",
        "experiment",
        "experiments",
        "experimentalsetup",
        "evaluation",
        "results",
        "analysis",
        "discussion",
        "limitations",
        "conclusion",
    }
    current = "body"
    buckets: Dict[str, List[str]] = {current: []}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = normalize_heading(re.sub(r"^\d+(\.\d+)*\s*", "", line))
        if heading in known and len(line) <= 80:
            current = heading
            buckets.setdefault(current, [])
            continue
        buckets.setdefault(current, []).append(line)
    return {key: "\n".join(value).strip() for key, value in buckets.items() if value}


def sentence_candidates(text: str) -> List[str]:
    compact = " ".join(text.split())
    if not compact:
        return []
    return [item.strip() for item in re.split(r"(?<=[\.\!\?])\s+", compact) if item.strip()]


def sentence_with_keywords(text: str, keywords: Sequence[str]) -> str:
    for sentence in sentence_candidates(text):
        lowered = normalize_text(sentence)
        if any(keyword in lowered for keyword in keywords):
            return sentence
    return ""


def build_text_context(record: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
    paper_id = canonical_paper_id(str(record.get("paper_id", "")))
    artifact_path = paper_text_artifact_path(workflow, paper_id)
    if artifact_path.exists():
        full_text = read_text(artifact_path)
        return {"path": artifact_path, "text": full_text, "sections": section_map_from_text(full_text)}
    pdf_path = fetch_pdf(record, workflow)
    if pdf_path is None:
        return {"path": None, "text": "", "sections": {}}
    full_text = extract_pdf_text(pdf_path)
    write_text(artifact_path, full_text)
    return {"path": artifact_path, "text": full_text, "sections": section_map_from_text(full_text)}


def render_paper_note(
    record: Dict[str, Any],
    notes_root: Path,
    copied_figures: List[Dict[str, Any]],
    related_notes: List[Dict[str, Any]],
    synthesis_report_path: Optional[Path],
    dossier_path: Optional[Path],
    text_context: Optional[Dict[str, Any]] = None,
) -> str:
    paper_id = canonical_paper_id(str(record.get("paper_id", "")))
    title = str(record.get("title", paper_id))
    published_at = str(record.get("published_at", ""))
    source_url = str(record.get("source_url", ""))
    pdf_url = str(record.get("pdf_url", ""))
    categories = list(record.get("categories") or [])
    topics = detect_topics(record)
    related_lines: List[str] = []
    for item in related_notes[:6]:
        note_link = markdown_link(Path(str(item["path"])), notes_root)
        overlaps = "、".join(item.get("overlaps", [])) or "主题相关"
        related_lines.append(f"- [[{note_link}|{item['title']}]]：重合点包括 {overlaps}")

    figure_lines: List[str] = []
    for item in copied_figures[:12]:
        image_name = Path(str(item["path"])).name
        figure_lines.append(f"- ![[{paper_id}/images/{image_name}]]")

    lines = [
        "---",
        'type: "paper-note"',
        f'paper_id: "{paper_id}"',
        f'title: "{title.replace(chr(34), chr(39))}"',
        f'profile_id: "{record.get("profile_id", "")}"',
        f'generated_at: "{utc_timestamp()}"',
        f'source: "{record.get("source", "")}"',
        f'source_url: "{source_url}"',
        f'pdf_url: "{pdf_url}"',
        f'published_at: "{published_at}"',
        f'authors: {json.dumps(record.get("authors", []), ensure_ascii=False)}',
        f'tags: {json.dumps(["research-paper", *topics[:3]], ensure_ascii=False)}',
        "---",
        "",
        f"# {title}",
        "",
        "## 论文信息",
        "",
        f"- paper_id：`{paper_id}`",
        f"- 发布时间：`{published_at or 'unknown'}`",
        f"- 作者：{', '.join(record.get('authors', [])) or 'unknown'}",
        f"- 分类：{', '.join(categories) or 'unknown'}",
        f"- 链接：[Abstract]({source_url}) | [PDF]({pdf_url})",
        "",
        "## 摘要原文",
        "",
        abstract_snapshot(str(record.get("abstract", "")), length=1400),
        "",
        "## 一句话概览",
        "",
        f"- {paper_glance(record)}",
        f"- 适合谁先看：{audience_summary(record)}",
        "",
        "## 这篇在解决什么问题",
        "",
        problem_summary(record, text_context),
        "",
        "## 它大概是怎么做的",
        "",
    ]
    for item in feature_bullets(record):
        lines.append(f"- {item}")
    if not feature_bullets(record):
        lines.append(f"- {method_summary(record, text_context)}")
    lines.extend(
        [
            "",
            "## 结果与结论怎么看",
            "",
            results_summary(record, text_context),
            "",
            "## 为什么值得现在读",
            "",
            f"- {recommendation_summary(record)}",
            f"- {evidence_summary(record)}",
            f"- {reading_focus_summary(record)}",
            "",
            "## 阅读提示",
            "",
            "- 这份笔记优先结合正文文本、标题、摘要、triage 信号和本地链接结果生成，但仍不能替代完整通读。",
            "- 如果这篇论文非常新，影响力和可复现性往往还没有稳定显现，建议把实验和附录一起核对。",
            "",
            "## 相关笔记",
            "",
        ]
    )
    if related_lines:
        lines.extend(related_lines)
    else:
        lines.append("- 暂未找到高相关本地笔记。")
    if synthesis_report_path is not None:
        lines.append(f"- synthesis report：`{synthesis_report_path}`")
    lines.extend(["", "## 配图索引", ""])
    if figure_lines:
        lines.extend(figure_lines)
    else:
        lines.append("- 暂未提取到可用配图。")
    lines.extend(["", "## 运行痕迹", ""])
    if dossier_path is not None:
        lines.append(f"- dossier：`{dossier_path}`")
    if text_context and text_context.get("path") is not None:
        lines.append(f"- full_text：`{text_context['path']}`")
    return "\n".join(lines).strip() + "\n"


def shortlist_theme_lines(selected: Sequence[Dict[str, Any]]) -> List[str]:
    counts: Dict[str, int] = {}
    for item in selected:
        for topic in detect_topics(item):
            counts[topic] = counts.get(topic, 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    if not ranked:
        return ["- 本次 shortlist 没有明显主题集中趋势。"]
    lines = []
    for topic, count in ranked[:3]:
        lines.append(f"- `{topic}`：在 shortlist 中出现 {count} 次。")
    return lines


def daily_item_brief(record: Dict[str, Any]) -> str:
    return f"{paper_glance(record)} {method_summary(record)}"


def daily_item_reason(record: Dict[str, Any]) -> str:
    return recommendation_summary(record)


def render_daily_note(
    manifest_payload: Dict[str, Any],
    triage_payload: Dict[str, Any],
    top3_notes: List[Dict[str, Any]],
    notes_root: Path,
) -> str:
    selected = list(triage_payload.get("selected", []))
    run_id = str(triage_payload.get("run_id", ""))
    generated_at = str(triage_payload.get("generated_at", utc_timestamp()))
    profile_id = str(triage_payload.get("profile_id", ""))
    lines = [
        "---",
        'type: "daily-paper-recommendation"',
        f'date: "{generated_at[:10]}"',
        f'profile_id: "{profile_id}"',
        f'run_id: "{run_id}"',
        f'candidate_count: {int(triage_payload.get("stats", {}).get("input_count", 0) or 0)}',
        f'shortlist_count: {int(triage_payload.get("stats", {}).get("selected_count", 0) or 0)}',
        'tags: ["research-foundry", "daily-recommendation"]',
        "---",
        "",
        f"# 每日论文推荐｜{generated_at[:10]}",
        "",
        "## 今日概览",
        "",
        f"- 研究画像：`{profile_id}`",
        f"- 运行批次：`{run_id}`",
        f"- 生成时间：`{generated_at}`",
        f"- 候选总数：`{triage_payload.get('stats', {}).get('input_count', 0)}`",
        f"- shortlist：`{triage_payload.get('stats', {}).get('selected_count', 0)}`",
        "",
        "## 今天主要在看什么",
        "",
    ]
    lines.extend(shortlist_theme_lines(selected))
    lines.extend(["", "## Source 状态", ""])
    source_status = manifest_payload.get("source_status", {}) or {}
    if source_status:
        for source_name, payload in source_status.items():
            lines.append(
                f"- `{source_name}`：status=`{payload.get('status', 'unknown')}`，candidate_count=`{payload.get('candidate_count', 0)}`"
            )
    else:
        lines.append("- 本次运行未记录 source 状态。")

    warnings = list(manifest_payload.get("warnings", []) or [])
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for item in warnings:
            lines.append(f"- {item}")

    lines.extend(["", "## Top 10 推荐", ""])
    for index, item in enumerate(selected[:10], start=1):
        lines.extend(
            [
                f"### {index}. {item.get('title', '')}",
                f"- paper_id：`{item.get('paper_id', '')}`",
                f"- score：`{item.get('scores', {}).get('total', item.get('score', 'n/a'))}`",
                f"- tier：`{item.get('tier', '')}`",
                f"- 研究概览：{daily_item_brief(item)}",
                f"- 建议先看：{reading_focus_summary(item)}",
                f"- 适合谁先看：{audience_summary(item)}",
                f"- 为什么入选：{daily_item_reason(item)}",
                "",
            ]
        )

    lines.extend(["## Top 3 深读入口", ""])
    if top3_notes:
        for item in top3_notes:
            note_link = markdown_link(Path(str(item["note_path"])), notes_root)
            lines.append(f"- [[{note_link}|{item['title']}]]")
    else:
        lines.append("- 本次未生成深读笔记。")
    return "\n".join(lines).strip() + "\n"


def prepare_today_materials(
    backend: Backend,
    workflow: Dict[str, Any],
    config_path: Path,
    profiles_path: Path,
    profile_id: str,
    notes_root: Path,
    intake: Dict[str, Any],
    triage: Dict[str, Any],
    triage_payload: Dict[str, Any],
    manifest_payload: Dict[str, Any],
    top_deepreads: int = 3,
) -> Dict[str, Any]:
    selected = list(triage_payload.get("selected", []))
    prepared_deepreads: List[Dict[str, Any]] = []
    for record in selected[: max(top_deepreads, 0)]:
        bundle = dict(record)
        bundle["_triage_file"] = str(triage["triage_result"])
        bundle["_candidate_file"] = str(intake["candidate_pool"])
        bundle["_run_id"] = str(triage_payload.get("run_id", ""))
        prepared = prepare_deepread_materials(
            backend,
            workflow,
            config_path,
            profiles_path,
            profile_id,
            notes_root,
            bundle,
            enable_links=True,
        )
        prepared_deepreads.append(
            {
                "paper_id": bundle.get("paper_id", ""),
                "title": bundle.get("title", ""),
                "target_note_path": str(prepared["note_path"]),
                "context_path": str(prepared["context_path"]),
                "template_path": str(prepared["template_path"]),
                "dossier_path": str(prepared["dossier_path"]),
                "synthesis_report_path": str(prepared["synthesis_report_path"] or ""),
                "full_text_path": str(prepared["full_text_path"] or ""),
                "figure_paths": [str(item.get("path", "")) for item in prepared["copied_figures"]],
            }
        )

    run_id = str(triage_payload.get("run_id", ""))
    target_daily_path = daily_note_path(notes_root, profile_id, str(triage_payload.get("generated_at", "")))
    template_path = backend.template_path("daily-recommendation-template.md")
    context_path = daily_context_path(workflow, run_id)
    shortlist_payload = []
    for item in selected[:10]:
        shortlist_payload.append(
            {
                "paper_id": item.get("paper_id", ""),
                "title": item.get("title", ""),
                "tier": item.get("tier", ""),
                "scores": item.get("scores", {}),
                "score_breakdown": item.get("score_breakdown", {}),
                "profile_hits": list(item.get("profile_hits", [])),
                "decision_reasons": item.get("decision_reasons", []),
                "abstract": item.get("abstract", ""),
                "categories": list(item.get("categories", [])),
                "published_at": item.get("published_at", ""),
                "source_url": item.get("source_url", ""),
                "pdf_url": item.get("pdf_url", ""),
            }
        )
    context_payload = {
        "kind": "daily_recommendation_context",
        "run_id": run_id,
        "profile_id": profile_id,
        "template_path": str(template_path),
        "target_note_path": str(target_daily_path),
        "candidate_pool_path": str(intake["candidate_pool"]),
        "triage_result_path": str(triage["triage_result"]),
        "reading_queue_path": str(triage["reading_queue"]) if triage.get("reading_queue") else "",
        "manifest_path": str(intake["candidate_pool"].parent / "run_manifest.json"),
        "generated_at": str(triage_payload.get("generated_at", "")),
        "candidate_count": triage_payload.get("stats", {}).get("input_count", 0),
        "shortlist_count": triage_payload.get("stats", {}).get("selected_count", 0),
        "source_status": manifest_payload.get("source_status", {}),
        "warnings": list(manifest_payload.get("warnings", []) or []),
        "shortlist": shortlist_payload,
        "top_deepreads": prepared_deepreads,
    }
    write_json_file(context_path, context_payload)
    return {
        "context_path": context_path,
        "template_path": template_path,
        "target_note_path": target_daily_path,
        "prepared_deepreads": prepared_deepreads,
    }


def run_source_intake(backend: Backend, config_path: Path, profiles_path: Path, profile_id: str) -> Dict[str, Any]:
    output = run_script(
        backend.phase_python("source-intake"),
        backend.phase_script("source-intake"),
        ["--config", str(config_path), "--profiles", str(profiles_path), "--profile-id", profile_id],
    )
    run_id = parse_logged_value(output, "run_id")
    candidate_pool = parse_logged_value(output, "candidate_pool")
    if not run_id or not candidate_pool:
        raise RuntimeError(f"source-intake did not return required outputs\n{output}")
    return {"run_id": run_id, "candidate_pool": Path(candidate_pool), "raw_output": output}


def run_candidate_triage(
    backend: Backend,
    config_path: Path,
    profiles_path: Path,
    profile_id: str,
    candidate_pool: Path,
) -> Dict[str, Any]:
    output = run_script(
        backend.phase_python("candidate-triage"),
        backend.phase_script("candidate-triage"),
        [
            "--config",
            str(config_path),
            "--profiles",
            str(profiles_path),
            "--profile-id",
            profile_id,
            "--input",
            str(candidate_pool),
        ],
    )
    triage_result = parse_logged_value(output, "triage_result")
    reading_queue = parse_logged_value(output, "reading_queue")
    if not triage_result:
        raise RuntimeError(f"candidate-triage did not return triage_result\n{output}")
    return {
        "triage_result": Path(triage_result),
        "reading_queue": Path(reading_queue) if reading_queue else None,
        "raw_output": output,
    }


def run_dossier(
    backend: Backend,
    config_path: Path,
    profiles_path: Path,
    profile_id: str,
    record: Dict[str, Any],
) -> Dict[str, Any]:
    args = [
        "--config",
        str(config_path),
        "--profiles",
        str(profiles_path),
        "--profile-id",
        profile_id,
        "--paper-id",
        canonical_paper_id(str(record.get("paper_id", ""))),
    ]
    triage_file = str(record.get("_triage_file", ""))
    candidate_file = str(record.get("_candidate_file", ""))
    if triage_file:
        args.extend(["--triage-file", triage_file])
    if candidate_file:
        args.extend(["--candidate-file", candidate_file])
    args.append("--skip-figures")
    output = run_script(
        backend.phase_python("evidence-dossier"),
        backend.phase_script("evidence-dossier"),
        args,
    )
    dossier_path = parse_logged_value(output, "dossier")
    figure_manifest_path = parse_logged_value(output, "figure_manifest")
    return {
        "dossier_path": Path(dossier_path) if dossier_path else None,
        "figure_manifest_path": Path(figure_manifest_path) if figure_manifest_path else None,
        "raw_output": output,
    }


def run_synthesis(backend: Backend, config_path: Path, dossier_path: Path, notes_root: Path) -> Dict[str, Any]:
    output = run_script(
        backend.phase_python("knowledge-synthesis"),
        backend.phase_script("knowledge-synthesis"),
        ["--config", str(config_path), "--dossier", str(dossier_path), "--notes-root", str(notes_root)],
    )
    report_path = parse_logged_value(output, "synthesis_report")
    relations_path = parse_logged_value(output, "relations")
    return {
        "report_path": Path(report_path) if report_path else None,
        "relations_path": Path(relations_path) if relations_path else None,
        "raw_output": output,
    }


def run_figure_extraction(backend: Backend, workflow: Dict[str, Any], record: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    artifact_root = runtime_artifact_root(workflow)
    paper_id = canonical_paper_id(str(record.get("paper_id", "")))
    manifest_path = artifact_root / f"figure_manifest-{paper_id}.json"
    output = run_script(
        backend.phase_python("figure-extraction"),
        backend.phase_script("figure-extraction"),
        [
            "--paper-id",
            paper_id,
            "--output-dir",
            str(output_dir),
            "--manifest-output",
            str(manifest_path),
            "--timeout",
            str(int(workflow.get("runtime", {}).get("request_timeout_seconds", 20))),
            "--retry-limit",
            str(int(workflow.get("runtime", {}).get("retry_limit", 3))),
            "--max-figures",
            str(int(workflow.get("dossier_policy", {}).get("max_figures", 12))),
        ],
    )
    return {"manifest_path": manifest_path, "manifest": read_json(manifest_path, default={}) or {}, "raw_output": output}


def prepare_deepread_materials(
    backend: Backend,
    workflow: Dict[str, Any],
    config_path: Path,
    profiles_path: Path,
    profile_id: str,
    notes_root: Path,
    record: Dict[str, Any],
    enable_links: bool = True,
) -> Dict[str, Any]:
    dossier_result = run_dossier(backend, config_path, profiles_path, profile_id, record)
    dossier_path = dossier_result["dossier_path"]
    if dossier_path is None:
        raise RuntimeError("dossier output missing")
    try:
        text_context = build_text_context(record, workflow)
    except RuntimeError:
        text_context = {"path": None, "text": "", "sections": {}}

    figure_manifest: Dict[str, Any] = {}
    try:
        figure_result = run_figure_extraction(
            backend,
            workflow,
            record,
            paper_image_dir(notes_root, canonical_paper_id(str(record.get("paper_id", "")))),
        )
        figure_manifest = figure_result["manifest"]
    except RuntimeError:
        figure_manifest = {"items": [], "figure_count": 0}
    copied_figures = [
        {
            "name": Path(str(item.get("path", ""))).name,
            "path": str(item.get("path", "")),
            "source": item.get("source", ""),
            "format": item.get("format", ""),
        }
        for item in list(figure_manifest.get("items", []))
        if item.get("path")
    ]

    note_path = paper_note_path(notes_root, canonical_paper_id(str(record.get("paper_id", ""))))
    related_notes = search_notes(
        notes_root,
        f"{record.get('title', '')}\n{record.get('abstract', '')}",
        limit=8,
        exclude_paths=[note_path],
    )

    synthesis_path: Optional[Path] = None
    if enable_links:
        synthesis_result = run_synthesis(backend, config_path, dossier_path, notes_root)
        synthesis_path = synthesis_result.get("report_path")

    template_path = backend.template_path("deepread-note-template.md")
    context_path = deepread_context_path(workflow, canonical_paper_id(str(record.get("paper_id", ""))))
    related_payload = []
    for item in related_notes:
        related_payload.append(
            {
                "title": item.get("title", ""),
                "path": str(item.get("path", "")),
                "vault_link": markdown_link(Path(str(item["path"])), notes_root),
                "score": item.get("score", 0),
                "overlaps": list(item.get("overlaps", [])),
            }
        )
    context_payload = {
        "kind": "deepread_context",
        "profile_id": profile_id,
        "paper_id": canonical_paper_id(str(record.get("paper_id", ""))),
        "title": record.get("title", ""),
        "target_note_path": str(note_path),
        "template_path": str(template_path),
        "notes_root": str(notes_root),
        "dossier_path": str(dossier_path),
        "synthesis_report_path": str(synthesis_path) if synthesis_path else "",
        "full_text_path": str(text_context.get("path")) if text_context.get("path") else "",
        "figure_paths": [str(item.get("path", "")) for item in copied_figures],
        "related_notes": related_payload,
        "record": {
            "paper_id": record.get("paper_id", ""),
            "title": record.get("title", ""),
            "abstract": record.get("abstract", ""),
            "authors": list(record.get("authors", [])),
            "published_at": record.get("published_at", ""),
            "categories": list(record.get("categories", [])),
            "source": record.get("source", ""),
            "source_url": record.get("source_url", ""),
            "pdf_url": record.get("pdf_url", ""),
            "profile_hits": list(record.get("profile_hits", [])),
            "scores": record.get("scores", {}),
            "score_breakdown": record.get("score_breakdown", {}),
            "tier": record.get("tier", ""),
            "decision_reasons": record.get("decision_reasons", []),
        },
    }
    write_json_file(context_path, context_payload)
    return {
        "note_path": note_path,
        "dossier_path": dossier_path,
        "synthesis_report_path": synthesis_path,
        "copied_figures": copied_figures,
        "related_notes": related_notes,
        "full_text_path": text_context.get("path"),
        "text_context": text_context,
        "context_path": context_path,
        "template_path": template_path,
    }


def build_deepread_note(
    backend: Backend,
    workflow: Dict[str, Any],
    config_path: Path,
    profiles_path: Path,
    profile_id: str,
    notes_root: Path,
    record: Dict[str, Any],
    enable_links: bool = True,
) -> Dict[str, Any]:
    result = prepare_deepread_materials(
        backend,
        workflow,
        config_path,
        profiles_path,
        profile_id,
        notes_root,
        record,
        enable_links=enable_links,
    )
    write_text(
        result["note_path"],
        render_paper_note(
            record,
            notes_root,
            result["copied_figures"],
            result["related_notes"],
            result["synthesis_report_path"],
            result["dossier_path"],
            result.get("text_context"),
        ),
    )
    return result


def console_summary(title: str, rows: Sequence[str]) -> str:
    return "\n".join([title, *rows]).strip() + "\n"
