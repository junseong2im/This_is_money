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
    def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators: EMA, ATR, ADX, VolumeZ, Returns.
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
        # TR is already calculated
        # Directional Movement
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

        # Smoothed
        # For simplicity and matching common implementations (like Wilder's),
        # we can use rolling mean or exponential. Original code used simple sum of last 14.
        # We will use rolling mean * 14 to match "sum of last 14" logic implicitly or just use rolling mean.
        # Original: sum(last 14)
        # Here: rolling(14).sum()

        roll_tr = df['tr'].rolling(window=14).sum()
        roll_plus = df['plus_dm'].rolling(window=14).sum()
        roll_minus = df['minus_dm'].rolling(window=14).sum()

        df['plus_di'] = 100 * (roll_plus / roll_tr)
        df['minus_di'] = 100 * (roll_minus / roll_tr)

        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])

        # ADX is usually smoothed DX. Original code used DX as ADX directly.
        # We will follow original logic for now but keep it in mind for upgrade.
        # "adx = dx  # 단순화 (실제는 smoothed)" -> Let's keep this simplification or make it slightly better.
        # Let's use a 14-period rolling mean of DX to be more "real" ADX?
        # No, let's stick to the user's logic first to avoid breaking logic, but maybe smooth it slightly.
        # Actually, let's stick to the simplified version to match `main.py` behavior exactly first,
        # or upgrade it. The prompt asked to "upgrade". So let's smooth it.
        df['adx'] = df['dx'].rolling(window=14).mean()

        # 4. Volume Z-Score
        # Original: using all available volumes for mean/std.
        # In streaming/windowed context, we usually use a rolling window.
        # `main.py` downloaded 30 candles and used all of them.
        # We will use a rolling window of 30 to match that "lookback" spirit.
        df['vol_mean'] = df['volume'].rolling(window=30).mean()
        df['vol_std'] = df['volume'].rolling(window=30).std()
        df['volume_z'] = (df['volume'] - df['vol_mean']) / df['vol_std']

        # 5. Returns
        df['ret_5'] = df['close'].pct_change(periods=1) # If data is 5m candles, this is 5m return
        df['ret_1'] = df['ret_5'] / 5 # Approximation

        # Fill NaNs
        df = df.fillna(0)

        return df
