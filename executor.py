import io
import re
import traceback
import multiprocessing as mp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from llm import (
    generate_code,
    repair_code,
    interpret_result,
    extract_python_code,
)

EXEC_TIMEOUT = 35
MAX_ATTEMPTS = 3  # 1 original + 2 retry

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


def validate_code(code: str):
    code_text = (code or "").strip()

    if not code_text:
        return False, "Code box is empty. Please generate or enter Python code first."

    for rule in BLOCKED_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, code_text, flags=re.IGNORECASE):
                return False, rule["message"]

    return True, ""

def detect_request_features(prompt: str) -> dict:
    prompt_lower = (prompt or "").lower()

    return {
        "needs_chart": any(k in prompt_lower for k in ["plot", "chart", "graph", "visualize"]),
        "needs_compare": any(k in prompt_lower for k in ["compare", "vs", "versus", "both", "difference"]),
        "needs_time_series": any(k in prompt_lower for k in ["monthly", "daily", "trend", "return", "over time"]),
        "needs_stat_test": any(k in prompt_lower for k in ["t-test", "ttest", "anova", "significant", "p-value", "hypothesis"]),
        "needs_descriptive": any(k in prompt_lower for k in ["mean", "median", "std", "standard deviation", "min", "max", "summary", "statistics"]),
        "needs_monthly_return": "monthly return" in prompt_lower or "monthly returns" in prompt_lower,
    }


def validate_generated_code(prompt: str, code: str, features: dict):
    issues = []
    code_lower = (code or "").lower()

    if features["needs_chart"]:
        has_plot = any(k in code_lower for k in ["plt.plot", "plt.bar", "plt.scatter", ".plot("])
        if not has_plot:
            issues.append("The user requested a chart, but the code does not appear to create one.")

    if features["needs_compare"]:
        ticker_mentions = re.findall(r'["\']([A-Z]{1,10})["\']', code)
        unique_tickers = set(ticker_mentions)
        if len(unique_tickers) < 2:
            issues.append("The user requested a comparison, but the code does not clearly use at least two datasets or tickers.")

    if features["needs_stat_test"]:
        has_test = any(k in code_lower for k in [
            "ttest_ind", "ttest_rel", "mannwhitneyu", "anova", "f_oneway",
            "pearsonr", "spearmanr", "linregress", "chi2"
        ])
        if not has_test:
            issues.append("The user requested a statistical test, but the code does not appear to run one.")

    # High-impact semantic check: monthly return order
    if features["needs_monthly_return"]:
        if "pct_change()" in code_lower and "resample(" in code_lower:
            pct_idx = code_lower.find("pct_change()")
            resample_idx = code_lower.find("resample(")
            if pct_idx != -1 and resample_idx != -1 and pct_idx < resample_idx:
                issues.append(
                    "For monthly returns, the code appears to compute pct_change() before resampling. "
                    "Monthly returns should usually be calculated from resampled monthly prices first, then pct_change()."
                )

    if issues:
        return False, " ".join(issues)
    return True, ""


def validate_execution_result(prompt: str, code: str, result: dict, features: dict):
    issues = []

    output_text = (result.get("output") or "").lower()
    has_image = result.get("image_bytes") is not None

    if features["needs_chart"] and not has_image:
        issues.append("The user requested a chart, but no plot image was generated.")

    # Broad empty / meaningless output checks
    if "count    0.0" in output_text or "count 0.0" in output_text:
        issues.append("The output suggests the result has zero valid observations.")

    if "all        nan" in output_text or "all nan" in output_text:
        issues.append("The output suggests the computed values are all NaN.")

    if features["needs_stat_test"]:
        has_t_stat = ("t-stat" in output_text) or ("t statistic" in output_text) or ("t-statistic" in output_text)
        has_p_val = ("p-value" in output_text) or ("p value" in output_text) or ("p_val" in output_text)
        if not (has_t_stat and has_p_val):
            issues.append("The user requested a statistical test, but the output does not clearly include both a test statistic and p-value.")

    if issues:
        return False, " ".join(issues)
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


def build_history_text(history):
    if not history:
        return ""

    lines = []
    for i, turn in enumerate(history, start=1):
        lines.append(f"========== Turn {i} ==========")
        lines.append("")
        lines.append("▶ USER")
        lines.append(turn["user"])
        lines.append("")
        lines.append("◆ ASSISTANT")
        lines.append(turn["assistant"])
        lines.append("")

    return "\n".join(lines).strip()


def is_external_data_error(error_text: str) -> bool:
    external_error_keywords = [
        "YFRateLimitError",
        "Too Many Requests",
        "429",
        "ReadTimeout",
        "ConnectTimeout",
        "ConnectionError",
        "Temporary failure",
        "Max retries exceeded",
        "timed out",
        "SSLError",
        "ProxyError",
        "RemoteDisconnected",
    ]

    return any(keyword in error_text for keyword in external_error_keywords)


def _prepare_execution_artifacts(result):
    img = None
    if result["image_bytes"] is not None:
        img = Image.open(io.BytesIO(result["image_bytes"]))

    execution_output = result["output"]

    if not execution_output.strip() and img is None:
        execution_output = "Code executed successfully, but nothing was printed."
    elif not execution_output.strip():
        execution_output = "Plot generated successfully."

    return execution_output, img


