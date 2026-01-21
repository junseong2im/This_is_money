import crypto from "crypto";

const BASE_URL = "https://fapi.binance.com";

const API_KEY = process.env.BINANCE_API_KEY || "";
const API_SECRET = process.env.BINANCE_API_SECRET || "";

type HttpMethod = "GET" | "POST";

function mustEnv() {
  if (!API_KEY || !API_SECRET) {
    throw new Error("BINANCE_API_KEY / BINANCE_API_SECRET not set");
  }
}

function sign(query: string) {
  return crypto.createHmac("sha256", API_SECRET).update(query).digest("hex");
}

async function signedRequest(endpoint: string, method: HttpMethod, params: Record<string, string | number | boolean> = {}) {
  mustEnv();

  const timestamp = Date.now();
  const qs = new URLSearchParams();

  // recvWindow 여유(서버 시간 오차 대응)
  qs.set("recvWindow", "60000");

  for (const [k, v] of Object.entries(params)) qs.set(k, String(v));
  qs.set("timestamp", String(timestamp));

  const signature = sign(qs.toString());
  qs.set("signature", signature);

  const url = `${BASE_URL}${endpoint}?${qs.toString()}`;

  const res = await fetch(url, {
    method,
    headers: {
      "X-MBX-APIKEY": API_KEY
    }
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.msg ? String(data.msg) : "Binance API error";
    throw new Error(msg);
  }
  return data;
}

export async function executeOrder(req: { symbol: string; side: "BUY" | "SELL"; quantity: number; reduceOnly?: boolean }) {
  const params: Record<string, string | number | boolean> = {
    symbol: req.symbol,
    side: req.side,
    type: "MARKET",
    quantity: req.quantity,
  };
  if (req.reduceOnly) params["reduceOnly"] = true;

  // Futures create order
  // 응답에 avgPrice가 없을 수 있어, 아래에서 후속 조회로 보강
  const created = await signedRequest("/fapi/v1/order", "POST", params);

  // order 조회로 avgPrice/execQty 보강(가능한 경우)
  let avgPrice = 0;
  let executedQty = 0;

  try {
    const ord = await signedRequest("/fapi/v1/order", "GET", {
      symbol: req.symbol,
      orderId: created.orderId
    });
    avgPrice = Number(ord.avgPrice || ord.price || 0);
    executedQty = Number(ord.executedQty || ord.origQty || 0);
  } catch {
    executedQty = Number(created.executedQty || created.origQty || 0);
    avgPrice = Number(created.avgPrice || 0);
  }

  return {
    orderId: String(created.orderId),
    status: String(created.status || "UNKNOWN"),
    executedQty,
    avgPrice
  };
}

export async function getBalanceUSDT() {
  const balances = await signedRequest("/fapi/v2/balance", "GET", {});
  const usdt = balances.find((a: any) => a.asset === "USDT");
  return {
    availableUSDT: Number(usdt?.availableBalance || 0),
    walletUSDT: Number(usdt?.balance || 0)
  };
}

export async function getPosition(symbol: string) {
  const arr = await signedRequest("/fapi/v2/positionRisk", "GET", { symbol });
  // 바이낸스가 배열로 줄 수도, 1개 객체로 줄 수도 있음
  const p = Array.isArray(arr) ? arr[0] : arr;

  const positionAmt = Number(p?.positionAmt || 0);
  if (!p || positionAmt === 0) return null;

  return {
    symbol: String(p.symbol),
    positionAmt,
    entryPrice: Number(p.entryPrice || 0),
    unRealizedProfit: Number(p.unRealizedProfit || 0)
  };
}
