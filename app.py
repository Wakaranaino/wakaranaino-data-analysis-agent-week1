import gradio as gr
from executor import run_agent

EXAMPLE_PROMPTS = {
    "AAPL Trend (100d)": "Plot AAPL closing prices for the last 100 days",
    "TSLA vs MSFT Chart": "Plot Tesla (TSLA) and Microsoft (MSFT) monthly returns for the last 1 year",
    "TSLA vs MSFT t-test": "Run a t-test on Tesla (TSLA) and Microsoft (MSFT) monthly returns over the last 1 year",
    "IBM Stats (100d)": "Show mean, median, standard deviation, min, and max of IBM closing prices for the last 100 days",
    "What about NVDA?": "What about NVDA?"
}


def fill_prompt(text):
    return text


with gr.Blocks() as demo:
    gr.Markdown("# AI Data Analysis Agent")

    history_state = gr.State([])

    # Row 1: Prompt + Conversation History
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(
                label="Prompt",
                lines=3,
                placeholder="Try: Plot AAPL closing prices for the last 100 days"
            )

            gr.Markdown("**Suggested prompts:**")
            with gr.Row():
                ex1 = gr.Button("AAPL Trend (100d)", size="sm")
                ex2 = gr.Button("TSLA vs MSFT Chart", size="sm")
                ex3 = gr.Button("TSLA vs MSFT t-test", size="sm")
                ex4 = gr.Button("IBM Stats (100d)", size="sm")
                ex5 = gr.Button("What about NVDA?", size="sm")

            submit_btn = gr.Button("Submit", variant="primary")

        with gr.Column():
            interpretation = gr.Textbox(
                label="Conversation History",
                lines=12
            )

    # Row 2: Plot + Execution Output
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

    # Row 3: Generated Python Code
    code_output = gr.Code(
        label="Generated Python Code",
        language="python",
        lines=12
    )

    # Row 4: Run Status
    run_status = gr.Textbox(
        label="Run Status",
        lines=1
    )

    ex1.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["AAPL Trend (100d)"]), outputs=prompt)
    ex2.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["TSLA vs MSFT Chart"]), outputs=prompt)
    ex3.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["TSLA vs MSFT t-test"]), outputs=prompt)
    ex4.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["IBM Stats (100d)"]), outputs=prompt)
    ex5.click(fn=lambda: fill_prompt(EXAMPLE_PROMPTS["What about NVDA?"]), outputs=prompt)

    submit_btn.click(
        fn=run_agent,
        inputs=[prompt, history_state],
        outputs=[
            code_output,
            execution_output,
            run_status,
            interpretation,
            plot_output,
            history_state
        ]
    )

demo.launch(ssr_mode=False)