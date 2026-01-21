from binance.client import Client
from infrastructure.exchange.types import OrderRequest, OrderResult

class BinanceFuturesClient:
    def __init__(self, api_key: str, api_secret: str):
        self.client = Client(api_key, api_secret)

    def place_order(self, req: OrderRequest) -> OrderResult:
        resp = self.client.futures_create_order(
            symbol=req.symbol,
            side=req.side,
            type=req.order_type,
            quantity=req.quantity
        )

        executed_qty = float(resp.get("executedQty", 0.0))

        # Futures는 fills가 없을 수 있음 → avgPrice/price/후속조회로 보강
        avg_price = 0.0
        if "avgPrice" in resp:
            try:
                avg_price = float(resp.get("avgPrice") or 0.0)
            except Exception:
                avg_price = 0.0

        if avg_price == 0.0:
            try:
                order = self.client.futures_get_order(symbol=req.symbol, orderId=resp["orderId"])
                avg_price = float(order.get("avgPrice") or order.get("price") or 0.0)
            except Exception:
                avg_price = 0.0

        return OrderResult(
            order_id=str(resp.get("orderId")),
            executed_qty=executed_qty,
            avg_price=avg_price,
            status=str(resp.get("status", "UNKNOWN"))
        )

    def get_position(self, symbol: str):
        positions = self.client.futures_position_information(symbol=symbol)
        for p in positions:
            if float(p.get("positionAmt", 0)) != 0:
                return p
        return None
