"""
[성과 리포터]
거래 성과 분석 및 리포트 생성
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import sys
sys.path.append('..')


@dataclass
class TradeRecord:
    """거래 기록"""
    timestamp: datetime
    symbol: str
    side: str
    action: str  # entry, exit
    price: float
    size: float
    pnl: float = 0.0
    reason: str = ""
    strategy: str = ""


@dataclass
class DailyStats:
    """일일 통계"""
    date: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    pnl: float = 0.0
    max_drawdown: float = 0.0
    start_equity: float = 0.0
    end_equity: float = 0.0


class PerformanceReporter:
    """
    성과 리포터
    - 거래 기록
    - 일일/주간/월간 통계
    - 전략별 성과 분석
    """
    
    def __init__(self, initial_equity: float):
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        
        # 거래 기록
        self.trades: List[TradeRecord] = []
        
        # 일일 통계
        self.daily_stats: Dict[str, DailyStats] = {}
        
        # 전략별 통계
        self.strategy_stats: Dict[str, Dict] = {}
        
        # 현재 날짜
        self._current_date = datetime.now().strftime('%Y-%m-%d')
        self._today_stats = DailyStats(
            date=self._current_date,
            start_equity=initial_equity
        )
    
    def record_trade(self, symbol: str, side: str, action: str,
                     price: float, size: float, pnl: float = 0.0,
                     reason: str = "", strategy: str = ""):
        """거래 기록"""
        
        trade = TradeRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            side=side,
            action=action,
            price=price,
            size=size,
            pnl=pnl,
            reason=reason,
            strategy=strategy
        )
        
        self.trades.append(trade)
        
        # 일일 통계 업데이트
        self._update_daily_stats(trade)
        
        # 전략별 통계 업데이트
        self._update_strategy_stats(trade)
    
    def _update_daily_stats(self, trade: TradeRecord):
        """일일 통계 업데이트"""
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 날짜 변경 체크
        if today != self._current_date:
            self._finalize_day()
            self._current_date = today
            self._today_stats = DailyStats(
                date=today,
                start_equity=self.current_equity
            )
        
        # 통계 업데이트
        if trade.action == "exit":
            self._today_stats.trades += 1
            self._today_stats.pnl += trade.pnl
            
            if trade.pnl > 0:
                self._today_stats.wins += 1
            else:
                self._today_stats.losses += 1
    
    def _update_strategy_stats(self, trade: TradeRecord):
        """전략별 통계 업데이트"""
        
        strategy = trade.strategy or "unknown"
        
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'win_pnl': 0.0,
                'loss_pnl': 0.0
            }
        
        stats = self.strategy_stats[strategy]
        
        if trade.action == "exit":
            stats['trades'] += 1
            stats['total_pnl'] += trade.pnl
            
            if trade.pnl > 0:
                stats['wins'] += 1
                stats['win_pnl'] += trade.pnl
            else:
                stats['losses'] += 1
                stats['loss_pnl'] += trade.pnl
    
    def _finalize_day(self):
        """일일 마감"""
        self._today_stats.end_equity = self.current_equity
        self.daily_stats[self._today_stats.date] = self._today_stats
    
    def update_equity(self, equity: float, drawdown: float = 0):
        """자산 업데이트"""
        self.current_equity = equity
        self._today_stats.end_equity = equity
        self._today_stats.max_drawdown = max(self._today_stats.max_drawdown, drawdown)
    
    def get_summary(self) -> Dict:
        """전체 요약"""
        
        total_trades = len([t for t in self.trades if t.action == "exit"])
        wins = len([t for t in self.trades if t.action == "exit" and t.pnl > 0])
        total_pnl = sum(t.pnl for t in self.trades if t.action == "exit")
        
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'initial_equity': self.initial_equity,
            'current_equity': self.current_equity,
            'total_return': (self.current_equity / self.initial_equity - 1) * 100,
            'total_trades': total_trades,
            'wins': wins,
            'losses': total_trades - wins,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / total_trades if total_trades > 0 else 0
        }
    
    def get_daily_report(self) -> Dict:
        """일일 리포트"""
        
        stats = self._today_stats
        win_rate = (stats.wins / stats.trades * 100) if stats.trades > 0 else 0
        
        return {
            'date': stats.date,
            'trades': stats.trades,
            'wins': stats.wins,
            'losses': stats.losses,
            'win_rate': win_rate,
            'pnl': stats.pnl,
            'max_drawdown': stats.max_drawdown,
            'start_equity': stats.start_equity,
            'end_equity': stats.end_equity,
            'daily_return': (stats.end_equity / stats.start_equity - 1) * 100 if stats.start_equity > 0 else 0
        }
    
    def get_strategy_report(self) -> Dict:
        """전략별 리포트"""
        
        report = {}
        
        for strategy, stats in self.strategy_stats.items():
            trades = stats['trades']
            win_rate = (stats['wins'] / trades * 100) if trades > 0 else 0
            avg_win = stats['win_pnl'] / stats['wins'] if stats['wins'] > 0 else 0
            avg_loss = stats['loss_pnl'] / stats['losses'] if stats['losses'] > 0 else 0
            
            report[strategy] = {
                'trades': trades,
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': win_rate,
                'total_pnl': stats['total_pnl'],
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': abs(stats['win_pnl'] / stats['loss_pnl']) if stats['loss_pnl'] != 0 else float('inf')
            }
        
        return report
    
    def get_recent_trades(self, n: int = 10) -> List[Dict]:
        """최근 거래"""
        
        recent = self.trades[-n:]
        return [
            {
                'time': t.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': t.symbol,
                'side': t.side,
                'action': t.action,
                'price': t.price,
                'size': t.size,
                'pnl': t.pnl,
                'reason': t.reason,
                'strategy': t.strategy
            }
            for t in reversed(recent)
        ]
    
    def export_json(self, filepath: str):
        """JSON 내보내기"""
        
        data = {
            'summary': self.get_summary(),
            'daily': {k: vars(v) for k, v in self.daily_stats.items()},
            'strategies': self.get_strategy_report(),
            'trades': [
                {
                    'timestamp': t.timestamp.isoformat(),
                    'symbol': t.symbol,
                    'side': t.side,
                    'action': t.action,
                    'price': t.price,
                    'size': t.size,
                    'pnl': t.pnl,
                    'reason': t.reason,
                    'strategy': t.strategy
                }
                for t in self.trades
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

