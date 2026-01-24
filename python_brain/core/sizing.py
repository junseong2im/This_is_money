"""
고급 포지션 사이징 (Enhanced Position Sizing)

핵심 개선:
1. Volatility Targeting (변동성 목표 기반)
2. Kelly Criterion 기반 사이징
3. 최대 손실 제한
"""
from core.types import StrategyStats

def position_size(equity: float, stat: StrategyStats, 
                  current_volatility: float = 0.005, # Current ATR% or similar
                  target_volatility: float = 0.40, # Target Annualized Vol 40%
                  max_position_pct: float = 0.50) -> float:
    """
    Volatility Targeting + Kelly Sizing
    
    Args:
        equity: 현재 자본
        stat: 전략 통계
        current_volatility: 현재 시장 변동성 (ATR% or similar)
        target_volatility: 목표 연환산 변동성 (예: 40%)
        max_position_pct: 최대 포지션 크기 제한
    
    Returns:
        포지션 크기 (USDT)
    """
    # 1. EV Check
    if stat.ev <= 0:
        return 0.0
    
    # 2. Volatility Targeting
    # Position Size % = Target Vol / Current Vol
    # Annual Vol ~= Daily Vol * sqrt(365) ~= 5m Vol * sqrt(365*288) ... simplified:
    # Let's use scalar target. If target daily move is 2% and current daily move is 4%, half size.

    # We treat current_volatility as the expected move over the trade duration.
    # But let's simplify:
    # Ideal Position = (Target Risk %) / (Stop Loss %)
    # This ensures if Stop Loss is hit, we lose exactly Target Risk %.

    target_risk_per_trade = 0.02 # 2% Equity Risk
    
    # Kelly Adjustment
    kelly_factor = 1.0
    if stat.avg_loss > 0 and stat.avg_win > 0:
        b = stat.avg_win / stat.avg_loss
        p = stat.win_rate
        q = 1 - p
        kelly = (b * p - q) / b if b > 0 else 0
        # Half Kelly for safety
        kelly_factor = max(0.5, min(kelly * 0.5, 1.5))
    
    # Adjust risk based on Kelly and Confidence
    adjusted_risk = target_risk_per_trade * kelly_factor * stat.confidence
    
    # Stop Loss distance is implied by strategy.
    # If we don't have exact SL here, we assume it's proportional to Volatility.
    # Usually SL is ~1.5 * ATR.
    # So Risk = PositionSize * (1.5 * ATR_pct)
    # PositionSize = Risk / (1.5 * ATR_pct)
    
    # If current_volatility passed in is ATR_pct:
    estimated_sl_pct = 1.5 * current_volatility
    if estimated_sl_pct == 0: estimated_sl_pct = 0.01
    
    position_size_usd = (equity * adjusted_risk) / estimated_sl_pct
    
    # Cap at Max Position
    position_size_usd = min(position_size_usd, equity * max_position_pct)
    
    return position_size_usd
