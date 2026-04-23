from __future__ import annotations

from typing import Any

import gradio as gr

from csv_executor import (
    load_csv_file,
    clear_dataset_session,
)


def handle_csv_upload(file_obj) -> tuple[Any, ...]:
    """
    UI-facing handler for CSV upload.

    Returns (structured summary):
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
    empty_preview: list[list[Any]] = []

    if file_obj is None:
        return (
            empty_state,
            "**File:** —",
            "**Rows:** —",
            "**Columns:** —",
            "**Missing cells:** —",
            "No CSV file uploaded yet.",
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
            f"CSV upload failed.\n\n{result.message}",
            "",
            "",
            empty_preview,
            gr.update(visible=True, open=True, label="CSV Dataset Summary")
        )

    summary = result.summary
    missing_total = int(sum(summary.get("missing_counts", {}).values()))

    return (
        result.session_data,
        f"**File:** {summary.get('file_name', 'uploaded.csv')}",
        f"**Rows:** {summary.get('row_count', 0)}",
        f"**Columns:** {summary.get('column_count', 0)}",
        f"**Missing cells:** {missing_total}",
        _build_basic_info(summary),
        _build_column_groups(summary),
        _build_missing_info(summary),
        _build_preview_table(summary),
        gr.update(
            visible=True,
            open=True,
            label=_build_csv_accordion_label(summary)
        )
    )


def handle_clear_csv() -> tuple[Any, ...]:
    """
    Reset CSV-related UI and state.

    Returns:
    - file input reset
    - csv_state reset
    - csv_file_name reset
    - csv_row_count reset
    - csv_column_count reset
    - csv_missing_total reset
    - csv_basic_info reset
    - csv_column_groups reset
    - csv_missing_info reset
    - csv_preview reset
    - accordion hidden
    """
    return (
        None,
        clear_dataset_session(),
        "**File:** —",
        "**Rows:** —",
        "**Columns:** —",
        "**Missing cells:** —",
        "",
        "",
        "",
        [],
        gr.update(
            visible=False,
            open=False,
            label="CSV Dataset Summary"
        )
    )


def build_initial_csv_summary_text() -> str:
    return ""


def _extract_file_path(file_obj) -> str | None:
    """
    Supports Gradio file objects across common shapes.
    """
    if file_obj is None:
        return None

    # Common gradio temp file object
    if hasattr(file_obj, "name") and file_obj.name:
        return str(file_obj.name)

    # Sometimes file object may already be a string path
    if isinstance(file_obj, str):
        return file_obj

    # Fallback for dict-like objects
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
    lines: list[str] = []
    lines.append("Dataset Overview")
    lines.append(f"- File name: {summary.get('file_name', 'uploaded.csv')}")
    lines.append(f"- Rows: {summary.get('row_count', 0)}")
    lines.append(f"- Columns: {summary.get('column_count', 0)}")
    lines.append("")
    lines.append("All Columns")
    for col in summary.get("column_names", []):
        lines.append(f"- {col}")
    return "\n".join(lines).strip()


def _build_column_groups(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    numeric_cols = summary.get("numeric_columns", [])
    datetime_cols = summary.get("datetime_columns", [])
    categorical_cols = summary.get("categorical_columns", [])

    lines.append("Column Groups")
    lines.append(f"- Numeric ({len(numeric_cols)}): {', '.join(numeric_cols) if numeric_cols else 'None'}")
    lines.append(f"- Datetime ({len(datetime_cols)}): {', '.join(datetime_cols) if datetime_cols else 'None'}")
    lines.append(f"- Categorical/Text ({len(categorical_cols)}): {', '.join(categorical_cols) if categorical_cols else 'None'}")
    return "\n".join(lines).strip()


def _build_missing_info(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    missing_counts = summary.get("missing_counts", {})
    lines.append("Missing Values by Column")

    if not missing_counts:
        lines.append("- No missing-value summary available.")
        return "\n".join(lines).strip()

    for col, count in missing_counts.items():
        lines.append(f"- {col}: {count}")
    return "\n".join(lines).strip()


def _build_preview_table(summary: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    preview_records = summary.get("preview_records", [])
    columns = summary.get("column_names", [])

    if not preview_records:
        return [["No preview available"]]

    if not columns and preview_records:
        columns = list(preview_records[0].keys())

    for record in preview_records:
        rows.append([record.get(col) for col in columns])

    return rows

