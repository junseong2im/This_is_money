import React, { useMemo, useState, useEffect } from 'react';
import { Brain, Server, Wifi, Zap, Sparkles, ChevronDown, ChevronUp, Activity } from 'lucide-react';
import { motion } from 'framer-motion';
import ChartWidget from './components/ChartWidget';
import AssetList from './components/AssetList';
import { CandlesResponse, Candle, SystemStatus } from './types';

const fmtNum = (v: any, digits = 2) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return n.toFixed(digits);
};
const fmtUsd = (v: any, digits = 0) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: digits })}`;
};
const signalKo = (sig?: string) => {
  const s = String(sig || '').toUpperCase();
  if (s === 'LONG' || s === 'BUY') return '롱(매수)';
  if (s === 'SHORT' || s === 'SELL') return '숏(매도)';
  if (s === 'EXIT') return '청산';
  return '대기';
};
const trendKo = (t?: string) => {
  const s = String(t || '').toLowerCase();
  if (s === 'up') return '상승';
  if (s === 'down') return '하락';
  if (s === 'range') return '횡보';
  return '—';
};

const htfLabel = (analysis: any) => {
  const htf = String(analysis?.htfInterval || '').trim();
  const mult = Number(analysis?.htfMult ?? 0);
  if (htf) return `HTF(${htf})`;
  if (Number.isFinite(mult) && mult > 1) return `HTF(x${mult})`;
  return 'HTF';
};

const emaLast = (values: number[], period: number) => {
  const p = Math.max(1, Math.floor(period));
  if (!values.length) return 0;
  if (p <= 1) return values[values.length - 1];
  const k = 2 / (p + 1);
  let prev = values[0];
  for (let i = 1; i < values.length; i++) {
    prev = values[i] * k + prev * (1 - k);
  }
  return prev;
};

const pctText = (p: number | null, digits = 1) => {
  if (p === null || !Number.isFinite(p)) return '—';
  const capped = Math.min(99.9, Math.max(0, p));
  return `${capped.toFixed(digits)}%`;
};

const App: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [chartData, setChartData] = useState<{ time: string, value: number }[]>([]);
  const [startEquity, setStartEquity] = useState<number | null>(null);
  const [chartMode, setChartMode] = useState<'equity' | 'candles'>('candles');
  const [symbol, setSymbol] = useState<string>('BTCUSDT');
  const [interval, setIntervalTf] = useState<string>('1m');
  const [candles, setCandles] = useState<Candle[]>([]);
  const [lastPrice, setLastPrice] = useState<number>(0);
  const [markers, setMarkers] = useState<CandlesResponse['markers']>([]);
  const [analysis, setAnalysis] = useState<CandlesResponse['analysis']>(null);
  const [lastAiSymbol, setLastAiSymbol] = useState<string>(''); // 최근 AI 분석이 실제로 들어온 심볼
  const [analysisFeed, setAnalysisFeed] = useState<Array<{
    time: number;
    price: number;
    signal: string;
    trend?: string;
    confidence?: number;
    longConfidence?: number;
    shortConfidence?: number;
    strength?: number;
    atr?: number;
    reason?: string;
  }>>([]);
  const [showPositions, setShowPositions] = useState(true);
  const [showAiFeed, setShowAiFeed] = useState(true);

  // API 주소:
  // - 로컬에서 볼 땐 http://localhost:4000
  // - 다른 PC/폰에서 대시보드를 열면 "localhost"는 그 기기 자신을 가리켜서 무조건 끊긴다.
  //   → 기본을 "현재 접속한 호스트:4000"로 맞춰 원격 접속에서도 자동 동작하게 한다.
  const apiBase = useMemo(() => {
    const env = (import.meta as any)?.env?.VITE_API_BASE;
    const envStr = (env ? String(env).trim() : '');
    if (envStr) return envStr.replace(/\/+$/, '');
    const proto = window.location.protocol || 'http:';
    const host = window.location.hostname || 'localhost';
    return `${proto}//${host}:4000`;
  }, []);

  // 지연/갱신 관측(디버깅): "어디가 느린지"를 화면에서 바로 확인
  const [netDiag, setNetDiag] = useState<{
    statusMs?: number;
    candlesMs?: number;
    priceMs?: number;
    statusAt?: number;
    candlesAt?: number;
    priceAt?: number;
  }>({});

  useEffect(() => {
    let alive = true;
    let inFlight = false;
    let ctl: AbortController | null = null;

    const loop = async () => {
      while (alive) {
        if (inFlight) {
          await new Promise(r => setTimeout(r, 50));
          continue;
        }
        inFlight = true;
        if (ctl) {
          try { ctl.abort(); } catch {}
        }
        ctl = new AbortController();
      try {
          const t0 = performance.now();
          const res = await fetch(`${apiBase}/status`, { signal: ctl.signal });
        if (!res.ok) throw new Error('Server Error');
        const data = await res.json();
          const ms = Math.max(0, Math.round(performance.now() - t0));
        
        setStatus(data);
        setIsConnected(true);
          setNetDiag(prev => ({ ...prev, statusMs: ms, statusAt: Date.now() }));

          // 포지션이 있으면 첫 심볼로 자동 맞춤(사용자가 직접 바꾸면 유지)
          if (data?.positions?.length > 0 && symbol === 'BTCUSDT') {
            const s = data.positions[0]?.symbol;
            if (s) setSymbol(s);
          }

        if (data.balance && startEquity === null) {
            setStartEquity(data.balance);
        }

        if (data.balance) {
            setChartData(prev => {
                const now = new Date().toLocaleTimeString();
                if (prev.length > 0 && prev[prev.length - 1].time === now) return prev;
                return [...prev.slice(-99), { time: now, value: data.balance }];
            });
        }
        } catch {
        setIsConnected(false);
        } finally {
          inFlight = false;
        }
        await new Promise(r => setTimeout(r, 1000));
      }
    };

    loop();
    return () => {
      alive = false;
      if (ctl) {
        try { ctl.abort(); } catch {}
      }
    };
  }, [startEquity, symbol]);

  useEffect(() => {
    if (chartMode !== 'candles') return;

    let alive = true;
    let inFlight = false;
    let ctl: AbortController | null = null;
    const fetchCandles = async () => {
      try {
        if (inFlight) return;
        inFlight = true;
        if (ctl) {
          try { ctl.abort(); } catch {}
        }
        ctl = new AbortController();
        const timeout = setTimeout(() => {
          try { ctl?.abort(); } catch {}
        }, 4500);
        const url = `${apiBase}/candles?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=300`;
        const t0 = performance.now();
        const res = await fetch(url, { signal: ctl.signal });
        clearTimeout(timeout);
        if (!res.ok) return;
        const data: CandlesResponse = await res.json();
        const ms = Math.max(0, Math.round(performance.now() - t0));
        if (!alive) return;
        if (Array.isArray(data.candles)) setCandles(data.candles);
        setMarkers(Array.isArray(data.markers) ? data.markers : []);
        setAnalysis(data.analysis ?? null);
        setNetDiag(prev => ({ ...prev, candlesMs: ms, candlesAt: Date.now() }));
      } catch {
      } finally {
        inFlight = false;
      }
    };

    fetchCandles();
    // 캔들(1m)은 자주 새로받을 필요가 없어서 빈도 낮춤(렌더링 부하 감소)
    const t = setInterval(fetchCandles, 8000);
    return () => {
      alive = false;
      if (ctl) {
        try { ctl.abort(); } catch {}
      }
      clearInterval(t);
    };
  }, [chartMode, symbol, interval]);

  // AI 분석 흐름(타임라인) 누적: analysis.time이 바뀔 때만 append
  useEffect(() => {
    if (!analysis || !analysis.time) return;
    // AI 심볼 기억(다른 심볼로 옮겼을 때 "AI 없음" 안내/복귀 버튼에 사용)
    try {
      const s = String((analysis as any)?.symbol || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
      if (s) setLastAiSymbol(s);
    } catch {}
    const t = Number(analysis.time);
    if (!Number.isFinite(t) || t <= 0) return;
    const p = Number(analysis.price ?? 0);
    const sig = String(analysis.signal || 'HOLD');
    setAnalysisFeed(prev => {
      const last = prev.length ? prev[prev.length - 1] : null;
      if (last && last.time === t) return prev;
      const next = [
        ...prev,
        {
          time: t,
          price: Number.isFinite(p) ? p : 0,
          signal: sig,
          trend: analysis.trend,
          confidence: analysis.confidence,
          longConfidence: analysis.longConfidence,
          shortConfidence: analysis.shortConfidence,
          strength: analysis.strength,
          atr: analysis.atr,
          reason: analysis.reason,
        }
      ];
      return next.slice(-160);
    });
  }, [analysis?.time]);

  useEffect(() => {
    if (chartMode !== 'candles') return;

    let alive = true;
    const fetchPrice = async () => {
      try {
        const ctl = new AbortController();
        const timeout = setTimeout(() => {
          try { ctl.abort(); } catch {}
        }, 2500);
        const url = `${apiBase}/price?symbol=${encodeURIComponent(symbol)}`;
        const t0 = performance.now();
        const res = await fetch(url, { signal: ctl.signal });
        clearTimeout(timeout);
        if (!res.ok) return;
        const data = await res.json();
        const ms = Math.max(0, Math.round(performance.now() - t0));
        if (!alive) return;
        const p = Number(data?.price ?? 0);
        if (Number.isFinite(p) && p > 0) setLastPrice(p);
        setNetDiag(prev => ({ ...prev, priceMs: ms, priceAt: Date.now() }));
      } catch {}
    };

    let inFlight = false;
    const loop = async () => {
      while (alive) {
        if (!inFlight) {
          inFlight = true;
          try { await fetchPrice(); } finally { inFlight = false; }
        }
        await new Promise(r => setTimeout(r, 1000));
      }
    };
    loop();
    return () => { alive = false; };
  }, [chartMode, symbol]);

  // 주의: 훅은 조건부 return 이전에 항상 같은 순서로 호출되어야 함
  const latestFeed = useMemo(() => {
    if (!analysisFeed.length) return [];
    return analysisFeed.slice(-30).reverse();
  }, [analysisFeed]);

  // 차트(현재 선택된 interval)의 "추정 추세"(EMA20/EMA50) — AI HTF 추세와 분리해서 보여준다.
  // IMPORTANT: 조건부 return 이전에 선언해서 훅 호출 순서를 고정한다.
  const chartTrend = useMemo(() => {
    if (!candles || candles.length < 60) return { trend: '', ema20: 0, ema50: 0 };
    const closes = candles.map(c => Number(c.close)).filter(Number.isFinite);
    if (closes.length < 60) return { trend: '', ema20: 0, ema50: 0 };
    const e20 = emaLast(closes, 20);
    const e50 = emaLast(closes, 50);
    const t = e20 > e50 ? 'up' : (e20 < e50 ? 'down' : 'range');
    return { trend: t, ema20: e20, ema50: e50 };
  }, [candles]);

  if (!status && !isConnected) {
    return (
      <div className="h-screen flex items-center justify-center flex-col gap-4 text-emerald-300">
        <div className="glass-strong px-6 py-5 flex items-center gap-3">
          <div className="animate-spin"><Zap size={18} /></div>
          <div className="text-sm tracking-[0.22em] uppercase font-mono text-slate-200">대시보드 시작 중...</div>
        </div>
        <div className="text-xs text-slate-400 font-mono">`{apiBase}/status` 응답 대기</div>
        </div>
    );
  }

  const equity = status?.balance ?? 0;
  const baseMoney = startEquity || equity; 
  const pnl = equity - baseMoney;
  const pnlPercent = baseMoney > 0 ? (pnl / baseMoney) * 100 : 0.0;

  const positions = status?.positions ?? [];
  const macro = status?.macro ?? { phase: '—', hurst: 0, entropy: 0, aiConfidence: 0, riskSentiment: 'NEUTRAL' };
  const risk = macro?.riskSentiment ?? 'NEUTRAL';
  // NOTE:
  // - analysis.time: 전략 타임프레임 "마감봉 시간"
  // - analysis.sentAt: 텔레메트리 "송신 시간"(heartbeat 포함)
  const analysisCandleAgeSec = analysis?.time ? Math.max(0, Math.floor(Date.now() / 1000 - analysis.time)) : null;
  const analysisSendAgeSec = analysis?.sentAt ? Math.max(0, Math.floor(Date.now() / 1000 - analysis.sentAt)) : null;
  // 송신 시간이 있으면 그걸로 생존/지연 판단(실시간 체감), 없으면 기존(마감봉 기준)으로 폴백
  const staleAi = analysisSendAgeSec !== null
    ? (analysisSendAgeSec >= 60)
    : (analysisCandleAgeSec !== null && analysisCandleAgeSec >= 240);
  const longConfPct = analysis?.longConfidence !== undefined && analysis?.longConfidence !== null
    ? Math.max(0, Math.min(1, Number(analysis.longConfidence))) * 100
    : null;
  const shortConfPct = analysis?.shortConfidence !== undefined && analysis?.shortConfidence !== null
    ? Math.max(0, Math.min(1, Number(analysis.shortConfidence))) * 100
    : null;
  const strength = analysis?.strength !== undefined && analysis?.strength !== null ? Number(analysis.strength) : null;
  const diagAge = (ts?: number) => (ts ? Math.max(0, Math.floor((Date.now() - ts) / 1000)) : null);
  // 화면 표시용: "마감봉 기준" 시간은 기존대로 유지하되, 생존/지연 판단은 sentAt 기반으로 별도 표기한다.
  const analysisAgeSec = analysisCandleAgeSec;

  return (
    <div className="h-screen text-slate-200 p-4 flex flex-col overflow-hidden selection:bg-emerald-500/25 text-xs">
      
      <header className="glass-strong shrink-0 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl border border-emerald-500/25 bg-emerald-500/10 flex items-center justify-center">
            <Server className="text-emerald-300" size={16} />
          </div>
          <div className="leading-tight">
            <div className="flex items-center gap-2">
              <h1 className="text-[13px] font-extrabold tracking-tight text-slate-50">
                트레이딩<span className="text-emerald-300"> 대시보드</span>
              </h1>
              <span className="text-[10px] font-mono text-slate-400">실시간 모니터링</span>
            </div>
            <div className="text-[10px] text-slate-400">
              상태 API: <span className="font-mono text-slate-300">{apiBase.replace(/^https?:\/\//, '')}</span>
          </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1.5 rounded-full border text-[10px] font-mono flex items-center gap-2 ${
            isConnected
              ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-200'
              : 'border-rose-500/25 bg-rose-500/10 text-rose-200'
          }`}>
            <Wifi size={12}/> {isConnected ? '연결됨' : '끊김'}
          </div>
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border border-cyan-500/20 bg-cyan-500/10 text-cyan-200 text-[10px] font-mono">
            <Sparkles size={12} />
            <span>{status?.mode === 'REAL' ? '실거래' : (status?.mode ?? '—')}</span>
           </div>
          <div className={`hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-mono ${
            staleAi ? 'border-rose-500/25 bg-rose-500/10 text-rose-200' : 'border-white/10 bg-white/5 text-slate-200'
          }`}>
            <Activity size={12}/>
            <span>상태 {netDiag.statusMs ?? '—'}ms</span>
            <span className="text-slate-400">/</span>
            <span>캔들 {netDiag.candlesMs ?? '—'}ms</span>
            <span className="text-slate-400">/</span>
            <span>가격 {netDiag.priceMs ?? '—'}ms</span>
            <span className="text-slate-400">|</span>
            <span>AI {analysisSendAgeSec === null ? (analysisCandleAgeSec === null ? '—' : `${analysisCandleAgeSec}s`) : `${analysisSendAgeSec}s`}</span>
            {staleAi && <span className="text-rose-200">(지연)</span>}
            <span className="text-slate-400">|</span>
            <span>poll {diagAge(netDiag.statusAt) ?? '—'}s/{diagAge(netDiag.candlesAt) ?? '—'}s/{diagAge(netDiag.priceAt) ?? '—'}s</span>
           </div>
        </div>
      </header>

      {status?.balanceError && (
        <div className="mt-4 glass px-4 py-3 border border-rose-500/25 bg-rose-500/10 text-rose-200 text-[11px] flex items-start gap-2">
          <div className="mt-0.5">주의:</div>
          <div className="min-w-0">
            <div className="font-semibold">잔고/포지션 조회가 실패했습니다 (그래서 총 자산이 0으로 보입니다)</div>
            <div className="mt-1 font-mono text-rose-200/80 break-words">{status.balanceError}</div>
          </div>
        </div>
      )}

      {/* MAIN LAYOUT */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0 mt-4">
        
        {/* LEFT: INFO */}
        <div className="lg:col-span-3 flex flex-col gap-4 min-h-0">
            <div className="glass p-4 shrink-0">
              <div className="flex items-center justify-between">
                <div className="text-[10px] uppercase tracking-wider text-slate-400">총 자산(추정)</div>
                <div className="text-[10px] font-mono text-slate-400">USDT</div>
              </div>
              <div className="mt-2 flex items-end justify-between gap-3">
                <div className="text-3xl font-extrabold tracking-tight text-slate-50 font-mono">
                    {fmtUsd(equity, 0)}
                </div>
                <div className={`text-xs font-semibold font-mono ${pnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                    {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)} ({pnlPercent.toFixed(2)}%)
                </div>
            </div>
              <div className="mt-3 hairline opacity-60"></div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
                <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                  <div className="text-slate-400">시작</div>
                  <div className="font-mono text-slate-200">{fmtUsd(baseMoney ?? 0, 0)}</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                  <div className="text-slate-400">손익</div>
                  <div className={`font-mono ${pnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                    {pnl >= 0 ? '+' : ''}{pnl.toFixed(0)}
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                  <div className="text-slate-400">모드</div>
                  <div className="font-mono text-slate-200">{status?.mode === 'REAL' ? '실거래' : (status?.mode ?? '—')}</div>
                </div>
                </div>
            </div>

            {/* 전략/AI 분석 (analysis 기반, 실제로 움직이는 값) */}
            <div className="glass flex-1 flex flex-col min-h-0 overflow-hidden">
                <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
                  <div className="text-[10px] uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <Brain size={14} className="text-cyan-300" /> 전략/AI 분석
                  </div>
                  <div className="text-[10px] font-mono text-slate-400">리스크 {risk}</div>
                </div>
                
                <div className="p-4 space-y-3 overflow-y-auto">
                    {!analysis && (
                      <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3 text-slate-400 text-xs">
                        분석 데이터 수신 대기 중… (python_brain → ts_executor 텔레메트리)
                      </div>
                    )}

                    {analysis && (
                      <>
                        <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
                          <div className="flex items-center justify-between">
                            <div className="text-[10px] uppercase tracking-wider text-slate-400">현재 신호</div>
                            <div className="text-slate-100 font-extrabold">{signalKo(analysis.signal)}</div>
                          </div>
                          <div className="mt-2 grid grid-cols-2 gap-2 text-[10px]">
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">{htfLabel(analysis)} 추세(AI)</div>
                              <div className="font-mono text-slate-200">{trendKo(analysis.trend)}</div>
                            </div>
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">업데이트</div>
                              <div className="font-mono text-slate-200">{analysisAgeSec === null ? '—' : `${analysisAgeSec}s 전`}</div>
                            </div>
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2 col-span-2">
                              <div className="flex items-center justify-between">
                                <div className="text-slate-400">차트 추세(EMA20/50)</div>
                                <div className={`font-mono ${chartTrend.trend && analysis?.trend && chartTrend.trend !== analysis.trend ? 'text-amber-200' : 'text-slate-200'}`}>
                                  {trendKo(chartTrend.trend)}
                                  {chartTrend.trend && analysis?.trend && chartTrend.trend !== analysis.trend ? ' · (큰추세와 반대)' : ''}
                                </div>
                              </div>
                              <div className="mt-1 text-[10px] font-mono text-slate-400">
                                EMA20 {fmtNum(chartTrend.ema20, 2)} · EMA50 {fmtNum(chartTrend.ema50, 2)}
                              </div>
                            </div>
                        </div>
                    </div>

                        <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-slate-400 text-[10px] uppercase tracking-wider">방향 신뢰도</span>
                            <span className="text-[10px] font-mono text-slate-400">롱/숏</span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-[10px]">
                            <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/5 px-3 py-2">
                              <div className="text-slate-300/80">롱</div>
                              <div className="mt-1 w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                                <motion.div
                                  className="h-full bg-gradient-to-r from-emerald-400 to-emerald-200"
                                  initial={{ width: 0 }}
                                  animate={{ width: `${longConfPct ?? 0}%` }}
                                />
                              </div>
                              <div className="mt-1 font-mono text-slate-100">{pctText(longConfPct)}</div>
                        </div>
                            <div className="rounded-xl border border-rose-500/15 bg-rose-500/5 px-3 py-2">
                              <div className="text-slate-300/80">숏</div>
                              <div className="mt-1 w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                            <motion.div 
                                  className="h-full bg-gradient-to-r from-rose-400 to-rose-200"
                                initial={{ width: 0 }}
                                  animate={{ width: `${shortConfPct ?? 0}%` }}
                            />
                        </div>
                              <div className="mt-1 font-mono text-slate-100">{pctText(shortConfPct)}</div>
                    </div>
                </div>
                          {Number(analysis.atr ?? 0) <= 0 && (
                            <div className="mt-2 text-[10px] text-amber-200 bg-amber-500/10 border border-amber-500/20 rounded-xl px-3 py-2">
                              워밍업 중: AI ATR/강도/신뢰도는 전략 타임프레임 봉이 충분히 쌓여야 계산됩니다. (초기엔 0으로 보일 수 있음)
                            </div>
                          )}
                          <div className="mt-2 grid grid-cols-3 gap-2 text-[10px]">
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">강도</div>
                              <div className="font-mono text-slate-200">{strength === null ? '—' : fmtNum(strength, 2)}</div>
                            </div>
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">ATR</div>
                              <div className="font-mono text-slate-200">{fmtNum(analysis.atr ?? 0, 2)}</div>
                            </div>
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">현재가</div>
                              <div className="font-mono text-slate-200">{fmtUsd(lastPrice || analysis.price || 0, 2)}</div>
            </div>
                        </div>
                    </div>

                        <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
                          <div className="text-[10px] uppercase tracking-wider text-slate-400">오버레이</div>
                          <div className="mt-2 grid grid-cols-2 gap-2 text-[10px]">
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">EMA(빠름)</div>
                              <div className="font-mono text-slate-200">{fmtNum(analysis.htfEmaFast ?? 0, 2)}</div>
                            </div>
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">EMA(느림)</div>
                              <div className="font-mono text-slate-200">{fmtNum(analysis.htfEmaSlow ?? 0, 2)}</div>
                            </div>
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">손절(SL)</div>
                              <div className="font-mono text-slate-200">{analysis.stopLoss ? fmtNum(analysis.stopLoss, 2) : '—'}</div>
                            </div>
                            <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                              <div className="text-slate-400">익절(TP)</div>
                              <div className="font-mono text-slate-200">{analysis.takeProfit ? fmtNum(analysis.takeProfit, 2) : '—'}</div>
                            </div>
                          </div>
                          <div className="mt-2 rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-[10px]">
                            <div className="text-slate-400">포지션</div>
                            <div className="mt-1 font-mono text-slate-200">
                              {analysis.positionSide ? analysis.positionSide : '없음'} {analysis.entryPrice ? `(진입 ${fmtNum(analysis.entryPrice, 2)})` : ''}
                            </div>
                            {analysis.reason && (
                              <div className="mt-1 text-slate-400 break-words">
                                사유: <span className="text-slate-300">{analysis.reason}</span>
                              </div>
                            )}
                            {(analysis as any)?.entryPlan?.breakoutLong?.triggerPrice && (
                              <div className="mt-2 text-[10px] rounded-xl border border-white/10 bg-black/10 px-3 py-2">
                                <div className="text-slate-400">예상 진입가(3단계: 관찰 → 소량 → 전체)</div>
                                <div className="mt-1 grid grid-cols-2 gap-2 font-mono text-slate-200">
                                  <div>
                                    롱 {fmtNum((analysis as any).entryPlan.breakoutLong.triggerPrice, 2)}
                                    <span className="text-slate-500"> (score {fmtNum((analysis as any).entryPlan.breakoutLong.score, 2)}/{fmtNum((analysis as any).entryPlan.breakoutLong.threshold, 2)})</span>
                                    {Boolean((analysis as any)?.entryPlan?.breakoutLong?.immediateOk) && (
                                      <span className="ml-2 px-2 py-0.5 rounded-full border border-emerald-500/35 bg-emerald-500/15 text-emerald-200">
                                        3단계(전체)
                                      </span>
                                    )}
                                    {Boolean((analysis as any)?.entryPlan?.breakoutLong?.softOk) && !Boolean((analysis as any)?.entryPlan?.breakoutLong?.immediateOk) && (
                                      <span className="ml-2 px-2 py-0.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 text-emerald-200/90">
                                        2단계(소량)
                                      </span>
                                    )}
                                    {Boolean((analysis as any)?.entryPlan?.breakoutLong?.watchOk) && !Boolean((analysis as any)?.entryPlan?.breakoutLong?.softOk) && !Boolean((analysis as any)?.entryPlan?.breakoutLong?.immediateOk) && (
                                      <span className="ml-2 px-2 py-0.5 rounded-full border border-slate-400/25 bg-slate-400/10 text-slate-200/80">
                                        1단계(관찰)
                                      </span>
                                    )}
                                  </div>
                                  <div>
                                    숏 {fmtNum((analysis as any).entryPlan.breakoutShort.triggerPrice, 2)}
                                    <span className="text-slate-500"> (score {fmtNum((analysis as any).entryPlan.breakoutShort.score, 2)}/{fmtNum((analysis as any).entryPlan.breakoutShort.threshold, 2)})</span>
                                    {Boolean((analysis as any)?.entryPlan?.breakoutShort?.immediateOk) && (
                                      <span className="ml-2 px-2 py-0.5 rounded-full border border-rose-500/35 bg-rose-500/15 text-rose-200">
                                        3단계(전체)
                                      </span>
                                    )}
                                    {Boolean((analysis as any)?.entryPlan?.breakoutShort?.softOk) && !Boolean((analysis as any)?.entryPlan?.breakoutShort?.immediateOk) && (
                                      <span className="ml-2 px-2 py-0.5 rounded-full border border-rose-500/25 bg-rose-500/10 text-rose-200/90">
                                        2단계(소량)
                                      </span>
                                    )}
                                    {Boolean((analysis as any)?.entryPlan?.breakoutShort?.watchOk) && !Boolean((analysis as any)?.entryPlan?.breakoutShort?.softOk) && !Boolean((analysis as any)?.entryPlan?.breakoutShort?.immediateOk) && (
                                      <span className="ml-2 px-2 py-0.5 rounded-full border border-slate-400/25 bg-slate-400/10 text-slate-200/80">
                                        1단계(관찰)
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="mt-1 text-slate-500">
                                  ADX {fmtNum((analysis as any).entryPlan.meta?.adx ?? 0, 1)} / 최소 {fmtNum((analysis as any).entryPlan.breakoutLong.minAdx ?? 0, 1)}
                                  {' · '}
                                  수량 {fmtNum((analysis as any).entryPlan.meta?.previewQty ?? 0, 6)}
                                  {' · '}
                                  금액 {fmtUsd((analysis as any).entryPlan.meta?.previewNotional ?? 0, 2)}
                                </div>
                              </div>
                            )}
                            {Boolean((analysis as any)?.entryPlan?.ctLong?.inWashoutWindow) && (analysis as any)?.entryPlan?.ctLong?.triggerPrice && (
                              <div className="mt-2 text-[10px] rounded-xl border border-cyan-500/15 bg-cyan-500/5 px-3 py-2">
                                <div className="text-slate-400">예상 진입가(반등롱 · 급락 이후)</div>
                                <div className="mt-1 font-mono text-slate-200">
                                  {fmtNum((analysis as any).entryPlan.ctLong.triggerPrice, 2)}
                                  <span className="text-slate-500">
                                    {' '}
                                    (윈도우 {String(Boolean((analysis as any).entryPlan.ctLong.inWashoutWindow))}
                                    {' · '}
                                    확인 {String(Boolean((analysis as any).entryPlan.ctLong.confirmOk))}/{String((analysis as any).entryPlan.ctLong.confirmUpBars ?? 0)}봉
                                    )
                                  </span>
                                </div>
                                <div className="mt-1 text-slate-500">
                                  최근고점 {fmtNum((analysis as any).entryPlan.ctLong.recentHigh ?? 0, 2)}
                                  {' · '}
                                  급락 {fmtNum((analysis as any).entryPlan.ctLong.drop ?? 0, 2)} / 필요 {fmtNum((analysis as any).entryPlan.ctLong.needDrop ?? 0, 2)}
                                  {' · '}
                                  저점 {fmtNum((analysis as any).entryPlan.ctLong.washoutLow ?? 0, 2)}
                                </div>
                              </div>
                            )}
                            {Boolean((analysis as any)?.entryPlan?.ctShort?.inPumpWindow) && (analysis as any)?.entryPlan?.ctShort?.triggerPrice && (
                              <div className="mt-2 text-[10px] rounded-xl border border-rose-500/15 bg-rose-500/5 px-3 py-2">
                                <div className="text-slate-400">예상 진입가(반락숏 · 급상승 이후)</div>
                                <div className="mt-1 font-mono text-slate-200">
                                  {fmtNum((analysis as any).entryPlan.ctShort.triggerPrice, 2)}
                                  <span className="text-slate-500">
                                    {' '}
                                    (윈도우 {String(Boolean((analysis as any).entryPlan.ctShort.inPumpWindow))}
                                    {' · '}
                                    확인 {String(Boolean((analysis as any).entryPlan.ctShort.confirmOk))}/{String((analysis as any).entryPlan.ctShort.confirmDownBars ?? 0)}봉
                                    )
                            </span>
                        </div>
                                <div className="mt-1 text-slate-500">
                                  최근저점 {fmtNum((analysis as any).entryPlan.ctShort.recentLow ?? 0, 2)}
                                  {' · '}
                                  급상승 {fmtNum((analysis as any).entryPlan.ctShort.rise ?? 0, 2)} / 필요 {fmtNum((analysis as any).entryPlan.ctShort.needRise ?? 0, 2)}
                                  {' · '}
                                  고점 {fmtNum((analysis as any).entryPlan.ctShort.pumpHigh ?? 0, 2)}
                                </div>
                              </div>
                            )}
                        </div>
                    </div>
                      </>
                    )}
                </div>
            </div>
        </div>

        {/* CENTER: CHART (확장) + AI 흐름 + 포지션 */}
        <div className="lg:col-span-9 flex flex-col gap-4 min-h-0">
            {/* CHART (높이/가로 확장) */}
            <div className="glass p-4 flex flex-col flex-1 min-h-0">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-400">차트</div>
                  <div className="text-[12px] font-semibold text-slate-100">{chartMode === 'candles' ? '실시간 캔들' : '자산 곡선'}</div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center rounded-full border border-white/10 bg-white/5 p-1 text-[10px] font-mono">
                    <button
                      onClick={() => setChartMode('candles')}
                      className={`px-3 py-1 rounded-full ${chartMode === 'candles' ? 'bg-emerald-500/15 text-emerald-200 border border-emerald-500/20' : 'text-slate-300'}`}
                    >
                      캔들
                    </button>
                    <button
                      onClick={() => setChartMode('equity')}
                      className={`px-3 py-1 rounded-full ${chartMode === 'equity' ? 'bg-cyan-500/15 text-cyan-200 border border-cyan-500/20' : 'text-slate-300'}`}
                    >
                      자산
                    </button>
            </div>
            
                  {chartMode === 'candles' && (
                    <div className="flex items-center gap-2">
                      {/* AI 분석은 봇이 돌고 있는 심볼에서만 나온다. 다른 심볼이면 "고장"처럼 보이므로 즉시 안내 */}
                      {(!analysis) && (
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-amber-500/25 bg-amber-500/10 text-[10px] text-amber-200">
                          <span className="font-mono">AI 분석 없음</span>
                          {lastAiSymbol ? (
                            <button
                              onClick={() => setSymbol(lastAiSymbol)}
                              className="px-2 py-0.5 rounded-full border border-amber-400/30 bg-amber-400/10 text-amber-100 hover:bg-amber-400/15"
                            >
                              {lastAiSymbol}로 이동
                            </button>
                          ) : (
                            <span className="text-amber-200/80">봇 심볼에서만 표시됨</span>
                          )}
                        </div>
                      )}
                      <select
                        value={symbol}
                        onChange={(e) => setSymbol(e.target.value)}
                        className="text-[10px] font-mono bg-black/20 border border-white/10 rounded-full px-3 py-1.5 text-slate-200 outline-none"
                      >
                        {/* 기본 목록 */}
                        <option value="BTCUSDT">BTCUSDT{lastAiSymbol && lastAiSymbol !== 'BTCUSDT' ? ' (AI 없음)' : ''}</option>
                        <option value="ETHUSDT">ETHUSDT{lastAiSymbol && lastAiSymbol !== 'ETHUSDT' ? ' (AI 없음)' : ''}</option>
                        <option value="SOLUSDT">SOLUSDT (AI 없음)</option>
                        <option value="BNBUSDT">BNBUSDT (AI 없음)</option>
                        {positions.map(p => (
                          <option key={p.symbol} value={p.symbol}>
                            {p.symbol}{lastAiSymbol && lastAiSymbol !== p.symbol ? ' (AI 없음)' : ''}
                          </option>
                        ))}
                      </select>
                      <select
                        value={interval}
                        onChange={(e) => setIntervalTf(e.target.value)}
                        className="text-[10px] font-mono bg-black/20 border border-white/10 rounded-full px-3 py-1.5 text-slate-200 outline-none"
                      >
                        <option value="1m">1m</option>
                        <option value="3m">3m</option>
                        <option value="5m">5m</option>
                        <option value="15m">15m</option>
                        <option value="1h">1h</option>
                        <option value="4h">4h</option>
                      </select>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex-1 min-h-0">
                <ChartWidget
                  mode={chartMode}
                  equityData={chartData}
                  candles={candles}
                  macro={macro}
                  symbol={symbol}
                  interval={interval}
                  lastPrice={lastPrice}
                  markers={markers || []}
                  analysis={analysis || null}
                />
                </div>
                </div>
            
            {/* AI 흐름(타임라인): 로그 영역 대신 "AI가 어떻게 바뀌는지"를 보여줌 */}
            <div className="glass flex flex-col min-h-0 overflow-hidden">
              <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity size={14} className="text-cyan-300" />
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-slate-400">AI 분석 흐름</div>
                    <div className="text-[12px] font-semibold text-slate-100">
                      {analysisAgeSec === null ? '업데이트 대기' : `최근 업데이트: ${analysisAgeSec}s 전`}
                </div>
            </div>
        </div>
                <button
                  onClick={() => setShowAiFeed(v => !v)}
                  className="px-2 py-1 rounded-full border border-white/10 bg-white/5 text-slate-200 text-[10px] font-mono flex items-center gap-1"
                >
                  {showAiFeed ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                  {showAiFeed ? '접기' : '펼치기'}
                </button>
              </div>
              {showAiFeed && (
                <div className="p-3 overflow-y-auto max-h-[220px] font-mono text-[10px] space-y-2">
                  {latestFeed.length === 0 && (
                    <div className="text-slate-500 italic text-center py-6">AI 스냅샷이 아직 없습니다…</div>
                )}
                  {latestFeed.map((x) => {
                    const conf = Number.isFinite(Number(x.confidence)) ? Math.max(0, Math.min(1, Number(x.confidence))) : 0;
                    const lconf = Number.isFinite(Number((x as any).longConfidence)) ? Math.max(0, Math.min(1, Number((x as any).longConfidence))) : 0;
                    const sconf = Number.isFinite(Number((x as any).shortConfidence)) ? Math.max(0, Math.min(1, Number((x as any).shortConfidence))) : 0;
                    const st = Number.isFinite(Number(x.strength)) ? Number(x.strength) : 0;
                    const tr = String(x.trend || 'range');
                    const trKo = tr === 'up' ? '상승' : (tr === 'down' ? '하락' : '횡보');
                    const color = tr === 'down' ? 'text-rose-300' : (tr === 'up' ? 'text-emerald-300' : 'text-slate-300');
                    const ts = new Date(Number(x.time) * 1000).toLocaleString();
                    return (
                      <div key={x.time} className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-slate-400">{ts}</span>
                          <span className={`font-semibold ${color}`}>AI {trKo}</span>
                        </div>
                        <div className="mt-1 text-slate-200">
                          신호 <span className="text-slate-50 font-semibold">{signalKo(x.signal)}</span>
                          <span className="text-slate-500"> · </span>
                          롱 {pctText(lconf * 100)} / 숏 {pctText(sconf * 100)}
                          <span className="text-slate-500"> · </span>
                          강도 {st.toFixed(2)}
                          <span className="text-slate-500"> · </span>
                          가격 {fmtUsd(x.price, 2)}
                        </div>
                        {x.reason && (
                          <div className="mt-1 text-slate-400 break-words">사유: <span className="text-slate-300">{x.reason}</span></div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            
            {/* 포지션 목록 (필요 시만 펼쳐서 차트 가시성 우선) */}
            <div className="glass flex flex-col min-h-0 overflow-hidden">
              <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-slate-400">포지션</div>
                    <div className="text-[12px] font-semibold text-slate-100">보유 계약</div>
                  </div>
                  <span className="px-2 py-1 rounded-full text-[10px] font-mono border border-white/10 bg-white/5 text-slate-200">
                    {positions.length}
                        </span>
                </div>
                <button
                  onClick={() => setShowPositions(v => !v)}
                  className="px-2 py-1 rounded-full border border-white/10 bg-white/5 text-slate-200 text-[10px] font-mono flex items-center gap-1"
                >
                  {showPositions ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                  {showPositions ? '접기' : '펼치기'}
                </button>
              </div>
              {showPositions && (
                <div className="overflow-y-auto max-h-[220px] rounded-[14px] border-t border-white/10 bg-black/10">
                  <AssetList positions={positions} />
                    </div>
              )}
            </div>
        </div>

      </div>
    </div>
  );
};

export default App;