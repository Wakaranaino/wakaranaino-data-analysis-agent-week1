import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL_SIMPLE = "meta-llama/llama-4-scout-17b-16e-instruct"
MODEL_COMPLEX = "meta-llama/llama-4-scout-17b-16e-instruct"  # swap to "llama-3.1-70b-versatile" when ready to test

API_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Prompt templates — BASE and COMPLEX are the same length by design.
# COMPLEX swaps out generic rules and replaces them with structural ones.
# ---------------------------------------------------------------------------

_BASE_SYSTEM_PROMPT = """You generate executable Python code for data analysis.
Return ONLY Python code. No markdown, no explanations.

Rules:
- Use only: pandas, matplotlib, yfinance, scipy, numpy
- Use ticker.history(period=...) per ticker; never yf.download([list])
- Use 'Close' only, never 'Adj Close'
- Default period: 3mo if not specified
- Convert to scalar before :.4f formatting: float(val) or val.item()
- Print results with clear labels
- Call plt.tight_layout() and plt.show()"""

_COMPLEX_SYSTEM_PROMPT = """You generate executable Python code for data analysis.
Return ONLY Python code. No markdown, no explanations.

Start with a plan comment block, then follow it exactly:
# Plan:
# Step 1: <what you will do>
# Step 2: <what you will do>
# ...

Structure rules:
- Download each ticker in its own block using ticker.history()
- Use 'Close' only, never 'Adj Close'
- Align or merge data only after each ticker is downloaded and verified
- Compute statistics or returns after alignment
- Run any statistical test last, after all data is ready
- Convert to scalar before :.4f formatting: float(val) or val.item()
- For monthly resampling use resample('ME'), not 'M'
- Print all results with clear labels; call plt.tight_layout() and plt.show()"""

# Repair prompts follow the same swap logic
_BASE_REPAIR_RULES = """Rules:
- Return ONLY corrected Python code. No markdown.
- Focus on the error message as the primary signal
- Use 'Close' only; if error mentions Adj Close, switch to Close
- If error mentions Series.__format__ or ndarray, convert to scalar before formatting
- Use ticker.history() per ticker separately
- Keep the fix minimal — change only what the error requires"""

_COMPLEX_REPAIR_RULES = """Rules:
- Return ONLY corrected Python code. No markdown.
- Re-read the plan comments and check each step matches the code below it
- If a step is missing or out of order, rewrite that section
- Use 'Close' only; if error mentions Adj Close, switch to Close
- If error mentions Series.__format__ or ndarray, convert to scalar before formatting
- If columns are missing after a merge, inspect both DataFrames before merging
- For monthly resampling use resample('ME'), not 'M'
- Keep the fix minimal — change only what the error requires"""


# ---------------------------------------------------------------------------
# Task classifier
# ---------------------------------------------------------------------------

_COMPLEX_SIGNALS = [
    "compare", "vs", "versus", "both", "t-test", "ttest",
    "correlation", "multiple", "between", "together",
    "side by side", "same chart", "overlay"
]

def classify_task(prompt: str) -> str:
    """Returns 'complex' if the prompt involves multi-step or multi-ticker work."""
    prompt_lower = prompt.lower()
    hits = sum(1 for s in _COMPLEX_SIGNALS if s in prompt_lower)
    return "complex" if hits >= 2 else "simple"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def extract_python_code(raw_text: str) -> str:
    raw_text = raw_text.strip()
    if "```python" in raw_text:
        return raw_text.split("```python", 1)[1].split("```", 1)[0].strip()
    if "```" in raw_text:
        return raw_text.split("```", 1)[1].split("```", 1)[0].strip()
    return raw_text


def format_history_for_prompt(history=None) -> str:
    if not history:
        return "No prior conversation history."
    successful_turns = [t for t in history if t.get("success") is True]
    if not successful_turns:
        return "No prior successful conversation history."
    formatted_turns = []
    for turn in successful_turns[-3:]:
        user_text = turn.get("user", "").strip()
        assistant_text = turn.get("assistant", "").strip()
        formatted_turns.append(f"User: {user_text}\nAssistant: {assistant_text}")
    return "\n\n".join(formatted_turns)


def _post_chat(messages, model=MODEL_SIMPLE):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {"model": model, "messages": messages}
    response = requests.post(GROQ_URL, headers=headers, json=data, timeout=API_TIMEOUT)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Core LLM functions
# ---------------------------------------------------------------------------

def generate_code(prompt: str, history=None) -> str:
    task_type = classify_task(prompt)
    history_text = format_history_for_prompt(history)
    model = MODEL_COMPLEX if task_type == "complex" else MODEL_SIMPLE

    system_prompt = _COMPLEX_SYSTEM_PROMPT if task_type == "complex" else _BASE_SYSTEM_PROMPT

    user_prompt = f"""Conversation history:
{history_text}

Current user request:
{prompt}"""

    return _post_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=model
    )


