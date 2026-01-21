from infrastructure.ts_executor_client import TsExecutorClient

class HttpExecutor:
    """
    ts_executor로 '실행'만 위임한다.
    - 전략 판단 ❌
    - 리스크 판단 ❌
    - 포지션 추적 ❌ (추적은 main loop 동기화에서)
    """
    def __init__(self, ts: TsExecutorClient, symbol: str = "BTCUSDT"):
        self.ts = ts
        self.symbol = symbol

    def execute(self, decision: dict, price: float, funding_rate: float):
        side = decision.get("side")
        size_usdt = decision.get("size")

        # side/size 없으면 실행층이 추측하지 않는다
        if not side or not size_usdt:
            return

        qty = round(float(size_usdt) / float(price), 3)
        if qty <= 0:
            return

        self.ts.execute_market(symbol=self.symbol, side=side, quantity=qty, reduce_only=False)
