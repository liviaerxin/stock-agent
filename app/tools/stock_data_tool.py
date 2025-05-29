from langchain.tools import tool
from pathlib import Path
import yfinance as yf
import pandas as pd
import os
import json
from app import STOCK_SYMBOLS


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
    if not STOCK_SYMBOLS:
        # Get NASDAQ-100 symbols from Wikipedia
        url = "https://en.wikipedia.org/wiki/NASDAQ-100"
        tables = pd.read_html(url)
        df = tables[4]  # The 5th table contains the companies list
        nasdaq_100_symbols = df["Ticker"].tolist()
        tickers = nasdaq_100_symbols
    else:
        tickers = STOCK_SYMBOLS
        
    data = yf.download(tickers, period="2d", threads=True, progress=False)
    pct = data["Close"].pct_change()
    pct.columns = pd.MultiIndex.from_product([["pct"], pct.columns])
    data = pd.concat([data, pct], axis=1)
    top_stock_symbol = data["pct"].iloc[-1].idxmax()
    top_stock_gain = data["pct"].iloc[-1].max()
    day = data["pct"].iloc[-1].name

    # print("{} gain {} the highest percentage gain at {}".format(top_stock_symbol, top_stock_gain, day))

    return {
        "symbol": top_stock_symbol,
        "pct": f"{top_stock_gain:.2f}",
        "day": day.isoformat(),
    }


def get_and_save_stock_data(symbol: str, period: str = "5d") -> pd.DataFrame:
    """
    Fetch historical stock data (Open, High, Low, Close, Volume) for the given symbol.

    Args:
        symbol (str): Stock ticker symbol, e.g. "AAPL".
        period (str, optional): Time period to fetch data for. Defaults to "5d".
                               Examples: "1d", "5d", "1mo", "1y".
    
    Returns:
        pd.DataFrame: DataFrame with historical OHLC and volume data.
    """
    data = yf.Ticker(symbol).history(period=period)
    
    return data


def get_stock_news(symbol: str, last_n_news:int=5) -> list:
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