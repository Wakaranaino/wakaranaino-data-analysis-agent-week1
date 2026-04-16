import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"
API_TIMEOUT = 30


def extract_python_code(raw_text: str) -> str:
    raw_text = raw_text.strip()

    if "```python" in raw_text:
        return raw_text.split("```python", 1)[1].split("```", 1)[0].strip()

    if "```" in raw_text:
        return raw_text.split("```", 1)[1].split("```", 1)[0].strip()

    return raw_text


def _post_chat(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL_NAME,
        "messages": messages
    }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=data,
        timeout=API_TIMEOUT
    )
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]


def generate_code(prompt: str) -> str:
    system_prompt = """
You are a Python data analysis code generator.
Return ONLY executable Python code.
STRICT RULES:
- No markdown
- No explanations
- No text before or after the code
- Use only available libraries
- Prefer simple, robust code
- Prefer direct solutions over clever or highly abstract code
- Avoid unnecessary imports, wrappers, or transformations
- Always print results in clean human-readable format
- When working with tabular data, inspect column names before using ambiguous or user-provided field names
- Do not assume a column exists without checking or using a clearly justified mapping
- If a user-provided field name may be ambiguous or incorrect, inspect the available columns and use the closest valid field only when appropriate
- When possible, write code that is resilient to minor naming differences
- For plots, use matplotlib and call plt.show()
- If formatting a value with f-strings (e.g. :.2f), make sure the value is a scalar, not a pandas Series
- Convert Series results to scalar before formatting when needed (e.g. .item(), float(), or selecting one value)
- Interpret the user's intended meaning, not just the exact field wording
- If a requested field name does not exactly exist, map it to the closest valid field based on available columns and context
- Do not preserve invalid or misspelled field names just for consistency with the user's wording
- If no timeframe is specified, default to a recent period instead of inventing arbitrary historical dates
Use only these libraries when needed:
pandas, matplotlib, yfinance
"""

    return _post_chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ])


def repair_code(prompt: str, bad_code: str, error_message: str) -> str:
    repair_prompt = f"""
The following Python code failed.
User request:
{prompt}
Failed code:
{bad_code}
Execution error:
{error_message}
Fix the code so it runs correctly.
RULES:
- Return ONLY corrected executable Python code
- No markdown
- No explanations
- Prefer simple, robust code
- Use the execution error as the primary signal to identify the problem
- If a variable or column name is invalid:
  - inspect the available structure (e.g., data.columns)
  - use the closest valid field when justified
- Do not preserve broken names from the original code
- If uncertainty remains, write code that safely checks before accessing data
- Avoid unnecessary imports or complex logic
- Always print results in clean human-readable format
- If formatting a value with f-strings (e.g. :.2f), make sure the value is a scalar, not a pandas Series
- Convert Series results to scalar before formatting when needed (e.g. .item(), float(), or selecting one value)
- If the error mentions Series.__format__, convert the Series to a scalar before formatting
- Use the execution error and available data structure to infer the user's intended meaning
- If a requested field name is invalid, replace it with the closest valid field based on meaning, not literal wording
- Do not preserve broken or misspelled names for consistency with the original request
- If no timeframe was specified, prefer a recent default period rather than arbitrary hard-coded dates
"""

    raw = _post_chat([
        {"role": "system", "content": "You fix Python code."},
        {"role": "user", "content": repair_prompt}
    ])
    return extract_python_code(raw)


def interpret_result(prompt: str, code: str, execution_output: str, status: str) -> str:
    interpretation_prompt = f"""
You are a data analysis assistant.
User request:
{prompt}
Generated Python code:
{code}
Execution output:
{execution_output}
Run status:
{status}
Write a clear, concise interpretation for the user.
RULES:
- Start with the final result and what it means (this is the main focus)
- If applicable, briefly explain what data was used (e.g., which column or metric)
- If user wording was mapped to a different actual column, clearly state the mapping:
  Example: "Interpreted 'closingprice' as 'Close'"
- Keep explanations short and natural (2–4 sentences total)
- If the code required fixing:
  - Mention it briefly at the END as a short note
  - Do NOT start with the error
  - Do NOT over-explain the debugging process
- If the run failed completely:
  - Explain the reason clearly and what likely caused it
- Do NOT mention internal APIs, retries, or system mechanics
- Do NOT repeat raw outputs verbatim
"""

    return _post_chat([
        {"role": "system", "content": "You explain data analysis results clearly and briefly."},
        {"role": "user", "content": interpretation_prompt}
    ])