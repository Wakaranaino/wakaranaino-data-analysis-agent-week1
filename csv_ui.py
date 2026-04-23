from __future__ import annotations

from pathlib import Path
from typing import Any

import gradio as gr

from csv_executor import (
    load_csv_file,
    format_summary_text,
    clear_dataset_session,
)


def handle_csv_upload(file_obj) -> tuple[dict[str, Any], Any, Any]:
    """
    UI-facing handler for CSV upload.

    Returns:
    - csv_state
    - csv_summary_text
    - accordion update
    """
    empty_state = clear_dataset_session()

    if file_obj is None:
        return (
            empty_state,
            "No CSV file uploaded yet.",
            gr.update(visible=False, open=False)
        )

    file_path = _extract_file_path(file_obj)
    if not file_path:
        return (
            empty_state,
            "Could not read the uploaded file path.",
            gr.update(visible=True, open=True)
        )

    result = load_csv_file(file_path)

    if not result.success:
        return (
            empty_state,
            f"CSV upload failed.\n\n{result.message}",
            gr.update(visible=True, open=True)
        )

    summary_text = format_summary_text(result.summary)

    return (
        result.session_data,
        summary_text,
        gr.update(
            visible=True,
            open=True,
            label=_build_csv_accordion_label(result.summary)
        )
    )


def handle_clear_csv() -> tuple[Any, dict[str, Any], str, Any]:
    """
    Reset CSV-related UI and state.

    Returns:
    - file input reset
    - csv_state reset
    - csv_summary cleared
    - accordion hidden
    """
    return (
        None,
        clear_dataset_session(),
        "",
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