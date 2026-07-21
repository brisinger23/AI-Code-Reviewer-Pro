"""AI Code Reviewer Pro — Gradio application entry point.

A modern, dark, responsive UI for reviewing source code across many languages
and review lenses. The heavy lifting lives in `reviewer.py`; this module wires
the interface and formats results.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional; env vars can be set directly
    pass

import gradio as gr

from reviewer import ReviewError, review_code
from utils import (
    LANGUAGES,
    REVIEW_MODE_NAMES,
    badge,
    code_language_token,
    render_markdown_report,
    score_label,
)

APP_DIR = Path(__file__).parent
THEME_CSS = (APP_DIR / "theme.css").read_text(encoding="utf-8")
REPORTS_DIR = APP_DIR / "assets" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PLACEHOLDER_CODE = """def fibonacci(n):
    # Naive recursive Fibonacci — try reviewing this!
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

result = fibonacci(35)
print(result)
"""


def _findings_markdown(items: list[dict], impact_key: str = "severity") -> str:
    """Render a list of findings as compact Markdown for a results panel."""
    if not items:
        return "> ✅ **No issues found in this category.**"
    blocks = []
    for i, it in enumerate(items, 1):
        level = it.get(impact_key) or it.get("impact") or it.get("severity") or "n/a"
        line = it.get("line", "n/a")
        title = it.get("title", "Finding")
        detail = it.get("detail", "")
        fix = it.get("fix", "")
        block = f"### {i}. {title}\n{badge(level)} · `line {line}`\n\n{detail}"
        if fix:
            block += f"\n\n> 💡 **Fix:** {fix}"
        blocks.append(block)
    return "\n\n---\n\n".join(blocks)


def _architecture_markdown(arch: dict) -> str:
    if not arch:
        return "_No architecture assessment available._"
    parts = []
    if arch.get("assessment"):
        parts.append(arch["assessment"])
    for label, key, icon in (
        ("Strengths", "strengths", "✅"),
        ("Concerns", "concerns", "⚠️"),
        ("Suggestions", "suggestions", "💡"),
    ):
        values = arch.get(key) or []
        if values:
            parts.append(f"**{icon} {label}**\n" + "\n".join(f"- {v}" for v in values))
    return "\n\n".join(parts)


def _best_practices_markdown(items: list[dict]) -> str:
    if not items:
        return "> ✅ **Code already follows the key best practices.**"
    return "\n\n---\n\n".join(
        f"### {i}. {it.get('title', '')}\n{it.get('detail', '')}"
        for i, it in enumerate(items, 1)
    )


def _complexity_markdown(complexity: dict, metrics: dict) -> str:
    return (
        f"| Metric | Value |\n"
        f"| --- | --- |\n"
        f"| Rating | **{complexity.get('rating', '—')}** |\n"
        f"| Time complexity | `{complexity.get('estimated_time_complexity', '—')}` |\n"
        f"| Space complexity | `{complexity.get('estimated_space_complexity', '—')}` |\n"
        f"| Cyclomatic (model) | {complexity.get('cyclomatic_estimate', '—')} |\n"
        f"| Cyclomatic (static) | {metrics.get('cyclomatic_proxy', '—')} |\n"
        f"| Total lines | {metrics.get('total_lines', 0)} |\n"
        f"| Code lines | {metrics.get('code_lines', 0)} |\n"
        f"| Comment lines | {metrics.get('comment_lines', 0)} |\n"
        f"| Branch points | {metrics.get('branch_points', 0)} |\n"
        + (f"\n\n{complexity.get('notes')}" if complexity.get("notes") else "")
    )


def run_review(code: str, language: str, mode: str):
    """Gradio callback: run a review and populate every output component."""
    try:
        result = review_code(code, language, mode)
    except ReviewError as exc:
        error_md = f"### ⚠️ Review could not be completed\n\n{exc}"
        return (
            "— / 10",
            error_md,   # summary
            error_md,   # bugs
            "",         # security
            "",         # performance
            "",         # architecture
            "",         # best practices
            "",         # complexity
            gr.update(value="", visible=False),   # refactored code
            "",         # markdown report
            gr.update(visible=False),             # download
        )

    data = result.data
    metrics = result.metrics

    report_md = render_markdown_report(data, language, mode, metrics)

    # Persist the report so it can be downloaded.
    safe_lang = language.replace("/", "-").replace(" ", "_")
    report_path = REPORTS_DIR / f"code_review_{safe_lang}_{mode.replace(' ', '_')}.md"
    report_path.write_text(report_md, encoding="utf-8")

    refactored = data.get("refactored_code", "")

    return (
        score_label(data.get("overall_score")),
        f"### 📝 Summary\n\n{data.get('summary', '') or '_No summary provided._'}",
        _findings_markdown(data.get("bugs", []), "severity"),
        _findings_markdown(data.get("security_issues", []), "severity"),
        _findings_markdown(data.get("performance_issues", []), "impact"),
        _architecture_markdown(data.get("architecture_review", {})),
        _best_practices_markdown(data.get("best_practices", [])),
        _complexity_markdown(data.get("complexity", {}), metrics),
        gr.update(
            value=refactored,
            language=code_language_token(language),
            visible=bool(refactored),
        ),
        report_md,
        gr.update(value=str(report_path), visible=True),
    )


def on_language_change(language: str):
    """Update the editor's syntax highlighting when the language changes."""
    return gr.update(language=code_language_token(language))


