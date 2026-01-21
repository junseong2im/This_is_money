import React, { useEffect, useMemo, useRef } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { createChart, CandlestickSeries, LineSeries, createSeriesMarkers, type IChartApi, type ISeriesApi, type UTCTimestamp, type ISeriesMarkersPluginApi, type IPriceLine } from 'lightweight-charts';
import type { Candle, MacroIndicators } from '../types';

interface ChartWidgetProps {
  mode: 'equity' | 'candles';
  equityData?: { time: string; value: number }[];
  candles?: Candle[];
  macro?: MacroIndicators | null;
  symbol?: string;
  interval?: string;
  lastPrice?: number;
  markers?: Array<{
    time: number;
    color: string;
    position: 'aboveBar' | 'belowBar' | 'inBar';
    shape: 'arrowUp' | 'arrowDown' | 'circle' | 'square';
    text?: string;
  }>;
  analysis?: {
    symbol: string;
    interval: string;
    time: number;
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
}

function ema(values: number[], period: number) {
  if (period <= 1) return values.map((v, i) => ({ i, v }));
  const k = 2 / (period + 1);
  let prev: number | null = null;
  const out: { i: number; v: number }[] = [];
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    prev = prev === null ? v : v * k + prev * (1 - k);
    out.push({ i, v: prev });
  }
  return out;
}

function atrWilder(candles: Candle[], period: number) {
  const n = Math.max(2, Math.floor(period));
  const out: Array<{ time: UTCTimestamp; value: number }> = [];
  if (!candles || candles.length < 3) return out;
  let prevAtr: number | null = null;
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i];
    const prev = i > 0 ? candles[i - 1] : c;
    const tr = Math.max(
      c.high - c.low,
      Math.abs(c.high - prev.close),
      Math.abs(c.low - prev.close),
    );
    if (prevAtr === null) prevAtr = tr;
    else prevAtr = ((prevAtr * (n - 1)) + tr) / n;
    if (i >= n - 1 && Number.isFinite(prevAtr) && prevAtr > 0) {
      out.push({ time: c.time as UTCTimestamp, value: prevAtr });
    }
  }
  return out;
}

