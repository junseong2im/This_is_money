from enum import Enum
from core.features import MarketFeatures

class MarketRegime(Enum):
    TREND = "trend"
    CHOP = "chop"
    DISTRIBUTION = "distribution"
    SQUEEZE = "squeeze"

def detect_regime(f: MarketFeatures) -> MarketRegime:
    if f.atr_pct < 0.006 and f.adx < 18:
        return MarketRegime.CHOP
    if f.atr_pct > 0.015 and f.volume_z > 1.2:
        return MarketRegime.SQUEEZE
    if f.adx > 22:
        return MarketRegime.TREND
    return MarketRegime.DISTRIBUTION
