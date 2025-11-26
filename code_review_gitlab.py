import argparse
import getpass
import os
import re
import urllib.parse
from typing import List, Optional, Dict, Any

import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from langchain_ollama import ChatOllama
except ImportError:
    from langchain_community.chat_models import ChatOllama

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel


def setup_environment(use_local: bool):
    """Sets up API keys and Tokens."""
    # 1. LLM Setup
    if not use_local:
        if not os.environ.get("GOOGLE_API_KEY"):
            print("🔑 Google API Key not found.")
            os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter Google AI API Key: ")

    # 2. GitLab Setup
    if not os.environ.get("GITLAB_PRIVATE_TOKEN"):
        print("🔒 GitLab Private Token not found (Scope required: read_api or read_repository).")
        os.environ["GITLAB_PRIVATE_TOKEN"] = getpass.getpass("Enter GitLab Private Token: ")


def get_gitlab_headers():
    return {"PRIVATE-TOKEN": os.environ["GITLAB_PRIVATE_TOKEN"]}


def fetch_mr_changes(gitlab_url: str, project_id: str, mr_iid: str) -> Dict[str, Any]:
    """Fetches the MR details including the list of changes."""
    # Encode project ID if it contains slashes
    safe_id = urllib.parse.quote(str(project_id), safe='')

    # Ensure URL doesn't end with slash to avoid double slashes
    base_url = gitlab_url.rstrip('/')

    url = f"{base_url}/api/v4/projects/{safe_id}/merge_requests/{mr_iid}/changes"
    print(f"📡 Fetching MR metadata from: {url}")

    response = requests.get(url, headers=get_gitlab_headers())
    if response.status_code != 200:
        raise Exception(f"Failed to fetch MR: {response.status_code} - {response.text}")

    return response.json()


def fetch_raw_file(gitlab_url: str, project_id: str, file_path: str, ref: str) -> str:
    """Fetches the raw content of a specific file at a specific branch/ref."""
    safe_id = urllib.parse.quote(str(project_id), safe='')
    safe_path = urllib.parse.quote(file_path, safe='')
    base_url = gitlab_url.rstrip('/')

    url = f"{base_url}/api/v4/projects/{safe_id}/repository/files/{safe_path}/raw?ref={ref}"

    response = requests.get(url, headers=get_gitlab_headers())
    if response.status_code != 200:
        return f"[Error fetching file content: {response.status_code}]"

    return response.text


def load_merge_request_data(gitlab_url: str, project_id: str, mr_id: str, file_filter: Optional[List[str]] = None) -> \
        List[Document]:
    """
    Loads documents specifically for a Merge Request Review.
    Combines the Diff + Full Content for context.
    """
    mr_data = fetch_mr_changes(gitlab_url, project_id, mr_id)
    source_branch = mr_data.get('source_branch')
    changes = mr_data.get('changes', [])

    print(f"✅ Found {len(changes)} changed files in MR !{mr_id}")

    docs = []

    for change in changes:
        file_path = change['new_path']

        # Apply Extension Filter
        if file_filter and not any(file_path.endswith(ext) for ext in file_filter):
            continue

        # Skip deleted files
        if change['deleted_file']:
            continue

        print(f"   ⬇️  Loading: {file_path}")

        # 1. Get the Diff (Changes)
        diff_content = change['diff']

        # 2. Get the Full Content (Context)
        full_content = fetch_raw_file(gitlab_url, project_id, file_path, source_branch)

        # 3. Construct the Document
        # We present both to the LLM so it sees the change AND where it lives.
        combined_content = (
            f"FILENAME: {file_path}\n"
            f"--- BEGIN DIFF (CHANGES) ---\n{diff_content}\n--- END DIFF ---\n\n"
            # line below could be commented out because it might take more time on weak models (below 32b)
            f"--- BEGIN FULL FILE CONTENT (CONTEXT) ---\n{full_content}\n--- END FULL FILE CONTENT ---\n"
        )

        docs.append(Document(page_content=combined_content, metadata={"source": file_path}))

    return docs


def format_documents_for_context(docs: List[Document]) -> str:
    """Simple joiner since the documents already contain headers."""
    return "\n".join([d.page_content for d in docs])


