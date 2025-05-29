import pandas as pd
import json

url = "https://en.wikipedia.org/wiki/NASDAQ-100"
tables = pd.read_html(url)
df = tables[4]  # The 5th table contains the companies list
symbols = df["Ticker"].tolist()
with open("./stock_symbols.json", "w") as f:
    json.dump(symbols, f)