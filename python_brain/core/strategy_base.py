from typing import Optional, Protocol
from core.features import MarketFeatures
from core.types import StrategySignal

class Strategy(Protocol):
    name: str

    def generate(self, f: MarketFeatures) -> Optional[StrategySignal]:
        ...
