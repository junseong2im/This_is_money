import pandas as pd
import numpy as np
from typing import List, Dict

class DataProcessor:
    """
    Process raw market data into features using Pandas for performance and accuracy.
    """

    @staticmethod
    def to_dataframe(klines: List[List]) -> pd.DataFrame:
        """
        Convert Binance kline format to DataFrame.
        Klines format: [open_time, open, high, low, close, volume, ...]
        """
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])

        # Numeric conversion
        cols = ["open", "high", "low", "close", "volume"]
        df[cols] = df[cols].astype(float)

        # Keep necessary columns
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        return df

    @staticmethod
    def calculate_hurst(series: pd.Series, max_lags: int = 20) -> float:
        """
        Calculate the Hurst Exponent of a time series.
        H < 0.5: Mean Reverting
        H ~ 0.5: Random Walk
        H > 0.5: Trending
        """
        lags = range(2, max_lags)
        tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]

        # Avoid log(0)
        tau = [t if t > 0 else 1e-10 for t in tau]

        # Polyfit log(lags) vs log(tau)
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0

    @staticmethod
    def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators: EMA, ATR, ADX, VolumeZ, Returns, Hurst.
        """
        df = df.copy()

        # 1. EMA
        df['ema_fast'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()

        # EMA Slope (normalized)
        df['ema_fast_slope'] = (df['ema_fast'] - df['ema_fast'].shift(1)) / df['ema_fast'].shift(1)
        df['ema_slow_slope'] = (df['ema_slow'] - df['ema_slow'].shift(1)) / df['ema_slow'].shift(1)

        # 2. ATR (14)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr_value'] = df['tr'].rolling(window=14).mean()
        df['atr_pct'] = df['atr_value'] / df['close']

        # 3. ADX (14)
        df['up_move'] = df['high'] - df['high'].shift(1)
        df['down_move'] = df['low'].shift(1) - df['low']

        df['plus_dm'] = np.where(
            (df['up_move'] > df['down_move']) & (df['up_move'] > 0),
            df['up_move'],
            0
        )
        df['minus_dm'] = np.where(
            (df['down_move'] > df['up_move']) & (df['down_move'] > 0),
            df['down_move'],
            0
        )

        roll_tr = df['tr'].rolling(window=14).sum()
        roll_plus = df['plus_dm'].rolling(window=14).sum()
        roll_minus = df['minus_dm'].rolling(window=14).sum()

        df['plus_di'] = 100 * (roll_plus / roll_tr)
        df['minus_di'] = 100 * (roll_minus / roll_tr)

        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(window=14).mean()

        # 4. Volume Z-Score
        df['vol_mean'] = df['volume'].rolling(window=30).mean()
        df['vol_std'] = df['volume'].rolling(window=30).std()
        df['volume_z'] = (df['volume'] - df['vol_mean']) / df['vol_std']

        # 5. Returns
        df['ret_5'] = df['close'].pct_change(periods=1)
        df['ret_1'] = df['ret_5'] / 5

        # 6. Hurst Exponent (Rolling)
        # We need a rolling window to calculate Hurst.
        # Standard window is 100 periods to be statistically significant,
        # but for speed in this bot we might use 50-100.
        # This is computationally expensive, so use apply carefully.

        # Using a lambda with rolling apply
        hurst_window = 100

        # Simplified Hurst calculation helper
        def get_hurst(x):
            try:
                # x is numpy array
                lags = range(2, 20)
                # Calculate diffs for various lags
                # This is R/S analysis simplified or Generalized Hurst
                # Method: std of differences
                tau = []
                for lag in lags:
                    # diff = x[lag:] - x[:-lag] -> this is wrong index wise for a small window
                    # correct:
                    diff = x[lag:] - x[:-lag]
                    s = np.std(diff)
                    tau.append(s if s > 0 else 1e-10)

                poly = np.polyfit(np.log(lags), np.log(tau), 1)
                return poly[0] * 2.0
            except:
                return 0.5

        # We will only calculate for the last few rows in production,
        # but for backtest we need it all.
        # Rolling apply is slow in Pandas.
        # Let's optimize: only calculate if needed or accept slowness in backtest.
        # For production (main.py), we pass ~100 candles, so it's fast.

        df['hurst'] = df['close'].rolling(window=hurst_window).apply(get_hurst, raw=True)

        # Fill NaNs
        df = df.fillna(0)

        # If hurst is 0 (filled NaNs), set to 0.5 (random walk)
        df['hurst'] = df['hurst'].replace(0, 0.5)

        return df
