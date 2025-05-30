from typing import List, Optional
from langchain.tools import tool
from pathlib import Path
import yfinance as yf
import pandas as pd
from app import config

# tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META"]  # example subset


def get_top_nasdaq_gainer() -> dict:
    """
    Get the NASDAQ stock with the highest percentage gain today.

    Returns:
        dict: {
            "symbol": str,     # Stock symbol with highest gain
            "pct": str,        # Percentage gain as string formatted to 2 decimals
            "day": str         # Date string in ISO format (YYYY-MM-DD)
        }
    """
    if config.STOCK_SYMBOLS:
        # Get NASDAQ-100 symbols from Wikipedia
        url = "https://en.wikipedia.org/wiki/NASDAQ-100"
        tables = pd.read_html(url)
        df = tables[4]  # The 5th table contains the companies list
        nasdaq_100_symbols = df["Ticker"].tolist()
        tickers = nasdaq_100_symbols
    else:
        tickers = config.STOCK_SYMBOLS

    data = yf.download(tickers, period="2d", threads=True, progress=False)
    pct = data["Close"].pct_change()
    pct.columns = pd.MultiIndex.from_product([["pct"], pct.columns])
    data = pd.concat([data, pct], axis=1)
    top_stock_symbol = data["pct"].iloc[-1].idxmax()
    top_stock_gain = data["pct"].iloc[-1].max()
    day = data["pct"].iloc[-1].name

    return {
        "symbol": top_stock_symbol,
        "pct": f"{top_stock_gain:.2f}",
        "day": day.isoformat(),
    }


def get_stock_data(symbol: str, period: str = "5d") -> pd.DataFrame:
    """
    Fetch stock data for the given symbol and period.
    Args:
        symbol (str): Stock ticker symbol, e.g. "AAPL".
        period (str, optional): Period for which to fetch data. Defaults to "5d".
    Returns:
        pd.DataFrame: DataFrame containing stock data.
    """

    data = yf.Ticker(symbol).history(period=period)

    return data


def get_stock_news(symbol: str, last_n_news: int = 5) -> list:
    """
    Fetch recent news headlines for the given stock symbol.

    Args:
        symbol (str): Stock ticker symbol, e.g. "AAPL".
        last_n_news (int, optional): Number of recent news articles to retrieve. Defaults to 5.

    Returns:
        list: List of news items (dictionaries). Empty list if no news found.
    """
    ticker = yf.Ticker(symbol)
    return ticker.news[-last_n_news:-1]
