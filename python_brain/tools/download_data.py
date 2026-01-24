import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta

def download_klines(symbol="BTCUSDT", interval="5m", days=30, save_path="data"):
    base_url = "https://fapi.binance.com/fapi/v1/klines"
    limit = 1000

    end_time = int(time.time() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

    all_klines = []

    print(f"Downloading {days} days of {interval} data for {symbol}...")

    current_start = start_time

    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "startTime": current_start,
            "endTime": end_time
        }

        try:
            r = requests.get(base_url, params=params)
            r.raise_for_status()
            data = r.json()

            if not data:
                break

            all_klines.extend(data)

            last_timestamp = data[-1][0]
            current_start = last_timestamp + 1

            print(f"Downloaded {len(data)} candles, up to {datetime.fromtimestamp(last_timestamp/1000)}")

            if len(data) < limit or last_timestamp >= end_time:
                break

            time.sleep(0.1)

        except Exception as e:
            print(f"Error: {e}")
            break

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # Columns
    cols = [
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ]

    df = pd.DataFrame(all_klines, columns=cols)
    filename = f"{save_path}/{symbol}_{interval}_{days}d.csv"
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} rows to {filename}")
    return filename

if __name__ == "__main__":
    download_klines()
