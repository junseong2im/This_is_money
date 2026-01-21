from dataclasses import dataclass
from typing import Literal

Side = Literal["BUY", "SELL"]

@dataclass
class OrderRequest:
    symbol: str
    side: Side
    quantity: float
    order_type: str = "MARKET"

@dataclass
class OrderResult:
    order_id: str
    executed_qty: float
    avg_price: float
    status: str
