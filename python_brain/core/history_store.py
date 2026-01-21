from collections import defaultdict, deque

class StrategyHistoryStore:
    def __init__(self, maxlen: int = 100):
        self.store = defaultdict(lambda: deque(maxlen=maxlen))

    def add(self, strategy: str, regime: str, trade: dict):
        key = f"{strategy}:{regime}"
        self.store[key].append(trade)

    def get(self, strategy: str, regime: str):
        return list(self.store[f"{strategy}:{regime}"])
