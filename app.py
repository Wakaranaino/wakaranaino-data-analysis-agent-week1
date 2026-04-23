import gradio as gr
from executor import run_agent, run_edited_code
from llm import explain_code
from csv_ui import handle_csv_upload, handle_clear_csv
from csv_executor import clear_dataset_session, run_csv_agent


EXAMPLE_PROMPTS = {
    "AAPL Trend": "Plot AAPL closing prices for the last 100 days",
    "TSLA vs MSFT": "Compare the monthly returns of Tesla (TSLA) and Microsoft (MSFT) over the past year. Show both on the same chart and run a t-test to see if the mean returns are significantly different.",
    "IBM Stats": "Show mean, median, standard deviation, min, and max of IBM closing prices for the last 100 days",
    "Same for NVDA": "Do the same for NVDA as for IBM"
}


def fill_prompt(text):
    return text


def clear_prompt():
    return ""


def new_chat():
    return "", []


def run_agent_ui(prompt, history_state, csv_state):
    if csv_state and csv_state.get("active"):
        code, execution_output, run_status, interpretation, plot_output, updated_history = run_csv_agent(
            prompt=prompt,
            history=history_state,
            csv_state=csv_state
        )
    else:
        code, execution_output, run_status, interpretation, plot_output, updated_history = run_agent(prompt, history_state)
    return (
        code,
        execution_output,
        run_status,
        interpretation,
        plot_output,
        updated_history,
        "",
        False,
        gr.update(interactive=False),
        gr.update(value="Edit", variant="secondary"),
        ""
    )


def handle_edit_or_run(edit_mode, code, history_state):
    if not edit_mode:
        return (
            code,
            gr.update(interactive=True),
            gr.update(value="Run", variant="primary"),
            True,
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            history_state
        )

    execution_output, run_status, interpretation, plot_output, updated_history = run_edited_code(
        code=code,
        history_state=history_state
    )

    return (
        code,
        gr.update(interactive=False),
        gr.update(value="Edit", variant="secondary"),
        False,
        execution_output,
        run_status,
        interpretation,
        plot_output,
        updated_history
    )


def explain_code_ui(code):
    return explain_code(code)


custom_js = """
function () {
  function scrollHistoryToBottom() {
    const ta = document.querySelector('#history-textbox textarea');
    if (ta) ta.scrollTop = ta.scrollHeight;
  }
  // Gradio replaces the textarea element on each update,
  // so we scroll at multiple points after the update settles.
  function scheduledScroll() {
    scrollHistoryToBottom();
    setTimeout(scrollHistoryToBottom, 100);
    setTimeout(scrollHistoryToBottom, 300);
    setTimeout(scrollHistoryToBottom, 600);
  }
  // Watch the parent container for DOM changes (element replacement)
  function attachObserver() {
    const container = document.querySelector('#history-textbox');
    if (!container) {
      setTimeout(attachObserver, 500);
      return;
    }
    const observer = new MutationObserver(scheduledScroll);
    observer.observe(container, { childList: true, subtree: true });
  }
  attachObserver();
}
"""

