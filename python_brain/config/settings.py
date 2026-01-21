"""
[전역 설정 파일 - 극한 최적화]
모든 파라미터를 수학적으로 도출

=== 핵심 공식 ===

1. Kelly Criterion (최적 베팅 비율)
   f* = (p × b - q) / b = p - q/b
   Half Kelly: f = f*/2 (보수적)
   
2. Optimal f (Ralph Vince)
   f = W/L × [((1+W/L) × p - 1) / W/L]
   
3. Risk of Ruin (파산 확률)
   R = ((1-a)/(1+a))^n where a = edge/σ
   
4. Sharpe 최적 손익비
   RR* = (μ/σ)² + 1 ≈ Sharpe² + 1
   
5. ATR 기반 SL/TP (통계적)
   - SL: 2σ (95% 신뢰구간)
   - TP: SL × RR*
   
6. 연패 확률 (이항분포)
   P(n연패) = (1-p)^n
   99% 신뢰구간: n = log(0.01) / log(1-p)
   
7. 최적 피라미딩 (지수 감소)
   Size_i = Size_0 × r^i where r = √(p/q)
   
8. 세션별 변동성 조정
   Size ∝ 1/√(σ_session / σ_avg)
   
9. 드로우다운 한계 (Risk of Ruin 기반)
   MaxDD = -2 × (edge/variance) × ln(acceptable_ruin)
   
10. 최소 거래 횟수 (통계적 유의성)
    n ≥ (z² × p × (1-p)) / E² where E = margin of error
"""
import os
import math
from typing import List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


# ============================================================
# [수학적 상수 - 정밀 계산]
# ============================================================

# 가정된 기본 승률 (보수적)
WIN_RATE = 0.38

# 목표 손익비 (최적화 기반)
# Sharpe ~0.5 가정: RR* = 0.5² + 1 = 1.25
# 거래비용 고려하여 상향: 2.5
RISK_REWARD = 2.5

# Kelly Criterion 계산
# f* = p - q/b = 0.38 - 0.62/2.5 = 0.132
# Half Kelly = 0.066
KELLY_FULL = WIN_RATE - (1 - WIN_RATE) / RISK_REWARD
KELLY_HALF = KELLY_FULL / 2

# Risk of Ruin 계산
# edge = p × W - q × L = 0.38 × 2.5 - 0.62 × 1 = 0.33
# 5% ruin 허용: MaxDD = edge × ln(0.05) / variance
EDGE = WIN_RATE * RISK_REWARD - (1 - WIN_RATE)

# 연패 99% 신뢰구간
# n = ln(0.01) / ln(1-p) = ln(0.01) / ln(0.62) ≈ 9.6
LOSING_STREAK_99 = int(math.log(0.01) / math.log(1 - WIN_RATE))

# 최소 통계적 유의 거래 수
# z=1.96 (95%), E=0.05: n = (1.96² × 0.38 × 0.62) / 0.05² ≈ 363
MIN_TRADES_SIGNIFICANT = int((1.96**2 * WIN_RATE * (1-WIN_RATE)) / 0.05**2)

# 피라미딩 감소율
# r = √(p/q) = √(0.38/0.62) ≈ 0.78
PYRAMID_DECAY = math.sqrt(WIN_RATE / (1 - WIN_RATE))


