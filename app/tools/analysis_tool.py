from langchain.tools import tool

import json
from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from app import PERIOD, LLM_MODEL
import yfinance as yf

llm = init_chat_model(LLM_MODEL)


def generate_stock_analysis_code(stock_symbol: str) -> str:
    """Generates Python code to analyze a stock

    Args:
        stock_symbol (str): Stock symbol, like `AAPL`.

    Returns:
        str: Python code
        
    The generated Python code will:
      - Analyze past `period` days of stock data for `symbol`.
      - Calculate average daily change.
      - Calculate volatility (std deviation of daily changes).
      - Determine upward/downward trend.
      - List close prices in the period.
      - Output analysis as a JSON dictionary printed at the end.
    """
    prompt = """Write Python code to analyze stock {stock_symbol}:
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
    """.format(
        symbol=stock_symbol, period=PERIOD
    )

    msg = llm.invoke(prompt)
    return msg.content



def generate_stock_analysis_code_default(stock_symbol: str) -> str:
    """Generates Python code to analyze a stock in fallback"""
    code = """
import yfinance as yf

try:
    stock = yf.Ticker("{stock_symbol}")
    hist = stock.history(period='1mo')
    latest_close = hist['Close'][-1]
    previous_close = hist['Close'][-2]
    change = latest_close - previous_close
    change_percent = (change / previous_close) * 100
    analysis = f"{stock_symbol}recent performance: {{change}}"

except Exception as e:
    analysis = f"Error during analysis: {{str(e)}}"
print(analysis)
    """.format(
        stock_symbol
    )

    return code


def generate_analysis_fallback(stock_symbol: str, period: str = "5d") -> str:
    """Generate a fallback stock analysis if the LLM or agent or code execution fails.
    Args:
        symbol (str): Stock ticker symbol, e.g. "AAPL".
        period (str, optional): Time period to fetch data for. Defaults to "5d".
                               Examples: "1d", "5d", "1mo", "1y".
    
    Returns:
        str: analysis string
    """
    stock = yf.Ticker(stock_symbol)
    df = stock.history(period=period)  # Covers 5 trading days

    df["Daily Change"] = df["Close"].pct_change()
    last_5_days = df.tail(5)

    avg_change = last_5_days["Daily Change"].mean()
    volatility = last_5_days["Daily Change"].std()
    net_change = last_5_days["Close"].iloc[-1] - last_5_days["Close"].iloc[0]

    if net_change > 0:
        trend = "upward 📈"
    elif net_change < 0:
        trend = "downward 📉"
    else:
        trend = "flat ➖"

    result = {
        "stock": stock_symbol,
        "period": period,
        "average_daily_change": f"{avg_change:.2f}",
        "volatility": volatility,
        "trend": trend,
        "close_prices": last_5_days["Close"].tolist(),
    }
    return json.dumps(result)


# print(generate_stock_analysis_code("TSLA"))