def run_agent(prompt: str, history: list | None = None):
    try:
        if history is None:
            history = []

        is_valid, validation_message = validate_prompt(prompt)
        if not is_valid:
            updated_history = history + [{
                "user": prompt,
                "assistant": "Request blocked. See Execution Output for details.",
                "success": False
            }]
            history_text = build_history_text(updated_history)

            return (
                "",
                validation_message,
                "Blocked by input validation",
                history_text,
                None,
                updated_history
            )

        raw_code = generate_code(prompt, history=history)
        code = extract_python_code(raw_code)
        features = detect_request_features(prompt)

        is_code_ok, code_check_message = validate_generated_code(prompt, code, features)
        if not is_code_ok:
            code = repair_code(prompt, code, code_check_message, history=history)

        attempt = 0
        last_error = None

        while attempt < MAX_ATTEMPTS:
            result = execute_code_with_timeout(code, EXEC_TIMEOUT)

            if result["success"]:
                is_result_ok, result_check_message = validate_execution_result(prompt, code, result, features)

                if is_result_ok:
                    if attempt == 0:
                        status = "Executed on first try"
                    else:
                        status = f"Fixed and executed on retry (attempt {attempt})"
                    break

                last_error = f"Post-execution validation failed: {result_check_message}"
                attempt += 1

                if attempt >= MAX_ATTEMPTS:
                    updated_history = history + [{
                        "user": prompt,
                        "assistant": "Request failed. See Execution Output for details.",
                        "success": False
                    }]
                    history_text = build_history_text(updated_history)
                    execution_output, img = _prepare_execution_artifacts(result)

                    return (
                        code,
                        f"{execution_output}\n\nValidation issue: {result_check_message}",
                        "Validation failed",
                        history_text,
                        img,
                        updated_history
                    )

                code = repair_code(prompt, code, result_check_message, history=history)
                continue

            last_error = result["error"]
            attempt += 1

            if is_external_data_error(last_error):
                updated_history = history + [{
                    "user": prompt,
                    "assistant": "Request failed. See Execution Output for details.",
                    "success": False
                }]
                history_text = build_history_text(updated_history)

                return (
                    code,
                    f"Execution error: {last_error}",
                    "External data source / API error",
                    history_text,
                    None,
                    updated_history
                )

            if attempt >= MAX_ATTEMPTS:
                updated_history = history + [{
                    "user": prompt,
                    "assistant": "Request failed. See Execution Output for details.",
                    "success": False
                }]
                history_text = build_history_text(updated_history)

                return (
                    code,
                    f"Execution error (after {attempt-1} retries): {last_error}",
                    "Retry failed",
                    history_text,
                    None,
                    updated_history
                )

            code = repair_code(prompt, code, last_error, history=history)

        execution_output, img = _prepare_execution_artifacts(result)

        interpretation = interpret_result(prompt, code, execution_output, status, history=None)

        updated_history = history + [{
            "user": prompt,
            "assistant": interpretation,
            "success": True
        }]
        history_text = build_history_text(updated_history)

        return code, execution_output, status, history_text, img, updated_history

    except Exception as e:
        updated_history = (history or []) + [{
            "user": prompt,
            "assistant": "Request failed due to a system or API error. See Execution Output for details.",
            "success": False
        }]
        history_text = build_history_text(updated_history)

        return (
            "",
            f"System error: {str(e)}",
            "System/API error",
            history_text,
            None,
            updated_history
        )


def run_edited_code(code: str, history_state: list | None = None):
    try:
        if history_state is None:
            history_state = []

        manual_label = "[Manual Edit Run]"

        is_valid, validation_message = validate_code(code)
        if not is_valid:
            updated_history = history_state + [{
                "user": manual_label,
                "assistant": "Edited code blocked. See Execution Output for details.",
                "success": False
            }]
            history_text = build_history_text(updated_history)

            return (
                validation_message,
                "Blocked edited code",
                history_text,
                None,
                updated_history
            )

        result = execute_code_with_timeout(code, EXEC_TIMEOUT)

        if not result["success"]:
            error_text = result["error"] or "Unknown execution error."
            updated_history = history_state + [{
                "user": manual_label,
                "assistant": "Edited code failed. See Execution Output for details.",
                "success": False
            }]
            history_text = build_history_text(updated_history)

            return (
                f"Execution error: {error_text}",
                "Edited code failed",
                history_text,
                None,
                updated_history
            )

        execution_output, img = _prepare_execution_artifacts(result)
        status = "Executed edited code"

        interpretation = interpret_result(manual_label, code, execution_output, status, history=None)

        updated_history = history_state + [{
            "user": manual_label,
            "assistant": interpretation,
            "success": True
        }]
        history_text = build_history_text(updated_history)

        return (
            execution_output,
            status,
            history_text,
            img,
            updated_history
        )

    except Exception as e:
        manual_label = "[Manual Edit Run]"
        updated_history = (history_state or []) + [{
            "user": manual_label,
            "assistant": "Edited code failed due to a system error. See Execution Output for details.",
            "success": False
        }]
        history_text = build_history_text(updated_history)

        return (
            f"System error: {str(e)}",
            "Edited code system error",
            history_text,
            None,
            updated_history
        )