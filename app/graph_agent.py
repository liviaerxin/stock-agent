# === Imports ===
from typing import TypedDict, Annotated, Literal
from pathlib import Path
import uuid
import os
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed

from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig

from langchain.chat_models import init_chat_model

# === App Imports ===
from . import config
from .tools.graph_agent_tools import (
    State,
    ConfigSchema,
    get_top_nasdaq_gainer_tool,
    get_and_save_stock_data_tool,
    execute_python_code_tool,
    send_email_tool,
)
from .tools.core.stock_data import get_stock_news
from .tools.core.analysis import generate_analysis_fallback

# === Initialize LLM ===
llm = init_chat_model(config.LLM_MODEL)


# === Graph Nodes ===
get_stock_symbol_tool_node = ToolNode([get_top_nasdaq_gainer_tool], name="get_stock_symbol_tool_node")
get_stock_data_tool_node = ToolNode([get_and_save_stock_data_tool], name="get_stock_data_tool_node")
generate_analysis_tool_node = ToolNode([execute_python_code_tool], name="generate_analysis_tool_node")
get_stock_news_tool_node = ToolNode([get_stock_news], name="get_stock_news_tool_node")
send_email_tool_node = ToolNode([send_email_tool], name="send_email_tool_node")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_stock_symbol_node(state: State):
    system_prompt = """
    - Get the today top performance stock in Nasdaq
    """

    system_message = {
        "role": "system",
        "content": system_prompt,
    }

    llm_with_tools = llm.bind_tools([get_top_nasdaq_gainer_tool])
    response = llm_with_tools.invoke([system_message] + state["messages"])

    return {"messages": [response]}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_stock_data_node(state: State, config: RunnableConfig):
    stock_data_saved_path = os.path.join(config["configurable"]["data_dir"], str(uuid.uuid4()))

    system_prompt = """
    - Get the stock {symbol} past {period} days data and save to {saved_path}
    """.format(
        symbol=state["stock_symbol"], period=config["configurable"]["period"], saved_path=stock_data_saved_path
    )

    system_message = {
        "role": "system",
        "content": system_prompt,
    }

    llm_with_tools = llm.bind_tools([get_and_save_stock_data_tool])
    response = llm_with_tools.invoke([system_message] + state["messages"])

    return {"messages": [response]}


def generate_analysis_node(state: State, config: RunnableConfig):
    generate_code_system_prompt = """Write Python code to analyze the stock {stock_symbol}:
    - The last {period} trading days is in {stock_data_saved_path} file, you can use `pandas` to load the csv file, index is `Date`.
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
    - At the code end, print out the analysis using `print()`

    Only return Python code. No explanation.
        """.format(
        stock_symbol=state["stock_symbol"],
        period=config["configurable"]["period"],
        stock_data_saved_path=state["stock_data_saved_path"],
    )

    # print(generate_code_system_prompt)
    system_message = {
        "role": "system",
        "content": generate_code_system_prompt,
    }

    llm_with_tools = llm.bind_tools([execute_python_code_tool], parallel_tool_calls=False, tool_choice="any")
    response = llm_with_tools.invoke([system_message] + state["messages"])

    return {"messages": [response]}


def generate_analysis_fallback_node(state: State, config: RunnableConfig):
    tool_call = {
        "name": "generate_analysis_fallback",
        "args": {
            "stock_symbol": state["stock_symbol"],
            "period": config["configurable"]["period"],
        },
        "id": str(uuid.uuid4()),
        "type": "tool_call",
    }

    tool_call_message = AIMessage(content="", tool_calls=[tool_call])
    tool_message = tool(generate_analysis_fallback).invoke(tool_call)
    response = AIMessage(f"fallback to generate analysis: {tool_message.content}")

    # result = generate_analysis_fallback(state["stock_symbol"], state["period"])
    return {"messages": [tool_call_message, tool_message, response], "stock_analysis": tool_message.content}


