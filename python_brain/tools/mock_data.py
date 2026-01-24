import pandas as pd
import numpy as np
import time

def generate_mock_data(symbol="BTCUSDT", days=30, interval_mins=5):
    print(f"Generating mock data for {symbol} with Regimes...")
    periods = int(days * 24 * 60 / interval_mins)

    price = 50000.0

    data = []

    start_ts = int(time.time() * 1000) - periods * interval_mins * 60 * 1000

    # State machine
    state = "chop" # chop, uptrend, downtrend
    state_duration = 0

    for i in range(periods):
        # State transition
        if state_duration <= 0:
            rand = np.random.random()
            if rand < 0.4:
                state = "chop"
                state_duration = np.random.randint(50, 200) # 4-16 hours
            elif rand < 0.7:
                state = "uptrend"
                state_duration = np.random.randint(50, 150)
            else:
                state = "downtrend"
                state_duration = np.random.randint(50, 150)

        state_duration -= 1

        # Trend bias
        bias = 0
        volatility = 0.002

        if state == "uptrend":
            bias = 0.0005 # +0.05% per candle
            volatility = 0.0015
        elif state == "downtrend":
            bias = -0.0005
            volatility = 0.0015
        else:
            bias = 0
            volatility = 0.003 # Higher volatility in chop

        change = np.random.normal(bias, price * volatility)

        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + abs(np.random.normal(0, price * volatility * 0.5))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, price * volatility * 0.5))

        # Volume: higher in trends
        vol_base = 100 if state == "chop" else 200
        vol = np.random.lognormal(np.log(vol_base), 0.5)

        timestamp = start_ts + i * interval_mins * 60 * 1000

        data.append([timestamp, open_p, high_p, low_p, close_p, vol, timestamp, 0,0,0,0,0])
        price = close_p

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    filename = f"data/{symbol}_{interval_mins}m_mock_trend.csv"
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} rows to {filename}")
    return filename

if __name__ == "__main__":
    generate_mock_data()
