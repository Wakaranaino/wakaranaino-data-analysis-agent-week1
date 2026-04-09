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
You are a Python code generator.

STRICT RULES:
- Return ONLY executable Python code
- Do NOT include markdown fences
- Do NOT include explanations, notes, or labels
- Do NOT include any text before or after the code
- Print numerical/text results clearly
- For plots, use matplotlib
- It is OK to call plt.show()
- Always print results in clean human-readable format (no pandas dtype output)

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

IMPORTANT:
- If a column name does not exist, replace it with the closest valid column name.
- Do not keep invalid column names from the user request.
- For yfinance stock data, common columns include: Open, High, Low, Close, Adj Close, Volume.
- Return ONLY corrected executable Python code.
- Always print results in clean human-readable format (no pandas dtype output)
- No markdown.
- No explanation.
- No extra text.
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
            return code, f"Execution error (after retry): {str(e2)}", "Retry failed", None

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

    return code, execution_output, status, img

demo = gr.Interface(
    fn=run_agent,
    inputs=gr.Textbox(label="Prompt", lines=2),
    outputs=[
    gr.Code(label="Generated Python Code", language="python"),
    gr.Textbox(label="Execution Output", lines=12),
    gr.Textbox(label="Run Status"),
    gr.Image(label="Plot Output")
    ],
    title="AI Data Analysis Agent"
)

demo.launch()