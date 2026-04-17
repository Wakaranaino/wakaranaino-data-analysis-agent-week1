import gradio as gr
from executor import run_agent

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
    return code, execution_output, run_status, interpretation, plot_output, updated_history, ""


css = """
.compact-gap {margin-top: -10px;}
.example-row button {
    min-height: 42px !important;
}
"""

with gr.Blocks(css=css) as demo:
    gr.Markdown("# AI Data Analysis Agent")

    history_state = gr.State([])

    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(
                label="Prompt",
                lines=3,
                placeholder="Try: Plot AAPL closing prices for the last 100 days"
            )

            with gr.Row(elem_classes="example-row"):
                ex1 = gr.Button("AAPL Trend", size="sm")
                ex2 = gr.Button("TSLA vs MSFT", size="sm")
                ex3 = gr.Button("IBM Stats", size="sm")
                ex4 = gr.Button("Same for NVDA", size="sm")

            with gr.Row(elem_classes="compact-gap"):
                clear_btn = gr.Button("Clear")
                submit_btn = gr.Button("Submit", variant="primary")

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
        lines=12
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
            prompt
        ]
    )

demo.launch(ssr_mode=False)