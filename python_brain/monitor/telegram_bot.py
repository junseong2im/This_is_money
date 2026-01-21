"""
[텔레그램 알림]
거래/경고 알림 전송
"""
import requests
from typing import Dict, Optional
from datetime import datetime
import sys
sys.path.append('..')
from config.settings import settings


class TelegramNotifier:
    """
    텔레그램 알림 봇
    - 거래 알림
    - 경고 알림
    - 일일 리포트
    """
    
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or settings.TELEGRAM_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)
        
        if self.enabled:
            self.base_url = f"https://api.telegram.org/bot{self.token}"
            print(f"[Telegram] 알림 활성화")
        else:
            print(f"[Telegram] 알림 비활성화 (토큰/채팅ID 없음)")
    
    def _send(self, message: str, parse_mode: str = "HTML") -> bool:
        """메시지 전송"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            response = requests.post(url, data=data, timeout=10)
            return response.ok
        except Exception as e:
            print(f"[Telegram] 전송 실패: {e}")
            return False
    
    def trade_alert(self, action: str, symbol: str, price: float,
                    size: float, reason: str, pnl: Optional[float] = None):
        """거래 알림"""
        
        emoji = "🟢" if action.lower() in ["buy", "long"] else "🔴"
        pnl_str = f"\n💰 PnL: ${pnl:+,.2f}" if pnl is not None else ""
        
        message = f"""
{emoji} <b>{action.upper()}</b> {symbol}

📊 Price: ${price:,.2f}
📦 Size: {size:.6f}
📝 Reason: {reason}{pnl_str}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self._send(message)
    
    def position_update(self, symbol: str, side: str, entry: float,
                        current: float, pnl_pct: float, stop: float):
        """포지션 업데이트"""
        
        emoji = "📈" if pnl_pct > 0 else "📉"
        
        message = f"""
{emoji} <b>Position Update</b>

📍 {symbol} {side.upper()}
🎯 Entry: ${entry:,.2f}
💹 Current: ${current:,.2f}
📊 PnL: {pnl_pct*100:+.2f}%
🛑 Stop: ${stop:,.2f}
"""
        self._send(message)
    
    def warning_alert(self, title: str, message: str):
        """경고 알림"""
        
        text = f"""
⚠️ <b>WARNING: {title}</b>

{message}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self._send(text)
    
    def error_alert(self, error: str, details: str = ""):
        """에러 알림"""
        
        message = f"""
🚨 <b>ERROR</b>

{error}
{details}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self._send(message)
    
    def daily_report(self, stats: Dict):
        """일일 리포트"""
        
        equity = stats.get('equity', 0)
        initial = stats.get('initial', 0)
        trades = stats.get('trades', 0)
        win_rate = stats.get('win_rate', 0)
        pnl = stats.get('pnl', 0)
        dd = stats.get('drawdown', 0)
        
        return_pct = (equity / initial - 1) * 100 if initial > 0 else 0
        
        message = f"""
📊 <b>Daily Report</b>

💰 Equity: ${equity:,.2f}
📈 Return: {return_pct:+.2f}%
📉 Drawdown: {dd:.2f}%

🔄 Trades: {trades}
✅ Win Rate: {win_rate:.1f}%
💵 Day PnL: ${pnl:+,.2f}

⏰ {datetime.now().strftime('%Y-%m-%d')}
"""
        self._send(message)
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        return self._send("🤖 Bot Connected!")

