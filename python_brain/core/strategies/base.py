class BaseStrategy:
    """
    Strategy is a performance container, NOT a signal generator.
    """

    name: str = "base"

    def __init__(self):
        self.trades = []
        self.total_pnl = 0.0

    def record_trade(self, pnl: float):
        self.trades.append(pnl)
        self.total_pnl += pnl

    def expectancy(self) -> float:
        if not self.trades:
            return 0.0
        return self.total_pnl / len(self.trades)

    def trade_count(self) -> int:
        return len(self.trades)
