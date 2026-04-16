import gradio as gr
from executor import run_agent

with gr.Blocks() as demo:
    gr.Markdown("# AI Data Analysis Agent")

    history_state = gr.State([])

    # Row 1: Prompt + Conversation History
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(
                label="Prompt",
                lines=3,
                placeholder="Enter your request here..."
            )
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