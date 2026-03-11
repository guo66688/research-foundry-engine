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


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


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


def render_paper_note(
    record: Dict[str, Any],
    notes_root: Path,
    copied_figures: List[Dict[str, Any]],
    related_notes: List[Dict[str, Any]],
    synthesis_report_path: Optional[Path],
    dossier_path: Optional[Path],
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
        "## 中文解读",
        "",
        f"- 主题判断：{' / '.join(topics[:2])}",
        f"- {contribution_summary(record)}",
        f"- {evidence_summary(record)}",
        "",
        "## 研究背景与动机",
        "",
        "这篇工作试图解决当前方向中的具体瓶颈，是否真正抓住主问题，仍建议结合正文引言继续确认。",
        "",
        "## 方法概述",
        "",
        contribution_summary(record),
        "",
        "## 实验与结果",
        "",
        evidence_summary(record),
        "",
        "## 研究价值评估",
        "",
    ]
    for reason in profile_reasons(record):
        lines.append(f"- {reason}")
    lines.append(f"- {method_signal_summary(record)}")
    lines.extend(
        [
            "",
            "## 优势",
            "",
            "- 主题方向明确，容易判断与当前画像的关系。",
            "- 摘要中提供了一定的方法或实验信号，值得进入精读候选。",
            "",
            "## 局限",
            "",
            "- 当前笔记仍主要依据标题、摘要和 triage 信号，尚未替代通读正文。",
            "- 如果论文很新，影响力和复现稳定性仍需后续观察。",
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
    return "\n".join(lines).strip() + "\n"


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
        "## Source 状态",
        "",
    ]
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
                f"- 推荐理由：{'; '.join(profile_reasons(item))} {method_signal_summary(item)}",
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
    dossier_result = run_dossier(backend, config_path, profiles_path, profile_id, record)
    dossier_path = dossier_result["dossier_path"]
    if dossier_path is None:
        raise RuntimeError("dossier output missing")

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

    write_text(
        note_path,
        render_paper_note(record, notes_root, copied_figures, related_notes, synthesis_path, dossier_path),
    )
    return {
        "note_path": note_path,
        "dossier_path": dossier_path,
        "synthesis_report_path": synthesis_path,
        "copied_figures": copied_figures,
        "related_notes": related_notes,
    }


def console_summary(title: str, rows: Sequence[str]) -> str:
    return "\n".join([title, *rows]).strip() + "\n"