def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="AI Code Reviewer Pro",
        theme=gr.themes.Base(),
        css=THEME_CSS,
        fill_height=True,
    ) as demo:
        gr.HTML(
            """
            <div class="app-header">
              <div class="app-header__brand">
                <span class="app-header__logo">⌘</span>
                <div>
                  <h1>AI Code Reviewer Pro</h1>
                  <p>Principal-level, multi-language code review — powered by the
                     OpenAI Responses API.</p>
                </div>
              </div>
            </div>
            """
        )

        with gr.Row(equal_height=False):
            # ---------------- Left: input column ----------------
            with gr.Column(scale=5, min_width=380):
                with gr.Group(elem_classes="panel"):
                    with gr.Row():
                        language = gr.Dropdown(
                            LANGUAGES,
                            value="Python",
                            label="Language",
                            elem_classes="control",
                        )
                        mode = gr.Dropdown(
                            REVIEW_MODE_NAMES,
                            value="General",
                            label="Review mode",
                            elem_classes="control",
                        )
                    code = gr.Code(
                        value=PLACEHOLDER_CODE,
                        language="python",
                        label="Your code",
                        lines=20,
                        elem_classes="code-editor",
                    )
                    with gr.Row():
                        review_btn = gr.Button(
                            "🔍 Review Code",
                            variant="primary",
                            elem_classes="review-btn",
                            scale=3,
                        )
                        clear_btn = gr.Button("Clear", scale=1)

            # ---------------- Right: results column ----------------
            with gr.Column(scale=7, min_width=420):
                with gr.Group(elem_classes="panel score-panel"):
                    gr.Markdown("#### Overall score")
                    score = gr.Label(
                        value="— / 10",
                        show_label=False,
                        elem_classes="score-value",
                    )

                summary = gr.Markdown(
                    "Run a review to see the summary here.",
                    elem_classes="panel summary-panel",
                )

                with gr.Tabs():
                    with gr.Tab("🐞 Bugs"):
                        bugs_out = gr.Markdown("_Awaiting review…_")
                    with gr.Tab("🔒 Security"):
                        security_out = gr.Markdown("_Awaiting review…_")
                    with gr.Tab("⚡ Performance"):
                        performance_out = gr.Markdown("_Awaiting review…_")
                    with gr.Tab("🏛️ Architecture"):
                        architecture_out = gr.Markdown("_Awaiting review…_")
                    with gr.Tab("✅ Best Practices"):
                        best_out = gr.Markdown("_Awaiting review…_")
                    with gr.Tab("📊 Complexity"):
                        complexity_out = gr.Markdown("_Awaiting review…_")
                    with gr.Tab("♻️ Refactored"):
                        refactored_out = gr.Code(
                            label="Refactored code",
                            language="python",
                            visible=False,
                        )
                    with gr.Tab("📄 Report"):
                        report_out = gr.Markdown(
                            "_The full Markdown report will appear here._",
                            elem_classes="report-panel",
                        )
                        download_btn = gr.DownloadButton(
                            "⬇️ Download report (.md)",
                            visible=False,
                        )

        gr.HTML(
            """
            <div class="app-footer">
              Paste code, pick a language and review mode, then click
              <strong>Review Code</strong>. Reports can be copied or downloaded.
            </div>
            """
        )

        # -------------------- Wiring --------------------
        outputs = [
            score,
            summary,
            bugs_out,
            security_out,
            performance_out,
            architecture_out,
            best_out,
            complexity_out,
            refactored_out,
            report_out,
            download_btn,
        ]

        review_btn.click(
            fn=run_review,
            inputs=[code, language, mode],
            outputs=outputs,
            api_name="review",
        )

        language.change(fn=on_language_change, inputs=language, outputs=code)

        clear_btn.click(
            fn=lambda: gr.update(value=""),
            inputs=None,
            outputs=code,
        )

    return demo


def main() -> None:
    # Free hosts (Render, Koyeb, Cloud Run, Railway) inject the port via $PORT.
    port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))
    demo = build_app()
    demo.queue(default_concurrency_limit=4).launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=port,
        show_api=False,
    )


if __name__ == "__main__":
    main()