css = """
:root {
    --ui-bg: #f7f8fb;
    --ui-card: #ffffff;
    --ui-border: #e5e7eb;
    --ui-text: #111827;
    --ui-muted: #6b7280;
    --ui-accent: #ea7a33;
}
.gradio-container {
    width: min(1760px, calc(100vw - 40px)) !important;
    max-width: min(1760px, calc(100vw - 40px)) !important;
    margin: 0 auto !important;
    padding: 14px 16px 20px !important;
    background: linear-gradient(180deg, #fbfcff 0%, var(--ui-bg) 100%) !important;
    border-radius: 16px !important;
}
.gradio-container h1 {
    margin-bottom: 4px !important;
    font-size: 48px !important;
    line-height: 1.1 !important;
    letter-spacing: -0.02em !important;
    color: var(--ui-text) !important;
}
.app-subtitle p {
    margin: 0 0 12px 0 !important;
    font-size: 16px !important;
    color: var(--ui-muted) !important;
}
.top-row {
    gap: 12px !important;
    align-items: stretch !important;
}
.left-pane,
.right-pane {
    background: var(--ui-card) !important;
    border: 1px solid var(--ui-border) !important;
    border-radius: 14px !important;
    padding: 12px !important;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05) !important;
    min-height: 0 !important;
}
.left-pane textarea,
.right-pane textarea,
#execution-output textarea,
#code-explanation textarea,
#run-status textarea {
    border-radius: 12px !important;
    border-color: #e3e7ef !important;
}
.example-row {
    gap: 8px !important;
    margin-top: -4px !important;
    margin-bottom: 8px !important;
    flex-wrap: wrap !important;
}
.example-row button {
    min-width: unset !important;
    width: auto !important;
    min-height: 32px !important;
    height: 32px !important;
    padding: 0 12px !important;
    font-size: 13px !important;
    border-radius: 999px !important;
    border: 1px solid #dde3ee !important;
    background: #f7f9fc !important;
    color: #273244 !important;
    flex: 0 0 auto !important;
}
.action-row {
    margin-top: -1px !important;
    gap: 8px !important;
    flex-wrap: nowrap !important;
}
.action-row > * {
    flex: 1 1 0 !important;
    min-width: 0 !important;
}
.action-row button,
.action-row .gr-button {
    min-height: 40px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
.action-row button.primary {
    background: linear-gradient(180deg, #ef8b45 0%, var(--ui-accent) 100%) !important;
    border-color: var(--ui-accent) !important;
    color: #ffffff !important;
}
.action-row button.primary:hover {
    background: linear-gradient(180deg, #e78039 0%, #dd6f2a 100%) !important;
    border-color: #dd6f2a !important;
}
.panel-action-row {
    display: flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
    margin-top: 8px !important;
    gap: 0 !important;
}
.panel-action-row > * {
    flex: 0 0 auto !important;
    width: auto !important;
    max-width: none !important;
}
#edit-run-btn {
    width: 110px !important;
    min-width: 110px !important;
    border-radius: 14px !important;
}
#code-output-wrap {
    position: relative;
}
#code-output-wrap #edit-run-btn {
    position: absolute !important;
    top: 8px;
    right: 64px;
    z-index: 20;
    height: 24px !important;
    min-height: 24px !important;
    width: 92px !important;
    min-width: 92px !important;
    max-width: 92px !important;
    padding: 0 !important;
    font-size: 12px !important;
    line-height: 24px !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
}
#explain-code-btn {
    width: 145px !important;
    min-width: 145px !important;
    border-radius: 14px !important;
}
#code-explain-wrap {
    position: relative;
}
#code-explain-wrap #explain-code-btn {
    position: absolute !important;
    top: 8px;
    right: 10px;
    z-index: 20;
    height: 24px !important;
    min-height: 24px !important;
    width: 120px !important;
    min-width: 120px !important;
    max-width: 120px !important;
    padding: 0 !important;
    font-size: 12px !important;
    line-height: 24px !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
}
#history-wrap {
    position: relative;
}
#history-textbox textarea {
    overflow-y: scroll !important;
    height: 322px !important;
    min-height: 322px !important;
    max-height: 322px !important;
}
.history-panel-title {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: var(--body-text-color) !important;
    margin: 0 0 10px 0 !important;
}
#history-wrap #clear-history-btn {
    position: absolute !important;
    top: 8px;
    right: 10px;
    z-index: 20;
    height: 22px !important;
    min-height: 22px !important;
    width: 74px !important;
    min-width: 74px !important;
    max-width: 74px !important;
    padding: 0 !important;
    font-size: 12px !important;
    line-height: 22px !important;
    font-weight: 600 !important;
    border-radius: 999px !important;
}
.io-row,
.code-row {
    gap: 12px !important;
    margin-top: 10px !important;
}
#plot-output,
#execution-output,
#code-output,
#code-explanation,
#run-status {
    background: var(--ui-card) !important;
    border: 1px solid #e4e8f0 !important;
    border-radius: 14px !important;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04) !important;
}
#plot-output,
#execution-output {
    height: auto !important;
    min-height: 500px !important;
    max-height: none !important;
}
#prompt-input textarea {
    height: 150px !important;
    min-height: 150px !important;
    max-height: 150px !important;
    overflow-y: auto !important;
}
#execution-output textarea,
#code-explanation textarea {
    height: 430px !important;
    min-height: 430px !important;
    max-height: 430px !important;
    overflow-y: auto !important;
}
#code-output pre,
#code-output textarea,
#code-output .cm-editor,
#code-output .cm-scroller {
    height: 430px !important;
    min-height: 430px !important;
    max-height: 430px !important;
    overflow: auto !important;
}
.csv-summary-panel {
    background: linear-gradient(180deg, rgba(160, 192, 148, 0.07), rgba(255, 255, 255, 0.02)) !important;
    border: 1px solid rgba(146, 180, 132, 0.5) !important;
    border-radius: 12px !important;
    padding: 8px !important;
    font-size: 12px !important;
    overflow-x: auto !important;
}
.csv-sections-row {
    display: grid !important;
    grid-template-columns: 1.05fr 1.35fr 1fr 1.45fr !important;
    gap: 0 !important;
    align-items: stretch !important;
    min-width: 1120px !important;
}
.csv-section-col {
    padding: 0 8px !important;
    min-width: 0 !important;
}
.csv-section-col + .csv-section-col {
    border-left: 1px solid #d5ddcf !important;
}
.csv-section-title {
    margin: 0 0 6px 0 !important;
    font-size: 12px !important;
    font-weight: 700 !important;
}
.csv-section-body {
    max-height: 168px !important;
    min-height: 168px !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    font-size: 12px !important;
    line-height: 1.28 !important;
}
.csv-overview-item {
    margin: 0 0 6px 0 !important;
    font-size: 12px !important;
}
.csv-overview-item:last-child {
    margin-bottom: 0 !important;
}
.csv-overview-item p {
    margin: 0 !important;
}
.csv-section-body p,
.csv-section-body li,
.csv-section-body table {
    font-size: 12px !important;
}
.csv-section-body ul {
    margin: 0 0 0 14px !important;
    padding: 0 !important;
}
.csv-preview-wrap {
    max-height: 168px !important;
    min-height: 168px !important;
    overflow: auto !important;
}
.csv-preview-wrap table {
    font-size: 11px !important;
}
.csv-actions-row {
    margin-top: 8px !important;
    justify-content: flex-end !important;
}
.csv-actions-row > * {
    flex: 0 0 auto !important;
}
.csv-actions-row button {
    width: 132px !important;
    min-width: 132px !important;
}
.csv-chip-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
}
.csv-chip {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 999px;
    border: 1px solid #ffd68a;
    background: #fff7e6;
    font-size: 10px;
}
#csv-upload {
    margin-top: 6px !important;
    margin-bottom: 8px !important;
    border: 1px solid #e4e8f0 !important;
    border-radius: 12px !important;
    background: #ffffff !important;
    padding: 4px !important;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03) !important;
    height: 62px !important;
    min-height: 62px !important;
    max-height: 62px !important;
    overflow: hidden !important;
}
#csv-upload .file-preview,
#csv-upload .file-preview-holder {
    min-height: 0 !important;
}
#csv-upload .file-drop {
    min-height: 30px !important;
    max-height: 30px !important;
    height: 30px !important;
    padding: 4px 10px !important;
    border-radius: 8px !important;
    border: 1px dashed #cfd8e6 !important;
    background: #fafcff !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    overflow: hidden !important;
    position: relative !important;
}
#csv-upload .file-drop .file-drop-icon {
    display: none !important;
}
#csv-upload .file-drop .file-drop-text,
#csv-upload .file-drop p,
#csv-upload .file-drop span,
#csv-upload .file-drop small,
#csv-upload .file-drop svg {
    display: none !important;
}
#csv-upload .file-drop::after {
    content: "Drop CSV here or click to upload";
    font-size: 11px !important;
    line-height: 1.2 !important;
    color: #6b7280 !important;
    white-space: nowrap !important;
}
/* Gradio v6 internal wrappers can set larger min-heights; override aggressively */
#csv-upload [class*="file"],
#csv-upload [class*="upload"],
#csv-upload [class*="drop"] {
    min-height: unset !important;
}
#csv-upload [class*="drop"] {
    min-height: 30px !important;
    max-height: 30px !important;
    height: 30px !important;
}
/* Keep top cards visually aligned after uploader compaction */
.left-pane,
.right-pane {
    min-height: 0 !important;
}
"""

