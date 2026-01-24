import itertools
import pandas as pd
import numpy as np
import time
from core.strategies.breakout import BreakoutStrategy
from core.strategies.trend import TrendStrategy
from core.strategies.mean_reversion import MeanReversionStrategy
from backtest_engine import BacktestEngine
from tools.mock_data import generate_realistic_crypto_data

def optimize():
    print("Generating REALISTIC optimization dataset...")
    # Generate 15 days of data (Speed up)
    csv_path = generate_realistic_crypto_data("BTCUSDT_OPT", days=15, interval_mins=5)

    # Define Parameter Grid
    # Focused on Breakout and Trend as they are best for "Realistic" crypto data (Trends + Fat Tails)

    param_grid = {
        "breakout": {
            "MIN_ADX": [20, 25, 30],
            "BASE_SL_ATR": [1.0, 1.5, 2.0],
            "BASE_TP_ATR": [2.0, 4.0, 6.0] # Crypto trends can run far
        },
        "trend": {
            "MIN_ADX": [20, 25, 30],
            "BASE_SL_ATR": [1.5, 2.0, 2.5],
            "BASE_TP_ATR": [3.0, 5.0, 8.0]
        }
    }

    results = []

    print("Starting Grid Search...")

    start_time = time.time()

    # 1. Optimize Breakout
    print("\n--- Optimizing Breakout ---")
    keys = list(param_grid["breakout"].keys())
    values = list(param_grid["breakout"].values())
    combinations = list(itertools.product(*values))

    for combo in combinations:
        params = dict(zip(keys, combo))
        # Patch Class
        for k, v in params.items():
            setattr(BreakoutStrategy, k, v)

        engine = BacktestEngine(initial_equity=10000)
        # Suppress prints
        import sys, os
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

        try:
            engine.run(csv_path)
        finally:
            sys.stdout = original_stdout

        final_equity = engine.equity
        ret = (final_equity - 10000) / 10000
        trades = len(engine.trades)

        # Fitness Score: Return * log(Trades) (We want profit BUT also statistical significance)
        score = ret * np.log(trades + 1) if trades > 10 else -1.0

        results.append({
            "strategy": "breakout",
            "params": params,
            "return": ret,
            "trades": trades,
            "score": score
        })
        print(f"Breakout {params} -> Ret: {ret:.2%}, Trades: {trades}, Score: {score:.4f}")

    # 2. Optimize Trend
    print("\n--- Optimizing Trend ---")
    keys = list(param_grid["trend"].keys())
    values = list(param_grid["trend"].values())
    combinations = list(itertools.product(*values))

    for combo in combinations:
        params = dict(zip(keys, combo))
        for k, v in params.items():
            setattr(TrendStrategy, k, v)

        engine = BacktestEngine(initial_equity=10000)
        # Suppress prints
        sys.stdout = open(os.devnull, 'w')
        try:
            engine.run(csv_path)
        finally:
            sys.stdout = original_stdout

        final_equity = engine.equity
        ret = (final_equity - 10000) / 10000
        trades = len(engine.trades)
        score = ret * np.log(trades + 1) if trades > 10 else -1.0

        results.append({
            "strategy": "trend",
            "params": params,
            "return": ret,
            "trades": trades,
            "score": score
        })
        print(f"Trend {params} -> Ret: {ret:.2%}, Trades: {trades}, Score: {score:.4f}")

    # Find Best per Strategy
    best_breakout = max([r for r in results if r['strategy'] == 'breakout'], key=lambda x: x['score'])
    best_trend = max([r for r in results if r['strategy'] == 'trend'], key=lambda x: x['score'])

    print("\n=== OPTIMIZATION RESULT ===")
    print(f"Best Breakout: {best_breakout}")
    print(f"Best Trend: {best_trend}")

    return best_breakout, best_trend

if __name__ == "__main__":
    optimize()
