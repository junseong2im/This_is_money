class PositionTracker:
    def __init__(self):
        self.position = None

    def update_from_exchange(self, position_info):
        if not position_info:
            self.position = None
            return

        size = float(position_info.get("positionAmt", 0.0))
        if size == 0.0:
            self.position = None
            return

        self.position = {
            "size": size,
            "entry_price": float(position_info.get("entryPrice", 0.0)),
            "unrealized_pnl": float(position_info.get("unRealizedProfit", 0.0))
        }

    def is_open(self) -> bool:
        return self.position is not None

    def close(self):
        self.position = None
