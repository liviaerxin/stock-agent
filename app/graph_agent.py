from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.runnables import RunnableLambda
from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, InjectedState
from langchain_core.messages import AIMessage, ToolMessage
import pandas as pd
from pathlib import Path
from langgraph.types import Command, interrupt
import json
import uuid
from langchain_core.tools import InjectedToolCallId, tool

from langchain.chat_models import init_chat_model
from tenacity import retry, stop_after_attempt, wait_fixed

from app.tools.analysis_tool import *
from app.tools.stock_data_tool import *
from app.tools.code_executer_tool import *
from app.tools.email_tool import *
from app import PERIOD, LLM_MODEL, NUM_NEWS, DATA_DIR

llm = init_chat_model(LLM_MODEL)

# === LangGraph state ===
class State(TypedDict):
    messages: Annotated[list, add_messages]
    stock_symbol: str
    stock_pct: float
    day: str
    period: str
    stock_data: pd.DataFrame
    stock_data_saved_path: str
    stock_analysis: str
    stock_sentiment: str
    tool_status: bool


@tool
def execute_python_code_tool(
    code: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
):
    """Executes Python code in a subprocess with timeout and isolation."""
    result = execute_python_code(code)

    if result["status"] != "success" or not result["output"]:
        return Command(
            update={
                "tool_status": False,
                "messages": [ToolMessage("Fail", tool_call_id=tool_call_id)],
            }
        )
    else:
        return Command(
            update={
                "tool_status": True,
                "stock_analysis": result["output"],
                "messages": [ToolMessage(result["output"], tool_call_id=tool_call_id)],
            }
        )


@tool
def get_top_nasdaq_gainer_tool(
    # # access information that's dynamically updated inside the agent
    # state: Annotated[State, InjectedState],
    # # access static data that is passed at agent invocation
    # config: RunnableConfig,
    tool_call_id: Annotated[str, InjectedToolCallId],
):
    """Get the NASDAQ stock with the highest percentage gain today."""
    data = get_top_nasdaq_gainer()

    symbol = data.get("symbol")
    day = data.get("day")
    pct = data.get("pct")

    state_update = {
        "stock_symbol": symbol,
        "stock_pct": pct,
        "day": day,
    }

    # We return a Command object in the tool to update our state.
    return Command(
        update={
            "stock_symbol": symbol,
            "stock_pct": pct,
            "day": day,
            # update the message history
            "messages": [
                ToolMessage("Successfully get the stock symbol" + json.dumps(state_update), tool_call_id=tool_call_id)
            ],
        }
    )


