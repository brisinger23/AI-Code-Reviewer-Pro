"""AI Code Reviewer Pro — Gradio application entry point.

A premium, animated, dark, responsive UI for reviewing source code across many
languages and review lenses. The heavy lifting lives in `reviewer.py`; this
module wires the interface, formats results, and handles errors gracefully.
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
    detect_language,
    render_markdown_report,
    score_label,
)

APP_DIR = Path(__file__).parent
THEME_CSS = (APP_DIR / "theme.css").read_text(encoding="utf-8")
MICRO_JS = (APP_DIR / "assets" / "interactions.js").read_text(encoding="utf-8")
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

# Injected once into <head>; installs ripple + score count-up micro-interactions.
HEAD_HTML = f"<script>{MICRO_JS}</script>"

# Placeholder shown in every results panel before the first review.
_IDLE = (
    "<div class='idle-hint'><span class='idle-dot'></span> Awaiting review — "
    "run a review to populate this panel.</div>"
)


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------

def _findings_markdown(items: list[dict], impact_key: str = "severity") -> str:
    """Render a list of findings as compact Markdown for a results panel."""
    if not items:
        return "<div class='ok-card'>✅ <strong>No issues found in this category.</strong></div>"
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
        return "<div class='ok-card'>✅ <strong>Code already follows the key best practices.</strong></div>"
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


def _error_card(title: str, message: str) -> str:
    """A premium, animated error card (styled + shake via CSS)."""
    return (
        "<div class='error-card'>"
        f"<div class='error-card__title'>⚠️ {title}</div>"
        f"<div class='error-card__body'>{message}</div>"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def _error_outputs(title: str, message: str):
    """Populate every output with a graceful error state (shown once)."""
    card = _error_card(title, message)
    notice = (
        "<div class='idle-hint'><span class='idle-dot'></span> "
        "See the summary above for details.</div>"
    )
    return (
        "— / 10",
        card,     # summary (the single, prominent error card)
        notice,   # bugs
        notice,   # security
        notice,   # performance
        notice,   # architecture
        notice,   # best practices
        notice,   # complexity
        gr.update(value="", visible=False),  # refactored
        "",                                   # report
        gr.update(visible=False),            # download
    )


def run_review(code: str, language: str, mode: str, autodetect: bool):
    """Gradio callback: run a review and populate every output component."""
    # Friendly guard before hitting the API.
    if not code or not code.strip():
        yield _error_outputs(
            "Nothing to review",
            "Paste some code into the editor, then click <strong>Review Code</strong>.",
        )
        return

    # Auto-detect keeps the language in sync with what was actually pasted.
    if autodetect:
        detected, confidence = detect_language(code)
        if confidence >= 0.25:
            language = detected

    try:
        result = review_code(code, language, mode)
    except ReviewError as exc:
        yield _error_outputs("Review could not be completed", str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - never crash the UI
        yield _error_outputs(
            "Unexpected error",
            f"{exc}<br><br>Please try again in a moment.",
        )
        return

    data = result.data
    metrics = result.metrics
    report_md = render_markdown_report(data, language, mode, metrics)

    # Persist the report so it can be downloaded.
    safe_lang = language.replace("/", "-").replace(" ", "_")
    report_path = REPORTS_DIR / f"code_review_{safe_lang}_{mode.replace(' ', '_')}.md"
    report_path.write_text(report_md, encoding="utf-8")

    refactored = data.get("refactored_code", "")

    yield (
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


def autodetect_on_edit(code: str, enabled: bool, current_lang: str):
    """Live language detection as the user edits, without disrupting typing."""
    if not enabled or not code or not code.strip():
        return gr.update(), gr.update(), gr.update(value="")

    lang, confidence = detect_language(code)
    pct = int(confidence * 100)
    if confidence < 0.25:
        status = "🪄 <span class='detect-muted'>Auto-detect: not enough signal yet…</span>"
        return gr.update(), gr.update(), gr.update(value=status)

    status = f"🪄 Detected <strong>{lang}</strong> · <span class='detect-pct'>{pct}%</span>"
    if lang == current_lang:
        return gr.update(), gr.update(), gr.update(value=status)

    # Switch language + editor highlighting; value unchanged so no edit loop.
    return (
        gr.update(value=lang),
        gr.update(language=code_language_token(lang)),
        gr.update(value=status),
    )


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="AI Code Reviewer Pro",
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.indigo,
            neutral_hue=gr.themes.colors.slate,
        ),
        css=THEME_CSS,
        head=HEAD_HTML,
        fill_height=True,
    ) as demo:
        # Animated ambient background layers.
        gr.HTML("<div class='aurora'></div><div class='grid-overlay'></div>")

        gr.HTML(
            """
            <div class="app-header">
              <div class="app-header__brand">
                <span class="app-header__logo">⌘</span>
                <div>
                  <h1>AI Code Reviewer Pro</h1>
                  <p>Principal-level, multi-language code review — with instant
                     language detection and an actionable, downloadable report.</p>
                </div>
              </div>
              <div class="app-header__badges">
                <span class="pill pill--live">● Live</span>
                <span class="pill">15 languages</span>
                <span class="pill">8 review modes</span>
              </div>
            </div>
            """
        )

        with gr.Row(equal_height=False):
            # ---------------- Left: input column ----------------
            with gr.Column(scale=5, min_width=380):
                with gr.Group(elem_classes="panel panel--in"):
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
                    with gr.Row(elem_classes="detect-bar", equal_height=True):
                        autodetect = gr.Checkbox(
                            value=True,
                            label="🪄 Auto-detect language",
                            elem_classes="detect-toggle",
                            scale=2,
                            container=False,
                        )
                        detect_status = gr.Markdown(
                            "", elem_classes="detect-status"
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
                            "🔍  Review Code",
                            variant="primary",
                            elem_classes="review-btn",
                            scale=3,
                        )
                        clear_btn = gr.Button(
                            "Clear", elem_classes="ghost-btn", scale=1
                        )

            # ---------------- Right: results column ----------------
            with gr.Column(scale=7, min_width=420):
                with gr.Group(elem_classes="panel score-panel panel--in"):
                    gr.HTML("<div class='score-caption'>Overall score</div>")
                    score = gr.Label(
                        value="— / 10",
                        show_label=False,
                        elem_classes="score-value",
                    )
                    gr.HTML(
                        "<div class='score-bar'><span></span></div>"
                        "<div class='score-hint'>Quality out of 10 · updates after "
                        "each review</div>"
                    )

                summary = gr.Markdown(
                    "<div class='idle-hint'><span class='idle-dot'></span> "
                    "Run a review to see the executive summary here.</div>",
                    elem_classes="panel summary-panel panel--in",
                )

                with gr.Tabs(elem_classes="result-tabs"):
                    with gr.Tab("🐞 Bugs"):
                        bugs_out = gr.Markdown(_IDLE)
                    with gr.Tab("🔒 Security"):
                        security_out = gr.Markdown(_IDLE)
                    with gr.Tab("⚡ Performance"):
                        performance_out = gr.Markdown(_IDLE)
                    with gr.Tab("🏛️ Architecture"):
                        architecture_out = gr.Markdown(_IDLE)
                    with gr.Tab("✅ Best Practices"):
                        best_out = gr.Markdown(_IDLE)
                    with gr.Tab("📊 Complexity"):
                        complexity_out = gr.Markdown(_IDLE)
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
                            "⬇️  Download report (.md)",
                            visible=False,
                            elem_classes="download-btn",
                        )

        gr.HTML(
            """
            <div class="app-footer">
              Paste code, pick a review mode, then hit
              <strong>Review Code</strong>. Language is detected automatically —
              reports can be copied or downloaded.
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
            inputs=[code, language, mode, autodetect],
            outputs=outputs,
            api_name="review",
            show_progress="full",
        )

        # Live auto-detection as the user edits.
        code.change(
            fn=autodetect_on_edit,
            inputs=[code, autodetect, language],
            outputs=[language, code, detect_status],
            show_progress="hidden",
        )

        language.change(fn=on_language_change, inputs=language, outputs=code)

        clear_btn.click(
            fn=lambda: (gr.update(value=""), gr.update(value="")),
            inputs=None,
            outputs=[code, detect_status],
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
