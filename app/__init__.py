import json
from pathlib import Path
import json
import os

config = Path(__file__).parent.parent / "config.json"

with open(config.as_posix(), "r") as f:
    config = json.load(f)

PERIOD = config["period"]
NUM_NEWS = config["num_news"]
FROM_EMAIL = config["from_email"]
TO_EMAILS = config["to_emails"]
SMTP_SERVER = config["smtp_server"]
LLM_MODEL = config["llm_model"]


data = Path(__file__).parent.parent / "data"
data.mkdir(parents=True, exist_ok=True)
DATA_DIR = data.as_posix()


STOCK_SYMBOLS_FILE = Path(__file__).parent.parent / "stock_symbols.json"
if STOCK_SYMBOLS_FILE and os.path.isfile(STOCK_SYMBOLS_FILE):
    with open(STOCK_SYMBOLS_FILE,) as f:
        STOCK_SYMBOLS: list = json.loads(f.read())
else:
    STOCK_SYMBOLS = None