def generate_csv_code(prompt: str, dataset_summary: dict | None = None, history=None) -> str:
    history_text = format_history_for_prompt(history)
    summary = dataset_summary or {}
    missing_counts = summary.get("missing_counts", {}) or {}
    missing_top_k = sorted(
        [(k, int(v)) for k, v in missing_counts.items() if int(v) > 0],
        key=lambda x: x[1],
        reverse=True
    )[:8]
    summary_text = (
        f"- File: {summary.get('file_name', 'uploaded.csv')}\n"
        f"- Rows: {summary.get('row_count', 0)}\n"
        f"- Columns: {summary.get('column_count', 0)}\n"
        f"- Numeric columns: {summary.get('numeric_columns', [])}\n"
        f"- Categorical columns: {summary.get('categorical_columns', [])}\n"
        f"- Categorical samples: {summary.get('categorical_samples', {})}\n"
        f"- Missing counts (top): {missing_top_k}\n"
    )

    system_prompt = """You generate executable Python code for file-based data analysis.
Return ONLY Python code. No markdown or explanations.

Context:
- A pandas DataFrame named df is already loaded.

Rules:
- Use only pandas, numpy, scipy, matplotlib.
- Use df directly. Do not read files unless explicitly requested.
- Do not fetch external/network data unless explicitly requested.
- Follow user intent; infer reasonable defaults when request is underspecified.
- For text filters, normalize with: .astype(str).str.strip().str.lower().
- If you infer columns/groups, print a short "Assumptions Used" section.
- For statistical comparisons, print subgroup sizes before running tests.
- If plotting is requested, call plt.tight_layout() and plt.show()."""

    user_prompt = f"""Conversation history:
{history_text}

Dataset profile:
{summary_text}

Current user request:
{prompt}"""

    raw = _post_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=MODEL_SIMPLE
    )
    return extract_python_code(raw)


def repair_code(prompt: str, bad_code: str, error_message: str, history=None) -> str:
    task_type = classify_task(prompt)
    history_text = format_history_for_prompt(history)
    model = MODEL_COMPLEX if task_type == "complex" else MODEL_SIMPLE
    repair_rules = _COMPLEX_REPAIR_RULES if task_type == "complex" else _BASE_REPAIR_RULES

    repair_prompt = f"""Conversation history:
{history_text}

Current user request:
{prompt}

Failed code:
{bad_code}

Execution error:
{error_message}

Fix the code.

{repair_rules}"""

    raw = _post_chat(
        [
            {"role": "system", "content": "You fix Python code. Return ONLY corrected Python code."},
            {"role": "user", "content": repair_prompt}
        ],
        model=model
    )
    return extract_python_code(raw)


def repair_csv_code(
    prompt: str,
    bad_code: str,
    error_message: str,
    dataset_summary: dict | None = None,
    history=None
) -> str:
    history_text = format_history_for_prompt(history)
    summary = dataset_summary or {}
    summary_text = (
        f"- Numeric columns: {summary.get('numeric_columns', [])}\n"
        f"- Categorical columns: {summary.get('categorical_columns', [])}\n"
        f"- Categorical samples: {summary.get('categorical_samples', {})}\n"
    )

    repair_prompt = f"""Conversation history:
{history_text}

Dataset profile:
{summary_text}

Current user request:
{prompt}

Failed code:
{bad_code}

Execution/validation issue:
{error_message}

Fix rules:
- Keep intent unchanged.
- Keep fixes minimal and specific to the failure.
- Use df directly; no file/network I/O unless explicitly requested.
- If category filters are used, normalize labels robustly.
- For multi-column stats, ensure output orientation is valid and readable."""

    raw = _post_chat(
        [
            {"role": "system", "content": "You fix Python code for CSV dataframe analysis.\nReturn ONLY corrected Python code."},
            {"role": "user", "content": repair_prompt}
        ],
        model=MODEL_SIMPLE
    )
    return extract_python_code(raw)


def interpret_csv_result(prompt: str, execution_output: str, status: str) -> str:
    interpretation_prompt = f"""User request:
{prompt}

Execution output:
{execution_output}

Run status:
{status}

Write 2-4 sentences:
- Summarize the result directly.
- Mention key metric/test outcome.
- If assumptions were inferred (columns/groups/labels), mention them briefly.
- Do not repeat raw output or code."""

    return _post_chat([
        {"role": "system", "content": "You explain analysis results clearly and briefly."},
        {"role": "user", "content": interpretation_prompt}
    ])


def interpret_result(prompt: str, code: str, execution_output: str, status: str, history=None) -> str:
    interpretation_prompt = f"""Current user request:
{prompt}

Execution output:
{execution_output}

Run status:
{status}

Write a short user-facing interpretation.

Rules:
- 2 to 4 sentences only
- Focus on the final result
- Mention the data/metric briefly if helpful
- If the run needed fixing, mention that briefly at the end
- Do not include code or debugging details
- Do not repeat raw output verbatim"""

    return _post_chat([
        {"role": "system", "content": "You explain data analysis results clearly and briefly."},
        {"role": "user", "content": interpretation_prompt}
    ])


def explain_code(code: str) -> str:
    code = (code or "").strip()
    if not code:
        return "No code is available to explain yet."

    lines = code.splitlines()
    numbered_code = "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))

    explanation_prompt = f"""Explain this numbered Python code for a beginner.

Code:
{numbered_code}

Return plain text only.

Format:

Purpose:
1 short summary.

Libraries used:
library - purpose

Code walkthrough:
Use numbered items.
Start with Line X: or Lines X-Y:
Use the shown line numbers.
Explain what the code does.
Do not repeat the comments, explain the code with accessble language 

Output:
1 short sentence.

Keep concise. No markdown symbols."""

    return _post_chat([
        {"role": "system", "content": "You explain Python code clearly in plain text."},
        {"role": "user", "content": explanation_prompt}
    ])



