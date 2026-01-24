from enum import Enum
from core.features import MarketFeatures

class MarketRegime(Enum):
    TREND = "trend"
    CHOP = "chop"
    DISTRIBUTION = "distribution"
    SQUEEZE = "squeeze"

def detect_regime(f: MarketFeatures) -> MarketRegime:
    """
    Advanced Regime Detection using Hurst Exponent and ADX.
    Hurst > 0.55 -> Persistent (Trending)
    Hurst < 0.45 -> Anti-persistent (Mean Reverting)
    """

    # 1. Squeeze: High volatility explosion (breakout imminent or happening)
    if f.atr_pct > 0.015 and f.volume_z > 2.0:
        return MarketRegime.SQUEEZE

    # 2. Trending: High Hurst OR High ADX
    # Hurst is cleaner, but ADX confirms strength.
    is_trending = (f.hurst > 0.6) or (f.adx > 25)

    if is_trending:
        return MarketRegime.TREND

    # 3. Mean Reversion (Distribution): Low Hurst
    if f.hurst < 0.45:
        return MarketRegime.DISTRIBUTION

    # 4. Chop: Low ADX and Low Volatility
    if f.adx < 20 and f.atr_pct < 0.005:
        return MarketRegime.CHOP

    # Default to Distribution (safe mean reversion) or Chop
    return MarketRegime.DISTRIBUTION
