import time
import os
import traceback

from core.engine import TradingEngine
from core.features import MarketFeatures
from core.data_processor import DataProcessor

from infrastructure.position_tracker import PositionTracker
from infrastructure.executor import TradeExecutor
from infrastructure.executor_factory import create_executor_and_data_clients

from infrastructure.exchange.binance_futures import BinanceFuturesClient
from infrastructure.ts_executor_client import TsExecutorClient

from monitor.logger import TradeLogger
from monitor.reporter import TradeReporter
from monitor.telegram_bot import TelegramBot

# =========================
# 1. 환경 설정
# =========================

SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
INTERVAL_SEC = int(os.getenv("INTERVAL_SEC", "60"))
EXECUTOR_MODE = os.getenv("EXECUTOR_MODE", "local").strip().lower()

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================
# 2. 초기화
# =========================

engine = TradingEngine()
tracker = PositionTracker()

# executor + data client 생성
executor, data_client = create_executor_and_data_clients(SYMBOL)

# local mode면 executor를 여기서 기존 방식 그대로 생성
if EXECUTOR_MODE == "local":
    assert isinstance(data_client, BinanceFuturesClient)
    client = data_client
    executor = TradeExecutor(client=client, tracker=tracker, engine=engine, symbol=SYMBOL)
else:
    # http mode: data_client는 TsExecutorClient
    assert isinstance(data_client, TsExecutorClient)
    client = None  # python_brain은 키를 들고 있지 않음

# --- monitor (observer only) ---
logger = TradeLogger()
reporter = TradeReporter()
telegram = TelegramBot(TG_TOKEN, TG_CHAT_ID) if TG_TOKEN and TG_CHAT_ID else None

equity = 0.0  # 실계좌면 조회해서 세팅(아래에서 동기화)

# =========================
# 3. Feature Builder (계산 전용)
# =========================

import requests

def build_features(symbol: str) -> MarketFeatures:
    """
    Binance Public API로 실제 지표를 계산한다.
    - klines: ATR, ADX, EMA slope, 수익률 계산
    - premiumIndex: markPrice, funding rate
    """
    # 1) 현재가 + 펀딩비
    r = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex", params={"symbol": symbol}, timeout=5)
    r.raise_for_status()
    j = r.json()
    price = float(j["markPrice"])
    funding_rate = float(j.get("lastFundingRate", 0.0))
    
    # 2) klines (5분봉 120개 = 10시간 데이터)
    # Hurst Exponent needs ~100 candles
    kr = requests.get(
        "https://fapi.binance.com/fapi/v1/klines",
        params={"symbol": symbol, "interval": "5m", "limit": 120},
        timeout=5
    )
    kr.raise_for_status()
    klines = kr.json()
    
    if len(klines) < 105:
        # 데이터 부족시 기본값 반환
        return MarketFeatures(
            price=price, atr_pct=0.01, atr_value=price * 0.01, adx=20,
            ema_fast_slope=0.0, ema_slow_slope=0.0, volume_z=1.0,
            funding_rate=funding_rate, ret_1=0.0, ret_5=0.0, hurst=0.5
        )
    
    # 3) Pandas DataProcessor로 계산
    df = DataProcessor.to_dataframe(klines)
    df = DataProcessor.add_indicators(df)
    
    # 마지막 캔들이 '현재' 캔들
    last = df.iloc[-1]
    
    return MarketFeatures(
        price=price, # markPrice (funding-adjusted logic might prefer this over kline close)
        atr_pct=last['atr_pct'],
        atr_value=last['atr_value'],
        adx=last['adx'],
        ema_fast_slope=last['ema_fast_slope'],
        ema_slow_slope=last['ema_slow_slope'],
        volume_z=last['volume_z'],
        funding_rate=funding_rate,
        ret_1=last['ret_1'],
        ret_5=last['ret_5'],
        hurst=last['hurst']
    )

# =========================
# 4. 메인 루프
# =========================

def main():
    global equity

    logger.system("ENGINE_START", {"symbol": SYMBOL, "mode": EXECUTOR_MODE})
    if telegram:
        telegram.send(f"🚀 Quant Engine Started ({SYMBOL}) mode={EXECUTOR_MODE}")

    while True:
        try:
            # 0) (http 모드) equity/position 동기화는 ts_executor로
            if EXECUTOR_MODE == "http":
                bal = data_client.get_balance()
                if bal.get("success"):
                    equity = float(bal.get("walletUSDT") or 0.0)

            # 1) Feature 생성(공개 API)
            features = build_features(SYMBOL)

            # 2) core 판단
            decision = engine.step(features, equity)

            # 3) 실행
            if decision:
                logger.trade("DECISION", decision)
                if telegram:
                    telegram.trade_signal(decision)

                executor.execute(
                    decision=decision,
                    price=features.price,
                    funding_rate=features.funding_rate
                )

            # 4) 포지션 상태 동기화
            prev_open = tracker.is_open()

            if EXECUTOR_MODE == "local":
                pos = client.get_position(SYMBOL)
            else:
                p = data_client.get_position(SYMBOL)
                pos = (p.get("position") if p.get("success") else None)

            tracker.update_from_exchange(pos)
            now_open = tracker.is_open()

            # 5) 포지션 종료 감지 → 리포트(현재는 단순 unrealized 기준, 향후 realized로 확장)
            if prev_open and not now_open:
                pnl = tracker.position["unrealized_pnl"] if tracker.position else 0.0
                logger.trade("CLOSE", {"pnl": pnl})
                reporter.record_trade(pnl)
                if telegram:
                    telegram.trade_close(pnl)

        except Exception as e:
            err = {"error": str(e), "trace": traceback.format_exc()}
            logger.error("RUNTIME_ERROR", err)
            if telegram:
                telegram.error_alert(err)

        time.sleep(INTERVAL_SEC)

# =========================
# 5. 엔트리 포인트
# =========================

if __name__ == "__main__":
    main()
