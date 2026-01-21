from dataclasses import dataclass

@dataclass
class MarketFeatures:
    price: float
    atr_pct: float
    atr_value: float  # ATR in price units (e.g., $500)
    adx: float
    ema_fast_slope: float
    ema_slow_slope: float
    volume_z: float
    funding_rate: float
    ret_1: float
    ret_5: float
