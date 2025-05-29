from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent, ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import Tool

from app.tools.analysis_tool import *
from app.tools.stock_data_tool import *
from app.tools.code_executer_tool import *
from app.tools.email_tool import * 
from app import PERIOD, LLM_MODEL

model = init_chat_model(
    LLM_MODEL,
    temperature=0
)

tool_node = ToolNode([get_top_nasdaq_gainer, generate_stock_analysis_code, get_stock_news, execute_python_code, generate_analysis_fallback, send_email])


system_prompt = """
You are an autonomous agent tasked with generating and executing stock analysis.

You are an autonomous stock analyst. Use the tools provided to:
1. Fetch the top NASDAQ gainer using `get_top_nasdaq_gainer`.
2. Generate analysis code in Python, it can
    - Analyze past {period} days data
    - Calculate average daily change
    - Calculate volatility (std deviation of Daily Changes)
    - Determine upward/downward trend
    - List close prices in this period 
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
4. After generating analysis, get the latest {n_news} stock news headline by `get_stock_news`, then analyze the sentiments.
5. Using both of the data analysis and the sentiment to make a summary for email friendly.
6. Finally send the summary via email using tool `send_email`.

Plan and complete the task end-to-end.

Be robust. Do not ask the user. Complete this task end-to-end autonomously.
""".format(period=PERIOD, n_news=5)


agent = create_react_agent(
    model=model,
    tools=tool_node,
    prompt=system_prompt,
    # checkpointer=checkpointer,
    # response_format=WeatherResponse,
)


# Run the agent

# user_input = "Find the top NASDAQ stock today, analyze its past 5 days, then send the analysis via email"
# user_input = "Find the top NASDAQ stock today, then analyze its past 5 days, and finally email the results to me."

# for step in agent.stream(
#     {"messages": [{"role": "user", "content": ""}]},
#     # config,
#     stream_mode="updates"
# ):
#     # print(step)
#     for _, v in step.items():
#         v["messages"][-1].pretty_print()

# for step in agent.stream(
#     {"messages": [{"role": "user", "content": user_input}]},
#     config,
#     stream_mode="values"
# ):
#     step["messages"][-1].pretty_print()