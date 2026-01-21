import os

from infrastructure.http_executor import HttpExecutor
from infrastructure.ts_executor_client import TsExecutorClient
from infrastructure.executor import TradeExecutor  # 기존 로컬 executor
from infrastructure.exchange.binance_futures import BinanceFuturesClient

def create_executor_and_data_clients(symbol: str):
    """
    returns (executor, data_client)
    - local: executor=TradeExecutor, data_client=BinanceFuturesClient
    - http : executor=HttpExecutor,  data_client=TsExecutorClient (position/balance via ts_executor)
    """
    mode = os.getenv("EXECUTOR_MODE", "local").strip().lower()

    if mode == "http":
        endpoint = os.getenv("EXECUTOR_HTTP_ENDPOINT", "").strip()
        token = os.getenv("EXECUTOR_AUTH_TOKEN", "").strip()
        if not endpoint:
            raise RuntimeError("EXECUTOR_HTTP_ENDPOINT not set")

        ts = TsExecutorClient(endpoint, token=token)
        if not ts.health():
            raise RuntimeError(f"ts_executor not reachable: {endpoint}")

        executor = HttpExecutor(ts, symbol=symbol)
        return executor, ts

    if mode == "local":
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("BINANCE API KEY / SECRET not set (local mode)")

        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
        # local executor는 main에서 tracker/engine 주입하므로 여기선 client만 리턴
        return None, client  # executor는 main에서 TradeExecutor로 생성

    raise RuntimeError(f"Unknown EXECUTOR_MODE={mode}")
