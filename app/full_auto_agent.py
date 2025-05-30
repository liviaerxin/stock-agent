from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent, ToolNode

from app.tools.core.analysis import *
from app.tools.core.stock_data import *
from app.tools.core.code_execution import *
from app.tools.core.email import *

from app import config

model = init_chat_model(
    config.LLM_MODEL,
    temperature=0
)

tool_node = ToolNode([get_top_nasdaq_gainer, get_stock_news, execute_python_code, generate_analysis_fallback, send_email_by_smtp])

system_prompt = """
You are an autonomous agent tasked with generating and executing stock analysis.

You are an autonomous stock analyst. Use the tools provided to:
1. Fetch the top NASDAQ gainer using `get_top_nasdaq_gainer`.
2. Generate analysis code in Python, it can
    - Analyze past {period} days data
    - Calculate average daily change
    - Calculate volatility (std deviation of Daily Changes)
    - Determine upward/downward trend
    - Put the analysis in json, example like
    ```
    analysis = {{
        "stock": "symbol",
        "period": "5d",
        "average_daily_change": 0.2,
        "volatility": 0.2,
        "trend": "UP",
        "close_prices": [123, 123, 133, 344, 123],
    }}
    ```
    - At the code end, print out the analysis using `print()`.
3. Run the analysis python code via `execute_python_code`, if failed, try use fallback `generate_analysis_fallback` to generate analysis.
4. After getting analysis, get the latest {n_news} stock news headline by `get_stock_news`, then analyze the sentiments.
5. Using all the analysis data and the sentiment to make a summary (including `all the analysis data`)for email friendly.
6. Finally send email including the summary by tool `send_email_by_smtp`.
    - sender email: {from_email}
    - recipient email address: {to_emails}
    - SMTP server: {smtp_server}
Do it step by step.

Be robust. Do not ask the user. Complete this task end-to-end autonomously.
""".format(period=config.PERIOD, n_news=config.NUM_NEWS, from_email=config.FROM_EMAIL, to_emails=config.TO_EMAILS, smtp_server=config.SMTP_SERVER)

def build_graph():
    graph = create_react_agent(
        model=model,
        tools=tool_node,
        prompt=system_prompt,
    )

    return graph

if __name__ == "__main__":
    agent = build_graph()
    # Run the agent

    # user_input = "Find the top NASDAQ stock today, analyze its past 5 days, then send the analysis via email"
    # user_input = "Find the top NASDAQ stock today, then analyze its past 5 days, and finally email the results to me."

    for step in agent.stream(
        {"messages": [{"role": "user", "content": ""}]},
        # config,
        stream_mode="updates"
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