def generate_sentiment_node(state: State, config: RunnableConfig):
    generate_sentiment_system_prompt = """Generate a sentiment the stock {symbol}:
    - Get the stock recent {num_news} news headlines
    """.format(
        symbol=state["stock_symbol"],
        num_news=config["configurable"]["num_news"],
    )

    system_message = {
        "role": "system",
        "content": generate_sentiment_system_prompt,
    }

    llm_with_tools = llm.bind_tools([get_stock_news])
    response = llm_with_tools.invoke([system_message] + state["messages"])

    return {"messages": [response], "stock_sentiment": response.content}


def generate_summary_node(state: State):
    generate_summary_system_prompt = """Generate a summary for the stock based on analysis and sentiment:
    - Include all the analysis data from: {analysis}, including the close prices, etc.
    - Give a sentiment: {sentiment}
    - Use bulletin in body
    - Make the email subject and body to be user friendly
    - Send the summary via email
    """.format(
        analysis=state["stock_analysis"], sentiment=state["stock_sentiment"]
    )

    system_message = {
        "role": "system",
        "content": generate_summary_system_prompt,
    }

    llm_with_tools = llm.bind_tools([send_email_tool], tool_choice="any")
    response = llm_with_tools.invoke([system_message] + state["messages"])

    return {"messages": [response]}


# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state: State) -> Literal["ACTION", "NEXT"]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
    messages = state["messages"]
    last_message = messages[-1]
    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "ACTION"
    else:
        return "NEXT"


def route_after_tool(state: State) -> Literal["NEXT", "FALLBACK"]:
    if state["tool_status"]:
        return "NEXT"
    else:
        return "FALLBACK"


def build_graph():
    # === Build the graph ===
    graph = StateGraph(State, config_schema=ConfigSchema)

    # Add node
    graph.add_node("get_stock_symbol_node", get_stock_symbol_node)
    graph.add_node("get_stock_symbol_tool_node", get_stock_symbol_tool_node)
    graph.add_node("get_stock_data_node", get_stock_data_node)
    graph.add_node("get_stock_data_tool_node", get_stock_data_tool_node)
    graph.add_node("generate_analysis_node", generate_analysis_node)
    graph.add_node("generate_analysis_tool_node", generate_analysis_tool_node)
    graph.add_node("generate_summary_node", generate_summary_node)
    graph.add_node("send_email_tool_node", send_email_tool_node)
    graph.add_node("generate_analysis_fallback_node", generate_analysis_fallback_node)
    graph.add_node("generate_sentiment_node", generate_sentiment_node)
    graph.add_node("get_stock_news_tool_node", get_stock_news_tool_node)

    # Add edges to connect nodes
    graph.add_edge(START, "get_stock_symbol_node")
    graph.add_edge("get_stock_symbol_node", "get_stock_symbol_tool_node")
    graph.add_edge("get_stock_symbol_tool_node", "get_stock_data_node")
    graph.add_edge("get_stock_data_node", "get_stock_data_tool_node")
    graph.add_edge("get_stock_data_tool_node", "generate_analysis_node")

    graph.add_edge("generate_analysis_node", "generate_analysis_tool_node")
    graph.add_conditional_edges(
        "generate_analysis_tool_node",
        route_after_tool,
        {
            "NEXT": "generate_sentiment_node",
            "FALLBACK": "generate_analysis_fallback_node",
        },
    )
    graph.add_edge("generate_analysis_fallback_node", "generate_sentiment_node")

    graph.add_conditional_edges(
        "generate_sentiment_node",
        should_continue,
        {
            "NEXT": "generate_summary_node",
            "ACTION": "get_stock_news_tool_node",
        },
    )
    graph.add_edge("get_stock_news_tool_node", "generate_sentiment_node")
    graph.add_edge("generate_summary_node", "send_email_tool_node")
    graph.add_edge("send_email_tool_node", END)

    # Compile the graph and run
    return graph.compile()


if __name__ == "__main__":
    agent = build_graph()
    for step in agent.stream(
        {"messages": []},
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
        stream_mode="values",
    ):
        # print(step)
        # for _, v in step.items():
        #     v["messages"][-1].pretty_print()
        if "messages" in step and step["messages"]:
            step["messages"][-1].pretty_print()
