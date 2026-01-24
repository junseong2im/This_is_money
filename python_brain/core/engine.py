from core.regime import detect_regime, MarketRegime
from core.ev_estimator import EVEstimator
from core.history_store import StrategyHistoryStore
from dataclasses import asdict
from core.selector import select_best
from core.sizing import position_size

from core.strategies.breakout import BreakoutStrategy
from core.strategies.trend import TrendStrategy
from core.strategies.mean_reversion import MeanReversionStrategy

REGIME_POOL = {
    MarketRegime.TREND: [BreakoutStrategy(), TrendStrategy()],
    MarketRegime.DISTRIBUTION: [MeanReversionStrategy()],
    MarketRegime.SQUEEZE: [],
    MarketRegime.CHOP: [],
}

class TradingEngine:
    def __init__(self):
        self.ev = EVEstimator()
        self.history = StrategyHistoryStore()
        self.cooldown = {}  # strategy: remaining bars

    def on_trade_close(self, strategy, regime, pnl):
        self.history.add(strategy, regime, {"pnl": pnl})
        if pnl < 0:
            self.cooldown[strategy] = self.cooldown.get(strategy, 0) + 3

    def step(self, features, equity):
        regime = detect_regime(features)
        strategies = REGIME_POOL.get(regime, [])
        stats = []

        for s in strategies:
            if self.cooldown.get(s.name, 0) > 0:
                self.cooldown[s.name] -= 1
                continue

            signal = s.generate(features)
            if not signal:
                continue

            trades = self.history.get(s.name, regime.value)
            stat = self.ev.estimate(
                s.name, regime.value, trades, features.funding_rate
            )
            # Attach signal to stat so we can retrieve it later
            stat.signal = signal
            stats.append(stat)

        best = select_best(stats)
        if not best:
            return None

        # Pass current ATR pct for volatility targeting
        size = position_size(equity, best, current_volatility=features.atr_pct)
        if size <= 0:
            return None

        return {
            "strategy": best.name,
            "regime": best.regime,
            "size": size,
            "ev": best.ev,
            "signal": asdict(best.signal) if best.signal else None
        }
