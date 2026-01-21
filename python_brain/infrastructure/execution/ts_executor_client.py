import os
import requests
from typing import Optional, Dict, Any

class TsExecutorClient:
    def __init__(self, base_url: str, token: Optional[str] = None, timeout: int = 6):
        self.base_url = base_url.rstrip("/")
        self.token = token or ""
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["x-executor-token"] = self.token
        return h

    def health(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            return r.ok
        except Exception:
            return False

    def execute_market(self, symbol: str, side: str, quantity: float, reduce_only: bool = False) -> Dict[str, Any]:
        payload = {
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "orderType": "MARKET",
            "reduceOnly": bool(reduce_only),
        }
        r = requests.post(
            f"{self.base_url}/execute",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def get_balance(self) -> Dict[str, Any]:
        r = requests.get(
            f"{self.base_url}/account/balance",
            headers=self._headers(),
            timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def get_position(self, symbol: str) -> Dict[str, Any]:
        r = requests.get(
            f"{self.base_url}/account/position/{symbol}",
            headers=self._headers(),
            timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()
