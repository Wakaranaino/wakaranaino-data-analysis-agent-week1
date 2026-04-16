import io
import contextlib
import matplotlib.pyplot as plt
from PIL import Image

from llm import generate_code, repair_code, interpret_result, extract_python_code


def run_agent(prompt: str):
    raw_code = generate_code(prompt)
    code = extract_python_code(raw_code)

    max_attempts = 3  # 1 original + 2 retries
    attempt = 0
    last_error = None

    while attempt < max_attempts:
        output_buffer = io.StringIO()
        img = None

        try:
            with contextlib.redirect_stdout(output_buffer):
                exec(code, {"__builtins__": __builtins__})

            if attempt == 0:
                status = "Executed on first try"
            else:
                status = f"Fixed and executed on retry (attempt {attempt})"

            break

        except Exception as e:
            last_error = str(e)
            attempt += 1

            if attempt >= max_attempts:
                plt.close("all")
                return (
                    code,
                    f"Execution error (after {attempt-1} retries): {last_error}",
                    "Retry failed",
                    f"The system attempted to fix the code multiple times but failed. Final error: {last_error}",
                    None
                )

            code = repair_code(prompt, code, last_error)

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