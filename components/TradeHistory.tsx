
import React, { useEffect, useRef } from 'react';
import { TradeLogEntry, TradeAction } from '../dashboard/types';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface TradeHistoryProps {
  logs: TradeLogEntry[];
}

const TradeHistory: React.FC<TradeHistoryProps> = ({ logs }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col h-full bg-slate-900/50 border border-slate-800 rounded-lg overflow-hidden">
      <div className="p-3 border-b border-slate-800 bg-slate-900 flex justify-between items-center">
        <h3 className="font-bold text-sm text-slate-300 uppercase tracking-wider">Execution Log</h3>
        <span className="text-xs text-emerald-500 animate-pulse">● LIVE</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2 font-mono text-xs">
        {logs.length === 0 && (
          <div className="text-slate-500 text-center py-10">Waiting for market signals...</div>
        )}
        {logs.map((log) => (
          <div key={log.id} className="flex flex-col gap-1 p-2 rounded bg-slate-950/80 border border-slate-800">
            <div className="flex justify-between items-center">
              <span className="text-slate-500">{log.timestamp}</span>
              <span className={`font-bold ${
                log.action === TradeAction.BUY ? 'text-emerald-400' :
                log.action === TradeAction.SELL ? 'text-rose-500' : 'text-blue-400'
              }`}>
                {log.action} {log.asset}
              </span>
            </div>
            <div className="flex justify-between items-center">
               <span>@ ${log.price.toLocaleString()}</span>
               <span className="text-slate-400">Qty: {log.amount.toFixed(4)}</span>
            </div>
            {log.reasoning && (
              <p className="text-slate-400 italic border-l-2 border-slate-700 pl-2 mt-1">
                "{log.reasoning}"
              </p>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default TradeHistory;
