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
- **Ollama (Local Mode):** If using local models, ensure [Ollama](https://ollama.com/) is installed and running.

## 📦 Installation

1. **Clone the repository** (or save the script as `mr_reviewer.py`).
2. **Install dependencies**:
   
   ```bash
   pip install argparse requests langchain langchain-core langchain-ollama langchain-google-genai pydantic