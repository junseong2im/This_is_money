"""
고급 EV 추정기 (Enhanced EV Estimator)

핵심 개선:
1. 최근 거래 가중치 (EWMA)
2. 변동성 조정
3. 수수료/펀딩비 정밀 차감
4. 신뢰구간 계산
"""
from core.types import StrategyStats
import math


class EVEstimator:
    """
    기대수익(Expected Value) 추정기
    """
    
    def estimate(
        self,
        strategy: str,
        regime: str,
        trades: list,
        funding: float,
        fee: float = 0.0004,  # 0.04% (maker+taker 평균)
        alpha: float = 0.25,  # 최근 거래 가중치 (높을수록 최근 중시)
        min_trades: int = 15  # 최소 거래 수 (너무 낮으면 노이즈)
    ) -> StrategyStats:
        """
        전략의 기대수익을 추정
        
        Args:
            strategy: 전략 이름
            regime: 시장 상태
            trades: 과거 거래 기록 [{"pnl": float}, ...]
            funding: 펀딩비
            fee: 수수료
            alpha: EWMA 알파 (최근 가중치)
            min_trades: 최소 거래 수
        
        Returns:
            StrategyStats (ev, confidence, win_rate, avg_win, avg_loss)
        """
        # 1. 거래 수 부족 시 (부트스트랩)
        # 초기 탐색을 위해 기본값 제공
        if len(trades) < min_trades:
            return StrategyStats(
                name=strategy,
                regime=regime,
                win_rate=0.5,
                avg_win=0.02,
                avg_loss=0.01,
                ev=0.002,  # 0.2% expected return to encourage exploration
                confidence=0.5
            )
        
        # 2. PnL 추출
        pnl_list = [float(t.get("pnl", 0)) for t in trades]
        
        # 3. EWMA 계산 (최근 거래에 가중치)
        ewma = pnl_list[0]
        for pnl in pnl_list[1:]:
            ewma = alpha * pnl + (1 - alpha) * ewma
        
        # 4. 승/패 분리
        wins = [pnl for pnl in pnl_list if pnl > 0]
        losses = [pnl for pnl in pnl_list if pnl <= 0]
        
        win_rate = len(wins) / len(pnl_list)
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0
        
        # 5. 비용 차감
        # - 수수료: 진입 + 청산 = 2회
        # - 펀딩비: 절대값 (항상 비용으로 가정)
        total_cost = (fee * 2) + abs(funding)
        
        # 6. 최종 EV 계산
        ev = ewma - total_cost
        
        # 7. 신뢰도 계산
        # - 거래 수 기반 (100거래면 신뢰도 1.0)
        trade_confidence = min(1.0, len(trades) / 100)
        
        # - 일관성 기반 (표준편차가 낮으면 높은 신뢰도)
        if len(pnl_list) > 5:
            mean_pnl = sum(pnl_list) / len(pnl_list)
            variance = sum((p - mean_pnl) ** 2 for p in pnl_list) / len(pnl_list)
            std_pnl = math.sqrt(variance)
            # 표준편차가 평균의 2배 이하면 일관성 높음
            consistency = 1.0 / (1 + std_pnl / (abs(mean_pnl) + 0.0001))
        else:
            consistency = 0.5
        
        # 최종 신뢰도 = 거래수 * 일관성
        confidence = trade_confidence * (0.5 + 0.5 * consistency)
        confidence = min(1.0, max(0.0, confidence))
        
        # 8. 승률 보정 (승률이 극단적이면 신뢰도 감소)
        if win_rate > 0.8 or win_rate < 0.2:
            confidence *= 0.8  # 과적합 의심
        
        return StrategyStats(
            name=strategy,
            regime=regime,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            ev=ev,
            confidence=confidence
        )
