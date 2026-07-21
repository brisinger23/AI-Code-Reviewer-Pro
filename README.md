---
title: AI Code Reviewer Pro
emoji: ⌘
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
pinned: false
license: mit
---

# AI Code Reviewer Pro

A production-ready, multi-language **AI code review** application with a modern
dark UI. Paste code, pick a language and a review lens, and get a structured,
principal-level review — bugs, security, performance, architecture,
best-practices, complexity analysis, and a fully refactored version — all
rendered as an interactive report you can copy or download.

Powered by the **OpenAI Responses API** with careful prompt engineering.

---

## ✨ Features

- **Modern dark, responsive UI** built with Gradio Blocks and custom CSS.
- **Syntax-highlighted code editor** that adapts to the selected language.
- **15 languages:** Swift, Dart, Python, JavaScript, TypeScript, Java, Kotlin,
  Go, Rust, C#, C++, PHP, Ruby, SQL, HTML/CSS.
- **8 review modes:** General, Bugs, Performance, Security, Best Practices,
  Clean Architecture, Refactoring, Testing.
- **Structured output:**
  - Overall score out of 10
  - Bugs (with severity, line, and suggested fix)
  - Security issues
  - Performance issues
  - Architecture review (strengths, concerns, suggestions)
  - Best-practice suggestions
  - Complexity analysis (time/space Big-O, cyclomatic estimate + static proxy)
  - Refactored code
- **Markdown report** with copy and one-click **download**.

---

## 🚀 Quick start

### 1. Clone and install

```bash
git clone https://github.com/brisinger23/AI-Code-Reviewer-Pro.git
cd AI-Code-Reviewer-Pro
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-...
```

Or export it directly:

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### 3. Run

```bash
python app.py
```

Open the printed local URL (default `http://localhost:7860`).

---

## ⚙️ Configuration

| Variable             | Default        | Description                              |
| -------------------- | -------------- | ---------------------------------------- |
| `OPENAI_API_KEY`     | _(required)_   | Your OpenAI API key.                     |
| `OPENAI_MODEL`       | `gpt-4o`       | Model used for reviews.                  |
| `GRADIO_SERVER_NAME` | `0.0.0.0`      | Host interface to bind.                  |
| `GRADIO_SERVER_PORT` | `7860`         | Port to serve on.                        |

---

## 🧱 Project structure

```
AI-Code-Reviewer-Pro/
├── app.py            # Gradio UI and callbacks
├── reviewer.py       # Review engine (OpenAI Responses API)
├── prompts.py        # Prompt engineering + JSON contract
├── utils.py          # Catalogs, metrics, Markdown rendering
├── theme.css         # Dark responsive theme
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
└── assets/           # Logo and generated reports
```

## 🏗️ How it works

1. `prompts.py` builds a strict system + user prompt, including a JSON schema
   the model must satisfy and a mode-specific review lens.
2. `reviewer.py` calls the OpenAI Responses API, extracts the JSON, and
   normalizes it so every field is always present. It also computes lightweight,
   dependency-free static metrics locally.
3. `app.py` renders the structured result into a tabbed, dark UI and a
   downloadable Markdown report.

---

## 🌐 Deploy (free)

### Render (recommended — one click)

This repo ships a [`render.yaml`](render.yaml) Blueprint.

1. Go to **https://dashboard.render.com/blueprints** → **New Blueprint Instance**.
2. Connect this GitHub repo (`brisinger23/AI-Code-Reviewer-Pro`).
3. Render reads `render.yaml` and provisions a free web service.
4. In the service's **Environment**, set `OPENAI_API_KEY` to your key and click
   **Save** (this triggers a deploy). `OPENAI_MODEL` defaults to `gpt-4o-mini`.

> The free plan sleeps after inactivity and cold-starts on the next visit.

### Docker (Koyeb, Fly.io, Cloud Run, Railway, or local)

A portable [`Dockerfile`](Dockerfile) is included:

```bash
docker build -t ai-code-reviewer-pro .
docker run -p 7860:7860 -e OPENAI_API_KEY=sk-your-key ai-code-reviewer-pro
```

The app binds to `$PORT` when the host provides one, so it works on any
container platform out of the box.

### Hugging Face Spaces

The repo is also Spaces-ready (see the YAML header above). Note that hosting a
**Gradio** Space on HF's free CPU tier currently requires a PRO subscription;
create the Space, push this repo, and set `OPENAI_API_KEY` as a **Space secret**.

---

## 📝 License

Released under the [MIT License](#).
