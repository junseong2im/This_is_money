from dataclasses import dataclass

@dataclass
class MarketFeatures:
    price: float
    atr_pct: float
    atr_value: float
    adx: float
    ema_fast_slope: float
    ema_slow_slope: float
    volume_z: float
    funding_rate: float
    ret_1: float
    ret_5: float
    hurst: float = 0.5  # New feature
