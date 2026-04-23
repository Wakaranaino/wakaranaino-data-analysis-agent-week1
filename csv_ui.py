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
    empty_preview = gr.update(value=[["No preview available"]], headers=["Info"])

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
        _build_preview_table_update(summary),
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
        gr.update(value=[["No preview available"]], headers=["Info"]),
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
    file_name = summary.get("file_name", "uploaded.csv")
    row_count = summary.get("row_count", 0)
    col_count = summary.get("column_count", 0)
    numeric_count = len(summary.get("numeric_columns", []))
    datetime_count = len(summary.get("datetime_columns", []))
    categorical_count = len(summary.get("categorical_columns", []))

    return (
        "### Basic Info\n"
        "\n"
        "| Metric | Value |\n"
        "| --- | --- |\n"
        f"| File | `{file_name}` |\n"
        f"| Rows | {row_count} |\n"
        f"| Columns | {col_count} |\n"
        f"| Numeric Columns | {numeric_count} |\n"
        f"| Datetime Columns | {datetime_count} |\n"
        f"| Categorical/Text Columns | {categorical_count} |"
    )


def _build_column_groups(summary: dict[str, Any]) -> str:
    numeric_cols = summary.get("numeric_columns", [])
    datetime_cols = summary.get("datetime_columns", [])
    categorical_cols = summary.get("categorical_columns", [])
    numeric_text = _format_chip_group(numeric_cols)
    datetime_text = _format_chip_group(datetime_cols)
    categorical_text = _format_chip_group(categorical_cols)

    return (
        "### Column Groups\n"
        "\n"
        f"**Numeric ({len(numeric_cols)})**\n\n{numeric_text}\n\n"
        f"**Datetime ({len(datetime_cols)})**\n\n{datetime_text}\n\n"
        f"**Categorical/Text ({len(categorical_cols)})**\n\n{categorical_text}"
    )


def _build_missing_info(summary: dict[str, Any]) -> str:
    missing_counts = summary.get("missing_counts", {})
    row_count = max(int(summary.get("row_count", 0)), 1)
    missing_columns = [(col, count) for col, count in missing_counts.items() if int(count) > 0]
    missing_total = sum(int(count) for _, count in missing_columns)

    if missing_total == 0:
        return "### Missing Values\n\nNo missing values detected."

    lines = [
        "### Missing Values",
        "",
        "| Column | Missing Count | Missing % |",
        "| --- | ---: | ---: |",
    ]

    for col, count in missing_columns:
        pct = (int(count) / row_count) * 100
        lines.append(f"| `{col}` | {int(count)} | {pct:.2f}% |")

    return "\n".join(lines).strip()


def _build_preview_table_update(summary: dict[str, Any]):
    rows: list[list[Any]] = []
    preview_records = summary.get("preview_records", [])
    columns = summary.get("column_names", [])

    if not preview_records:
        return gr.update(value=[["No preview available"]], headers=["Info"])

    if not columns and preview_records:
        columns = list(preview_records[0].keys())

    for record in preview_records:
        rows.append([record.get(col) for col in columns])

    return gr.update(value=rows, headers=columns)


def _format_chip_group(columns: list[str]) -> str:
    if not columns:
        return "_None_"
    chips = [f"<span class='csv-chip'>{col}</span>" for col in columns]
    return "<div class='csv-chip-wrap'>" + " ".join(chips) + "</div>"