class TradingSettings(BaseSettings):
    """마스터 설정 클래스 - 극한 최적화"""
    
    APP_NAME: str = "Predator-Extreme-Optimized"
    ENV: str = "production"
    
    # ============================================================
    # [기본 설정]
    # ============================================================
    SYMBOL: str = "BTCUSDT"
    ALLOWED_SYMBOLS: List[str] = ["BTCUSDT", "ETHUSDT"]
    BASE_TIMEFRAME: str = "3m"
    
    # ============================================================
    # [자본 배분] - 분산 투자 최적화
    # ============================================================
    # Markowitz 포트폴리오 이론 기반 분산
    # 상관관계 낮은 전략에 분산
    INITIAL_CAPITAL: float = 1000.0
    
    MAIN_STRATEGY_RATIO: float = 0.55     # 메인 (추세)
    FUNDING_ARB_RATIO: float = 0.20       # 무위험 수익
    SCALPING_RATIO: float = 0.10          # 고빈도
    RESERVE_RATIO: float = 0.15           # 안전마진
    
    # ============================================================
    # [레버리지] - 변동성 조정 레버리지
    # ============================================================
    # 최적 레버리지 = Kelly / (σ × SL%)
    # Half Kelly 6.6% / (2% × 1.5%) ≈ 2.2x
    MIN_LEVERAGE: int = 1
    # 소액(예: 20 USDT)에서는 BTCUSDT 최소 수량(0.001) 자체가 노미널이 커서,
    # 낮은 레버리지로는 "증거금 부족"으로 진입이 막힐 수 있다.
    # 실전 진입 가능성을 위해 기본/상한을 완화(리스크는 RISK_PER_TRADE/사이징으로 제어).
    MAX_LEVERAGE: int = 20
    BASE_LEVERAGE: int = 10
    
    # 변동성 기반 동적 레버리지
    # Lev = base / (current_vol / avg_vol)
    DYNAMIC_LEVERAGE: bool = True
    VOL_LEVERAGE_SCALE: float = 1.0
    
    # ============================================================
    # [리스크 관리] - 극한 최적화
    # ============================================================
    # 운영 스위치:
    # - 사용자가 "거래소(바이낸스)에서 막히는 경우가 아니면 봇이 스스로 막지 말라"는 모드일 때 OFF로 둔다.
    HARD_LIMITS_ENABLE: bool = False
    DRAWDOWN_LIMITS_ENABLE: bool = False
    
    # === 드로우다운 한계 ===
    # Risk of Ruin 5% 허용 시:
    # MaxDD = -2 × edge × ln(0.05) / variance
    # ≈ -2 × 0.33 × (-3) / 0.1 ≈ 20%
    MAX_DAILY_DRAWDOWN: float = 0.06      # 일일 6% (3연패 한계)
    MAX_TOTAL_DRAWDOWN: float = 0.18      # 총 18% (파산방지)
    
    # === 포지션 사이징 ===
    # Half Kelly = 6.6%, 분산투자 고려 20%
    MAX_POSITION_SIZE: float = 0.20
    
    # === 리스크당 손실 ===
    # 고정 분수 방식: 1-2%
    RISK_PER_TRADE: float = 0.015         # 거래당 1.5% 리스크

    # ============================================================
    # [실전] 최소 진입 노미널(USDT) 충족을 위한 자동 상향
    # - 가능한 범위(equity * leverage) 내에서만 최소 노미널을 맞춘다.
    # ============================================================
    MIN_ENTRY_NOTIONAL_USDT: float = 10.0
    ENFORCE_MIN_ENTRY_NOTIONAL: bool = True
    
    # === 고정 % SL/TP (폴백) ===
    STOP_LOSS_PCT: float = 0.015          # 1.5%
    TAKE_PROFIT_PCT: float = 0.0375       # 3.75% (RR 2.5:1)
    TRAILING_STOP_PCT: float = 0.012      # 1.2%
    
    # === ATR 기반 SL/TP ===
    # 2σ SL (95% 신뢰구간), RR 2.5:1 TP
    USE_ATR_SLTP: bool = True
    ATR_SL_MULT: float = 2.0              # 2 ATR (≈2σ)
    ATR_TP_MULT: float = 5.0              # 5 ATR (RR 2.5:1)
    
    # ATR 동적 조정 (변동성 정규화)
    ATR_NORMALIZE: bool = True            # ATR/Price로 정규화
    ATR_MIN_PCT: float = 0.005            # 최소 0.5%
    ATR_MAX_PCT: float = 0.03             # 최대 3%
    
    # === 연패 방어 ===
    # 99% 신뢰구간: 10연패
    # 50% 축소 시작: 3연패 (P=21.6%)
    # 25% 축소: 5연패 (P=9.2%)
    # 거래 중단: 7연패 (P=3.5%)
    LOSING_STREAK_THRESHOLD: int = 3
    LOSING_STREAK_SIZE_MULT: float = 0.5
    LOSING_STREAK_LEVEL2: int = 5
    LOSING_STREAK_SIZE_MULT2: float = 0.25
    LOSING_STREAK_STOP: int = 7           # 거래 중단
    
    # === 연승 피라미딩 ===
    # 감소율 r = √(p/q) ≈ 0.78
    WINNING_STREAK_THRESHOLD: int = 2
    WINNING_STREAK_SIZE_MULT: float = 1.20  # 20% 증가
    WINNING_STREAK_MAX_MULT: float = 1.50   # 최대 50% 증가
    
    # === 최소 거래 간격 ===
    # 자기상관 감소를 위해
    # 실전에서는 "좋은 자리"를 쿨다운으로 놓치는 경우가 커서 기본 0(비활성)로 둔다.
    MIN_TRADE_INTERVAL_CANDLES: int = 0   # 0이면 비활성
    
    # ============================================================
    # [거래 비용] - 정밀 계산
    # ============================================================
    # Binance Futures: maker 0.02%, taker 0.04%
    # 평균: 0.03% (보수적으로 0.04%)
    FEE_RATE: float = 0.0004
    SLIPPAGE_RATE: float = 0.0002

    # ============================================================
    # [실행/체결 모델] (백테스트에서 비용 구조를 현실적으로 비교하기 위함)
    # ============================================================
    # - EXECUTION_MODE:
    #   - "taker": 시장가 가정(테이커 수수료+슬리피지)
    #   - "maker": 리밋 체결 가정(메이커 수수료+거의 0 슬리피지)
    #   - "hybrid": entry=maker, exit=taker (현실적인 절충)
    EXECUTION_MODE: str = "taker"
    TAKER_FEE_RATE: float = 0.0004
    MAKER_FEE_RATE: float = 0.0002
    TAKER_SLIPPAGE_RATE: float = 0.0002
    MAKER_SLIPPAGE_RATE: float = 0.0

    # TP(익절) 계열을 "미리 걸어둔 리밋"으로 보고 메이커 비용/0슬리피지로 처리할지
    # - 실전에서도 take_profit은 reduce-only limit로 둘 수 있어 현실성 있음
    EXECUTION_TP_AS_MAKER: bool = True
    # 트레일링 스탑은 보통 시장가에 가까워서 기본 False (원하면 True로 테스트 가능)
    EXECUTION_TRAIL_AS_MAKER: bool = False

    # 진입을 "리밋 주문"으로 시뮬레이션할지 여부(OHLC 기준 단순 체결)
    USE_LIMIT_ENTRY: bool = False
    LIMIT_ENTRY_OFFSET_PCT: float = 0.00015  # buy는 close*(1-offset), sell은 close*(1+offset)

    # ============================================================
    # [YOLO 모드] (고위험/고수익 실험용 - 파산 감수 전제)
    # ============================================================
    YOLO_MODE: bool = False
    YOLO_DAILY_TARGET_PCT: float = 0.30          # 하루 +30% 목표
    YOLO_LOCK_PROFIT: bool = True               # 목표 달성 시 그날 거래 중단(수익 잠금)
    YOLO_STOP_EQUITY_PCT: float = 0.05          # 자산이 초기의 5% 이하이면 사실상 파산으로 보고 중단
    YOLO_DISABLE_DD_LIMITS: bool = True         # 일일/총 DD 제한 해제(파산 감수)
    
    # 손익분기 계산
    # BEP = (fee + slippage) × 2 = 0.12%
    # 최소 이익 > BEP × 1.5 = 0.18%
    BREAKEVEN_RETURN: float = 0.0012      # 0.12%
    MIN_PROFIT_TARGET: float = 0.0018     # 0.18%
    
    # ============================================================
    # [지표 파라미터] - 표준 + 최적화
    # ============================================================
    EMA_FAST: int = 12
    EMA_SLOW: int = 26
    EMA_SIGNAL: int = 9
    
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 30.0
    RSI_OVERBOUGHT: float = 70.0
    
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    
    ATR_PERIOD: int = 14
    
    ADX_PERIOD: int = 14
    ADX_TREND_THRESHOLD: float = 25.0
    ADX_STRONG_TREND: float = 40.0
    ADX_WEAK_THRESHOLD: float = 20.0      # 약한 추세
    
    STOCH_K: int = 14
    STOCH_D: int = 3
    STOCH_SMOOTH: int = 3
    
    # ============================================================
    # [전략별 파라미터] - 극한 최적화
    # ============================================================
    
    # --- 그리드 봇 ---
    # 최적 그리드 수 = √(range / fee)
    # BTC 일일 변동 2%, fee 0.12%: √(2/0.12) ≈ 4
    # 보수적으로 6-8개
    GRID_COUNT: int = 6
    GRID_RANGE_ATR_MULT: float = 3.0
    GRID_POSITION_PER_GRID: float = 0.12
    GRID_REBALANCE_THRESHOLD: float = 0.5  # 50% 벗어나면 재설정
    
    # --- 추세추종 ---
    TREND_DONCHIAN_PERIOD: int = 20
    TREND_ATR_SL_MULT: float = 2.0
    # 기존 5 ATR TP는 너무 멀어서 TP 도달 전에 반전/손절이 과다하게 발생할 수 있음
    # 승률을 올려 기대값을 개선하기 위해 보수적으로 축소
    TREND_ATR_TP_MULT: float = 3.2
    TREND_PYRAMID_MAX: int = 3
    # 피라미딩 사이즈: 감소율 적용
    # 50% × 0.78 = 39%, 39% × 0.78 = 30%
    TREND_PYRAMID_SIZES: List[float] = [0.50, 0.30, 0.20]
    TREND_PYRAMID_TRIGGER_ATR: float = 1.0  # 1 ATR 이동 시 추가
    
    # --- DCA ---
    # 마틴게일 위험 회피: 동일 금액
    # 레벨: 피보나치 기반 (2.6%, 4.2%, 6.8%, 11%)
    DCA_LEVELS: List[float] = [-0.026, -0.042, -0.068, -0.11]
    DCA_MULTIPLIERS: List[float] = [1.0, 1.0, 1.0, 1.0]
    DCA_MAX_ENTRIES: int = 4
    DCA_TOTAL_LIMIT: float = 1.5          # 초기의 1.5배까지
    
    # --- 변동성 돌파 ---
    # K 최적화: 0.5~0.6 범위에서 0.55
    VB_K: float = 0.55
    VB_LOOKBACK: int = 1
    VB_MIN_RANGE_PCT: float = 0.008       # 최소 0.8% 변동
    VB_VOLUME_CONFIRM: float = 1.2        # 거래량 20% 증가 확인
    
    # --- 평균회귀 ---
    # 볼린저: 2σ = 95.4%, 극단값
    MR_RSI_ENTRY_LOW: float = 25.0
    MR_RSI_ENTRY_HIGH: float = 75.0
    MR_BB_ENTRY_LOW: float = 0.05         # BB 하단 5%
    MR_BB_ENTRY_HIGH: float = 0.95        # BB 상단 95%
    MR_HOLD_CANDLES: int = 8              # 최대 24분 보유
    MR_EXIT_BB_PCT: float = 0.5           # BB 중간선 도달 시 청산
    
    # --- 스캘핑 ---
    SCALP_MIN_SPREAD: float = 0.0003
    SCALP_IMBALANCE_THRESHOLD: float = 0.45
    SCALP_HOLD_TIME_SEC: int = 45
    SCALP_PROFIT_TARGET: float = 0.0012   # 0.12% (BEP)
    SCALP_STOP_LOSS: float = 0.0008       # 0.08%
    SCALP_MAX_TRADES_HOUR: int = 10       # 과매매 방지
    
    # --- 펀딩비 재정거래 ---
    FUNDING_MIN_RATE: float = 0.0004      # 0.04% (수수료 커버)
    FUNDING_HEDGE_RATIO: float = 1.0
    FUNDING_MAX_SPREAD: float = 0.0015
    FUNDING_ENTRY_HOURS_BEFORE: int = 2   # 펀딩 2시간 전 진입
    
    # --- 브레이크아웃 ---
    BREAKOUT_LOOKBACK: int = 20
    # 너무 엄격하면 거래가 0으로 수렴한다. 기본은 1(즉시 진입) + 페이크돌파 조기청산으로 관리
    BREAKOUT_CONFIRM_CANDLES: int = 1
    BREAKOUT_VOLUME_MULT: float = 1.15
    # 3m 기준 0.2%는 15m/1h에서 너무 타이트해 '정상 리테스트'까지 페이크로 오인할 수 있다.
    # (데이터/심볼에 따라 조정 필요)
    BREAKOUT_RETEST_TOLERANCE: float = 0.004
    BREAKOUT_FALSE_BREAKOUT_EXIT: int = 3  # N캔들 내 레벨 재침범 시 보호 발동
    # 페이크 돌파는 시장가 강제청산보다 "레벨 기반 보호 스탑(=SL 조정)"이 손실 왜곡이 적다.
    BREAKOUT_FALSE_BREAKOUT_USE_PROTECT_SL: bool = True

    # 브레이크아웃 리스크/청산(부분익절)
    # 진입은 "고정 0.1%" 대신 ATR 기반 돌파폭을 요구해 노이즈 돌파를 줄인다.
    BREAKOUT_ATR_BREAK_MULT: float = 0.35
    BREAKOUT_MIN_ADX: float = 18.0
    # 약세장(하락)에서는 ADX가 낮은데도 '느린 하락 추세'가 이어지는 경우가 많다.
    # 숏은 롱보다 구조적으로 빠른 진입이 필요할 수 있어, 숏 전용 임계를 분리한다.
    # 다만 "수익 우선"이면 너무 낮추면 노이즈 숏이 늘 수 있어 16 정도로 보수적으로 둔다.
    BREAKOUT_SHORT_MIN_ADX: float = 16.0

    # 돌파 캔들 종가 위치(0~1): 롱은 상단, 숏은 하단에 위치해야 신뢰
    BREAKOUT_CLOSE_POS_LONG: float = 0.78
    BREAKOUT_CLOSE_POS_SHORT: float = 0.22

    # ============================================================
    # [돌파구 개선] 멀티 타임프레임 + 변동성 확장 + 시간손절
    # ============================================================
    # 3m 기준 5개 = 15m
    BREAKOUT_HTF_MULT: int = 5
    BREAKOUT_HTF_EMA_FAST: int = 8
    BREAKOUT_HTF_EMA_SLOW: int = 21
    BREAKOUT_REQUIRE_HTF_TREND: bool = True
    BREAKOUT_ALLOW_LONG: bool = True
    BREAKOUT_ALLOW_SHORT: bool = True

    # ATR 확장: 현재 ATR이 최근 평균보다 커야 "진짜 돌파"로 본다
    BREAKOUT_ATR_EXPANSION_LOOKBACK: int = 20
    BREAKOUT_ATR_EXPANSION_MULT: float = 1.10

    # 시간손절: N봉 내에 충분히 유리하게 못 가면 포지션 정리(슬리피지/수수료 누수 방지)
    # 시간손절은 3m에서는 손절 누수 완화가 되기도 하지만,
    # 15m 이상에서는 오히려 불리한 청산 이벤트가 늘 수 있어 기본 OFF(0)로 둔다.
    BREAKOUT_TIME_STOP_BARS: int = 0
    BREAKOUT_MIN_FAVORABLE_ATR: float = 0.35

    # ============================================================
    # [완전 다른 전략] HTF 추세 롱온리 (저빈도, 수수료/노이즈 최소화)
    # ============================================================
    # NOTE: 백테스트 기준으로는 손실이 커져 기본 비활성화
    USE_HTF_TREND_MODE: bool = False
    # 프로필/실험 설정이 섞여도 "HTF만" 강제로 돌리고 싶을 때 사용(백테스트 비교용)
    # 실전 기본값은 False(멀티전략 모드). 백테스트/실험에서만 강제로 True를 켜는 것을 권장한다.
    FORCE_HTF_ONLY: bool = False
    HTF_TREND_LONG_ONLY: bool = True
    # HTF 추세 전략에서 숏을 허용할지(기본 OFF).
    # - 실전은 롱온리로 운영하다가, 백테스트로 검증된 경우에만 True로 전환 권장
    HTF_TREND_ALLOW_SHORT: bool = True

    # ============================================================
    # [실험] HTF 하락 중 역추세 롱(반등 스캘프)
    # - 기본 OFF: 검증 전 실전에 넣으면 DD/수수료 누수로 망가질 확률이 큼
    # - 조건: RSI/BB 극단(과매도) + ADX 약함 + 반등 캔들 확인 + 쿨다운
    # ============================================================
    CT_LONG_ENABLE: bool = True
    CT_LONG_RISK_PER_TRADE: float = 0.006          # equity의 0.6% 리스크(작게)
    CT_LONG_MAX_POS_SIZE_MULT: float = 0.25        # MAX_POSITION_SIZE * 이 값으로 상한
    CT_LONG_MAX_ADX: float = 22.0                  # ADX가 높으면 역추세 금지(너무 낮으면 트리거가 0으로 수렴)
    CT_LONG_MAX_ATR_PCT: float = 0.030             # ATR/price가 너무 크면 진입 금지
    CT_LONG_SL_ATR_MULT: float = 1.35              # 손절: 1.35 ATR
    CT_LONG_TP_ATR_MULT: float = 1.70              # 익절: 1.70 ATR
    CT_LONG_TP1_ATR_MULT: float = 0.85             # 부분익절(TP1): 0.85 ATR
    CT_LONG_TP1_FRACTION: float = 0.55             # TP1에서 청산 비중
    CT_LONG_TRAIL_PCT: float = 0.006               # 트레일링(%) - 반등 수익 보존용
    CT_LONG_COOLDOWN_BARS: int = 30                # 재진입 쿨다운(봉)
    CT_LONG_TIME_STOP_BARS: int = 6                # 시간손절(봉) (역추세는 오래 끌면 대부분 재하락)
    CT_LONG_MIN_FAVORABLE_ATR: float = 0.15        # time stop까지 MFE < 0.15 ATR이면 정리
    CT_LONG_MIN_BODY_ATR: float = 0.06             # 반등 캔들 바디가 최소 0.06 ATR
    CT_LONG_MIN_CLOSE_POS: float = 0.55            # 캔들 종가가 범위 상단에 위치해야(0~1)
    CT_LONG_CONFIRM_UP_BARS: int = 2               # 확인진입: 최근 N봉 연속 상승(종가 기준)
    CT_LONG_BE_ARM_ATR: float = 0.35               # MFE가 0.35 ATR 이상이면 BE 보호 발동
    CT_LONG_BE_BUFFER_PCT: float = 0.0006          # BE 보호 시 SL을 entry*(1+buffer)로(수수료/잡음 감안)

    # --- "빅 쇼트 이후 반등" 전용(캡튤레이션 → 리클레임) ---
    CT_LONG_WASHOUT_ENABLE: bool = True            # CT_LONG_ENABLE=True일 때 함께 적용
    CT_LONG_WASHOUT_LOOKBACK_BARS: int = 40        # 최근 고점 탐색 구간(봉)
    CT_LONG_WASHOUT_DROP_ATR_MULT: float = 2.3     # recent_high - close >= ATR * k 이면 급락으로 간주
    # 3m 같은 짧은 봉에서는 ATR%가 매우 작을 수 있어, 최소 ATR% 필터가 있으면 washout 감지가 0건이 되는 경우가 많다.
    # drop>=ATR*k가 이미 변동성 정규화이므로, 기본은 0(미적용)으로 둔다.
    CT_LONG_WASHOUT_MIN_ATR_PCT: float = 0.0       # 급락을 '빅쇼트'로 인정할 최소 변동성(ATR/price). 0이면 미적용
    CT_LONG_WASHOUT_MAX_ATR_PCT: float = 0.040     # 너무 과하면(패닉) 제외
    CT_LONG_WASHOUT_MIN_VOL_MULT: float = 1.00     # 거래량 스파이크(최근 평균 대비) (1.0이면 사실상 미적용)
    CT_LONG_WASHOUT_WINDOW_BARS: int = 24          # 급락 감지 후 반등 진입 허용 윈도우(봉)
    CT_LONG_RECLAIM_EMA_FAST: bool = False         # 반등 확인: close가 EMA_fast 위로 회복해야 함
    CT_LONG_PLAN_REBOUND_ATR_MULT: float = 0.60    # (표시용) 급락 후 반등 롱 트리거: washout_low + ATR*k

    # ===== CT_SHORT (급상승 후 반락 숏) =====
    CT_SHORT_ENABLE: bool = True
    CT_SHORT_RISK_PER_TRADE: float = 0.006
    CT_SHORT_MAX_POS_SIZE_MULT: float = 0.25
    CT_SHORT_MAX_ADX: float = 22.0
    CT_SHORT_MAX_ATR_PCT: float = 0.030
    CT_SHORT_SL_ATR_MULT: float = 1.35
    CT_SHORT_TP_ATR_MULT: float = 1.70
    CT_SHORT_TP1_ATR_MULT: float = 0.85
    CT_SHORT_TP1_FRACTION: float = 0.55
    CT_SHORT_TRAIL_PCT: float = 0.006
    CT_SHORT_COOLDOWN_BARS: int = 30
    CT_SHORT_TIME_STOP_BARS: int = 6
    CT_SHORT_MIN_FAVORABLE_ATR: float = 0.15
    CT_SHORT_MIN_BODY_ATR: float = 0.06
    CT_SHORT_MAX_CLOSE_POS: float = 0.45            # 반락 캔들 종가가 범위 하단에 위치해야(0~1)
    CT_SHORT_CONFIRM_DOWN_BARS: int = 2              # 확인진입: 최근 N봉 연속 하락(종가 기준)
    CT_SHORT_BE_ARM_ATR: float = 0.35
    CT_SHORT_BE_BUFFER_PCT: float = 0.0006

    # "빅펌프" 감지(급상승) → 반락 숏 허용 윈도우
    CT_SHORT_PUMPOUT_ENABLE: bool = True
    CT_SHORT_PUMPOUT_LOOKBACK_BARS: int = 40
    CT_SHORT_PUMPOUT_RISE_ATR_MULT: float = 2.3      # close - recent_low >= ATR*k
    CT_SHORT_PUMPOUT_MIN_ATR_PCT: float = 0.0
    CT_SHORT_PUMPOUT_MAX_ATR_PCT: float = 0.040
    CT_SHORT_PUMPOUT_MIN_VOL_MULT: float = 1.00
    CT_SHORT_PUMPOUT_WINDOW_BARS: int = 24
    CT_SHORT_RECLAIM_EMA_FAST: bool = False          # 반락 확인: close가 EMA_fast 아래로 내려와야 함

    CT_SHORT_PLAN_FADE_ATR_MULT: float = 0.60        # (표시용) 급상승 후 반락 숏 트리거: pumphigh - ATR*k

    # --- HTF 숏 전용 진입 필터(롱 대비 더 보수적으로 기본값 설정) ---
    # 숏은 급반등/쇼트 스퀴즈 리스크가 커서, 신호가 약하면 그냥 안 들어가게 설계한다.
    # 실전에서 거래가 0으로 수렴하는 것을 방지하기 위해 기본값을 완화한다.
    HTF_TREND_SHORT_MIN_STRENGTH_ATR: float = 0.30
    HTF_TREND_SHORT_ENTRY_ATR_BUFFER: float = 0.35
    HTF_TREND_SHORT_MAX_ATR_PCT: float = 0.030
    # HTF(상위 타임프레임) 구성: 3m 기준 20개=1h
    # - HTF 추세 모드는 브레이크아웃 필터용 HTF와 분리해서 튜닝한다.
    HTF_TREND_MULT: int = 20
    HTF_TREND_EMA_FAST: int = 16
    HTF_TREND_EMA_SLOW: int = 64

    # HTF 추세 포지션 사이징(추세 홀딩은 노출을 크게 잡아야 buy&hold에 근접한다)
    # - 기존 MAX_POSITION_SIZE/RISK_PER_TRADE와 분리해서 HTF 모드만 별도 제어
    HTF_TREND_MAX_POSITION_SIZE: float = 2.2   # equity의 220%까지(수익 우선)
    HTF_TREND_RISK_PER_TRADE: float = 0.02     # 거래당 2% 리스크
    HTF_TREND_SIZE: float = 1.0                # 추가 스케일(0~1 권장)

    # 리스크/진입 필터
    HTF_TREND_ATR_SL_MULT: float = 2.2
    HTF_TREND_TRAIL_PCT: float = 0.0
    # 진입 버퍼/쿨다운이 과하면 "신호는 있는데 진입이 없다"가 자주 발생한다.
    HTF_TREND_ENTRY_ATR_BUFFER: float = 0.20
    HTF_TREND_REENTRY_COOLDOWN_BARS: int = 30
    # HTF 추세는 "추세 유지 동안 홀딩"이 목적이라, 기본은 손절을 끄고(추세 반전 청산)
    # 노출(포지션 가치)을 직접 제어한다.
    HTF_TREND_SIZING_MODE: str = "exposure"   # "risk" | "exposure"
    HTF_TREND_TARGET_EXPOSURE: float = 1.3    # 동적 노출 사용 시 기준점(최소 노출은 EXPOSURE_MIN)
    HTF_TREND_USE_STOP_LOSS: bool = False

    # HTF 추세 동적 노출: 추세가 강할수록 노출을 키운다(수익 우선 모드)
    HTF_TREND_DYNAMIC_EXPOSURE: bool = True
    HTF_TREND_EXPOSURE_MIN: float = 1.1
    HTF_TREND_EXPOSURE_MAX: float = 2.2
    HTF_TREND_EXPOSURE_STRENGTH_MIN_ATR: float = 0.25
    HTF_TREND_EXPOSURE_STRENGTH_MAX_ATR: float = 0.90
    # HTF 추세 진입 필터(약한 추세/과변동 구간 진입 방지)
    # strength = (EMA_fast - EMA_slow) / ATR  (long 기준)
    HTF_TREND_MIN_STRENGTH_ATR: float = 0.15
    # atr_pct = ATR / price  (예: 0.02 = 2%/bar)
    HTF_TREND_MAX_ATR_PCT: float = 0.030

    # HTF 추세 보호 트레일(샹들리에/Chandelier Exit)
    # - 급락/급반전만 잘라내서 DD를 줄이고, 추세는 최대한 길게 가져간다.
    HTF_TREND_ENABLE_CHANDELIER: bool = True
    HTF_TREND_CHANDELIER_ATR_MULT: float = 4.2
    HTF_TREND_CHANDELIER_ARM_AFTER_ATR: float = 1.2  # 최소 이익이 ATR*N 이상일 때만 발동(너무 이른 청산 방지)

    # 샹들리에/시간손절 동적 튜닝(강한 추세=더 넓게/느리게, 약한 추세=더 빠르게 정리)
    HTF_TREND_DYNAMIC_EXITS: bool = False
    HTF_TREND_CHANDELIER_ATR_MULT_STRONG: float = 5.0
    HTF_TREND_CHANDELIER_ATR_MULT_WEAK: float = 3.6
    HTF_TREND_TIME_STOP_BARS_STRONG: int = 180
    HTF_TREND_TIME_STOP_BARS_WEAK: int = 90

    # HTF 추세 손실 제한(초기 역방향/급락으로 크게 물리는 케이스 차단)
    # - SL을 완전히 켜면 트레이드가 과도하게 늘거나(노이즈) 수익이 깎일 수 있어,
    #   HTF 모드에만 별도로 "재앙 방지" 컷을 둔다.
    HTF_TREND_ENABLE_CATASTROPHIC_STOP: bool = False
    HTF_TREND_CATASTROPHIC_MAX_LOSS_PCT: float = 0.12  # 12% 손실 제한(블랙스완 대응)
    # entry_atr 기반 컷은 3m에서 과도하게 촘촘해질 수 있어 기본 OFF
    HTF_TREND_CATASTROPHIC_USE_ENTRY_ATR: bool = False
    HTF_TREND_CATASTROPHIC_ATR_MULT: float = 12.0      # entry_atr 기준(ON일 때만)

    # HTF 추세 시간손절(횡보/약추세에서 'EMA 역전까지' 버티며 크게 물리는 손실을 줄임)
    HTF_TREND_TIME_STOP_BARS: int = 120          # 3m 기준 6시간
    HTF_TREND_MIN_FAVORABLE_ATR: float = 0.80    # 이 기간 동안 MFE가 ATR*N 미만이면 정리

    # HTF 추세 소프트 청산(EMA 역전 '이전'에 가격이 EMA_slow 아래로 깊게 밀리면 먼저 정리)
    # - htf_trend_exit(EMA 역전) 손실이 큰 구간을 줄이는 목적
    HTF_TREND_SOFT_EXIT_BELOW_SLOW_ATR: float = 0.0
    # HTF 추세 소프트 청산(숏): EMA 역전 '이전'에 가격이 EMA_slow 위로 깊게 올라오면 먼저 정리
    HTF_TREND_SHORT_SOFT_EXIT_ABOVE_SLOW_ATR: float = 0.0
    # HTF 추세 약화 청산: up 유지라도 추세 강도가 임계치 아래로 떨어지면 먼저 정리
    HTF_TREND_EXIT_MIN_STRENGTH_ATR: float = 0.0
    # HTF 추세 약화 청산(숏): down 유지라도 추세 강도가 임계치 아래로 떨어지면 먼저 정리
    HTF_TREND_SHORT_EXIT_MIN_STRENGTH_ATR: float = 0.0

    # HTF 모드 전용 DD 한도(수익 우선이지만, 전역 설정에 영향 주지 않기 위해 분리)
    HTF_TREND_MAX_TOTAL_DRAWDOWN: float = 0.40
    HTF_TREND_MAX_DAILY_DRAWDOWN: float = 0.25
    # HTF_TREND_MODE를 켰을 때만 의미가 있다.
    # - True: HTF 모드 신호 없으면 "다른 전략"도 차단(저빈도/노이즈 최소화)
    # - False: HTF 모드 신호 없으면 다른 전략이 보조로 진입 가능(거래 수 증가)
    HTF_TREND_DISABLE_OTHER_STRATEGIES: bool = False

    # HTF 추세 DD 저감: 부분 축소(Scale-out)
    # - 추세가 한 번 크게 꺾일 때 전량 청산 대신 일부만 줄여 DD를 깎고,
    #   나머지로 추세가 이어질 때 수익을 최대한 유지한다.
    HTF_TREND_SCALE_OUT_ENABLED: bool = False
    HTF_TREND_SCALE_OUT_MAX_COUNT: int = 1
    HTF_TREND_SCALE_OUT_FRACTION: float = 0.35
    HTF_TREND_SCALE_OUT_ATR_MULT: float = 3.0
    HTF_TREND_SCALE_OUT_ARM_AFTER_ATR: float = 1.5

    # ============================================================
    # [실전 실행 리스크 모델] (지정가/미체결/펀딩/강제청산)
    # ============================================================
    # 지정가 체결을 기본으로 강제하고, 미체결/지연 체결을 모델링한다.
    LIMIT_ONLY_MODE: bool = False

    # 진입 지정가 오프셋은 기존 LIMIT_ENTRY_OFFSET_PCT를 사용한다.
    LIMIT_EXIT_OFFSET_PCT: float = 0.00020   # 청산은 체결 우선이라 진입보다 작게

    # 지정가 대기/재호가(체결 못 하면 따라붙음)
    LIMIT_MAX_WAIT_BARS: int = 12            # 3m 기준 36분
    LIMIT_REQUOTE_EACH_BAR: bool = True
    LIMIT_REQUOTE_STEP_PCT: float = 0.00010  # 매 봉마다 가격을 이만큼씩 더 공격적으로 조정

    # 부분체결(선택): 1.0이면 항상 전량 체결
    LIMIT_PARTIAL_FILL_FRACTION: float = 1.0

    # 미체결 처리 정책(더 현실적으로)
    LIMIT_ENTRY_CANCEL_ON_EXPIRE: bool = True          # 진입은 만료되면 놓침(거래 기회 손실)
    LIMIT_EXIT_FORCE_MARKET_ON_EXPIRE: bool = True     # 청산은 만료되면 시장가로 강제(실전: 위험 회피)

    # 펀딩(선물) 모델: 8시간마다 포지션 노미널에 펀딩 적용
    FUNDING_ENABLED: bool = True
    FUNDING_INTERVAL_HOURS: int = 8
    FUNDING_RATE_PER_INTERVAL: float = 0.00010  # 0.01%/8h (보수적으로 비용으로만 가정 가능)
    FUNDING_ASSUME_PAY_ONLY: bool = True         # True면 long/short 모두 비용(보수적)

    # 강제청산(레버리지 노출 기반) 모델
    LIQUIDATION_ENABLED: bool = True
    MAINT_MARGIN_RATE: float = 0.005            # 0.5%
    LIQUIDATION_FEE_RATE: float = 0.0010        # 0.1% (청산 수수료)

    # ============================================================
    # [돌파 점수 모델] (룰 기반이지만 분류기처럼 동작)
    # - 여러 조건을 가중합으로 묶고 score>=threshold 일 때만 진입
    # ============================================================
    BREAKOUT_SCORE_THRESHOLD: float = 0.72
    # 숏은 롱보다 더 빠르게 반응해야 하는 케이스가 많아 점수 임계치를 분리한다.
    # 수익 우선(느려도 됨): 숏 점수 임계는 너무 낮추지 않는다.
    BREAKOUT_SHORT_SCORE_THRESHOLD: float = 0.70
    BREAKOUT_SCORE_W_ADX: float = 0.20
    BREAKOUT_SCORE_W_VOL: float = 0.20
    BREAKOUT_SCORE_W_CLOSE_POS: float = 0.20
    BREAKOUT_SCORE_W_BREAK: float = 0.25
    BREAKOUT_SCORE_W_ATR_EXP: float = 0.15

    # 숏 품질 필터(수익 우선)
    BREAKOUT_SHORT_REQUIRE_HTF_TREND: bool = True     # 큰추세가 하락 정렬일 때만
    BREAKOUT_SHORT_REQUIRE_ATR_EXPANSION: bool = True # 변동성 확장(가속) 동반일 때만
    BREAKOUT_SHORT_MIN_VOL_RATIO: float = 1.05        # 거래량이 평균 대비 최소 5% 이상일 때만(0이면 미적용)

    # ------------------------------------------------------------
    # [소프트 진입] (타당성 있으면 "소량 선진입" → 기회손실 감소)
    # - threshold를 무작정 낮추는 대신, "soft threshold"에서 작은 사이즈만 허용
    # - hard filter(숏 HTF/ATR/볼륨)는 기본 유지하되, 매우 강한 이탈에서는 일부 우회 가능
    # ------------------------------------------------------------
    BREAKOUT_SOFT_ENTRY_ENABLE: bool = True
    BREAKOUT_SOFT_THRESHOLD_DELTA: float = 0.08       # soft_thr = thr - delta (ex: 0.72→0.64)
    BREAKOUT_SOFT_SIZE: float = 0.32                  # soft 진입 사이즈(Decision.size)
    BREAKOUT_SOFT_MIN_ADX_RELAX: float = 2.0          # soft에서 minAdx를 이 값만큼 완화(0이면 미완화)
    BREAKOUT_SHORT_STRONG_BREAK_RATIO: float = 2.0    # (delta/needDelta) >= 이 값이면 숏 하드필터 일부 우회 허용

    # ------------------------------------------------------------
    # [3단계 진입] 1) 관찰(진입X) 2) 소량(soft) 3) 전체(immediate)
    # - 1단계는 "지켜보는 자리"를 명확히 보여주기 위한 상태/선이며 실제 진입은 하지 않는다.
    # ------------------------------------------------------------
    ENTRY_3STAGE_ENABLE: bool = True
    BREAKOUT_WATCH_EXTRA_DELTA: float = 0.06          # watch_thr = (soft_thr) - extra_delta (더 완화)
    BREAKOUT_WATCH_MIN_ADX_RELAX: float = 6.0         # watch에서 ADX 완화 폭(soft보다 더 완화)
    # 3단계 가격 분리(같은 트리거 금지): full(3) 기준 버퍼의 비율로 stage2/stage1 가격을 앞당긴다.
    # - 롱: watchPrice < softPrice < fullPrice
    # - 숏: watchPrice > softPrice > fullPrice
    # 돌파 3단계 가격:
    # - 1단계(관찰)은 pre-break(레벨 직전)이라 너무 멀면 의미가 없고,
    # - 2단계(소량)은 첫 이탈 직후로 최대한 당겨야 "거래량 끝물"에 따라붙는 문제가 줄어든다.
    BREAKOUT_STAGE2_BUFFER_MULT: float = 0.28         # 2단계(소량) 버퍼 = fullBuf * mult
    BREAKOUT_STAGE1_BUFFER_MULT: float = 0.18         # 1단계(관찰) 버퍼 = fullBuf * mult

    # 3단계 라인 계산에 사용하는 "공정가치" 보조 지표(롤링 VWAP)
    BREAKOUT_VWAP_WINDOW: int = 60
    BREAKOUT_WATCH_VWAP_ATR_OFFSET: float = 0.10
    # 2단계 소량 진입이 지나치게 멀어져 후행(chasing)되는 걸 막기 위한 ATR 상한
    BREAKOUT_SOFT_MAX_ATR_CAP: float = 0.35
    # 3단계 전체 진입(full)이 너무 멀어져 "많이 오른 뒤에야 롱/많이 떨어진 뒤에야 숏"이 되는 걸 방지하기 위한 상한
    BREAKOUT_FULL_MAX_ATR_CAP: float = 0.95

    # 레벨(저항/지지)이 현재가에서 너무 멀면 "끝물"에만 닿는다.
    # - 최근 N봉의 로컬 레벨을 대안으로 계산하고,
    # - 현재가와의 거리가 ATR * K를 넘으면 로컬 레벨을 채택한다.
    BREAKOUT_LEVEL_LOCAL_LOOKBACK: int = 10
    BREAKOUT_LEVEL_MAX_GAP_ATR: float = 1.25

    # 위 두 값은 고정값으로 두면 시장 상태에 따라 과도하게 보수/공격으로 치우칠 수 있다.
    # - True: ATR%/ADX 기반으로 K(갭 임계)와 N(로컬 룩백)을 자동 조절
    # - False: 설정값을 그대로 사용
    BREAKOUT_LEVEL_AUTO_TUNE: bool = True
    BREAKOUT_LEVEL_LOCAL_LOOKBACK_MIN: int = 6
    BREAKOUT_LEVEL_LOCAL_LOOKBACK_MAX: int = 20
    BREAKOUT_LEVEL_MAX_GAP_ATR_MIN: float = 0.60
    BREAKOUT_LEVEL_MAX_GAP_ATR_MAX: float = 2.20

    CT_WATCH_ENABLE: bool = True
    CT_WATCH_DROP_RATIO: float = 0.65                 # drop >= needDrop*ratio면 "관찰" 상태(확인봉 전)
    CT_WATCH_RISE_RATIO: float = 0.65                 # rise >= needRise*ratio면 "관찰" 상태(확인봉 전)
    # CT 3단계 가격 분리(같은 트리거 금지): full 트리거 기준으로 ATR만큼 앞당겨 1/2단계 가격을 만든다.
    CT_STAGE2_ATR_BACK: float = 0.10                  # 2단계(소량): fullPrice에서 ATR*k 만큼 앞당김(롱은 - / 숏은 +)
    CT_STAGE1_ATR_BACK: float = 0.25                  # 1단계(관찰): fullPrice에서 ATR*k 만큼 더 앞당김

    # ATR% 기반 소프트 진입 자동 조절
    # - atr_pct = ATR / price
    # - 저변동(atr_pct <= LOW)에서는 소프트를 조금 더 공격적으로(임계 완화 폭↑ / 사이즈↑)
    # - 고변동(atr_pct >= HIGH)에서는 소프트를 더 보수적으로(임계 완화 폭↓ / 사이즈↓)
    SOFT_VOL_ATR_PCT_LOW: float = 0.008              # 0.8%
    SOFT_VOL_ATR_PCT_HIGH: float = 0.020             # 2.0%
    SOFT_DELTA_SCALE_LOW: float = 1.10               # 저변동: delta * 1.10
    SOFT_DELTA_SCALE_HIGH: float = 0.65              # 고변동: delta * 0.65
    SOFT_SIZE_SCALE_LOW: float = 1.05                # 저변동: size * 1.05
    SOFT_SIZE_SCALE_HIGH: float = 0.70               # 고변동: size * 0.70

    # CT(급락/급상승 역추세) 소프트 진입: "확인봉" 없이도 강신호면 소량 진입
    CT_SOFT_ENTRY_ENABLE: bool = True
    CT_SOFT_RISK_MULT: float = 0.70                  # CT soft는 리스크/사이즈를 줄여 선진입
    CT_LONG_STRONG_OVERRIDE_MULT: float = 1.35        # drop >= needDrop*mult이면 confirmOk 없이도 softOk 허용
    CT_SHORT_STRONG_OVERRIDE_MULT: float = 1.35       # rise >= needRise*mult이면 confirmOk 없이도 softOk 허용
    CT_SOFT_RISK_SCALE_HIGH_VOL: float = 0.80         # 고변동에서는 CT soft 리스크를 추가로 축소

    # ------------------------------------------------------------
    # [예상 진입가(트리거) 도망 방지] Trigger Lock
    # - 한 번 "타당성(softOk 이상)"이 나오면 트리거가 계속 멀어지는(chasing) 현상을 막는다.
    # - 롱: 트리거는 내려가거나(유리) 고정만 허용, 올라가는(불리) 업데이트는 금지
    # - 숏: 트리거는 올라가거나(유리) 고정만 허용, 내려가는(불리) 업데이트는 금지
    # ------------------------------------------------------------
    ENTRY_TRIGGER_LOCK_ENABLE: bool = True
    ENTRY_TRIGGER_LOCK_BARS: int = 18                 # 락 유지 기간(봉). 3m 기준 54분
    ENTRY_TRIGGER_LOCK_ARM_ON: str = "soft"           # "soft" | "immediate"

    # ------------------------------------------------------------
    # [터치 후 빠른 판단/진입] (예상 진입가에 닿으면 10초 내 결론)
    # - 가격이 트리거를 "한 번이라도" 충족하면, 짧은 윈도우 동안 더 빠르게 재평가하여
    #   노이즈/윅 때문에 confirm tick이 끊겨도 기회를 놓치지 않게 한다.
    # ------------------------------------------------------------
    ENTRY_TOUCH_DECISION_WINDOW_SEC: float = 10.0     # 터치 후 이 시간 안에 결론(진입/무시)
    ENTRY_TOUCH_FAST_POLL_SEC: float = 0.10           # 터치 윈도우 동안 재평가 주기(초)

    # ============================================================
    # [실전] 인트라바(봉 진행 중) 진입 옵션
    # - "마감봉까지 기다리지 않고" 현재가가 트리거를 돌파/이탈하면 즉시 진입을 허용
    # - 판단 로직(필터/점수)은 유지하고, 타이밍만 빠르게 만든다.
    # ============================================================
    INTRABAR_ENTRY_ENABLE: bool = True
    INTRABAR_ENTRY_POLL_SEC: float = 0.25         # 현재가 체크 주기(초)
    # "2틱 확정"은 기회손실이 커질 수 있어 기본 1(즉시)로 둔다.
    INTRABAR_ENTRY_CONFIRM_TICKS: int = 1         # 연속 N회 조건 충족 시 진입

    # ============================================================
    # [CT(급락/급상승) 전용 유예] 성급한 진입을 방지하기 위한 추가 확인
    # - 브레이크아웃은 빠르게, CT는 조금 더 "차트 확인" 후 진입
    # ============================================================
    CT_INTRABAR_CONFIRM_TICKS: int = 3             # CT 진입은 연속 N틱 확인 후 실행(유예)

    # 손절/익절은 '자주 먹는 TP1 + 길게 끌고 가는 TP2' 구조
    # SL은 조금 더 타이트하게(손실 기대값 줄이기), TP1/TP2는 현실적으로 도달 가능한 거리로
    BREAKOUT_ATR_SL_MULT: float = 1.6
    BREAKOUT_ATR_TP1_MULT: float = 1.0
    BREAKOUT_ATR_TP2_MULT: float = 2.0
    PARTIAL_TP_FRACTION: float = 0.60  # TP1에서 청산할 비중
    
    # ============================================================
    # [시간대 필터] - 변동성 기반 조정
    # ============================================================
    SESSION_ASIA_START: int = 0
    SESSION_ASIA_END: int = 8
    SESSION_EUROPE_START: int = 8
    SESSION_EUROPE_END: int = 16
    SESSION_US_START: int = 14
    SESSION_US_END: int = 22
    
    # 변동성 기반 사이즈 조정
    # 아시아: σ ≈ 0.7σ_avg → size × √(1/0.7) = 1.2 (but 역으로 줄임)
    # 미국: σ ≈ 1.3σ_avg → size × √(1/1.3) = 0.87 (but 변동성 높으니 줄임)
    SESSION_ASIA_SIZE_MULT: float = 0.6   # 낮은 변동성 = 낮은 확신
    SESSION_EUROPE_SIZE_MULT: float = 0.9
    SESSION_US_SIZE_MULT: float = 1.0     # 기준
    
    # 거래 금지 시간
    BLACKOUT_HOURS: List[int] = [23, 0, 1, 2]  # 저유동성
    NEWS_BLACKOUT_MINUTES: int = 30       # 주요 뉴스 전후 30분
    
    # ============================================================
    # [AI 분류기] - 최적 아키텍처
    # ============================================================
    # Hidden = √(12 × 3 × 64) ≈ 48 → 64 (2^k)
    # Layers: target 500K params
    CLASSIFIER_SEQ_LEN: int = 64
    CLASSIFIER_HIDDEN: int = 128          # 더 큰 표현력
    CLASSIFIER_LAYERS: int = 2
    CLASSIFIER_DROPOUT: float = 0.3
    CLASSIFIER_CONFIDENCE: float = 0.65   # 신뢰도 임계값
    
    # 앙상블 설정
    CLASSIFIER_ENSEMBLE: bool = False     # 앙상블 사용 여부
    CLASSIFIER_ENSEMBLE_COUNT: int = 3    # 앙상블 모델 수
    
    # ============================================================
    # [경로]
    # ============================================================
    CHECKPOINT_DIR: str = "checkpoints"
    CLASSIFIER_PATH: str = "checkpoints/market_classifier.pt"
    DATA_DIR: str = "data"
    
    # ============================================================
    # [API]
    # ============================================================
    BINANCE_WS_URL: str = "wss://fstream.binance.com/ws"
    BINANCE_REST_URL: str = "https://fapi.binance.com"
    
    # ============================================================
    # [모니터링]
    # ============================================================
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    
    DASHBOARD_PORT: int = 8050
    LOG_LEVEL: str = "INFO"
    
    # ============================================================
    # [계산된 파생 값]
    # ============================================================
    @property
    def kelly_full(self) -> float:
        """Full Kelly Criterion"""
        return WIN_RATE - (1 - WIN_RATE) / RISK_REWARD
    
    @property
    def kelly_half(self) -> float:
        """Half Kelly (권장)"""
        return self.kelly_full / 2
    
    @property
    def edge(self) -> float:
        """기대 수익률 (edge)"""
        return WIN_RATE * RISK_REWARD - (1 - WIN_RATE)
    
    @property
    def min_rr_ratio(self) -> float:
        """손익분기 손익비"""
        return (1 - WIN_RATE) / WIN_RATE
    
    @property
    def losing_streak_99pct(self) -> int:
        """99% 신뢰구간 최대 연패"""
        return LOSING_STREAK_99
    
    @property
    def min_trades_statistical(self) -> int:
        """통계적 유의성 최소 거래 수"""
        return MIN_TRADES_SIGNIFICANT
    
    @property
    def optimal_pyramid_decay(self) -> float:
        """피라미딩 감소율"""
        return PYRAMID_DECAY
    
    # ============================================================
    # Pydantic Config
    # ============================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )


