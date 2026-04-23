from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd


MAX_PREVIEW_ROWS = 5
MAX_CATEGORY_UNIQUES = 20


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