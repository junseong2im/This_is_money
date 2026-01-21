from infrastructure.execution.executor_base import BaseExecutor
from infrastructure.exchange.binance_futures import BinanceFuturesClient
from infrastructure.exchange.types import OrderRequest

class LocalExecutor(BaseExecutor):
    """
    Local executor:
    - Executes orders directly via BinanceFuturesClient
    - No strategy logic
    - No risk logic
    """

    def __init__(
        self,
        client: BinanceFuturesClient,
        symbol: str = "BTCUSDT"
    ):
        self.client = client
        self.symbol = symbol

    def execute(
        self,
        decision: dict,
        price: float,
        funding_rate: float
    ):
        """
        decision example (from core):
        {
            "strategy": "trend",
            "side": "BUY",
            "size": 100.0
        }
        """

        side = decision.get("side")
        size_usdt = decision.get("size")

        if not side or not size_usdt:
            return  # execution layer does not guess

        quantity = round(size_usdt / price, 3)
        if quantity <= 0:
            return

        order = OrderRequest(
            symbol=self.symbol,
            side=side,
            quantity=quantity,
            order_type="MARKET"
        )

        # 🔥 실제 주문 실행
        self.client.place_order(order)
