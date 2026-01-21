def estimate_fee(notional: float, taker_fee: float = 0.0004) -> float:
    return abs(notional) * taker_fee

def estimate_funding(notional: float, funding_rate: float) -> float:
    return abs(notional) * funding_rate
