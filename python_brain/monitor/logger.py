"""
[로거]
구조화된 로깅
"""
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class Logger:
    """
    구조화된 로거
    - 콘솔 출력
    - 파일 저장
    - JSON 포맷
    """
    
    def __init__(self, name: str = "TradingBot", level: LogLevel = LogLevel.INFO,
                 log_file: Optional[str] = None):
        self.name = name
        self.level = level
        self.log_file = log_file
        
        # 파일 핸들러
        self._file_handler = None
        if log_file:
            self._file_handler = open(log_file, 'a', encoding='utf-8')
    
    def _log(self, level: LogLevel, message: str, data: Optional[Dict] = None):
        """내부 로깅"""
        if level.value < self.level.value:
            return
        
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'level': level.name,
            'logger': self.name,
            'message': message
        }
        
        if data:
            log_entry['data'] = data
        
        # 콘솔 출력
        self._print_console(level, timestamp, message, data)
        
        # 파일 저장
        if self._file_handler:
            self._file_handler.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            self._file_handler.flush()
    
    def _print_console(self, level: LogLevel, timestamp: str, 
                       message: str, data: Optional[Dict]):
        """콘솔 출력"""
        
        # 레벨별 색상 (ANSI)
        colors = {
            LogLevel.DEBUG: '\033[90m',    # 회색
            LogLevel.INFO: '\033[92m',     # 녹색
            LogLevel.WARNING: '\033[93m',  # 노란색
            LogLevel.ERROR: '\033[91m',    # 빨간색
            LogLevel.CRITICAL: '\033[95m'  # 보라색
        }
        reset = '\033[0m'
        
        color = colors.get(level, '')
        time_short = timestamp[11:19]  # HH:MM:SS
        
        output = f"{color}[{time_short}] [{level.name:8}] {message}{reset}"
        
        if data:
            data_str = ' | '.join(f"{k}={v}" for k, v in data.items())
            output += f" | {data_str}"
        
        print(output)
    
    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, kwargs if kwargs else None)
    
    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, kwargs if kwargs else None)
    
    def warning(self, message: str, **kwargs):
        self._log(LogLevel.WARNING, message, kwargs if kwargs else None)
    
    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, kwargs if kwargs else None)
    
    def critical(self, message: str, **kwargs):
        self._log(LogLevel.CRITICAL, message, kwargs if kwargs else None)
    
    def trade(self, action: str, symbol: str, price: float, size: float, 
              reason: str, pnl: Optional[float] = None):
        """거래 로그"""
        data = {
            'action': action,
            'symbol': symbol,
            'price': f"${price:,.2f}",
            'size': f"{size:.6f}",
            'reason': reason
        }
        if pnl is not None:
            data['pnl'] = f"${pnl:,.2f}"
        
        self._log(LogLevel.INFO, f"TRADE: {action.upper()}", data)
    
    def position(self, side: str, entry: float, current: float, 
                 pnl_pct: float, stop: float, target: float):
        """포지션 로그"""
        data = {
            'side': side,
            'entry': f"${entry:,.2f}",
            'current': f"${current:,.2f}",
            'pnl': f"{pnl_pct*100:+.2f}%",
            'stop': f"${stop:,.2f}",
            'target': f"${target:,.2f}"
        }
        self._log(LogLevel.INFO, "POSITION", data)
    
    def equity(self, current: float, initial: float, pnl: float, 
               drawdown: float):
        """자산 로그"""
        data = {
            'equity': f"${current:,.2f}",
            'return': f"{(current/initial-1)*100:+.2f}%",
            'pnl': f"${pnl:+,.2f}",
            'dd': f"{drawdown:.2f}%"
        }
        self._log(LogLevel.INFO, "EQUITY", data)
    
    def close(self):
        """로거 종료"""
        if self._file_handler:
            self._file_handler.close()


# 글로벌 로거
_logger: Optional[Logger] = None

def get_logger() -> Logger:
    """글로벌 로거 반환"""
    global _logger
    if _logger is None:
        _logger = Logger(name="TradingBot", level=LogLevel.INFO)
    return _logger

