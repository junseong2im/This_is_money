from typing import Optional
from core.strategies.base import BaseStrategy
from core.features import MarketFeatures
from core.types import StrategySignal


class TrendStrategy(BaseStrategy):
    """
    고급 추세 추종 전략 (Enhanced Trend Following Strategy)
    
    핵심 개선:
    1. 펀딩비 역방향 전략 (숏 과열 → 롱, 롱 과열 → 숏)
    2. 모멘텀 확인 (ret_1, ret_5)
    3. 동적 RR (추세 강도에 따라)
    4. 변동성 필터 강화
    """
    name = "trend"
    
    # 파라미터
    MIN_ADX = 30           # Optimized: Very strong trend only
    MIN_ATR_PCT = 0.002
    STRONG_ADX = 40        # Higher threshold for "Strong"
    BASE_SL_ATR = 1.5      # Optimized: Moderate stop
    BASE_TP_ATR = 3.0      # Optimized: 2:1 Reward Risk ratio
    MAX_TP_ATR = 6.0

    def generate(self, f: MarketFeatures) -> Optional[StrategySignal]:
        # 1. 기본 조건
        if f.adx < self.MIN_ADX:
            return None
        if f.atr_pct < self.MIN_ATR_PCT:
            return None
        
        # 2. 추세 강도 계산
        is_strong_trend = f.adx > self.STRONG_ADX
        
        # 3. 펀딩비 신호 (역방향이 유리)
        funding_long_signal = f.funding_rate < -0.0001  # 숏 과열 → 롱 유리
        funding_short_signal = f.funding_rate > 0.0002  # 롱 과열 → 숏 유리
        
        # 4. 모멘텀 확인
        long_momentum = f.ret_1 > 0 and f.ret_5 > 0
        short_momentum = f.ret_1 < 0 and f.ret_5 < 0
        
        # 5. 동적 목표가 계산
        tp_mult = self.BASE_TP_ATR
        if is_strong_trend:
            tp_mult += 1.0  # 강한 추세시 목표 확장
        if funding_long_signal or funding_short_signal:
            tp_mult += 0.5  # 펀딩비 유리시 보너스
        tp_mult = min(tp_mult, self.MAX_TP_ATR)
        
        # 6. Long 조건
        if f.ema_fast_slope > 0.0008 and f.ema_slow_slope > 0.0002:
            # 모멘텀 확인 또는 펀딩비 유리
            if not (long_momentum or funding_long_signal):
                return None
            
            sl_mult = self.BASE_SL_ATR
            # 펀딩비 유리하면 손절 약간 넓게 (버틸 가치 있음)
            if funding_long_signal:
                sl_mult = 2.0
            
            stop = f.price - (f.atr_value * sl_mult)
            target = f.price + (f.atr_value * tp_mult)
            
            return StrategySignal(
                direction="long",
                entry=f.price,
                stop=stop,
                target=target
            )
        
        # 7. Short 조건
        if f.ema_fast_slope < -0.0008 and f.ema_slow_slope < -0.0002:
            if not (short_momentum or funding_short_signal):
                return None
            
            sl_mult = self.BASE_SL_ATR
            if funding_short_signal:
                sl_mult = 2.0
            
            stop = f.price + (f.atr_value * sl_mult)
            target = f.price - (f.atr_value * tp_mult)
            
            return StrategySignal(
                direction="short",
                entry=f.price,
                stop=stop,
                target=target
            )
        
        return None
