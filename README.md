# 🚀 AI-Powered GitLab Merge Request Reviewer

This script automates the code review process for GitLab Merge Requests (MRs). It fetches changed files, analyzes the `diff` (with full file context), and uses Large Language Models (LLMs) to detect bugs, security vulnerabilities, and code style issues.

It supports **Local LLMs** (via Ollama/DeepSeek) for privacy and cost-savings, as well as **Cloud LLMs** (Google Gemini) for higher performance.

## ✨ Features

- **Hybrid AI Support:** Run completely offline using **Ollama** (default) or use **Google Gemini 1.5 Pro**.
- **Context-Aware Analysis:** Provides the LLM with both the *Diff* (what changed) and the *Full File Content* (context for imports/variables).
- **Smart Filtering:** Automatically ignores deleted files and focuses on code extensions (`.py`, `.js`, `.go`, `.cpp`, etc.).
- **Structured Reporting:** Generates a `mr_review_report.md` file and outputs a clear **PASSED** or **FAILED** status.
- **Secure:** Supports environment variables for sensitive tokens.

## 🛠️ Prerequisites

- **Python 3.9+**
- **GitLab Access:** A Personal Access Token (PAT) with `read_api` or `read_repository` scope.
- **Ollama (Local Mode):** If using local models, ensure [Ollama](https://ollama.com/) is installed and running [YouTube Video Instructions](https://www.youtube.com/watch?v=cEv1ucRDoa0).

## 📦 Installation

1. **Clone the repository** (or save the script as `mr_reviewer.py`).
2. **Install dependencies**:
   
   ```bash
   pip install argparse requests langchain langchain-core langchain-ollama langchain-google-genai pydantic
   
## ⚙️ Environment Setup

Before running the script, ensure you have the necessary API tokens. You can set them as environment variables or enter them interactively when prompted.

### 1. GitLab Access (Required)
You need a Personal Access Token (PAT) to fetch Merge Request data.
* **Scope required:** `read_api` or `read_repository`.

```bash
# Linux/macOS
export GITLAB_PRIVATE_TOKEN="glpat-xxxxxxxxxxxxxxxxx"

# Windows (PowerShell)
$env:GITLAB_PRIVATE_TOKEN="glpat-xxxxxxxxxxxxxxxxx"
```

## 📝 Arguments Description

The script accepts several command-line arguments to configure the GitLab connection, the LLM backend, and file filtering.

| Argument | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `--gitlab-url` | ✅ Yes | *None* | The base URL of your GitLab instance (e.g., `https://gitlab.company.com`). |
| `--project-id` | ✅ Yes | *None* | The Project ID (integer) or URL-encoded Namespace/Project path. |
| `--mr-id` | ✅ Yes | *None* | The internal ID (IID) of the Merge Request you want to review. |
| `--local` | No | `True` | Set to `True` to use local Ollama. Set to `False` to use Google Gemini. |
| `--model` | No | `deepseek-r1:32b` | The specific model name to use (e.g., `llama3`, `gemini-2.5-flash`). |
| `--model-url` | No | `http://localhost:11434` | The base URL for the local Ollama API (useful for Docker/remote setups). |
| `--extensions` | No | `.py .js .ts ...` | Space-separated list of file extensions to include in the review. |