import pandas as pd
import numpy as np
import time

def generate_realistic_crypto_data(symbol="BTCUSDT", days=60, interval_mins=5):
    """
    Generates 'Realistic' Crypto Data with:
    1. Regime Switching (Bull, Bear, Chop, Pump, Dump)
    2. Volatility Clustering (GARCH-like behavior)
    3. Noise & Anomalies (Wicks)
    """
    print(f"Generating REALISTIC crypto data for {symbol}...")
    periods = int(days * 24 * 60 / interval_mins)

    # Starting Price
    price = 50000.0

    # State Machine Config
    # (Regime Name, Duration Mean, Duration Std, Drift Mean, Drift Std, Volatility, Volatility of Vol)
    regimes = {
        "bull_trend":  {"dur": 300, "drift": 0.0002, "vol": 0.002},  # Steady up
        "bear_trend":  {"dur": 300, "drift": -0.0002, "vol": 0.002}, # Steady down
        "chop":        {"dur": 500, "drift": 0.0,     "vol": 0.001}, # Low vol ranging
        "high_vol_chop":{"dur": 200, "drift": 0.0,    "vol": 0.005}, # Dangerous ranging
        "pump":        {"dur": 50,  "drift": 0.001,   "vol": 0.008}, # Violent Up
        "dump":        {"dur": 50,  "drift": -0.001,  "vol": 0.008}, # Violent Down
    }

    current_regime = "chop"
    regime_timer = 0

    data = []
    start_ts = int(time.time() * 1000) - periods * interval_mins * 60 * 1000

    # History for indicators
    prices = []

    for i in range(periods):
        # 1. State Transition
        if regime_timer <= 0:
            # Pick new regime based on logic (Markov chain simplified)
            r = np.random.random()
            if current_regime == "chop":
                # Chop -> Trend or Breakout
                if r < 0.4: next_r = "chop"
                elif r < 0.7: next_r = "bull_trend"
                else: next_r = "bear_trend"
            elif current_regime in ["bull_trend", "bear_trend"]:
                # Trend -> Chop or Reversal or Acceleration
                if r < 0.5: next_r = current_regime # Continue
                elif r < 0.8: next_r = "chop"
                else: next_r = "pump" if current_regime == "bull_trend" else "dump"
            else:
                # Extreme -> Chop
                next_r = "high_vol_chop"

            current_regime = next_r
            # Set duration
            cfg = regimes[current_regime]
            regime_timer = int(np.random.normal(cfg["dur"], cfg["dur"]*0.2))
            regime_timer = max(10, regime_timer)

        regime_timer -= 1
        cfg = regimes[current_regime]

        # 2. Price Movement
        # Drift + Noise
        drift = cfg["drift"]
        vol = cfg["vol"]

        # Fat tail event? (1% chance of 5-sigma move)
        if np.random.random() < 0.001:
            vol *= 5

        change_pct = np.random.normal(drift, vol)

        # Autocorrelation (Momentum) - 20% of previous move persists
        if i > 1:
            prev_change = (prices[-1] - prices[-2]) / prices[-2]
            change_pct = change_pct * 0.8 + prev_change * 0.2

        price = price * (1 + change_pct)
        prices.append(price)

        # 3. Candle Formation
        # Open is usually prev close
        open_p = prices[-2] if i > 0 else price
        close_p = price

        # High/Low wicks based on volatility
        wick_len = price * vol * np.random.random()
        high_p = max(open_p, close_p) + wick_len
        low_p = min(open_p, close_p) - wick_len

        # Volume (Higher in trends/pumps)
        vol_base = 1000
        if "pump" in current_regime or "dump" in current_regime: vol_base *= 5
        if "trend" in current_regime: vol_base *= 2
        volume = np.random.lognormal(np.log(vol_base), 0.5)

        ts = start_ts + i * interval_mins * 60 * 1000
        data.append([ts, open_p, high_p, low_p, close_p, volume, ts+1, 0,0,0,0,0])

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    filename = f"data/{symbol}_REALISTIC_{days}d.csv"
    import os
    if not os.path.exists("data"): os.makedirs("data")
    df.to_csv(filename, index=False)
    print(f"Generated {len(df)} candles of realistic data -> {filename}")
    return filename

if __name__ == "__main__":
    generate_realistic_crypto_data()
