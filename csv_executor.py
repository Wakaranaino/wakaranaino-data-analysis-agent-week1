from __future__ import annotations

import io
import traceback
import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from PIL import Image

from llm import generate_csv_code, repair_csv_code, interpret_result


MAX_PREVIEW_ROWS = 5
MAX_CATEGORY_UNIQUES = 20
CSV_EXEC_TIMEOUT = 35
CSV_MAX_ATTEMPTS = 2


@dataclass
class CSVLoadResult:
    success: bool
    message: str
    file_name: Optional[str] = None
    df: Optional[pd.DataFrame] = None
    summary: Optional[dict[str, Any]] = None
    session_data: Optional[dict[str, Any]] = None


def load_csv_file(file_path: str | Path) -> CSVLoadResult:
    """
    Load a CSV file and return:
    - the DataFrame
    - a structured summary
    - a session payload for later app-level storage

    This first draft only supports standard CSV files.
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return CSVLoadResult(
                success=False,
                message=f"File not found: {path}"
            )

        if path.suffix.lower() != ".csv":
            return CSVLoadResult(
                success=False,
                message="Only .csv files are supported in this version."
            )

        df = pd.read_csv(path)

        summary = summarize_dataframe(df, file_name=path.name)
        session_data = build_dataset_session(df, summary, file_name=path.name)

        return CSVLoadResult(
            success=True,
            message="CSV loaded successfully.",
            file_name=path.name,
            df=df,
            summary=summary,
            session_data=session_data
        )

    except UnicodeDecodeError:
        return CSVLoadResult(
            success=False,
            message="Failed to read the CSV file due to encoding issues. Please save the file as UTF-8 CSV and try again."
        )

    except pd.errors.EmptyDataError:
        return CSVLoadResult(
            success=False,
            message="The uploaded CSV file is empty."
        )

    except pd.errors.ParserError as e:
        return CSVLoadResult(
            success=False,
            message=f"Failed to parse the CSV file: {e}"
        )

    except Exception as e:
        return CSVLoadResult(
            success=False,
            message=f"Unexpected error while loading CSV: {e}"
        )


def summarize_dataframe(df: pd.DataFrame, file_name: Optional[str] = None) -> dict[str, Any]:
    """
    Build a structured summary that is easy to show in the UI
    and easy to reuse later for prompt context.
    """
    rows, cols = df.shape

    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    missing_counts = {col: int(df[col].isna().sum()) for col in df.columns}

    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    datetime_columns = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

    categorical_columns = [
        col for col in df.columns
        if col not in numeric_columns and col not in datetime_columns
    ]

    preview_records = _safe_preview_records(df, n=MAX_PREVIEW_ROWS)
    unique_counts = {col: int(df[col].nunique(dropna=True)) for col in df.columns}

    categorical_samples = {}
    for col in categorical_columns:
        values = df[col].dropna().astype(str).unique().tolist()[:MAX_CATEGORY_UNIQUES]
        categorical_samples[col] = values

    summary = {
        "file_name": file_name or "uploaded.csv",
        "row_count": int(rows),
        "column_count": int(cols),
        "column_names": df.columns.tolist(),
        "dtypes": dtypes,
        "missing_counts": missing_counts,
        "unique_counts": unique_counts,
        "numeric_columns": numeric_columns,
        "datetime_columns": datetime_columns,
        "categorical_columns": categorical_columns,
        "categorical_samples": categorical_samples,
        "preview_records": preview_records,
    }

    return summary


def build_dataset_session(
    df: pd.DataFrame,
    summary: dict[str, Any],
    file_name: Optional[str] = None
) -> dict[str, Any]:
    """
    Prepare a session payload to store in app-level state later.
    This is not full persistent memory yet, but it is the dataset
    object package we will keep sticky during a CSV session.
    """
    return {
        "active": True,
        "file_name": file_name or summary.get("file_name", "uploaded.csv"),
        "df": df,
        "summary": summary,
        "user_notes": "",
    }


def format_summary_text(summary: dict[str, Any]) -> str:
    """
    Convert the summary dict into a readable plain-text summary
    for an initial UI panel or textbox.
    """
    lines: list[str] = []

    lines.append(f"File: {summary['file_name']}")
    lines.append(f"Rows: {summary['row_count']}")
    lines.append(f"Columns: {summary['column_count']}")
    lines.append("")

    lines.append("Column names:")
    for col in summary["column_names"]:
        lines.append(f"- {col}")
    lines.append("")

    lines.append("Data types:")
    for col, dtype in summary["dtypes"].items():
        lines.append(f"- {col}: {dtype}")
    lines.append("")

    lines.append("Missing values:")
    for col, missing in summary["missing_counts"].items():
        lines.append(f"- {col}: {missing}")
    lines.append("")

    if summary["numeric_columns"]:
        lines.append("Numeric columns:")
        for col in summary["numeric_columns"]:
            lines.append(f"- {col}")
        lines.append("")

    if summary["datetime_columns"]:
        lines.append("Datetime columns:")
        for col in summary["datetime_columns"]:
            lines.append(f"- {col}")
        lines.append("")

    if summary["categorical_columns"]:
        lines.append("Categorical/text columns:")
        for col in summary["categorical_columns"]:
            lines.append(f"- {col}")
        lines.append("")

    lines.append("Preview (first rows):")
    preview_records = summary.get("preview_records", [])

    if not preview_records:
        lines.append("- No preview available.")
    else:
        for i, row in enumerate(preview_records, start=1):
            lines.append(f"Row {i}:")
            for key, value in row.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

    return "\n".join(lines).strip()


def clear_dataset_session() -> dict[str, Any]:
    """
    Reset dataset session state.
    Useful later when user uploads a new CSV or clears the session.
    """
    return {
        "active": False,
        "file_name": None,
        "df": None,
        "summary": None,
        "user_notes": "",
    }


def _safe_preview_records(df: pd.DataFrame, n: int = 5) -> list[dict[str, Any]]:
    """
    Convert the first few rows into JSON-friendly records for display/state.
    """
    preview = df.head(n).copy()

    # Convert problematic values into safe printable values
    preview = preview.where(pd.notnull(preview), None)

    records: list[dict[str, Any]] = []
    for _, row in preview.iterrows():
        record: dict[str, Any] = {}
        for col, value in row.items():
            record[str(col)] = _safe_cell_value(value)
        records.append(record)

    return records


def _safe_cell_value(value: Any) -> Any:
    """
    Make cell values safe for storing in summary/session structures.
    """
    if value is None:
        return None

    # pandas timestamps
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    # numpy / pandas scalar types
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, (int, float, str, bool)):
        return value

    return str(value)


def _build_history_text(history: list[dict[str, Any]] | None) -> str:
    if not history:
        return ""

    lines: list[str] = []
    for i, turn in enumerate(history, start=1):
        lines.append(f"========== Turn {i} ==========")
        lines.append("")
        lines.append("▶ USER")
        lines.append(str(turn.get("user", "")))
        lines.append("")
        lines.append("◆ ASSISTANT")
        lines.append(str(turn.get("assistant", "")))
        lines.append("")
    return "\n".join(lines).strip()


def _execute_csv_code_worker(code: str, df: pd.DataFrame, queue: mp.Queue):
    import io
    import contextlib
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    from scipy import stats

    output_buffer = io.StringIO()

    try:
        globals_ctx = {
            "__builtins__": __builtins__,
            "df": df.copy(),
            "pd": pd,
            "np": np,
            "plt": plt,
            "stats": stats,
        }

        with contextlib.redirect_stdout(output_buffer):
            exec(code, globals_ctx)

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


def _execute_csv_code_with_timeout(code: str, df: pd.DataFrame, timeout: int = CSV_EXEC_TIMEOUT) -> dict[str, Any]:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_execute_csv_code_worker, args=(code, df, queue))
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


def _prepare_csv_execution_artifacts(result: dict[str, Any]) -> tuple[str, Any]:
    img = None
    if result.get("image_bytes") is not None:
        img = Image.open(io.BytesIO(result["image_bytes"]))

    execution_output = (result.get("output") or "").strip()
    if not execution_output and img is None:
        execution_output = "Code executed successfully, but nothing was printed."
    elif not execution_output:
        execution_output = "Plot generated successfully."

    return execution_output, img


def _csv_prompt_needs_stat_test(prompt: str) -> bool:
    prompt_lower = (prompt or "").lower()
    return any(k in prompt_lower for k in [
        "t-test", "ttest", "anova", "hypothesis", "p-value", "significant"
    ])


def _validate_csv_execution_result(prompt: str, execution_output: str) -> tuple[bool, str]:
    prompt_lower = (prompt or "").lower()
    text = (execution_output or "").lower()

    # Global no-value guard: any analysis output that clearly indicates no usable values.
    no_value_hints = [
        "empty dataframe",
        "empty data frame",
        "no rows",
        "no data",
        "0 rows",
        "no valid observations",
        "all nan",
        "all values are nan",
        "count    0.0",
        "count 0.0",
    ]
    if any(hint in text for hint in no_value_hints):
        return False, (
            "Execution output indicates no usable values for analysis."
        )

    if _csv_prompt_needs_stat_test(prompt):
        has_test_hint = any(k in text for k in ["t-test", "ttest", "t-stat", "t statistic", "p-value", "p value"])
        if has_test_hint and "nan" in text:
            return False, (
                "Statistical output contains NaN. Ensure subgroup filtering returns non-empty numeric groups, "
                "normalize category labels, and rerun the test."
            )

    # If prompt requests an analysis result, "nothing printed" should not be treated as success.
    analysis_intents = [
        "analy", "stat", "compare", "plot", "chart", "graph", "test", "mean", "median",
        "std", "distribution", "correlation", "regression", "histogram", "summary"
    ]
    if "nothing was printed" in text and any(k in prompt_lower for k in analysis_intents):
        return False, "Analysis request returned no printed values."

    return True, ""


def run_csv_agent(prompt: str, history: list | None, csv_state: dict[str, Any] | None):
    try:
        if history is None:
            history = []

        if not prompt or not str(prompt).strip():
            updated_history = history + [{
                "user": prompt or "",
                "assistant": "Please enter a prompt.",
                "success": False
            }]
            return "", "Please enter a prompt.", "CSV request blocked", _build_history_text(updated_history), None, updated_history

        if not csv_state or not csv_state.get("active") or csv_state.get("df") is None:
            updated_history = history + [{
                "user": prompt,
                "assistant": "No active CSV dataset. Upload a CSV file first.",
                "success": False
            }]
            return "", "No active CSV dataset. Upload a CSV file first.", "No CSV session", _build_history_text(updated_history), None, updated_history

        df = csv_state["df"]
        summary = csv_state.get("summary") or {}

        last_error = None
        code = ""

        for attempt in range(CSV_MAX_ATTEMPTS):
            if attempt == 0:
                code = generate_csv_code(prompt, dataset_summary=summary, history=history)
            else:
                code = repair_csv_code(
                    prompt=prompt,
                    bad_code=code,
                    error_message=last_error or "Unknown error",
                    dataset_summary=summary,
                    history=history
                )

            result = _execute_csv_code_with_timeout(code, df, timeout=CSV_EXEC_TIMEOUT)
            if result.get("success"):
                execution_output, img = _prepare_csv_execution_artifacts(result)
                is_valid, validation_message = _validate_csv_execution_result(prompt, execution_output)
                if is_valid:
                    status = "Executed on CSV dataset" if attempt == 0 else f"Fixed and executed on CSV retry (attempt {attempt})"
                    interpretation = interpret_result(f"[FILE] {prompt}", code, execution_output, status, history=None)
                    updated_history = history + [{
                        "user": prompt,
                        "assistant": interpretation,
                        "success": True
                    }]
                    return code, execution_output, status, _build_history_text(updated_history), img, updated_history

                last_error = f"Post-execution validation failed: {validation_message}"
                continue

            last_error = result.get("error") or "Unknown execution error."

        updated_history = history + [{
            "user": prompt,
            "assistant": "CSV analysis failed. See Execution Output for details.",
            "success": False
        }]
        return (
            code,
            f"Execution error (after {CSV_MAX_ATTEMPTS - 1} retry): {last_error}",
            "CSV execution failed",
            _build_history_text(updated_history),
            None,
            updated_history
        )
    except Exception as e:
        updated_history = (history or []) + [{
            "user": prompt,
            "assistant": "CSV analysis failed due to a system or API error. See Execution Output for details.",
            "success": False
        }]
        return (
            "",
            f"System error: {str(e)}",
            "CSV system/API error",
            _build_history_text(updated_history),
            None,
            updated_history
        )




