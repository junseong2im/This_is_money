import pandas as pd
import numpy as np
from core.data_processor import DataProcessor

def test_processor():
    # Mock data: 50 candles
    data = []
    base_price = 50000.0
    for i in range(50):
        price = base_price + np.random.normal(0, 50)
        high = price + 10
        low = price - 10
        volume = 100 + np.random.normal(0, 10)
        # [timestamp, open, high, low, close, volume, ...]
        row = [
            1600000000000 + i*300000,
            price, high, low, price, volume,
            0, 0, 0, 0, 0, 0
        ]
        data.append(row)
        base_price = price

    df = DataProcessor.to_dataframe(data)
    print("DataFrame shape:", df.shape)

    df_processed = DataProcessor.add_indicators(df)
    print("Processed Columns:", df_processed.columns)

    # Check last row
    last = df_processed.iloc[-1]
    print("\nLast Row Features:")
    print(f"Price: {last['close']}")
    print(f"ADX: {last['adx']}")
    print(f"ATR: {last['atr_value']}")
    print(f"EMA Fast Slope: {last['ema_fast_slope']}")

    assert 'adx' in df_processed.columns
    assert 'atr_value' in df_processed.columns
    assert not np.isnan(last['adx']), "ADX should not be NaN (after enough data)"

if __name__ == "__main__":
    test_processor()
