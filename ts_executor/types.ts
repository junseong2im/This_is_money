export type OrderSide = "BUY" | "SELL";

export interface ExecuteOrderRequest {
  symbol: string;
  side: OrderSide;
  quantity: number;
  orderType?: "MARKET";
  reduceOnly?: boolean;
}

export interface ExecuteOrderResponse {
  success: boolean;
  orderId?: string;
  executedQty?: number;
  avgPrice?: number;
  status?: string;
  error?: string;
}

export interface BalanceResponse {
  success: boolean;
  availableUSDT?: number;
  walletUSDT?: number;
  error?: string;
}

export interface PositionResponse {
  success: boolean;
  position?: {
    symbol: string;
    positionAmt: number;
    entryPrice: number;
    unRealizedProfit: number;
  };
  error?: string;
}
