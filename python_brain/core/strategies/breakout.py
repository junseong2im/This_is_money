from typing import Optional
from core.strategies.base import BaseStrategy
from core.features import MarketFeatures
from core.types import StrategySignal


class BreakoutStrategy(BaseStrategy):
    """
    고급 돌파 전략 (Enhanced Breakout Strategy)
    
    핵심 개선:
    1. 동적 ATR 배수 (변동성에 따라 조정)
    2. ADX 강도 기반 목표가 확장
    3. 거래량 급증 보너스
    4. 트레일링 스탑 힌트 제공
    """
    name = "breakout"
    
    # 파라미터 (튜닝 가능)
    MIN_ADX = 20
    MIN_ATR_PCT = 0.002  # Optimized for standard market
    MIN_VOLUME_Z = 0.5   # Lowered volume threshold
    BASE_SL_ATR = 1.2      # 손절: 1.2 ATR (더 타이트하게)
    BASE_TP_ATR = 2.0      # 기본 목표: 2.0 ATR
    MAX_TP_ATR = 4.0       # 최대 목표 (강한 추세시)

    def generate(self, f: MarketFeatures) -> Optional[StrategySignal]:
        # 1. 기본 조건 체크
        if f.adx < self.MIN_ADX:
            return None
        if f.atr_pct < self.MIN_ATR_PCT:
            return None
        if f.volume_z < self.MIN_VOLUME_Z:
            return None
        
        # 2. 동적 목표가 계산 (ADX + 거래량 기반)
        # ADX가 높을수록 추세가 강함 → 목표가 확장
        adx_bonus = min((f.adx - 25) * 0.05, 1.0)  # ADX 25→45일 때 0→1
        volume_bonus = min((f.volume_z - 1.0) * 0.3, 0.5)  # 거래량 급증시 보너스
        
        tp_multiplier = self.BASE_TP_ATR + adx_bonus + volume_bonus
        tp_multiplier = min(tp_multiplier, self.MAX_TP_ATR)
        
        # 3. 동적 손절 (변동성 높으면 약간 넓게)
        sl_multiplier = self.BASE_SL_ATR
        if f.atr_pct > 0.015:  # 변동성 높음
            sl_multiplier = 1.5
        
        # 4. Long 조건: 상승 추세 돌파
        if f.ema_fast_slope > 0.0005 and f.ema_slow_slope > 0:
            # 펀딩비 체크: 롱 과열이면 스킵
            if f.funding_rate > 0.0003:  # 0.03% 이상이면 과열
                return None
            
            stop = f.price - (f.atr_value * sl_multiplier)
            target = f.price + (f.atr_value * tp_multiplier)
            
            return StrategySignal(
                direction="long",
                entry=f.price,
                stop=stop,
                target=target
            )
        
        # 5. Short 조건: 하락 추세 돌파
        if f.ema_fast_slope < -0.0005 and f.ema_slow_slope < 0:
            # 펀딩비 체크: 숏 과열이면 스킵
            if f.funding_rate < -0.0003:
                return None
            
            stop = f.price + (f.atr_value * sl_multiplier)
            target = f.price - (f.atr_value * tp_multiplier)
            
            return StrategySignal(
                direction="short",
                entry=f.price,
                stop=stop,
                target=target
            )
        
        return None
