import time
import os
import traceback

from core.engine import TradingEngine
from core.features import MarketFeatures

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
    
    # 2) klines (5분봉 30개 = 2.5시간 데이터)
    kr = requests.get(
        "https://fapi.binance.com/fapi/v1/klines",
        params={"symbol": symbol, "interval": "5m", "limit": 30},
        timeout=5
    )
    kr.raise_for_status()
    klines = kr.json()
    
    if len(klines) < 20:
        # 데이터 부족시 기본값 반환
        return MarketFeatures(
            price=price, atr_pct=0.01, atr_value=price * 0.01, adx=20,
            ema_fast_slope=0.0, ema_slow_slope=0.0, volume_z=1.0,
            funding_rate=funding_rate, ret_1=0.0, ret_5=0.0
        )
    
    # OHLCV 파싱
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    
    # 3) ATR 계산 (14기간)
    trs = []
    for i in range(1, len(klines)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    atr_value = sum(trs[-14:]) / 14 if len(trs) >= 14 else sum(trs) / max(len(trs), 1)
    atr_pct = atr_value / price
    
    # 4) ADX 간략 계산 (DX 평균)
    plus_dm = []
    minus_dm = []
    for i in range(1, len(klines)):
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
    
    atr_sum = sum(trs[-14:]) if len(trs) >= 14 else sum(trs)
    plus_di = 100 * sum(plus_dm[-14:]) / max(atr_sum, 0.0001)
    minus_di = 100 * sum(minus_dm[-14:]) / max(atr_sum, 0.0001)
    dx = 100 * abs(plus_di - minus_di) / max(plus_di + minus_di, 0.0001)
    adx = dx  # 단순화 (실제는 smoothed)
    
    # 5) EMA slope (9기간 fast, 21기간 slow)
    def ema(data, period):
        if len(data) < period:
            return data[-1] if data else 0
        k = 2 / (period + 1)
        result = data[0]
        for val in data[1:]:
            result = val * k + result * (1 - k)
        return result
    
    ema_fast_now = ema(closes, 9)
    ema_fast_prev = ema(closes[:-1], 9)
    ema_slow_now = ema(closes, 21)
    ema_slow_prev = ema(closes[:-1], 21)
    
    ema_fast_slope = (ema_fast_now - ema_fast_prev) / max(ema_fast_prev, 0.0001)
    ema_slow_slope = (ema_slow_now - ema_slow_prev) / max(ema_slow_prev, 0.0001)
    
    # 6) Volume Z-score
    vol_mean = sum(volumes) / len(volumes)
    vol_std = (sum((v - vol_mean) ** 2 for v in volumes) / len(volumes)) ** 0.5
    volume_z = (volumes[-1] - vol_mean) / max(vol_std, 0.0001)
    
    # 7) 수익률 (1분, 5분 approximation from 5m candles)
    ret_5 = (closes[-1] - closes[-2]) / closes[-2] if len(closes) >= 2 else 0.0
    ret_1 = ret_5 / 5  # 5분봉 기준 추정
    
    return MarketFeatures(
        price=price,
        atr_pct=atr_pct,
        atr_value=atr_value,
        adx=adx,
        ema_fast_slope=ema_fast_slope,
        ema_slow_slope=ema_slow_slope,
        volume_z=volume_z,
        funding_rate=funding_rate,
        ret_1=ret_1,
        ret_5=ret_5
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
