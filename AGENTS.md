# Developer Guide

## Python Brain

### Advanced Features (Hurst & Volatility Targeting)
The system now includes sophisticated quantitative components:
1.  **Hurst Exponent**: Calculates persistence of trends. Used in `regime.py` to distinguish real trends from chop.
2.  **Volatility Targeting**: `core/sizing.py` now sizes positions to target a fixed portfolio volatility (default 40% annualized), reducing risk in turbulent markets.
3.  **Optimization**: `optimize.py` allows automated parameter tuning.

### Backtesting
New backtesting infrastructure has been added to `python_brain`.
To run a backtest:

1. Generate mock data (or download if API available):
   ```bash
   cd python_brain
   python tools/mock_data.py
   ```
2. Run the engine:
   ```bash
   PYTHONPATH=. python -c "from backtest_engine import BacktestEngine; engine = BacktestEngine(); engine.run('data/BTCUSDT_5m_mock_trend.csv')"
   ```

### Optimization
To run the automated optimizer:
```bash
cd python_brain
PYTHONPATH=. python optimize.py
```

### Strategies
Strategies are located in `core/strategies/`.
They have been optimized using the `optimize.py` script.
current best settings for Breakout: `SL 1.2 ATR`, `TP 3.0 ATR`.
