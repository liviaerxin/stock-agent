"""
python main.py --full-auto-agent
"""

import typer
from dotenv import load_dotenv, find_dotenv
import getpass
import json
import os
from app import full_auto_agent, graph_agent, PERIOD

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
        agent = full_auto_agent.agent
    else:
        agent = graph_agent.agent

    print(agent.get_graph().draw_ascii())
    
    # png_bytes = agent.get_graph().draw_mermaid_png()
    # with open("graph.png", "wb") as f:
    #     f.write(png_bytes)
    
    for step in agent.stream(
        {
            "messages": [],
            "period": PERIOD,
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