const ChartWidget: React.FC<ChartWidgetProps> = ({
  mode,
  equityData = [],
  candles = [],
  macro,
  symbol,
  interval,
  lastPrice,
  markers = [],
  analysis = null,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const emaFastRef = useRef<ISeriesApi<'Line'> | null>(null);
  const emaSlowRef = useRef<ISeriesApi<'Line'> | null>(null);
  const markersApiRef = useRef<ISeriesMarkersPluginApi<UTCTimestamp> | null>(null);
  const priceLinesRef = useRef<{
    entry?: IPriceLine;
    sl?: IPriceLine;
    tp?: IPriceLine;
    trail?: IPriceLine;
    aiEmaFast?: IPriceLine;
    aiEmaSlow?: IPriceLine;
    aiAtrUp?: IPriceLine;
    aiAtrDn?: IPriceLine;
    aiRes?: IPriceLine;
    aiSup?: IPriceLine;
    aiVwap?: IPriceLine;
    aiBaseEmaSlow?: IPriceLine;
    aiEntryLong?: IPriceLine;
    aiEntryShort?: IPriceLine;
    aiEntryCtLong?: IPriceLine;
    aiEntryCtShort?: IPriceLine;
    aiEntryLongNow?: IPriceLine;
    aiEntryShortNow?: IPriceLine;
    aiEntryCtLongNow?: IPriceLine;
    aiEntryCtShortNow?: IPriceLine;
    aiEntryLongSoft?: IPriceLine;
    aiEntryShortSoft?: IPriceLine;
    aiEntryCtLongSoft?: IPriceLine;
    aiEntryCtShortSoft?: IPriceLine;
    aiCommitLong?: IPriceLine;
    aiCommitShort?: IPriceLine;
    aiCommitCtLong?: IPriceLine;
    aiCommitCtShort?: IPriceLine;
  }>({});
  const didFitRef = useRef(false);
  const lastBarRef = useRef<{ time: UTCTimestamp; open: number; high: number; low: number; close: number } | null>(null);
  const candleMetaRef = useRef<{ len: number; first: number; last: number } | null>(null);
  const emaFastPrevRef = useRef<number | null>(null);
  const emaFastLastRef = useRef<number | null>(null);
  const emaSlowPrevRef = useRef<number | null>(null);
  const emaSlowLastRef = useRef<number | null>(null);
  const emaLastTimeRef = useRef<UTCTimestamp | null>(null);
  const EMA_FAST_K = useMemo(() => 2 / (20 + 1), []);
  const EMA_SLOW_K = useMemo(() => 2 / (50 + 1), []);

  const strokeColor = useMemo(() => {
    const d = equityData;
    const isProfit = d.length > 1 && d[d.length - 1].value >= d[0].value;
    return isProfit ? "#10b981" : "#f43f5e";
  }, [equityData]);

  const overlays = useMemo(() => {
    const longConf = (analysis?.longConfidence ?? 0) as number;
    const shortConf = (analysis?.shortConfidence ?? 0) as number;
    const strength = (analysis?.strength ?? 0) as number;
    const trend = (analysis?.trend ?? '') as string;
    const risk = macro?.riskSentiment ?? 'NEUTRAL';
    return { longConf, shortConf, strength, trend, risk };
  }, [macro, analysis]);

  const derived = useMemo(() => {
    // AI(백엔드) 분석이 느리거나 0으로 비어있을 때도,
    // 차트 캔들 자체(EMA/ATR)로 "그림"이 움직이게 만들기 위한 보조 분석.
    const cs = candles || [];
    if (cs.length < 60) {
      return { conf: 0, strength: 0, trend: '' };
    }
    const closes = cs.map(c => c.close);
    const e20 = ema(closes, 20);
    const e50 = ema(closes, 50);
    const last20 = e20[e20.length - 1]?.v ?? 0;
    const last50 = e50[e50.length - 1]?.v ?? 0;
    const trend = last20 > last50 ? 'up' : (last20 < last50 ? 'down' : 'range');

    const atr14 = atrWilder(cs, 14);
    const lastAtr = atr14.length ? atr14[atr14.length - 1].value : 0;
    const strength = (lastAtr > 0) ? (Math.abs(last20 - last50) / lastAtr) : 0;

    let conf = 0;
    if (strength > 0) {
      conf = (strength - 0.15) / (1.35 - 0.15);
      conf = Math.max(0, Math.min(1, conf));
    }
    return { conf, strength, trend };
  }, [candles]);

  // NOTE:
  // - overlays.* 는 python_brain → ts_executor 텔레메트리(=AI/전략) 값
  // - derived.* 는 차트 캔들로 만든 "추정값" (워밍업/지연 시 참고용)
  // UI에서 AI값처럼 보이게 섞으면 신뢰가 무너져서, 라벨을 분리한다.
  const isTelemetryWarm = useMemo(() => {
    const atr = Number(analysis?.atr ?? 0);
    return Number.isFinite(atr) && atr > 0;
  }, [analysis?.atr]);

  const pctText = (x: number) => {
    const v = Number(x);
    if (!Number.isFinite(v)) return '—';
    const p = Math.min(99.9, Math.max(0, v * 100));
    return `${p.toFixed(1)}%`;
  };

  const aiAgeSec = useMemo(() => {
    const t = Number((analysis as any)?.sentAt ?? 0);
    if (!t || !Number.isFinite(t)) return null;
    return Math.max(0, Math.floor(Date.now() / 1000 - t));
  }, [(analysis as any)?.sentAt]);

  const trendKo = (t?: string) => {
    const s = String(t || '').toLowerCase();
    if (s === 'up') return '상승';
    if (s === 'down') return '하락';
    if (s === 'range') return '횡보';
    return '—';
  };

  useEffect(() => {
    if (mode !== 'candles') return;
    if (!containerRef.current) return;

    if (chartRef.current) return; // already created

    // mode 전환/리마운트 케이스에서 stale ref가 남아 차트가 비어 보이는 문제 방지
    didFitRef.current = false;
    candleMetaRef.current = null;
    emaFastPrevRef.current = null;
    emaFastLastRef.current = null;
    emaSlowPrevRef.current = null;
    emaSlowLastRef.current = null;
    emaLastTimeRef.current = null;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: 'rgba(226,232,240,0.85)'
      },
      grid: {
        vertLines: { color: 'rgba(148,163,184,0.08)' },
        horzLines: { color: 'rgba(148,163,184,0.08)' }
      },
      rightPriceScale: { borderColor: 'rgba(148,163,184,0.15)' },
      timeScale: { borderColor: 'rgba(148,163,184,0.15)', timeVisible: true, secondsVisible: false },
      crosshair: {
        vertLine: { color: 'rgba(52,211,153,0.25)' },
        horzLine: { color: 'rgba(52,211,153,0.25)' }
      },
      handleScroll: true,
      handleScale: true,
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: 'rgba(52, 211, 153, 0.95)',
      downColor: 'rgba(251, 113, 133, 0.95)',
      borderUpColor: 'rgba(52, 211, 153, 0.95)',
      borderDownColor: 'rgba(251, 113, 133, 0.95)',
      wickUpColor: 'rgba(52, 211, 153, 0.75)',
      wickDownColor: 'rgba(251, 113, 133, 0.75)',
    });

    const emaFast = chart.addSeries(LineSeries, {
      color: 'rgba(34, 211, 238, 0.85)',
      lineWidth: 2,
      priceLineVisible: false
    });
    const emaSlow = chart.addSeries(LineSeries, {
      color: 'rgba(167, 139, 250, 0.75)',
      lineWidth: 2,
      priceLineVisible: false
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    emaFastRef.current = emaFast;
    emaSlowRef.current = emaSlow;

    // markers plugin
    markersApiRef.current = createSeriesMarkers<UTCTimestamp>(candleSeries as any, []);

    const ro = new ResizeObserver(() => {
      if (!containerRef.current || !chartRef.current) return;
      chartRef.current.resize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      emaFastRef.current = null;
      emaSlowRef.current = null;
      markersApiRef.current = null;
      priceLinesRef.current = {};
      didFitRef.current = false;
      candleMetaRef.current = null;
      emaFastPrevRef.current = null;
      emaFastLastRef.current = null;
      emaSlowPrevRef.current = null;
      emaSlowLastRef.current = null;
      emaLastTimeRef.current = null;
    };
  }, [mode]);

  useEffect(() => {
    if (mode !== 'candles') return;
    if (!chartRef.current || !candleSeriesRef.current) return;
    if (!candles || candles.length === 0) return;

    const series = candleSeriesRef.current;
    const firstT = Number(candles[0].time);
    const lastT = Number(candles[candles.length - 1].time);
    const prev = candleMetaRef.current;
    const shouldReset = !prev || prev.first !== firstT || candles.length < prev.len || lastT < prev.last;

    if (shouldReset) {
      const candleData = candles.map(c => ({
        time: c.time as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));
      series.setData(candleData);
      lastBarRef.current = candleData[candleData.length - 1] ?? null;
      candleMetaRef.current = { len: candles.length, first: firstT, last: lastT };

      // EMA는 전체 재계산(초기 로딩/리셋만)
      const closes = candles.map(c => c.close);
      const fast = ema(closes, 20).map(({ i, v }) => ({ time: candles[i].time as UTCTimestamp, value: v }));
      const slow = ema(closes, 50).map(({ i, v }) => ({ time: candles[i].time as UTCTimestamp, value: v }));
      emaFastRef.current?.setData(fast);
      emaSlowRef.current?.setData(slow);
      if (fast.length) {
        emaFastLastRef.current = fast[fast.length - 1].value;
        emaFastPrevRef.current = fast.length >= 2 ? fast[fast.length - 2].value : fast[fast.length - 1].value;
        emaLastTimeRef.current = fast[fast.length - 1].time;
      }
      if (slow.length) {
        emaSlowLastRef.current = slow[slow.length - 1].value;
        emaSlowPrevRef.current = slow.length >= 2 ? slow[slow.length - 2].value : slow[slow.length - 1].value;
      }
    } else {
      // 신규 캔들만 append/update로 반영 (setData 남발 방지 → UI 반응 개선)
      const prevLen = prev.len;
      const appendFrom = Math.max(0, prevLen); // 새로 늘어난 구간부터

      if (candles.length > prevLen) {
        for (let i = appendFrom; i < candles.length; i++) {
          const c = candles[i];
          const bar = { time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close };
          series.update(bar);
          lastBarRef.current = bar;

          // EMA는 신규 봉만 증분 업데이트
          const prevFast = emaFastLastRef.current ?? c.close;
          const prevSlow = emaSlowLastRef.current ?? c.close;
          emaFastPrevRef.current = prevFast;
          emaSlowPrevRef.current = prevSlow;

          const nextFast = c.close * EMA_FAST_K + prevFast * (1 - EMA_FAST_K);
          const nextSlow = c.close * EMA_SLOW_K + prevSlow * (1 - EMA_SLOW_K);
          emaFastLastRef.current = nextFast;
          emaSlowLastRef.current = nextSlow;
          emaLastTimeRef.current = c.time as UTCTimestamp;

          emaFastRef.current?.update({ time: c.time as UTCTimestamp, value: nextFast });
          emaSlowRef.current?.update({ time: c.time as UTCTimestamp, value: nextSlow });
        }
      } else {
        // 길이는 같은데 마지막 봉 값이 갱신됐을 수 있음 → 마지막 봉만 업데이트
        const c = candles[candles.length - 1];
        const bar = { time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close };
        series.update(bar);
        lastBarRef.current = bar;
        // EMA는 lastPrice 실시간 업데이트 useEffect에서 처리(여기선 재계산/재설정하지 않음)
      }

      candleMetaRef.current = { len: candles.length, first: firstT, last: lastT };
    }

    if (!didFitRef.current) {
      chartRef.current.timeScale().fitContent();
      didFitRef.current = true;
    }
  }, [mode, candles, EMA_FAST_K, EMA_SLOW_K]);

  // 분석 값으로 가격 라인(Entry/SL/TP/Trailing) 표시
  useEffect(() => {
    if (mode !== 'candles') return;
    if (!candleSeriesRef.current) return;

    const series = candleSeriesRef.current;
    const lines = priceLinesRef.current;

    const clearLine = (k: keyof typeof lines) => {
      const l = lines[k];
      if (l) {
        try { series.removePriceLine(l); } catch {}
        lines[k] = undefined;
      }
    };

    const upsertLine = (k: keyof typeof lines, price: number, title: string, color: string, lineWidth = 2, lineStyle = 2) => {
      if (!Number.isFinite(price) || price <= 0) { clearLine(k); return; }
      if (!lines[k]) {
        lines[k] = series.createPriceLine({
          price,
          color,
          lineWidth,
          lineStyle,
          axisLabelVisible: true,
          title,
        });
      } else {
        lines[k]?.applyOptions({ price, title, color, lineWidth, lineStyle });
      }
    };

    const entry = analysis?.entryPrice ?? 0;
    const sl = analysis?.stopLoss ?? 0;
    const tp = analysis?.takeProfit ?? 0;
    const tr = analysis?.trailingStop ?? 0;

    upsertLine('entry', entry, '진입', 'rgba(34,211,238,0.75)');
    upsertLine('sl', sl, '손절', 'rgba(251,113,133,0.75)');
    upsertLine('tp', tp, '익절', 'rgba(52,211,153,0.70)');
    upsertLine('trail', tr, '추적', 'rgba(251,191,36,0.70)');

    // --- 큰 추세(HTF) 오버레이 ---
    // 1) 큰 추세선(HTF EMA) 라인
    const aiEf = Number(analysis?.htfEmaFast ?? 0);
    const aiEs = Number(analysis?.htfEmaSlow ?? 0);
    upsertLine('aiEmaFast', aiEf, '큰추세선(빠름)', 'rgba(34,211,238,0.55)');
    upsertLine('aiEmaSlow', aiEs, '큰추세선(느림)', 'rgba(167,139,250,0.55)');

    // 3) 3단계 예상 진입가(관찰→소량→전체): 1/2/3 단계는 "서로 다른 가격"으로 표시한다.
    const ep = (analysis as any)?.entryPlan || {};
    const bl = ep?.breakoutLong || {};
    const bs = ep?.breakoutShort || {};
    const meta = ep?.meta || {};
    const vwap = Number(meta?.vwap ?? 0);
    const baseEmaSlow = Number(meta?.emaSlow ?? 0);
    const resLevel = Number(bl?.resistance ?? 0);
    const supLevel = Number(bs?.support ?? 0);
    const l1 = Number(bl?.watchPrice ?? 0);
    const l2 = Number(bl?.softPrice ?? 0);
    const l3 = Number(bl?.fullPrice ?? bl?.triggerPrice ?? 0);
    const s1 = Number(bs?.watchPrice ?? 0);
    const s2 = Number(bs?.softPrice ?? 0);
    const s3 = Number(bs?.fullPrice ?? bs?.triggerPrice ?? 0);
    const l3Armed = Boolean(bl?.immediateOk ?? false);
    const s3Armed = Boolean(bs?.immediateOk ?? false);
    const l2Armed = Boolean(bl?.softOk ?? false);
    const s2Armed = Boolean(bs?.softOk ?? false);

    // "1단계 이전에 선이 없다" 문제를 줄이기 위해,
    // 공정가치(VWAP/EMA_slow) + 피벗 레벨(저항/지지)을 추가로 표시한다.
    upsertLine('aiVwap', vwap, '기준(VWAP)', 'rgba(56,189,248,0.40)', 1, 3);
    upsertLine('aiBaseEmaSlow', baseEmaSlow, '기준(EMA 느림)', 'rgba(167,139,250,0.40)', 1, 3);
    upsertLine('aiRes', resLevel, '저항(피벗)', 'rgba(148,163,184,0.45)', 1, 3);
    upsertLine('aiSup', supLevel, '지지(피벗)', 'rgba(148,163,184,0.45)', 1, 3);

    upsertLine('aiEntryLong', l1, '1단계 관찰(롱·돌파)', 'rgba(148,163,184,0.55)', 1, 3);
    upsertLine(
      'aiEntryLongSoft',
      l2,
      l2Armed ? '2단계 소량진입(롱·돌파·준비됨)' : '2단계 소량진입(롱·돌파·대기)',
      l2Armed ? 'rgba(52,211,153,0.75)' : 'rgba(148,163,184,0.45)',
      l2Armed ? 2 : 1,
      l2Armed ? 2 : 3
    );
    upsertLine(
      'aiEntryLongNow',
      l3,
      l3Armed ? '3단계 전체진입(롱·돌파·준비됨)' : '3단계 전체진입(롱·돌파·대기)',
      l3Armed ? 'rgba(52,211,153,0.95)' : 'rgba(148,163,184,0.55)',
      l3Armed ? 3 : 1,
      l3Armed ? 0 : 3
    );

    upsertLine('aiEntryShort', s1, '1단계 관찰(숏·이탈)', 'rgba(148,163,184,0.55)', 1, 3);
    upsertLine(
      'aiEntryShortSoft',
      s2,
      s2Armed ? '2단계 소량진입(숏·이탈·준비됨)' : '2단계 소량진입(숏·이탈·대기)',
      s2Armed ? 'rgba(251,113,133,0.75)' : 'rgba(148,163,184,0.45)',
      s2Armed ? 2 : 1,
      s2Armed ? 2 : 3
    );
    upsertLine(
      'aiEntryShortNow',
      s3,
      s3Armed ? '3단계 전체진입(숏·이탈·준비됨)' : '3단계 전체진입(숏·이탈·대기)',
      s3Armed ? 'rgba(251,113,133,0.95)' : 'rgba(148,163,184,0.55)',
      s3Armed ? 3 : 1,
      s3Armed ? 0 : 3
    );

    clearLine('aiCommitLong');
    clearLine('aiCommitShort');

    // 4) 예상 진입가(반등 롱: 급락 이후) - 급락 윈도우일 때만 표시(노이즈/혼란 방지)
    const ctLongTrig = Number(ep?.ctLong?.triggerPrice ?? 0);
    const inWin = Boolean(ep?.ctLong?.inWashoutWindow ?? false);
    if (inWin) {
      const cl = ep?.ctLong || {};
      const c1 = Number(cl?.watchPrice ?? 0);
      const c2 = Number(cl?.softPrice ?? 0);
      const c3 = Number(cl?.fullPrice ?? cl?.triggerPrice ?? 0);
      upsertLine('aiEntryCtLong', c1, '1단계 관찰(반등롱)', 'rgba(148,163,184,0.55)', 1, 3);
      upsertLine('aiEntryCtLongSoft', c2, '2단계 소량진입(반등롱)', 'rgba(34,211,238,0.75)', 2, 2);
      upsertLine('aiEntryCtLongNow', c3, '3단계 전체진입(반등롱)', 'rgba(34,211,238,0.95)', 3, 0);
    } else {
      clearLine('aiEntryCtLong');
      clearLine('aiEntryCtLongSoft');
      clearLine('aiEntryCtLongNow');
    }

    // 5) 예상 진입가(반락 숏: 급상승 이후) - 펌프 윈도우일 때만 표시
    const ctShortTrig = Number(ep?.ctShort?.triggerPrice ?? 0);
    const inPump = Boolean(ep?.ctShort?.inPumpWindow ?? false);
    if (inPump) {
      const cs = ep?.ctShort || {};
      const c1s = Number(cs?.watchPrice ?? 0);
      const c2s = Number(cs?.softPrice ?? 0);
      const c3s = Number(cs?.fullPrice ?? cs?.triggerPrice ?? 0);
      upsertLine('aiEntryCtShort', c1s, '1단계 관찰(반락숏)', 'rgba(148,163,184,0.55)', 1, 3);
      upsertLine('aiEntryCtShortSoft', c2s, '2단계 소량진입(반락숏)', 'rgba(251,113,133,0.75)', 2, 2);
      upsertLine('aiEntryCtShortNow', c3s, '3단계 전체진입(반락숏)', 'rgba(251,113,133,0.95)', 3, 0);
    } else {
      clearLine('aiEntryCtShort');
      clearLine('aiEntryCtShortSoft');
      clearLine('aiEntryCtShortNow');
    }

    // commit 라인은 3단계(전체진입) 선으로 대체됨
    clearLine('aiCommitCtLong');
    clearLine('aiCommitCtShort');

    // 2) ATR 채널(EMA 느림 기준 ± k*ATR) 라인
    // - 텔레메트리 ATR(전략 타임프레임)이 0이면, 차트 캔들로 만든 "추정 ATR"로만 시각화(라벨도 추정으로 표시)
    let atr = Number(analysis?.atr ?? 0);
    let usedFallback = false;
    if (!Number.isFinite(atr) || atr <= 0) {
      const a = atrWilder(candles || [], 14);
      atr = a.length ? Number(a[a.length - 1].value) : 0;
      usedFallback = atr > 0;
    }
    const k = 1.5; // 시각화용(과도한 선을 피하려고 1.5로 고정)
    if (Number.isFinite(aiEs) && aiEs > 0 && Number.isFinite(atr) && atr > 0) {
      const label = usedFallback ? '변동폭(추정)' : '변동폭';
      upsertLine('aiAtrUp', aiEs + atr * k, `${label} +${k}ATR`, 'rgba(52,211,153,0.35)');
      upsertLine('aiAtrDn', aiEs - atr * k, `${label} -${k}ATR`, 'rgba(251,113,133,0.35)');
    } else {
      clearLine('aiAtrUp');
      clearLine('aiAtrDn');
    }
  }, [mode, analysis, candles]);

  // 1초마다 현재가로 "마지막 캔들"을 업데이트해서 실시간처럼 보이게 함
  useEffect(() => {
    if (mode !== 'candles') return;
    if (!lastPrice || !Number.isFinite(lastPrice)) return;
    if (!candleSeriesRef.current) return;
    if (!lastBarRef.current) return;

    const b = lastBarRef.current;
    const close = lastPrice;
    const high = Math.max(b.high, close);
    const low = Math.min(b.low, close);
    const next = { ...b, close, high, low };
    lastBarRef.current = next;
    candleSeriesRef.current.update(next);

    // EMA도 실시간으로 마지막 포인트만 업데이트(차트 체감 반응 개선)
    if (emaLastTimeRef.current && emaLastTimeRef.current === next.time) {
      const prevFast = emaFastPrevRef.current ?? emaFastLastRef.current ?? close;
      const prevSlow = emaSlowPrevRef.current ?? emaSlowLastRef.current ?? close;
      const nextFast = close * EMA_FAST_K + prevFast * (1 - EMA_FAST_K);
      const nextSlow = close * EMA_SLOW_K + prevSlow * (1 - EMA_SLOW_K);
      emaFastLastRef.current = nextFast;
      emaSlowLastRef.current = nextSlow;
      emaFastRef.current?.update({ time: next.time, value: nextFast });
      emaSlowRef.current?.update({ time: next.time, value: nextSlow });
    }
  }, [mode, lastPrice]);

  // AI 분석 마커(차트 위에 "그림"처럼 남겨 신뢰도를 올림)
  // - trade markers와 같은 플러그인을 쓰므로, 둘을 합쳐서 setMarkers 한다.
  useEffect(() => {
    if (mode !== 'candles') return;
    if (!markersApiRef.current) return;

    const tradeMarkers = (markers || []).map(x => ({
      time: x.time as UTCTimestamp,
      color: x.color,
      position: x.position,
      shape: x.shape,
      text: x.text,
    }));

    const aiMarkers = [];
    // 분석 마커는 "마지막 봉" 기준으로 찍어서 차트에서 항상 보이게 한다.
    // (analysis.time은 3m 마감봉 기준이라 1m 차트 봉과 어긋나기 쉬움)
    const lastT = lastBarRef.current?.time;
    if (lastT) {
      const trend = String(overlays.trend || 'range');
      const trendKo = trend === 'up' ? '상승' : (trend === 'down' ? '하락' : '횡보');
      const lconf = Number.isFinite(Number(overlays.longConf)) ? Math.max(0, Math.min(1, Number(overlays.longConf))) : 0;
      const sconf = Number.isFinite(Number(overlays.shortConf)) ? Math.max(0, Math.min(1, Number(overlays.shortConf))) : 0;
      const strength = Number.isFinite(Number(overlays.strength)) ? Number(overlays.strength) : 0;

      const stale = (aiAgeSec !== null && aiAgeSec >= 240);
      const staleTag = stale ? ' · 업데이트 지연' : '';
      const warmTag = (!isTelemetryWarm && derived.strength > 0) ? ' · 워밍업(추정치 참고 가능)' : '';
      const txt = `AI ${trendKo} · 롱 ${pctText(lconf)} / 숏 ${pctText(sconf)} · 강도 ${strength.toFixed(2)}${staleTag}${warmTag}`;
      aiMarkers.push({
        time: lastT as UTCTimestamp,
        position: 'aboveBar' as const,
        color: trend === 'down'
          ? (stale ? 'rgba(251,113,133,0.55)' : 'rgba(251,113,133,0.95)')
          : (trend === 'up'
            ? (stale ? 'rgba(52,211,153,0.55)' : 'rgba(52,211,153,0.95)')
            : (stale ? 'rgba(148,163,184,0.55)' : 'rgba(148,163,184,0.90)')),
        shape: 'square' as const,
        text: txt,
      });
    }

    const merged = [...tradeMarkers, ...aiMarkers];
    // 너무 많으면 렌더링이 버벅이므로 상한을 둔다.
    const clipped = merged.slice(-260);
    markersApiRef.current.setMarkers(clipped as any);
  }, [mode, markers, analysis, candles, overlays.trend, overlays.longConf, overlays.shortConf, overlays.strength, aiAgeSec, isTelemetryWarm, derived.strength]);

  return (
    <div className="w-full h-full min-h-[220px] rounded-[16px] border border-emerald-500/10 bg-gradient-to-b from-white/5 to-transparent p-3 relative overflow-hidden">
      {/* overlay */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 text-[10px] font-mono">
        {/*
          오버레이 표기 규칙:
          - 한국어 라벨
          - 핵심 값(신뢰도/강도/추세/리스크/신호)만 압축 표기
        */}
        <span className="px-2 py-1 rounded-full border border-white/10 bg-black/20 text-slate-200">
          {mode === 'candles' ? `${symbol ?? 'BTCUSDT'} • ${interval ?? '1m'}` : '자산 곡선'}
        </span>
        {mode === 'candles' && (
          <span className="px-2 py-1 rounded-full border border-white/10 bg-black/20 text-slate-200">
            분석 업데이트 {aiAgeSec === null ? '—' : `${aiAgeSec}s 전`}
          </span>
        )}
        {!isTelemetryWarm && mode === 'candles' && (
          <span className="px-2 py-1 rounded-full border border-amber-500/20 bg-amber-500/10 text-amber-200">
            워밍업: AI ATR/강도 계산 중
          </span>
        )}
        <span className="px-2 py-1 rounded-full border border-emerald-500/15 bg-emerald-500/5 text-emerald-200">
          롱 {pctText(Math.max(0, Math.min(1, overlays.longConf)))}
        </span>
        <span className="px-2 py-1 rounded-full border border-rose-500/15 bg-rose-500/5 text-rose-200">
          숏 {pctText(Math.max(0, Math.min(1, overlays.shortConf)))}
        </span>
        <span className="px-2 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/10 text-cyan-200">
          강도 {Number.isFinite(overlays.strength) ? overlays.strength.toFixed(2) : '—'}
        </span>
        {/* 큰추세(HTF) */}
        {(overlays.trend) && (
          <span className="px-2 py-1 rounded-full border border-violet-500/20 bg-violet-500/10 text-violet-200">
            큰추세{(analysis as any)?.htfInterval ? `(${String((analysis as any).htfInterval)})` : ''} {trendKo(overlays.trend)}
          </span>
        )}
        {/* 차트(현재 interval) 추세: EMA20/50 기반 */}
        {(derived.trend) && (
          <span className="px-2 py-1 rounded-full border border-white/10 bg-white/5 text-slate-200">
            현재추세 {trendKo(derived.trend)}
            {(overlays.trend && derived.trend && overlays.trend !== derived.trend) ? ' · 큰추세와 반대' : ''}
          </span>
        )}
        {!isTelemetryWarm && derived.strength > 0 && (
          <span className="px-2 py-1 rounded-full border border-slate-500/20 bg-white/5 text-slate-200">
            차트추정 신뢰 {(Math.max(0, Math.min(1, derived.conf)) * 100).toFixed(0)}% · 강도 {derived.strength.toFixed(2)}
          </span>
        )}
        <span className="px-2 py-1 rounded-full border border-white/10 bg-white/5 text-slate-200">
          리스크 {String(overlays.risk || '')
            .replace('RISK_ON', '공격')
            .replace('RISK_OFF', '회피')
            .replace('NEUTRAL', '중립')}
        </span>
        {analysis?.signal && (
          <span className="px-2 py-1 rounded-full border border-white/10 bg-black/20 text-slate-100">
            신호 {analysis.signal}
          </span>
        )}
      </div>

      {mode === 'candles' ? (
        <div ref={containerRef} className="w-full h-full min-h-[220px]" />
      ) : (
      <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={equityData}>
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={strokeColor} stopOpacity={0.35}/>
              <stop offset="95%" stopColor={strokeColor} stopOpacity={0}/>
            </linearGradient>
          </defs>
            <CartesianGrid strokeDasharray="4 4" stroke="rgba(148,163,184,0.10)" vertical={false} />
          <XAxis 
            dataKey="time" 
              stroke="rgba(148,163,184,0.55)" 
              fontSize={11} 
            tickLine={false} 
            axisLine={false} 
            minTickGap={40}
          />
          <YAxis 
            domain={['auto', 'auto']} 
              stroke="rgba(148,163,184,0.55)" 
              fontSize={11} 
            tickLine={false} 
            axisLine={false}
            tickFormatter={(val) => `$${val}`}
            width={60}
          />
          <Tooltip
              contentStyle={{ backgroundColor: 'rgba(2,6,23,0.90)', borderColor: 'rgba(52,211,153,0.25)', color: '#E7EEF9', borderRadius: 12 }}
            itemStyle={{ color: strokeColor }}
            formatter={(value: number) => [`$${value.toFixed(2)}`, '자산']}
          />
          <Area 
            type="monotone" 
            dataKey="value" 
            stroke={strokeColor} 
              strokeWidth={2.25}
            fillOpacity={1} 
            fill="url(#colorValue)" 
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
      )}
    </div>
  );
};

export default ChartWidget;