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


def format_history_for_prompt(history=None) -> str:
    if not history:
        return "No prior conversation history."

    successful_turns = [turn for turn in history if turn.get("success") is True]

    if not successful_turns:
        return "No prior successful conversation history."

    formatted_turns = []
    for turn in successful_turns[-3:]:
        user_text = turn.get("user", "").strip()
        assistant_text = turn.get("assistant", "").strip()
        formatted_turns.append(f"User: {user_text}\nAssistant: {assistant_text}")

    return "\n\n".join(formatted_turns)


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


def generate_code(prompt: str, history=None) -> str:
    history_text = format_history_for_prompt(history)

    system_prompt = """
You generate executable Python code for data analysis.
Return ONLY Python code.

Rules:
- No markdown or explanations
- Use only: pandas, matplotlib, yfinance, scipy, numpy
- Prefer simple, direct, robust code
- Print results clearly
- Inspect available columns before selecting fields
- Match the user's intended meaning, not just exact wording
- Do not keep invalid or misspelled field names
- For yfinance, use 'Close' by default and never assume 'Adj Close' exists
- If no timeframe is given, use a recent default period
- If formatting with :.2f, first convert Series/ndarray values to a scalar (e.g. .item(), float(), or .iloc[0])
- Use matplotlib for plots and call plt.show()
"""

    user_prompt = f"""
Conversation history:
{history_text}

Current user request:
{prompt}
"""

    return _post_chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])


def repair_code(prompt: str, bad_code: str, error_message: str, history=None) -> str:
    history_text = format_history_for_prompt(history)

    repair_prompt = f"""
Conversation history:
{history_text}

Current user request:
{prompt}

Failed code:
{bad_code}

Execution error:
{error_message}

Fix the code.

Rules:
- Return ONLY corrected Python code
- No markdown or explanations
- Prefer simple, robust code
- Use the error as the main signal; if it mentions Series.__format__ or ndarray.__format__, convert the value to a scalar before printing
- Inspect available columns before selecting fields
- Replace invalid field names with the closest valid one when justified
- Do not preserve broken or misspelled names
- For yfinance, use 'Close' by default and never assume 'Adj Close' exists
- If formatting with :.2f, first convert Series/ndarray values to a scalar (e.g. .item(), float(), or .iloc[0])
- If the error mentions Adj Close, switch to Close
- Avoid unnecessary imports or complex logic
"""

    raw = _post_chat([
        {"role": "system", "content": "You fix Python code."},
        {"role": "user", "content": repair_prompt}
    ])
    return extract_python_code(raw)


def interpret_result(prompt: str, code: str, execution_output: str, status: str, history=None) -> str:

    interpretation_prompt = f"""
Current user request:
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
- Do not include code
- Do not include debugging details
- Do not repeat raw output verbatim
"""

    return _post_chat([
        {"role": "system", "content": "You explain data analysis results clearly and briefly."},
        {"role": "user", "content": interpretation_prompt}
    ])

def explain_code(code: str) -> str:
    code = (code or "").strip()

    if not code:
        return "No code is available to explain yet."

    explanation_prompt = f"""
Explain the following Python code in plain English.

Code:
{code}

Rules:
- Use clear, simple English
- Be structured and easy to scan
- Do not rewrite the full code
- Do not use markdown code fences
- Keep it concise but useful
- Use this structure:

Purpose:
- Briefly explain what the code is trying to do

Libraries used:
- List the main libraries and what they are used for

Step-by-step:
1. Explain the first main step
2. Explain the next main step
3. Continue only as needed

Output:
- Briefly explain what the user should expect to see
"""

    return _post_chat([
        {"role": "system", "content": "You explain Python code clearly for non-expert users."},
        {"role": "user", "content": explanation_prompt}
    ])