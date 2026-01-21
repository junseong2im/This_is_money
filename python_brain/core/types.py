from dataclasses import dataclass
from typing import Literal

Direction = Literal["long", "short"]

@dataclass
class StrategySignal:
    direction: Direction
    entry: float
    stop: float
    target: float

@dataclass
class StrategyStats:
    name: str
    regime: str
    win_rate: float
    avg_win: float
    avg_loss: float
    ev: float
    confidence: float
