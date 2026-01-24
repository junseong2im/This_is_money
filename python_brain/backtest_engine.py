import pandas as pd
import numpy as np
from dataclasses import asdict
import os

from core.engine import TradingEngine
from core.features import MarketFeatures
from core.data_processor import DataProcessor

class BacktestEngine:
    def __init__(self, initial_equity=10000.0, commission=0.0004, slippage=0.0002):
        self.initial_equity = initial_equity
        self.equity = initial_equity
        self.commission = commission # Binance taker fee (0.04%)
        self.slippage = slippage # Estimated slippage (0.02%)

        self.engine = TradingEngine()

        self.position = None
        self.trades = []
        self.equity_curve = [initial_equity]

    def run(self, csv_path):
        print(f"Loading data from {csv_path}...")
        df_raw = pd.read_csv(csv_path)

        # Process features
        print("Calculating features...")
        df = DataProcessor.add_indicators(df_raw)

        # Remove warmup
        warmup = 100
        df = df.iloc[warmup:].reset_index(drop=True)

        print(f"Starting backtest on {len(df)} candles...")

        for i, row in df.iterrows():
            # Mock funding rate (random small drift)
            funding = np.random.normal(0, 0.0001)

            features = MarketFeatures(
                price=row['close'],
                atr_pct=row['atr_pct'],
                atr_value=row['atr_value'],
                adx=row['adx'],
                ema_fast_slope=row['ema_fast_slope'],
                ema_slow_slope=row['ema_slow_slope'],
                volume_z=row['volume_z'],
                funding_rate=funding,
                ret_1=row['ret_1'],
                ret_5=row['ret_5'],
                hurst=row['hurst']
            )

            # 1. Check existing position (SL/TP)
            # Use Low/High of current candle for SL/TP check
            self._check_exit(row['low'], row['high'], row['close'])

            # 2. Ask engine for decision
            if self.position is None:
                decision = self.engine.step(features, self.equity)

                # 3. Execute entry
                if decision:
                    self._execute_entry(decision, row['close'])

            # Track equity
            self.equity_curve.append(self.equity)

        self._print_stats()

    def _execute_entry(self, decision, price):
        signal = decision['signal']

        # Apply Slippage to Entry
        if signal['direction'] == 'long':
            entry_price = price * (1 + self.slippage)
        else:
            entry_price = price * (1 - self.slippage)

        # Commission
        cost = decision['size'] * self.commission
        self.equity -= cost

        self.position = {
            "strategy": decision['strategy'],
            "regime": decision['regime'],
            "size": decision['size'],
            "direction": signal['direction'],
            "entry": entry_price,
            "stop": signal['stop'],
            "target": signal['target'],
            "open_time": self.equity_curve[-1] # pseudo-timestamp index
        }

    def _check_exit(self, low, high, close):
        if not self.position:
            return

        p = self.position
        pnl_pct = 0
        closed = False
        exit_price = close
        reason = ""

        # Check SL/TP
        if p['direction'] == 'long':
            if low <= p['stop']:
                # SL hit: Assume worse execution (slippage on stop)
                exit_price = p['stop'] * (1 - self.slippage)
                closed = True
                reason = "SL"
            elif high >= p['target']:
                # TP hit
                exit_price = p['target'] * (1 - self.slippage) # Limit order usually no slippage but let's be conservative
                closed = True
                reason = "TP"
            # Else hold

        elif p['direction'] == 'short':
            if high >= p['stop']:
                # SL hit
                exit_price = p['stop'] * (1 + self.slippage)
                closed = True
                reason = "SL"
            elif low <= p['target']:
                # TP hit
                exit_price = p['target'] * (1 + self.slippage)
                closed = True
                reason = "TP"

        if closed:
            # Calculate PnL
            if p['direction'] == 'long':
                raw_pnl = (exit_price - p['entry']) / p['entry'] * p['size']
            else:
                raw_pnl = (p['entry'] - exit_price) / p['entry'] * p['size']

            # Exit Commission
            comm = p['size'] * self.commission
            net_pnl = raw_pnl - comm

            self.equity += net_pnl

            self.trades.append({
                "type": p['direction'],
                "entry": p['entry'],
                "exit": exit_price,
                "pnl": net_pnl,
                "reason": reason,
                "strategy": p['strategy']
            })

            # Notify engine
            self.engine.on_trade_close(p['strategy'], p['regime'], net_pnl)

            self.position = None

    def _print_stats(self):
        print("\n=== Backtest Results (Realistic) ===")
        print(f"Initial Equity: {self.initial_equity}")
        print(f"Final Equity: {self.equity:.2f}")
        total_ret = (self.equity - self.initial_equity) / self.initial_equity
        print(f"Return: {total_ret:.2%}")

        if not self.trades:
            print("No trades executed.")
            return

        wins = [t for t in self.trades if t['pnl'] > 0]
        win_rate = len(wins) / len(self.trades)
        print(f"Trades: {len(self.trades)}")
        print(f"Win Rate: {win_rate:.2%}")

        # Max Drawdown
        curve = np.array(self.equity_curve)
        peak = np.maximum.accumulate(curve)
        dd = (peak - curve) / peak
        max_dd = np.max(dd)
        print(f"Max Drawdown: {max_dd:.2%}")

        # Sharpe (Approx)
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        if len(returns) > 0 and returns.std() > 0:
            sharpe = returns.mean() / returns.std() * np.sqrt(288*365) # Annualized 5m
            print(f"Sharpe Ratio: {sharpe:.2f}")

        # Strategy breakdown
        df_t = pd.DataFrame(self.trades)
        print("\nBy Strategy:")
        print(df_t.groupby('strategy')['pnl'].sum())
