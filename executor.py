import io
import re
import traceback
import multiprocessing as mp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from llm import generate_code, repair_code, interpret_result, extract_python_code, verify_code_semantics

EXEC_TIMEOUT = 15
MAX_ATTEMPTS = 3  # 1 original + 2 retries

BLOCKED_RULES = [
    {
        "patterns": [
            r"\bos\.(remove|unlink|rmdir|system|popen)\b",
            r"\bshutil\.(rmtree|move|copy)\b",
            r"\b(delete|remove|overwrite|destroy)\b",
            r"\bopen\s*\(",
            r"\bwith\s+open\s*\("
        ],
        "message": "This prompt appears to request file-system access or file modification, which is not allowed. Please limit your request to safe data analysis tasks."
    },
    {
        "patterns": [
            r"\bsubprocess\b",
            r"\b(import|from)\s+subprocess\b",
            r"\b(shell command|bash|terminal command|cmd)\b"
        ],
        "message": "This prompt appears to request shell or subprocess execution, which is not allowed. Please ask for analysis, plotting, or statistics instead."
    },
    {
        "patterns": [
            r"\b(secret|token|password|api key|environment variable|env var)\b",
            r"\b__import__\b"
        ],
        "message": "This prompt appears to request secrets, credentials, or environment information, which is not allowed."
    },
    {
        "patterns": [
            r"\b(scan ports|port scan|hack|exploit|malware|ransomware)\b",
            r"\bimport\s+socket\b"
        ],
        "message": "This prompt appears to request harmful or security-related operations, which are not supported in this app."
    },
]


def validate_prompt(prompt: str):
    prompt_lower = prompt.lower().strip()

    if not prompt_lower:
        return False, "Please enter a prompt."

    for rule in BLOCKED_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, prompt_lower):
                return False, rule["message"]

    return True, ""


def _execute_code_worker(code: str, queue: mp.Queue):
    import io
    import contextlib
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, {"__builtins__": __builtins__})

        img_bytes = None
        if plt.get_fignums():
            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            img_bytes = buf.getvalue()
            plt.close("all")

        queue.put({
            "success": True,
            "output": output_buffer.getvalue(),
            "image_bytes": img_bytes,
            "error": None
        })

    except Exception:
        plt.close("all")
        queue.put({
            "success": False,
            "output": output_buffer.getvalue(),
            "image_bytes": None,
            "error": traceback.format_exc()
        })


def execute_code_with_timeout(code: str, timeout: int = EXEC_TIMEOUT):
    queue = mp.Queue()
    process = mp.Process(target=_execute_code_worker, args=(code, queue))
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "success": False,
            "output": "",
            "image_bytes": None,
            "error": f"Execution timed out after {timeout} seconds."
        }

    if queue.empty():
        return {
            "success": False,
            "output": "",
            "image_bytes": None,
            "error": "Execution failed without returning any result."
        }

    return queue.get()


def run_agent(prompt: str):
    is_valid, validation_message = validate_prompt(prompt)
    if not is_valid:
        return (
            "",
            validation_message,
            "Blocked by input validation",
            "The request was blocked because it appears to ask for unsafe or unsupported operations.",
            None
        )

    raw_code = generate_code(prompt)
    code = extract_python_code(raw_code)

    # Semantic verification before execution
    semantic_result = verify_code_semantics(prompt, code)
    if semantic_result != "PASS":
        code = repair_code(prompt, code, semantic_result)

    attempt = 0
    last_error = None

    while attempt < MAX_ATTEMPTS:
        result = execute_code_with_timeout(code, EXEC_TIMEOUT)

        if result["success"]:
            if attempt == 0:
                status = "Executed on first try"
            else:
                status = f"Fixed and executed on retry (attempt {attempt})"
            break

        last_error = result["error"]
        attempt += 1

        if attempt >= MAX_ATTEMPTS:
            return (
                code,
                f"Execution error (after {attempt-1} retries): {last_error}",
                "Retry failed",
                f"The system attempted to fix the code multiple times but failed. Final error: {last_error}",
                None
            )

        code = repair_code(prompt, code, last_error)

    img = None
    if result["image_bytes"] is not None:
        img = Image.open(io.BytesIO(result["image_bytes"]))

    execution_output = result["output"]

    if not execution_output.strip() and img is None:
        execution_output = "Code executed successfully, but nothing was printed."
    elif not execution_output.strip():
        execution_output = "Plot generated successfully."

    interpretation = interpret_result(prompt, code, execution_output, status)

    return code, execution_output, status, interpretation, img