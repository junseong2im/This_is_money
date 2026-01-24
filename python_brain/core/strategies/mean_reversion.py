from typing import Optional
from core.strategies.base import BaseStrategy
from core.features import MarketFeatures
from core.types import StrategySignal


class MeanReversionStrategy(BaseStrategy):
    """
    고급 평균 회귀 전략 (Enhanced Mean Reversion Strategy)
    
    핵심 개선:
    1. 다단계 과매도/과매수 판단
    2. 거래량 급증 시 진입 강화
    3. 빠른 익절 (RR 1:1.2 → 고승률)
    4. 추세장 필터 강화
    """
    name = "mean_reversion"
    
    # 파라미터
    MAX_ADX = 25  # 추세장 회피 (더 엄격)
    MAX_VOLUME_Z = 3.0  # 극단 거래량 회피
    MIN_ATR_PCT = 0.002
    
    # 진입 레벨 (약/중/강)
    WEAK_DIP = -0.006   # 0.6% 하락 (Optimized)
    STRONG_DIP = -0.012  # 1.2% 하락
    WEAK_PUMP = 0.006
    STRONG_PUMP = 0.012
    
    # 손절/익절
    BASE_SL_ATR = 0.8   # 빠른 손절
    WEAK_TP_ATR = 1.0   # 약한 신호: 빠른 익절
    STRONG_TP_ATR = 1.8  # 강한 신호: 더 큰 목표

    def generate(self, f: MarketFeatures) -> Optional[StrategySignal]:
        # 1. 추세장 필터 (평균회귀는 횡보장에서만)
        if f.adx > self.MAX_ADX:
            return None
        
        # 2. 극단 거래량 회피 (패닉 상황)
        if f.volume_z > self.MAX_VOLUME_Z:
            return None
        
        # 3. 최소 변동성
        if f.atr_pct < self.MIN_ATR_PCT:
            return None
        
        # 4. Long 조건: 과매도
        if f.ret_5 < self.WEAK_DIP:
            # 강한 과매도 vs 약한 과매도
            is_strong = f.ret_5 < self.STRONG_DIP and f.ret_1 < -0.005
            
            # 거래량 급증 시 더 강한 신호 (패닉 셀 후 반등 기대)
            volume_boost = f.volume_z > 1.2
            
            if not (is_strong or volume_boost or f.ret_1 < -0.003):
                return None
            
            sl_mult = self.BASE_SL_ATR
            tp_mult = self.STRONG_TP_ATR if is_strong else self.WEAK_TP_ATR
            
            stop = f.price - (f.atr_value * sl_mult)
            target = f.price + (f.atr_value * tp_mult)
            
            return StrategySignal(
                direction="long",
                entry=f.price,
                stop=stop,
                target=target
            )
        
        # 5. Short 조건: 과매수
        if f.ret_5 > self.WEAK_PUMP:
            is_strong = f.ret_5 > self.STRONG_PUMP and f.ret_1 > 0.005
            volume_boost = f.volume_z > 1.2
            
            if not (is_strong or volume_boost or f.ret_1 > 0.003):
                return None
            
            sl_mult = self.BASE_SL_ATR
            tp_mult = self.STRONG_TP_ATR if is_strong else self.WEAK_TP_ATR
            
            stop = f.price + (f.atr_value * sl_mult)
            target = f.price - (f.atr_value * tp_mult)
            
            return StrategySignal(
                direction="short",
                entry=f.price,
                stop=stop,
                target=target
            )
        
        return None
