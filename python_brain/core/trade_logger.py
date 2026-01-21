class TradeLogger:
    def __init__(self):
        self.logs = []

    def record(
        self,
        strategy: str,
        pnl: float,
        rr: float,
        duration: int,
        regime: str
    ):
        self.logs.append({
            "strategy": strategy,
            "pnl": pnl,
            "rr": rr,
            "duration": duration,
            "regime": regime
        })
