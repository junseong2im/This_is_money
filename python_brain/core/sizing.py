"""
고급 포지션 사이징 (Enhanced Position Sizing)

핵심 개선:
1. Kelly Criterion 기반 사이징
2. EV 크기에 따른 비례 배팅
3. 최대 손실 제한 (daily drawdown)
4. 승률 기반 조정
"""
from core.types import StrategyStats


def position_size(equity: float, stat: StrategyStats, 
                  base_risk: float = 0.02,
                  max_risk: float = 0.05,
                  max_position_pct: float = 0.15) -> float:
    """
    Kelly Criterion 기반 동적 포지션 사이징
    
    Args:
        equity: 현재 자본
        stat: 전략 통계 (ev, confidence, win_rate, avg_win, avg_loss)
        base_risk: 기본 리스크 (2%)
        max_risk: 최대 리스크 (5%)
        max_position_pct: 최대 포지션 비율 (15%)
    
    Returns:
        포지션 크기 (USDT)
    """
    # 1. EV가 음수면 진입 금지
    if stat.ev <= 0:
        return 0.0
    
    # 2. 신뢰도가 낮으면 진입 금지
    if stat.confidence < 0.3:
        return 0.0
    
    # 3. Kelly Criterion 계산
    # Kelly = (bp - q) / b
    # b = avg_win / avg_loss (odds ratio)
    # p = win_rate, q = 1 - p
    if stat.avg_loss > 0 and stat.avg_win > 0:
        b = stat.avg_win / stat.avg_loss
        p = stat.win_rate
        q = 1 - p
        kelly = (b * p - q) / b if b > 0 else 0
        kelly = max(0, min(kelly, 0.25))  # Kelly를 25%로 제한 (보수적)
    else:
        kelly = 0.1  # 기본값
    
    # 4. 최종 리스크 계산
    # - 기본 리스크 * 신뢰도 * Kelly 조정
    risk_pct = base_risk * stat.confidence
    
    # Kelly가 높으면 리스크 증가 (최대 max_risk까지)
    if kelly > 0.1:
        risk_pct = min(risk_pct * (1 + kelly), max_risk)
    
    # EV가 높으면 추가 보너스
    if stat.ev > 0.005:  # EV 0.5% 이상
        risk_pct = min(risk_pct * 1.2, max_risk)
    
    # 5. 포지션 크기 계산
    position = equity * risk_pct
    
    # 6. 최대 포지션 제한
    max_position = equity * max_position_pct
    position = min(position, max_position)
    
    return position


def dynamic_risk_adjustment(equity: float, 
                           peak_equity: float,
                           daily_pnl: float) -> float:
    """
    동적 리스크 조정 (드로우다운/연승 기반)
    
    Returns:
        리스크 조정 배수 (0.5 ~ 1.5)
    """
    # 현재 드로우다운 계산
    drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
    
    # 드로우다운이 크면 리스크 축소
    if drawdown > 0.10:  # 10% DD
        return 0.5
    elif drawdown > 0.05:  # 5% DD
        return 0.7
    
    # 오늘 수익 중이면 리스크 약간 증가
    if daily_pnl > 0:
        return 1.2
    
    return 1.0
