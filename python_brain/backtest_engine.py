import pandas as pd
import numpy as np
from dataclasses import asdict
import os

from core.engine import TradingEngine
from core.features import MarketFeatures
from core.data_processor import DataProcessor

class BacktestEngine:
    def __init__(self, initial_equity=10000.0, commission=0.0004):
        self.initial_equity = initial_equity
        self.equity = initial_equity
        self.commission = commission # Binance futures taker fee approx
        self.engine = TradingEngine()

        self.position = None # {type: 'long'/'short', entry: float, size: float, stop: float, target: float}
        self.trades = []
        self.equity_curve = []

    def run(self, csv_path):
        print(f"Loading data from {csv_path}...")
        df_raw = pd.read_csv(csv_path)

        # Process features
        print("Calculating features...")
        df = DataProcessor.add_indicators(df_raw)

        # Remove first 50 rows (warmup for indicators)
        df = df.iloc[50:].reset_index(drop=True)

        print(f"Starting backtest on {len(df)} candles...")

        for i, row in df.iterrows():
            # Create MarketFeatures
            # Mock funding rate for now (neutral)
            funding = 0.0001

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
                ret_5=row['ret_5']
            )

            # 1. Check existing position (SL/TP)
            self._check_exit(row['low'], row['high'], row['close'])

            # 2. Ask engine for decision
            # Pass current equity (simulated)
            decision = self.engine.step(features, self.equity)

            # 3. Execute entry
            if decision and self.position is None:
                self._execute_entry(decision, row['close'])

            # Track equity (approximate, mark-to-market is harder without tick data)
            # We track realized equity.
            self.equity_curve.append(self.equity)

        self._print_stats()

    def _execute_entry(self, decision, price):
        signal = decision['signal']
        self.position = {
            "strategy": decision['strategy'],
            "regime": decision['regime'],
            "size": decision['size'],
            "direction": signal['direction'],
            "entry": price,
            "stop": signal['stop'],
            "target": signal['target']
        }

    def _check_exit(self, low, high, close):
        if not self.position:
            return

        p = self.position
        pnl = 0
        closed = False

        # Check SL/TP
        if p['direction'] == 'long':
            if low <= p['stop']:
                # SL hit
                exit_price = p['stop'] # slippage ignored
                pnl = (exit_price - p['entry']) / p['entry'] * p['size']
                closed = True
                reason = "SL"
            elif high >= p['target']:
                # TP hit
                exit_price = p['target']
                pnl = (exit_price - p['entry']) / p['entry'] * p['size']
                closed = True
                reason = "TP"

        elif p['direction'] == 'short':
            if high >= p['stop']:
                # SL hit
                exit_price = p['stop']
                pnl = (p['entry'] - exit_price) / p['entry'] * p['size']
                closed = True
                reason = "SL"
            elif low <= p['target']:
                # TP hit
                exit_price = p['target']
                pnl = (p['entry'] - exit_price) / p['entry'] * p['size']
                closed = True
                reason = "TP"

        if closed:
            # Commission
            comm = p['size'] * self.commission * 2 # entry + exit
            net_pnl = pnl - comm
            self.equity += net_pnl

            self.trades.append({
                "type": p['direction'],
                "entry": p['entry'],
                "exit": exit_price,
                "pnl": net_pnl,
                "reason": reason,
                "strategy": p['strategy']
            })

            # Notify engine of close (for cooldown/learning)
            # engine.on_trade_close expects (strategy_name, regime, pnl)
            # We need to store regime in position too.
            self.engine.on_trade_close(p['strategy'], p['regime'], net_pnl)

            self.position = None

    def _print_stats(self):
        print("\n=== Backtest Results ===")
        print(f"Initial Equity: {self.initial_equity}")
        print(f"Final Equity: {self.equity:.2f}")
        total_ret = (self.equity - self.initial_equity) / self.initial_equity * 100
        print(f"Return: {total_ret:.2f}%")

        if not self.trades:
            print("No trades executed.")
            return

        wins = [t for t in self.trades if t['pnl'] > 0]
        win_rate = len(wins) / len(self.trades) * 100
        print(f"Trades: {len(self.trades)}")
        print(f"Win Rate: {win_rate:.2f}%")

        # Strategy breakdown
        df_t = pd.DataFrame(self.trades)
        print("\nBy Strategy:")
        print(df_t.groupby('strategy')['pnl'].sum())
