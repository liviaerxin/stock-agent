# === Imports ===
from typing import TypedDict, Annotated, Literal
from pathlib import Path
import uuid
import json
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
from app import config
from app.tools.core.analysis import *
from app.tools.core.stock_data import *
from app.tools.core.code_execution import *
from app.tools.core.email import *


# === Specify config schema ===
class ConfigSchema(TypedDict):
    from_email: str
    to_emails: list[str]
    smtp_server: str
    period: str
    num_news: int
    data_dir: str

# === Define Graph State ===
class State(TypedDict):
    messages: Annotated[list, add_messages]
    stock_symbol: str
    stock_pct: float
    day: str
    stock_data: dict
    stock_data_saved_path: str
    stock_analysis: str
    stock_sentiment: str
    tool_status: bool


# === Stateful Tool  ===
@tool
def execute_python_code_tool(
    code: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
):
    """Execute Python code to analyze stock data.

    Args:
        code (str): python code
        tool_call_id (Annotated[str, InjectedToolCallId]): _description_

    Returns:
        _type_: _description_
    """
    result = execute_python_code(code)

    if result["status"] != "success" or not result["output"]:
        return Command(
            update={
                "tool_status": False,
                "messages": [ToolMessage(result["error"], tool_call_id=tool_call_id)],
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
    """Retrieve today's top NASDAQ stock gainer."""
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
    """Fetch and save stock data to CSV.

    Args:
        symbol (str): stock symbol
        period (str): 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max,
        saved_path (str): file path
        tool_call_id (Annotated[str, InjectedToolCallId]): _description_

    Returns:
        _type_: _description_
    """
    data = get_stock_data(symbol, period)

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


@tool
def send_email_tool(
    subject: str,
    body: str,
    # # access information that's dynamically updated inside the agent
    # state: Annotated[State, InjectedState],
    # # access static data that is passed at agent invocation
    config: RunnableConfig,
    tool_call_id: Annotated[str, InjectedToolCallId],
):
    """
    Sends an email with the given subject and body using SMTP.
    The password is stored in the environment variable `EMAIL_PASSWORD`.

    Args:
        subject (str): Email subject line.
        body (str): Email body text.
    Returns:
        str: Success message if email sent.

    Raises:
        RuntimeError: If email sending fails.
    """

    from_email = config["configurable"]["from_email"]
    to_emails = config["configurable"]["to_emails"]
    smtp_server = config["configurable"]["smtp_server"]

    return send_email_by_smtp(subject=subject, body=body, from_email=from_email, to_emails=to_emails, smtp_server=smtp_server)
