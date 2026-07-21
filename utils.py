"""Utility helpers: catalogs, local complexity heuristics, and report rendering."""

from __future__ import annotations

import datetime as _dt
import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# Catalogs used by the UI
# ---------------------------------------------------------------------------

LANGUAGES: list[str] = [
    "Swift",
    "Dart",
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Kotlin",
    "Go",
    "Rust",
    "C#",
    "C++",
    "PHP",
    "Ruby",
    "SQL",
    "HTML/CSS",
]

# Maps a display language to the token used by the Gradio Code component so the
# editor highlights syntax correctly.
GRADIO_CODE_LANGUAGE: dict[str, str | None] = {
    "Swift": "python",  # closest available highlighter for Swift-like syntax
    "Dart": "typescript",
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Java": "java",
    "Kotlin": "java",
    "Go": "go",
    "Rust": "rust",
    "C#": "csharp",
    "C++": "cpp",
    "PHP": "php",
    "Ruby": "python",
    "SQL": "sql",
    "HTML/CSS": "html",
}

REVIEW_MODE_NAMES: list[str] = [
    "General",
    "Bugs",
    "Performance",
    "Security",
    "Best Practices",
    "Clean Architecture",
    "Refactoring",
    "Testing",
]

SEVERITY_BADGE: dict[str, str] = {
    "critical": "🔴 Critical",
    "high": "🟠 High",
    "medium": "🟡 Medium",
    "low": "🟢 Low",
    "very high": "🔴 Very High",
    "moderate": "🟡 Moderate",
}


def badge(level: str) -> str:
    """Return a human-friendly severity/impact badge."""
    return SEVERITY_BADGE.get((level or "").strip().lower(), f"⚪ {level or 'n/a'}")


def code_language_token(language: str) -> str | None:
    """Highlighter token for the Gradio Code editor."""
    return GRADIO_CODE_LANGUAGE.get(language, "python")


# ---------------------------------------------------------------------------
# Local, dependency-free complexity metrics (a quick heuristic layer that
# complements the model's qualitative complexity analysis).
# ---------------------------------------------------------------------------

_BRANCH_KEYWORDS = re.compile(
    r"\b(if|elif|else if|for|while|case|catch|except|&&|\|\||\?)\b"
)


def local_metrics(code: str) -> dict[str, int]:
    """Compute lightweight static metrics without executing the code."""
    lines = code.splitlines()
    non_blank = [ln for ln in lines if ln.strip()]
    comment_prefixes = ("#", "//", "/*", "*", "--", "<!--")
    comments = [ln for ln in non_blank if ln.strip().startswith(comment_prefixes)]
    branches = len(_BRANCH_KEYWORDS.findall(code))
    return {
        "total_lines": len(lines),
        "code_lines": len(non_blank) - len(comments),
        "comment_lines": len(comments),
        "branch_points": branches,
        # A rough cyclomatic proxy: one base path plus each branch point.
        "cyclomatic_proxy": branches + 1,
    }


# ---------------------------------------------------------------------------
# JSON extraction (defensive against stray prose or code fences)
# ---------------------------------------------------------------------------

def extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of the JSON object from a model response."""
    if not text:
        raise ValueError("Empty response from the model.")

    cleaned = text.strip()
    # Strip markdown fences if the model added them despite instructions.
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost { ... } span.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(cleaned[start : end + 1])

    raise ValueError("Could not parse a JSON object from the model response.")


# ---------------------------------------------------------------------------
# Markdown report rendering
# ---------------------------------------------------------------------------

def _render_findings(items: list[dict[str, Any]], key: str) -> str:
    if not items:
        return "_No issues found._\n"
    out = []
    for i, it in enumerate(items, 1):
        level = it.get("severity") or it.get("impact") or "n/a"
        line = it.get("line", "n/a")
        title = it.get("title", "Untitled finding")
        detail = it.get("detail", "")
        fix = it.get("fix", "")
        out.append(f"**{i}. {title}** — {badge(level)} · _line {line}_\n\n{detail}")
        if fix:
            out.append(f"\n> **Fix:** {fix}")
        out.append("\n")
    return "\n".join(out)


def render_markdown_report(
    result: dict[str, Any],
    language: str,
    mode: str,
    metrics: dict[str, int],
) -> str:
    """Render the full structured result into a shareable Markdown report."""
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    score = result.get("overall_score", "—")
    summary = result.get("summary", "")
    arch = result.get("architecture_review", {}) or {}
    complexity = result.get("complexity", {}) or {}

    md: list[str] = []
    md.append(f"# Code Review Report\n")
    md.append(
        f"**Language:** {language}  ·  **Mode:** {mode}  ·  "
        f"**Generated:** {stamp}\n"
    )
    md.append(f"## Overall Score: {score} / 10\n")
    if summary:
        md.append(f"{summary}\n")

    md.append("## 🐞 Bugs\n")
    md.append(_render_findings(result.get("bugs", []), "bugs"))

    md.append("## 🔒 Security Issues\n")
    md.append(_render_findings(result.get("security_issues", []), "security"))

    md.append("## ⚡ Performance Issues\n")
    md.append(_render_findings(result.get("performance_issues", []), "performance"))

    md.append("## 🏛️ Architecture Review\n")
    if arch.get("assessment"):
        md.append(arch["assessment"] + "\n")
    if arch.get("strengths"):
        md.append("**Strengths**\n")
        md.extend(f"- {s}" for s in arch["strengths"])
        md.append("")
    if arch.get("concerns"):
        md.append("**Concerns**\n")
        md.extend(f"- {c}" for c in arch["concerns"])
        md.append("")
    if arch.get("suggestions"):
        md.append("**Suggestions**\n")
        md.extend(f"- {s}" for s in arch["suggestions"])
        md.append("")

    md.append("## ✅ Best-Practice Suggestions\n")
    bp = result.get("best_practices", [])
    if bp:
        for i, item in enumerate(bp, 1):
            md.append(f"**{i}. {item.get('title', '')}**\n\n{item.get('detail', '')}\n")
    else:
        md.append("_No additional suggestions._\n")

    md.append("## 📊 Complexity Analysis\n")
    md.append(f"- **Rating:** {complexity.get('rating', '—')}")
    md.append(
        f"- **Time complexity:** {complexity.get('estimated_time_complexity', '—')}"
    )
    md.append(
        f"- **Space complexity:** {complexity.get('estimated_space_complexity', '—')}"
    )
    md.append(
        f"- **Cyclomatic (model estimate):** "
        f"{complexity.get('cyclomatic_estimate', '—')}"
    )
    md.append(
        f"- **Cyclomatic (static proxy):** {metrics.get('cyclomatic_proxy', '—')}"
    )
    md.append(
        f"- **Lines:** {metrics.get('total_lines', 0)} total · "
        f"{metrics.get('code_lines', 0)} code · "
        f"{metrics.get('comment_lines', 0)} comment"
    )
    if complexity.get("notes"):
        md.append(f"\n{complexity['notes']}\n")

    md.append("\n## ♻️ Refactored Code\n")
    refactored = result.get("refactored_code", "")
    if refactored:
        fence = code_language_token(language) or ""
        md.append(f"```{fence}\n{refactored}\n```")
    else:
        md.append("_No refactor produced._")

    return "\n".join(md).strip() + "\n"


def score_label(score: Any) -> str:
    """Format the score for the headline display component."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "— / 10"
    return f"{value:.1f} / 10"