# 설정 인스턴스
settings = TradingSettings()

# 계산된 값 출력
print(f"[OK] 설정 로드: {settings.APP_NAME}")
print(f"=" * 60)
print(f"[수학적 최적화 파라미터]")
print(f"   승률 가정     : {WIN_RATE*100:.0f}%")
print(f"   손익비        : {RISK_REWARD:.1f}:1")
print(f"   Full Kelly    : {settings.kelly_full*100:.2f}%")
print(f"   Half Kelly    : {settings.kelly_half*100:.2f}%")
print(f"   Edge          : {settings.edge*100:.2f}%")
print(f"   BEP 손익비    : {settings.min_rr_ratio:.2f}:1")
print(f"   99% 연패한계  : {settings.losing_streak_99pct}연패")
print(f"   유의 거래수   : {settings.min_trades_statistical}회")
print(f"   피라미딩 감소 : {settings.optimal_pyramid_decay:.2f}")
print(f"=" * 60)
print(f"[리스크 설정]")
print(f"   일일 DD 한계  : {settings.MAX_DAILY_DRAWDOWN*100:.0f}%")
print(f"   총 DD 한계    : {settings.MAX_TOTAL_DRAWDOWN*100:.0f}%")
print(f"   포지션 한계   : {settings.MAX_POSITION_SIZE*100:.0f}%")
print(f"   ATR SL/TP     : {settings.ATR_SL_MULT:.1f} / {settings.ATR_TP_MULT:.1f} ATR")
print(f"=" * 60)