class ReviewOutcome(BaseModel):
    is_ok: bool
    report: str


def get_llm(use_local: bool, model_name: str, model_url: Optional[str] = None):
    if use_local:
        print(f"🦙 Using local model: {model_name}")

        params = {
            "model": model_name,
            "temperature": 0.2,
            "num_ctx": 16384  # modify if needed, context to store memory about, number of tokens
        }

        # Add custom base_url if provided (e.g., http://localhost:11434)
        if model_url:
            print(f"   📍 Connecting to custom Ollama URL: {model_url}")
            params["base_url"] = model_url

        return ChatOllama(**params)
    else:
        print("☁️  Using Google Gemini 1.5 Pro")
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.2, convert_system_message_to_human=True)


def parse_markdown_response(ai_message) -> ReviewOutcome:
    text = ai_message.content
    match = re.search(r"FINAL_STATUS:\s*(PASSED|FAILED)", text, re.IGNORECASE)
    if match:
        status_str = match.group(1).upper()
        is_ok = (status_str == "PASSED")
        report_content = text.replace(match.group(0), "").strip()
    else:
        if "CRITICAL BUG" in text.upper() or "SECURITY VULNERABILITY" in text.upper():
            is_ok = False
        else:
            is_ok = True
        report_content = text
    return ReviewOutcome(is_ok=is_ok, report=report_content)


def run_mr_review(args):
    setup_environment(args.local)

    llm = get_llm(args.local, args.model, args.model_url)

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a Principal Software Engineer. You are reviewing a GitLab Merge Request."),
        ("human", "Here are the files modified in this Merge Request:\n\n{context}\n\n"
                  "For each file, I have provided the DIFF (what changed) and the FULL CONTENT (for context).\n"
                  "Please review strictly the **CHANGES** (the Diff), using the Full Content only to understand variable definitions or imports.\n\n"
                  "Focus on:\n"
                  "1. **Bugs introduced by the changes**\n"
                  "2. **Security vulnerabilities**\n"
                  "3. **Code Style/Maintainability** of the new code\n\n"
                  "IMPORTANT: Cite specific filenames and line numbers.\n"
                  "Format as Markdown.\n"
                  "End with:\nFINAL_STATUS: PASSED\nOR\nFINAL_STATUS: FAILED")
    ])

    target_extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".cpp"]

    print(f"🚀 Starting Review for MR !{args.mr_id} in project {args.project_id}")

    documents = load_merge_request_data(
        args.gitlab_url,
        args.project_id,
        args.mr_id,
        file_filter=target_extensions
    )

    if not documents:
        print("❌ No matching files found in this MR.")
        return

    mr_context = format_documents_for_context(documents)
    print(f"📊 Context size: ~{int(len(mr_context) / 4)} tokens")

    chain = prompt_template | llm | RunnableLambda(parse_markdown_response)

    print("🧠 Analyzing MR changes...")
    try:
        result = chain.invoke({"context": mr_context})
        print(f"\n📢 MR Review Status: {'✅ PASSED' if result.is_ok else '❌ FAILED'}")
        print("\n" + "=" * 30 + " REPORT " + "=" * 30 + "\n")
        print(result.report)

        with open("mr_review_report.md", "w", encoding='utf-8') as f:
            f.write(result.report)

    except Exception as e:
        print(f"❌ Error during analysis: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitLab Merge Request Reviewer with LLMs")

    # GitLab Args
    parser.add_argument("--gitlab-url", required=True, help="Base URL of GitLab instance")
    parser.add_argument("--project-id", required=True, help="Project ID or Namespace/Project")
    parser.add_argument("--mr-id", required=True, help="Merge Request IID")

    # Model Args
    parser.add_argument("--local", default=True, help="Use local LLM (Ollama)")
    parser.add_argument("--model", default="deepseek-r1:32b",
                        help="Model name (e.g., llama3, mistral, gemini-2.5-flash)")
    parser.add_argument("--model-url", default="http://localhost:11434",
                        help="Base URL for local model (e.g., http://localhost:11434)")

    args = parser.parse_args()

    run_mr_review(args)
