export interface Ticker {
  symbol: string;
  price: number;
  volume: number;
  change24h: number;
  timestamp: number;
}

export interface TradeOrder {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  price: number;
  amount: number;
  timestamp: number;
  status: 'FILLED' | 'PENDING' | 'CANCELED';
}

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'INFO' | 'TRADE' | 'ERROR' | 'WARNING' | 'SUCCESS';
  message: string;
  details?: string;
}

// [핵심 수정] 여기에 aiConfidence가 반드시 있어야 데이터가 넘어갑니다!
export interface MacroIndicators {
  phase: string;
  riskSentiment: string;
  hurst?: number;
  entropy?: number;
  aiConfidence?: number; // <--- 이 줄이 없으면 0%로 뜹니다
}

export interface Candle {
  time: number; // seconds (lightweight-charts)
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface CandlesResponse {
  symbol: string;
  interval: string;
  candles: Candle[];
  serverTime: number;
  macro: MacroIndicators | null;
  analysis?: {
    symbol: string;
    interval: string;
    baseInterval?: string;
    htfInterval?: string;
    htfMult?: number;
    time: number;
    sentAt?: number; // telemetry send time (seconds)
    price: number;
    signal: string;
    confidence?: number;
    longConfidence?: number;
    shortConfidence?: number;
    strength?: number;
    trend?: string;
    reason?: string;
    htfEmaFast?: number;
    htfEmaSlow?: number;
    atr?: number;
    stopLoss?: number;
    takeProfit?: number;
    trailingStop?: number;
    positionSide?: string;
    entryPrice?: number;
    entryPlan?: any;
  } | null;
  markers?: Array<{
    time: number;
    color: string;
    position: 'aboveBar' | 'belowBar' | 'inBar';
    shape: 'arrowUp' | 'arrowDown' | 'circle' | 'square';
    text?: string;
  }>;
}

export interface Position {
  symbol: string;
  amount: number;
  avgPrice: number;
  currentPrice: number;
  netPnL: number;
  pnlPercentage: number;
}

// (Dashboard용)
export interface SystemStatus {
  equity: number;
  balance: number;
  positions: Position[];
  logs: LogEntry[];
  macro: MacroIndicators | null;
  epochs: number;
  mode: string;
  balanceError?: string | null;
  timestamp: number;
}