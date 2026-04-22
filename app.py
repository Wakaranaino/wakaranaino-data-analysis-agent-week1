import gradio as gr
from executor import run_agent, run_edited_code
from llm import explain_code

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


def run_agent_ui(prompt, history_state):
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
        history_html,
        plot_output,
        updated_history
    )


def explain_code_ui(code):
    return explain_code(code)


css = """
.example-row {
    gap: 8px !important;
    margin-top: -6px !important;
    margin-bottom: 10px !important;
    flex-wrap: nowrap !important;
}
.example-row button {
    min-width: unset !important;
    width: auto !important;
    min-height: 34px !important;
    height: 34px !important;
    padding: 0 14px !important;
    font-size: 14px !important;
    border-radius: 18px !important;
    flex: 0 0 auto !important;
}
.action-row {
    margin-top: -2px !important;
    gap: 10px !important;
}
.action-row button {
    min-height: 42px !important;
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
#explain-code-btn {
    width: 145px !important;
    min-width: 145px !important;
    border-radius: 14px !important;
}
#history-wrap {
    position: relative;
}
.history-panel-title {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: var(--body-text-color) !important;
    margin: 0 0 10px 0 !important;
}
#history-wrap #clear-history-btn {
    position: absolute !important;
    top: 7px;
    right: 14px;
    z-index: 20;
    height: 24px !important;
    min-height: 24px !important;
    width: 78px !important;
    min-width: 78px !important;
    max-width: 78px !important;
    padding: 0 !important;
    font-size: 13px !important;
    line-height: 24px !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
}

"""

with gr.Blocks(css=css) as demo:
    gr.Markdown("# AI Data Analysis Agent")

    history_state = gr.State([])
    edit_mode_state = gr.State(False)

    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(
                label="Prompt",
                lines=3,
                placeholder="Try: Plot AAPL closing prices for the last 100 days"
            )

            with gr.Row(elem_classes="example-row"):
                ex1 = gr.Button("AAPL Trend", variant="secondary")
                ex2 = gr.Button("TSLA vs MSFT", variant="secondary")
                ex3 = gr.Button("IBM Stats", variant="secondary")
                ex4 = gr.Button("Same for NVDA", variant="secondary")

            with gr.Row(elem_classes="action-row"):
                submit_btn = gr.Button("Submit", variant="primary")
                clear_btn = gr.Button("Clear")

        with gr.Column():
            with gr.Group(elem_id="history-wrap"):
                interpretation = gr.Textbox(
                    label="Conversation History",
                    lines=12,
                    elem_id="history-textbox"
                )
                new_chat_btn = gr.Button(
                    "Clear",
                    variant="secondary",
                    elem_id="clear-history-btn"
                )

    with gr.Row():
        with gr.Column():
            plot_output = gr.Image(
                label="Plot Output",
                height=420
            )

        with gr.Column():
            execution_output = gr.Textbox(
                label="Execution Output",
                lines=14
            )

    with gr.Row():
        with gr.Column():
            code_output = gr.Code(
                label="Generated Python Code",
                language="python",
                lines=12,
                interactive=False
            )

            with gr.Row(elem_classes="panel-action-row"):
                edit_run_btn = gr.Button(
                    "Edit",
                    variant="secondary",
                    elem_id="edit-run-btn"
                )

        with gr.Column():
            code_explanation = gr.Textbox(
                label="Code Explanation",
                lines=12,
                interactive=False,
                placeholder="Click 'Explain Code' to see a structured explanation of the current code."
            )

            with gr.Row(elem_classes="panel-action-row"):
                explain_code_btn = gr.Button(
                    "Explain Code",
                    variant="primary",
                    elem_id="explain-code-btn"
                )

    run_status = gr.Textbox(
        label="Run Status",
        lines=1
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
        inputs=[prompt, history_state],
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
        show_progress="hidden"
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
        show_progress="hidden"
    )

    explain_code_btn.click(
        fn=explain_code_ui,
        inputs=[code_output],
        outputs=[code_explanation],
        show_progress="hidden"
    )

demo.launch(ssr_mode=False)