@tool
def get_and_save_stock_data_tool(
    symbol: str,
    period: str,
    saved_path: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
):
    """Get stock HLCO and volume data in past days, then save to file,
    period format 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max,
    """
    data = get_and_save_stock_data(symbol, period)

    data.to_csv(saved_path, index=True)

    state_update = {
        "stock_data": data.to_dict(),
        "stock_data_saved_path": saved_path,
    }

    # We return a Command object in the tool to update our state.
    return Command(
        update={
            # "stock_data": data.to_dict(),
            "stock_data_saved_path": saved_path,
            # update the message history
            "messages": [
                ToolMessage(
                    "Successfully get and save the stock data" + json.dumps({"stock_data_saved_path": saved_path}),
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )

# === Graph Nodes ===
get_stock_symbol_tool_node = ToolNode([get_top_nasdaq_gainer_tool], name="get_stock_symbol_tool_node")
get_stock_data_tool_node = ToolNode([get_and_save_stock_data_tool], name="get_stock_data_tool_node")
generate_analysis_tool_node = ToolNode([execute_python_code_tool], name="generate_analysis_tool_node")
get_stock_news_tool_node = ToolNode([get_stock_news], name="get_stock_news_tool_node")
send_email_tool_node = ToolNode([send_email], name="send_email_tool_node")


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
def get_stock_data_node(state: State):
    stock_data_saved_path = Path(DATA_DIR).joinpath("{}.csv".format(uuid.uuid4()))
    system_prompt = """
    - Get the stock{symbol} past {period} days data and save to {saved_path}
    """.format(
        symbol=state["stock_symbol"], period=state["period"], saved_path=stock_data_saved_path
    )

    system_message = {
        "role": "system",
        "content": system_prompt,
    }

    llm_with_tools = llm.bind_tools([get_and_save_stock_data_tool])
    response = llm_with_tools.invoke([system_message] + state["messages"])

    return {"messages": [response]}


def generate_analysis_node(state: State):
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
        stock_symbol=state["stock_symbol"], period=state["period"] ,stock_data_saved_path=state["stock_data_saved_path"]
    )

    # print(generate_code_system_prompt)
    system_message = {
        "role": "system",
        "content": generate_code_system_prompt,
    }

    llm_with_tools = llm.bind_tools([execute_python_code_tool], parallel_tool_calls=False, tool_choice="any")
    response = llm_with_tools.invoke([system_message] + state["messages"])

    return {"messages": [response]}

def generate_analysis_fallback_node(state: State):
    tool_call = {
        "name": "generate_analysis_fallback",
        "args": {
            "stock_symbol": state["stock_symbol"],
            "period": state["period"],
        },
        "id": str(uuid.uuid4()),
        "type": "tool_call",
    }

    tool_call_message = AIMessage(content="", tool_calls=[tool_call])
    tool_message = tool(generate_analysis_fallback).invoke(tool_call)
    response = AIMessage(f"fallback to generate analysis: {tool_message.content}")

    # result = generate_analysis_fallback(state["stock_symbol"], state["period"])
    return {"messages": [tool_call_message, tool_message, response], "stock_analysis": tool_message.content}


def generate_sentiment_node(state: State):
    generate_sentiment_system_prompt = """Generate a sentiment the stock {symbol}:
    - Get the stock recent {num_news} news headlines
    """.format(
        symbol=state["stock_symbol"],
        num_news=NUM_NEWS,
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
    - List analysis data from: {analysis}
    - Sentiment: {sentiment}
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

    llm_with_tools = llm.bind_tools([send_email], tool_choice="any")
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
    # Otherwise, we stop (reply to the user)
    else:
        return "NEXT"


def route_after_tool(state: State) -> Literal["NEXT", "FALLBACK"]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
    if state["tool_status"]:
        return "NEXT"
    # Otherwise, we stop (reply to the user)
    else:
        return "FALLBACK"


# === Build the graph ===
# graph = StateGraph(State)
graph = StateGraph(State)

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
# graph.add_edge("generate_analysis_tool_node", "generate_analysis_fallback_node")
graph.add_conditional_edges(
    "generate_analysis_tool_node",
    route_after_tool,
    {
        # Name returned by should_continue : Name of next node to visit
        "NEXT": "generate_sentiment_node",
        "FALLBACK": "generate_analysis_fallback_node",
    },
)
graph.add_edge("generate_analysis_fallback_node", "generate_sentiment_node")

graph.add_conditional_edges(
    "generate_sentiment_node",
    should_continue,
    {
        # Name returned by should_continue : Name of next node to visit
        "NEXT": "generate_summary_node",
        "ACTION": "get_stock_news_tool_node",
    },
)
graph.add_edge("get_stock_news_tool_node", "generate_sentiment_node")

# graph.add_edge("fallback_analysis_node", "generate_summary_node")

# graph.add_edge("safe_code_execution_node", "generate_summary_node")
graph.add_edge("generate_summary_node", "send_email_tool_node")
graph.add_edge("send_email_tool_node", END)

# Compile the graph and run
agent = graph.compile()


if __name__ == "__main__":
    for step in agent.stream(
        {"messages": [], "period": PERIOD},
        # config,
        stream_mode="values",
    ):
        # print(step)
        # for _, v in step.items():
        #     v["messages"][-1].pretty_print()
        if "messages" in step and step["messages"]:
            step["messages"][-1].pretty_print()
