import gradio as gr
from executor import run_agent, run_edited_code

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


def run_agent_ui(prompt, history_state):
    code, execution_output, run_status, interpretation, plot_output, updated_history = run_agent(prompt, history_state)
    return (
        code,
        execution_output,
        run_status,
        interpretation,
        plot_output,
        updated_history,
        "",          # clear prompt
        False,       # edit_mode_state
        gr.update(interactive=False),
        gr.update(value="Edit")
    )


def handle_edit_or_run(edit_mode, prompt, code, history_state):
    # First click: switch into edit mode
    if not edit_mode:
        return (
            code,                         # keep current code
            gr.update(interactive=True),  # make code editable
            gr.update(value="Run"),       # button label
            True,                         # edit_mode_state
            gr.update(),                  # execution_output unchanged
            gr.update(),                  # run_status unchanged
            gr.update(),                  # interpretation unchanged
            gr.update(),                  # plot_output unchanged
            history_state                 # history unchanged
        )

    # Second click: run manually edited code
    execution_output, run_status, interpretation, plot_output, updated_history = run_edited_code(
        prompt=prompt,
        code=code,
        history_state=history_state
    )

    return (
        code,                          # keep edited code visible
        gr.update(interactive=False),  # lock code box again
        gr.update(value="Edit"),       # button label back
        False,                         # edit_mode_state
        execution_output,
        run_status,
        interpretation,
        plot_output,
        updated_history
    )


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
                edit_run_btn = gr.Button("Edit", variant="secondary")

        with gr.Column():
            interpretation = gr.Textbox(
                label="Conversation History",
                lines=12
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

    code_output = gr.Code(
        label="Generated Python Code",
        language="python",
        lines=12,
        interactive=False
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
            edit_run_btn
        ]
    )

    edit_run_btn.click(
        fn=handle_edit_or_run,
        inputs=[edit_mode_state, prompt, code_output, history_state],
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
        ]
    )

demo.launch(ssr_mode=False)