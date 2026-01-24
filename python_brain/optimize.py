import itertools
import pandas as pd
import numpy as np
from core.strategies.breakout import BreakoutStrategy
from core.strategies.trend import TrendStrategy
from core.strategies.mean_reversion import MeanReversionStrategy
from backtest_engine import BacktestEngine
from tools.mock_data import generate_mock_data

def optimize():
    print("Generating optimization dataset...")
    csv_path = generate_mock_data("BTCUSDT_OPT", days=60, interval_mins=5)

    # Define Parameter Grid
    # We will patch the class attributes directly for the test

    param_grid = {
        "breakout": {
            "MIN_ADX": [15, 20, 25],
            "BASE_SL_ATR": [1.0, 1.2, 1.5],
            "BASE_TP_ATR": [2.0, 3.0]
        },
        "trend": {
            "MIN_ADX": [15, 20, 25],
            "MIN_ATR_PCT": [0.001, 0.002, 0.003]
        }
    }

    results = []

    print("Starting Grid Search...")

    # Iterate Breakout
    keys = list(param_grid["breakout"].keys())
    values = list(param_grid["breakout"].values())
    combinations = list(itertools.product(*values))

    for combo in combinations:
        # Patch Class
        params = dict(zip(keys, combo))
        for k, v in params.items():
            setattr(BreakoutStrategy, k, v)

        # Run Backtest
        engine = BacktestEngine(initial_equity=10000)
        engine.run(csv_path)

        # Calculate Metric (Sharpe-ish: Ret / MaxDD)
        # Simplified: Net Profit
        final_equity = engine.equity
        ret = (final_equity - 10000) / 10000

        results.append({
            "strategy": "breakout",
            "params": params,
            "return": ret,
            "trades": len(engine.trades)
        })
        print(f"Breakout {params} -> Ret: {ret:.2%}, Trades: {len(engine.trades)}")

    # Find Best
    best = max(results, key=lambda x: x['return'])
    print("\n=== OPTIMIZATION RESULT ===")
    print(f"Best Config: {best}")

    return best

if __name__ == "__main__":
    optimize()
