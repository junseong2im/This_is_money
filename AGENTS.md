# Developer Guide

## Python Brain

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

### Data Processing
`core/data_processor.py` is now the standard way to calculate indicators.
Do not calculate features manually in `main.py` or other scripts. Use `DataProcessor`.

### Strategies
Strategies are located in `core/strategies/`.
They have been optimized for standard 5m candles (ATR thresholds lowered).
Use `backtest_engine.py` to verify changes before committing strategy updates.
