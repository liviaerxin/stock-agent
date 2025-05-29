import subprocess
import tempfile
import json

def execute_python_code(code: str) -> dict:
    """
    Executes Python code in a subprocess with timeout and isolation.
    Returns a JSON string with status, output, and error if any.
    """
    try:
#         code = '''
# import yfinance as yf
# symbol = 'TSLA'
# stock = yf.Ticker(symbol)
# df = stock.history(period="7d")  # Covers 5 trading days

# df["Daily Change %"] = df["Close"].pct_change() * 100
# last_5_days = df.tail(5)

# avg_change = last_5_days["Daily Change %"].mean()
# net_change = last_5_days["Close"].iloc[-1] - last_5_days["Close"].iloc[0]

# if net_change > 0:
#     trend = "upward 📈"
# elif net_change < 0:
#     trend = "downward 📉"
# else:
#     trend = "flat ➖"

# result =  (
#     f"Stock: {symbol}"
#     f"Average Daily Change: {avg_change:.2f}%"
#     f"5-Day Trend: {trend}"
#     f"Close Prices: {last_5_days['Close'].tolist()}"
# )    
# print(result)
# '''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        result = subprocess.run(
            ['python', temp_path],
            capture_output=True,
            text=True,
            timeout=5  # seconds
        )
        
        return {
            "status": "success" if (result.returncode == 0 or not result.stdout) else "failed",
            "output": result.stdout,
            "error": result.stderr
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "error": "Execution timed out"
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }
            
# code = '''
# import yfinance as yf

# try:
#     stock = yf.Ticker('TSLA')
#     hist = stock.history(period='1mo')
#     latest_close = hist['Close'][-1]
#     previous_close = hist['Close'][-2]
#     change = latest_close - previous_close
#     change_percent = (change / previous_close) * 100
#     analysis = f"Tesla (TSLA) recent performance: {change}"

# except Exception as e:
#     analysis = f"Error during analysis: {str(e)}"
# print(analysis)
# '''

code = '''
import pandas as pd
import json

# Load the CSV data
file_path = "/Users/frankchen/Documents/stock-agent/data/xxx.csv"
df = pd.read_csv(file_path, index_col='Date', parse_dates=True)

# Ensure data is sorted by date
df = df.sort_index()

# Calculate daily change
df['Daily Change'] = df['Close'].diff()

# Calculate metrics
average_daily_change = df['Daily Change'].mean()
volatility = df['Daily Change'].std()

# Determine trend
trend = 'UP' if df['Daily Change'].iloc[-1] > 0 else 'DOWN'

# List close prices
close_prices = df['Close'].tolist()

# Prepare analysis result
analysis = {
    "stock": "META",
    "period": "5d",
    "average_daily_change": average_daily_change,
    "volatility": volatility,
    "trend": trend,
    "close_prices": close_prices,
}

json.dumps(analysis)

'''

# print(execute_python_code(code))