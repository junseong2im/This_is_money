"""
고급 전략 선택기 (Enhanced Strategy Selector)

핵심 개선:
1. EV + 승률 복합 점수
2. 최근 성과 가중치
3. 리스크 조정 수익률 (Sharpe-like)
"""
from typing import List, Optional
from core.types import StrategyStats


def select_best(stats: List[StrategyStats]) -> Optional[StrategyStats]:
    """
    최적 전략 선택 (복합 점수 기반)
    
    선택 기준:
    1. EV > 0 필수
    2. 복합 점수 = EV * sqrt(confidence) * win_rate_bonus
    """
    if not stats:
        return None
    
    # EV > 0인 것만 필터
    valid = [s for s in stats if s.ev > 0 and s.confidence > 0.2]
    
    if not valid:
        return None
    
    # 복합 점수 계산
    def composite_score(s: StrategyStats) -> float:
        # 기본 점수: EV
        score = s.ev
        
        # 신뢰도 가중치 (제곱근으로 완화)
        score *= (s.confidence ** 0.5)
        
        # 승률 보너스 (50% 이상이면 보너스)
        if s.win_rate > 0.55:
            score *= 1.2
        elif s.win_rate > 0.50:
            score *= 1.1
        elif s.win_rate < 0.40:
            score *= 0.8  # 승률 낮으면 페널티
        
        # 평균 손익비 (avg_win / avg_loss) 보너스
        if s.avg_loss > 0:
            rr_ratio = s.avg_win / s.avg_loss
            if rr_ratio > 2.0:
                score *= 1.15
            elif rr_ratio > 1.5:
                score *= 1.05
        
        return score
    
    # 최고 점수 전략 선택
    return max(valid, key=composite_score)


def rank_strategies(stats: List[StrategyStats], top_n: int = 3) -> List[StrategyStats]:
    """
    전략들을 점수순으로 정렬하여 상위 N개 반환
    """
    valid = [s for s in stats if s.ev > 0 and s.confidence > 0.2]
    
    def composite_score(s: StrategyStats) -> float:
        score = s.ev * (s.confidence ** 0.5)
        if s.win_rate > 0.55:
            score *= 1.2
        return score
    
    sorted_stats = sorted(valid, key=composite_score, reverse=True)
    return sorted_stats[:top_n]
