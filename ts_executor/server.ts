import express from "express";
import bodyParser from "body-parser";
import dotenv from "dotenv";
import { executeOrder, getBalanceUSDT, getPosition } from "./exchangeAdapter";
import { ExecuteOrderRequest } from "./types";

dotenv.config();

const app = express();
app.use(bodyParser.json({ limit: "256kb" }));

const PORT = Number(process.env.PORT || 3001);
const AUTH_TOKEN = process.env.EXECUTOR_AUTH_TOKEN || "";

// ✅ 외부에서 함부로 못 때리게: 토큰 없으면 실행/계좌조회 불가
function requireAuth(req: express.Request, res: express.Response, next: express.NextFunction) {
  if (!AUTH_TOKEN) {
    // 토큰 자체를 안 쓰는 구성도 가능하게 하되, 실전이면 반드시 넣어라
    return next();
  }
  const t = String(req.headers["x-executor-token"] || "");
  if (t !== AUTH_TOKEN) {
    return res.status(401).json({ success: false, error: "unauthorized" });
  }
  return next();
}

// 헬스체크는 오픈
app.get("/health", (_req, res) => res.json({ ok: true }));

/**
 * python_brain 전용 실행 엔드포인트
 * 판단 ❌ / 검증만 ✅ / 실행만 ✅
 */
app.post("/execute", requireAuth, async (req, res) => {
  const body: ExecuteOrderRequest = req.body;

  if (!body?.symbol || (body.side !== "BUY" && body.side !== "SELL")) {
    return res.status(400).json({ success: false, error: "Invalid payload: symbol/side" });
  }
  if (typeof body.quantity !== "number" || !Number.isFinite(body.quantity) || body.quantity <= 0) {
    return res.status(400).json({ success: false, error: "Invalid payload: quantity" });
  }

  try {
    const result = await executeOrder({
      symbol: body.symbol,
      side: body.side,
      quantity: body.quantity,
      reduceOnly: !!body.reduceOnly
    });

    return res.json({
      success: true,
      orderId: result.orderId,
      executedQty: result.executedQty,
      avgPrice: result.avgPrice,
      status: result.status
    });
  } catch (err: any) {
    return res.status(500).json({ success: false, error: String(err?.message || err) });
  }
});

/**
 * python_brain이 포지션/잔고 동기화할 때 쓰는 조회 API
 * dashboard는 절대 여기로 붙이면 안 됨(키가 여기 있음)
 */
app.get("/account/balance", requireAuth, async (_req, res) => {
  try {
    const b = await getBalanceUSDT();
    return res.json({ success: true, availableUSDT: b.availableUSDT, walletUSDT: b.walletUSDT });
  } catch (err: any) {
    return res.status(500).json({ success: false, error: String(err?.message || err) });
  }
});

app.get("/account/position/:symbol", requireAuth, async (req, res) => {
  try {
    const symbol = String(req.params.symbol || "").toUpperCase();
    const p = await getPosition(symbol);
    return res.json({ success: true, position: p || null });
  } catch (err: any) {
    return res.status(500).json({ success: false, error: String(err?.message || err) });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 ts_executor listening on port ${PORT}`);
});
