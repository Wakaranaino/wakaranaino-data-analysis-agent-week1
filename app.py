import gradio as gr
import requests
import os
import io
import contextlib
import matplotlib.pyplot as plt
from PIL import Image

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def extract_python_code(raw_text):
    raw_text = raw_text.strip()

    if "```python" in raw_text:
        return raw_text.split("```python", 1)[1].split("```", 1)[0].strip()

    if "```" in raw_text:
        return raw_text.split("```", 1)[1].split("```", 1)[0].strip()

    return raw_text

def generate_code(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

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

Use only these libraries when needed:
pandas, matplotlib, yfinance
"""

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    return result["choices"][0]["message"]["content"]

def repair_code(prompt, bad_code, error_message):
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

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
"""

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You fix Python code."},
            {"role": "user", "content": repair_prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    return extract_python_code(result["choices"][0]["message"]["content"])

def interpret_result(prompt, code, execution_output, status):
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

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

Write a short plain-English interpretation for the user.

RULES:
- Be concise
- If the code was fixed on retry, explicitly mention that the original code failed and was corrected
- If a column name was corrected, mention that clearly
- Explain the result in natural language
- Do not mention internal APIs or technical implementation details
"""

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You explain data analysis results clearly and briefly."},
            {"role": "user", "content": interpretation_prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    return result["choices"][0]["message"]["content"]

def run_agent(prompt):
    raw_code = generate_code(prompt)
    code = extract_python_code(raw_code)

    output_buffer = io.StringIO()
    img = None
    status = "Executed on first try"

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, {})

    except Exception as e:
        error_message = str(e)
        status = "Fixed and executed on retry"

        try:
            fixed_code = repair_code(prompt, code, error_message)

            output_buffer = io.StringIO()
            img = None

            with contextlib.redirect_stdout(output_buffer):
                exec(fixed_code, {})

            code = fixed_code

        except Exception as e2:
            plt.close("all")
            return code, f"Execution error (after retry): {str(e2)}", "Retry failed", "The app attempted to fix the code automatically, but the repaired version still failed.", None

    if plt.get_fignums():
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        img = Image.open(buf)
        plt.close("all")

    execution_output = output_buffer.getvalue()
    if not execution_output.strip() and img is None:
        execution_output = "Code executed successfully, but nothing was printed."
    elif not execution_output.strip():
        execution_output = "Plot generated successfully."

    interpretation = interpret_result(prompt, code, execution_output, status)

    return code, execution_output, status, interpretation, img

demo = gr.Interface(
    fn=run_agent,
    inputs=gr.Textbox(label="Prompt", lines=2),
    outputs=[
    gr.Code(label="Generated Python Code", language="python"),
    gr.Textbox(label="Execution Output", lines=12),
    gr.Textbox(label="Run Status"),
    gr.Textbox(label="Interpretation", lines=6),
    gr.Image(label="Plot Output")
    ],
    title="AI Data Analysis Agent"
)

demo.launch()