with gr.Blocks(css=css, js=custom_js) as demo:
    gr.Markdown("# AI Data Analysis Agent")
    gr.Markdown("Upload CSV data or ask questions to analyze datasets, run code, and visualize results.", elem_classes="app-subtitle")

    history_state = gr.State([])
    edit_mode_state = gr.State(False)
    csv_state = gr.State(clear_dataset_session())

    with gr.Row(elem_classes="top-row"):
        with gr.Column(elem_classes="left-pane"):
            prompt = gr.Textbox(
                label="Prompt",
                lines=3,
                max_lines=3,
                placeholder="Try: Plot AAPL closing prices for the last 100 days",
                elem_id="prompt-input"
            )

            with gr.Row(elem_classes="example-row"):
                ex1 = gr.Button("AAPL Trend", variant="secondary")
                ex2 = gr.Button("TSLA vs MSFT", variant="secondary")
                ex3 = gr.Button("IBM Stats", variant="secondary")
                ex4 = gr.Button("Same for NVDA", variant="secondary")

            with gr.Row(elem_classes="action-row"):
                submit_btn = gr.Button("Submit", variant="primary")
                clear_btn = gr.Button("Clear")

            csv_file = gr.File(
                label="Upload CSV",
                file_types=[".csv"],
                file_count="single",
                elem_id="csv-upload"
            )

        with gr.Column(elem_classes="right-pane"):
            with gr.Group(elem_id="history-wrap"):
                interpretation = gr.Textbox(
                    label="Conversation History",
                    lines=12,
                    max_lines=12,
                    elem_id="history-textbox"
                )
                new_chat_btn = gr.Button(
                    "Clear",
                    variant="secondary",
                    elem_id="clear-history-btn"
                )

    with gr.Accordion(
        "CSV Dataset Summary",
        open=False,
        visible=False
    ) as csv_summary_accordion:
        with gr.Column(elem_classes="csv-summary-panel"):
            with gr.Row(elem_classes="csv-sections-row"):
                with gr.Column(elem_classes="csv-section-col"):
                    gr.Markdown("### Overview", elem_classes="csv-section-title")
                    with gr.Column(elem_classes="csv-section-body"):
                        csv_file_name = gr.Markdown("**File:** —", elem_classes="csv-overview-item")
                        csv_row_count = gr.Markdown("**Rows:** —", elem_classes="csv-overview-item")
                        csv_column_count = gr.Markdown("**Columns:** —", elem_classes="csv-overview-item")
                        csv_missing_total = gr.Markdown("**Missing cells:** —", elem_classes="csv-overview-item")

                with gr.Column(elem_classes="csv-section-col"):
                    gr.Markdown("### Data Types (by Column Groups)", elem_classes="csv-section-title")
                    with gr.Column(elem_classes="csv-section-body"):
                        csv_column_groups = gr.Markdown("")
                        csv_basic_info = gr.Markdown("", visible=False)

                with gr.Column(elem_classes="csv-section-col"):
                    gr.Markdown("### Missing Values (top)", elem_classes="csv-section-title")
                    with gr.Column(elem_classes="csv-section-body"):
                        csv_missing_info = gr.Markdown("")

                with gr.Column(elem_classes="csv-section-col"):
                    gr.Markdown("### Preview (first 5 rows)", elem_classes="csv-section-title")
                    with gr.Column(elem_classes="csv-preview-wrap"):
                        csv_preview = gr.Dataframe(
                            value=[["No preview available"]],
                            headers=["Info"],
                            interactive=False,
                            wrap=True,
                            row_count=(5, "fixed"),
                            col_count=(1, "dynamic"),
                            show_label=False
                        )

            with gr.Row(elem_classes="csv-actions-row"):
                with gr.Column(scale=0, min_width=132):
                    clear_csv_btn = gr.Button("Clear CSV", variant="secondary")

    with gr.Row(elem_classes="io-row"):
        with gr.Column():
            plot_output = gr.Image(
                label="Plot Output",
                height=420,
                elem_id="plot-output"
            )

        with gr.Column():
            execution_output = gr.Textbox(
                label="Execution Output",
                lines=14,
                max_lines=14,
                elem_id="execution-output"
            )

    with gr.Row(elem_classes="code-row"):
        with gr.Column():
            with gr.Group(elem_id="code-output-wrap"):
                code_output = gr.Code(
                    label="Generated Python Code",
                    language="python",
                    lines=12,
                    interactive=False,
                    elem_id="code-output"
                )
                edit_run_btn = gr.Button(
                    "Edit",
                    variant="secondary",
                    elem_id="edit-run-btn"
                )

        with gr.Column():
            with gr.Group(elem_id="code-explain-wrap"):
                code_explanation = gr.Textbox(
                    label="Code Explanation",
                    lines=12,
                    max_lines=12,
                    interactive=False,
                    placeholder="Click 'Explain Code' to see a structured explanation of the current code.",
                    elem_id="code-explanation"
                )
                explain_code_btn = gr.Button(
                    "Explain Code",
                    variant="primary",
                    elem_id="explain-code-btn"
                )

    run_status = gr.Textbox(
        label="Run Status",
        lines=1,
        max_lines=1,
        elem_id="run-status"
    )

    ex1.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["AAPL Trend"]), outputs=prompt)
    ex2.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["TSLA vs MSFT"]), outputs=prompt)
    ex3.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["IBM Stats"]), outputs=prompt)
    ex4.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["Same for NVDA"]), outputs=prompt)

    clear_btn.click(
        fn=clear_prompt,
        outputs=prompt
    )

    new_chat_btn.click(
        fn=new_chat,
        outputs=[interpretation, history_state],
        show_progress="hidden"
    )

    submit_btn.click(
        fn=run_agent_ui,
        inputs=[prompt, history_state, csv_state],
        outputs=[
            code_output,
            execution_output,
            run_status,
            interpretation,
            plot_output,
            history_state,
            prompt,
            edit_mode_state,
            code_output,
            edit_run_btn,
            code_explanation
        ],
        show_progress="minimal"
    )

    edit_run_btn.click(
        fn=handle_edit_or_run,
        inputs=[edit_mode_state, code_output, history_state],
        outputs=[
            code_output,
            code_output,
            edit_run_btn,
            edit_mode_state,
            execution_output,
            run_status,
            interpretation,
            plot_output,
            history_state
        ],
        show_progress="minimal"
    )

    explain_code_btn.click(
        fn=explain_code_ui,
        inputs=[code_output],
        outputs=[code_explanation],
        show_progress="hidden"
    )

    csv_file.change(
        fn=handle_csv_upload,
        inputs=[csv_file],
        outputs=[
            csv_state,
            csv_file_name,
            csv_row_count,
            csv_column_count,
            csv_missing_total,
            csv_basic_info,
            csv_column_groups,
            csv_missing_info,
            csv_preview,
            csv_summary_accordion
        ],
        show_progress="minimal"
    )

    clear_csv_btn.click(
        fn=handle_clear_csv,
        outputs=[
            csv_file,
            csv_state,
            csv_file_name,
            csv_row_count,
            csv_column_count,
            csv_missing_total,
            csv_basic_info,
            csv_column_groups,
            csv_missing_info,
            csv_preview,
            csv_summary_accordion
        ],
        show_progress="hidden"
    )

demo.launch(ssr_mode=False)






