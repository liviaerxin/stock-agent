"""
python main.py --full-auto
"""

import typer
from dotenv import load_dotenv, find_dotenv
import getpass
import json
import os
from app import graph_agent, full_auto_agent, config

load_dotenv(find_dotenv())

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = getpass.getpass(prompt="Enter your OpenAI API key (required if using OpenAI): ")

if "EMAIL_PASSWORD" not in os.environ:
    os.environ["EMAIL_PASSWORD"] = getpass.getpass(
        prompt="Enter your EMAIL_PASSWORD (required if google_app_password ): "
    )


app = typer.Typer()


@app.command()
def run(full_auto: bool = typer.Option(False, help="RUN full autonomous ReAct agent")):
    if full_auto:
        agent = full_auto_agent.build_graph()
    else:
        agent = graph_agent.build_graph()

    print(agent.get_graph().draw_ascii())

    # png_bytes = agent.get_graph().draw_mermaid_png()
    # with open("graph.png", "wb") as f:
    #     f.write(png_bytes)

    for step in agent.stream(
        {
            "messages": [],
        },
        config={
            "configurable": {
                "period": config.PERIOD,
                "from_email": config.FROM_EMAIL,
                "to_emails": config.TO_EMAILS,
                "smtp_server": config.SMTP_SERVER,
                "num_news": config.NUM_NEWS,
                "data_dir": config.DATA_DIR,
            }
        },
        # config,
        stream_mode="updates",
    ):
        # print(step)
        for _, v in step.items():
            v["messages"][-1].pretty_print()


# for step in agent.stream(
#     {"messages": [{"role": "user", "content": user_input}]},
#     config,
#     stream_mode="values"
# ):
#     step["messages"][-1].pretty_print()

if __name__ == "__main__":
    app()
