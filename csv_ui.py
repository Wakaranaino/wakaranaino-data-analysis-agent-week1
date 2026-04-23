from __future__ import annotations

from typing import Any

import gradio as gr
import pandas as pd

from csv_executor import (
    load_csv_file,
    clear_dataset_session,
)


def handle_csv_upload(file_obj):
    """
    UI-facing handler for CSV upload.

    Returns:
    - csv_state
    - csv_file_name
    - csv_row_count
    - csv_column_count
    - csv_missing_total
    - csv_basic_info
    - csv_column_groups
    - csv_missing_info
    - csv_preview
    - accordion update
    """
    empty_state = clear_dataset_session()
    empty_preview = _empty_preview_df()

    if file_obj is None:
        return (
            empty_state,
            "**File:** —",
            "**Rows:** —",
            "**Columns:** —",
            "**Missing cells:** —",
            "No dataset uploaded yet.",
            "",
            "",
            empty_preview,
            gr.update(visible=False, open=False, label="CSV Dataset Summary")
        )

    file_path = _extract_file_path(file_obj)
    if not file_path:
        return (
            empty_state,
            "**File:** —",
            "**Rows:** —",
            "**Columns:** —",
            "**Missing cells:** —",
            "Could not read the uploaded file path.",
            "",
            "",
            empty_preview,
            gr.update(visible=True, open=True, label="CSV Dataset Summary")
        )

    result = load_csv_file(file_path)

    if not result.success or not result.summary:
        return (
            empty_state,
            "**File:** —",
            "**Rows:** —",
            "**Columns:** —",
            "**Missing cells:** —",
            f"CSV upload failed.

{result.message}",
            "",
            "",
            empty_preview,
            gr.update(visible=True, open=True, label="CSV Dataset Summary")
        )

    summary = result.summary
    total_missing = int(sum(summary.get("missing_counts", {}).values()))

    csv_file_name = f"**File:** {summary.get('file_name', 'uploaded.csv')}"
    csv_row_count = f"**Rows:** {summary.get('row_count', 0)}"
    csv_column_count = f"**Columns:** {summary.get('column_count', 0)}"
    csv_missing_total = f"**Missing cells:** {total_missing}"

    csv_basic_info = _build_basic_info(summary)
    csv_column_groups = _build_column_groups(summary)
    csv_missing_info = _build_missing_info(summary)
    csv_preview = _build_preview_df(summary)

    return (
        result.session_data,
        csv_file_name,
        csv_row_count,
        csv_column_count,
        csv_missing_total,
        csv_basic_info,
        csv_column_groups,
        csv_missing_info,
        csv_preview,
        gr.update(
            visible=True,
            open=True,
            label=_build_csv_accordion_label(summary)
        )
    )


def handle_clear_csv():
    """
    Reset CSV-related UI and state.
    """
    return (
        None,
        clear_dataset_session(),
        "**File:** —",
        "**Rows:** —",
        "**Columns:** —",
        "**Missing cells:** —",
        "No dataset uploaded yet.",
        "",
        "",
        _empty_preview_df(),
        gr.update(
            visible=False,
            open=False,
            label="CSV Dataset Summary"
        )
    )


def build_initial_csv_summary_text() -> str:
    return ""


def _extract_file_path(file_obj) -> str | None:
    if file_obj is None:
        return None

    if hasattr(file_obj, "name") and file_obj.name:
        return str(file_obj.name)

    if isinstance(file_obj, str):
        return file_obj

    if isinstance(file_obj, dict):
        if "name" in file_obj and file_obj["name"]:
            return str(file_obj["name"])
        if "path" in file_obj and file_obj["path"]:
            return str(file_obj["path"])

    return None


def _build_csv_accordion_label(summary: dict[str, Any]) -> str:
    file_name = summary.get("file_name", "uploaded.csv")
    row_count = summary.get("row_count", 0)
    col_count = summary.get("column_count", 0)
    return f"CSV Dataset Summary — {file_name} | {row_count} rows | {col_count} columns"


def _build_basic_info(summary: dict[str, Any]) -> str:
    file_name = summary.get("file_name", "uploaded.csv")
    row_count = summary.get("row_count", 0)
    col_count = summary.get("column_count", 0)
    column_names = summary.get("column_names", [])

    lines = [
        f"### Basic Info",
        f"- File: {file_name}",
        f"- Rows: {row_count}",
        f"- Columns: {col_count}",
        "",
        "### Column Names",
    ]

    for col in column_names:
        lines.append(f"- {col}")

    return "
".join(lines).strip()


def _build_column_groups(summary: dict[str, Any]) -> str:
    numeric = summary.get("numeric_columns", [])
    categorical = summary.get("categorical_columns", [])
    datetime_cols = summary.get("datetime_columns", [])

    lines = ["### Column Groups"]

    lines.append("")
    lines.append("**Numeric**")
    if numeric:
        for col in numeric:
            lines.append(f"- {col}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("**Categorical / Text**")
    if categorical:
        for col in categorical:
            lines.append(f"- {col}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("**Datetime**")
    if datetime_cols:
        for col in datetime_cols:
            lines.append(f"- {col}")
    else:
        lines.append("- None")

    return "
".join(lines).strip()


def _build_missing_info(summary: dict[str, Any]) -> str:
    missing_counts = summary.get("missing_counts", {})
    total_missing = int(sum(missing_counts.values()))

    lines = ["### Missing Values"]

    if total_missing == 0:
        lines.append("")
        lines.append("No missing values detected.")
        return "
".join(lines).strip()

    sorted_missing = sorted(
        missing_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    lines.append("")
    for col, count in sorted_missing:
        if count > 0:
            lines.append(f"- {col}: {count}")

    return "
".join(lines).strip()


def _build_preview_df(summary: dict[str, Any]) -> pd.DataFrame:
    records = summary.get("preview_records", [])
    if not records:
        return _empty_preview_df()
    return pd.DataFrame(records)


def _empty_preview_df() -> pd.DataFrame:
    return pd.DataFrame()
